import {createHash, randomUUID} from 'node:crypto';
import {infer} from './model.mjs';

/** Synthetic robustness demonstrations, not clinical or adversarial validation. */
const MODES = Object.freeze([
  {id:'baseline',label:'Clean replay',description:'Keep the original synthetic history unchanged.'},
  {id:'short_gap',label:'10-minute CGM gap',description:'Hide the last two CGM readings; the model can use its short-gap handling.'},
  {id:'cgm_dropout',label:'30-minute CGM dropout',description:'Hide the last six CGM readings; the freshness gate should abstain.'},
  {id:'cgm_bias',label:'+30 mg/dL CGM bias',description:'Add 30 mg/dL to the last 25 CGM readings, capped at 500 mg/dL. This may pass freshness checks despite biased input.'},
]);
const HORIZONS = [30,60,90,120];
const LIMITATIONS = Object.freeze([
  'Selected-window synthetic stress demonstration, not a clinical validation study or aggregate benchmark.',
  'SHA-256 hashes identify the input and model using the declared hash encodings; they are not digital signatures or proof of independent timestamping.',
  'Future truth is an unmodified snapshot from the synthetic dataset. It is never passed to prediction; the public dataset itself is not secret.',
  'Perturbations test an assumed sensor fault. No real device behavior or clinical robustness is established.',
  'Sessions are temporary in-memory records, expire after one hour by default, and disappear on server restart or capacity eviction.',
]);
const round = n => Number(n.toFixed(3));
const average = values => values.length ? values.reduce((a,b)=>a+b,0)/values.length : null;

export class ChallengeError extends Error {
  constructor(message,status=400){super(message);this.name='ChallengeError';this.status=status;}
}

/** Sort object keys recursively; preserve chronological array order. */
export function canonicalJson(value){
  if(Array.isArray(value)) return '['+value.map(canonicalJson).join(',')+']';
  if(value && typeof value==='object') return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonicalJson(value[k])).join(',')+'}';
  if(value===undefined || (typeof value==='number'&&!Number.isFinite(value))) throw new TypeError('Canonical JSON requires finite JSON values.');
  return JSON.stringify(value);
}

export const hashCanonicalJson = value => createHash('sha256').update(canonicalJson(value),'utf8').digest('hex');

function requireBody(body,allowed){
  if(!body || typeof body!=='object' || Array.isArray(body)) throw new ChallengeError('Request must be a JSON object.');
  for(const key of Object.keys(body)) if(!allowed.includes(key)) throw new ChallengeError(`Unknown challenge input: ${key}.`);
}

function perturb(patient,cursor,mode){
  // The prediction input is physically truncated, not merely protected by a cursor convention.
  const {series,...profile}=patient;
  const copy={...structuredClone(profile),series:structuredClone(series.slice(0,cursor+1))};
  const metadata={description:MODES.find(m=>m.id===mode).description,changedPoints:0,channel:'glucose'};
  if(mode==='short_gap' || mode==='cgm_dropout'){
    const count=mode==='short_gap'?2:6;
    for(let i=Math.max(0,cursor-count+1);i<=cursor;i++){
      if(copy.series[i].glucose!==null)metadata.changedPoints++;
      copy.series[i].glucose=null;
    }
    metadata.missingMinutes=Math.min(count,cursor+1)*5;
  }
  if(mode==='cgm_bias'){
    metadata.offsetMgDl=30;
    metadata.windowMinutes=120;
    for(let i=Math.max(0,cursor-24);i<=cursor;i++){
      const original=copy.series[i].glucose;
      if(typeof original==='number'&&Number.isFinite(original)){
        copy.series[i].glucose=Math.min(500,round(original+30));
        if(copy.series[i].glucose!==original)metadata.changedPoints++;
      }
    }
  }
  return {patient:copy,metadata};
}

export function createChallengeLab({patients,model,modelFileBytes,inferPrediction=infer,now=Date.now,ttlMs=3600000,maxChallenges=128,sessionCodec=null}){
  if(!Array.isArray(patients)||!model?.modelVersion)throw new TypeError('Registered patients and a versioned model are required.');
  if(!Number.isInteger(ttlMs)||ttlMs<1||ttlMs>3600000||!Number.isInteger(maxChallenges)||maxChallenges<1||maxChallenges>128)throw new RangeError('Challenge retention must be 1–128 records and no more than one hour.');
  const registered=new Map(patients.map(p=>[p.id,p]));
  if(modelFileBytes!==undefined && !Buffer.isBuffer(modelFileBytes) && !(modelFileBytes instanceof Uint8Array))throw new TypeError('modelFileBytes must contain raw model file bytes.');
  if(modelFileBytes!==undefined && canonicalJson(JSON.parse(Buffer.from(modelFileBytes).toString('utf8')))!==canonicalJson(model))throw new TypeError('Model file bytes do not match the parsed model.');
  // HTTP receipts use raw bytes for direct sha256sum verification. In-memory unit callers may use the declared canonical fallback.
  const modelSHA256=modelFileBytes===undefined?hashCanonicalJson(model):createHash('sha256').update(modelFileBytes).digest('hex');
  const hashEncoding={model:modelFileBytes===undefined?'canonical-json-sorted-keys-v1':'raw-file-bytes',input:'canonical-json-sorted-keys-v1'};
  const sessions=new Map();
  if(sessionCodec && (typeof sessionCodec.seal!=='function'||typeof sessionCodec.open!=='function'))throw new TypeError('A session codec must provide seal and open functions.');
  const limitations=sessionCodec?LIMITATIONS.map(text=>text.startsWith('Sessions are temporary')?'The browser carries an encrypted, authenticated frozen snapshot. It expires after one hour and may be invalidated by model or key changes; it is not a clinical record.':text):LIMITATIONS;
  const purge=timestamp=>{for(const [id,entry] of sessions)if(entry.expires<=timestamp)sessions.delete(id);};

  function create(body){
    requireBody(body,['patientId','cursor','mode']);
    if(typeof body.patientId!=='string'||!body.patientId.trim()||body.patientId.length>128)throw new ChallengeError('A registered patientId is required.');
    const original=registered.get(body.patientId);
    if(!original)throw new ChallengeError('Registered patient not found.',404);
    const mode=body.mode===undefined?'baseline':body.mode;
    if(typeof mode!=='string'||!MODES.some(m=>m.id===mode))throw new ChallengeError('Mode must be baseline, short_gap, cgm_dropout, or cgm_bias.');
    const cursor=body.cursor===undefined?(original.defaultCursor??original.series.length-1):body.cursor;
    if(!Number.isInteger(cursor)||cursor<0||cursor>=original.series.length)throw new ChallengeError('Cursor must be an integer within the registered series.');
    const timestamp=now();
    purge(timestamp);
    const changed=perturb(original,cursor,mode);
    let prediction;
    try{prediction=structuredClone(inferPrediction(changed.patient,cursor,{}));}
    catch(error){throw new ChallengeError(`Challenge inference failed: ${error.message}`);}
    const cutoffTimestamp=changed.patient.series[cursor].timestamp;
    const cutoff=Date.parse(cutoffTimestamp),first=Date.parse(changed.patient.series[0].timestamp);
    const receipt={
      patientId:original.id,cursor,cutoffTimestamp,modelVersion:model.modelVersion,modelSHA256,
      inputSHA256:hashCanonicalJson({patientId:original.id,cursor,ehr:changed.patient.ehr,series:changed.patient.series}),
      hashFormat:'sha256-receipt-v1',hashEncoding:{...hashEncoding},
      featureWindow:{startTimestamp:new Date(Math.max(first,cutoff-287*300000)).toISOString(),endTimestamp:cutoffTimestamp,historyMinutes:1440,
        availableHistoryMinutes:Math.min(1440,(cutoff-first)/60000+5)},
      latestUsedTimestamp:cutoffTimestamp,createdAt:new Date(timestamp).toISOString(),expiresAt:new Date(timestamp+ttlMs).toISOString(),
      limitations:[...limitations],
    };
    // Prediction is complete before consulting future outcomes. Keep only four exact-horizon truth values.
    const futureByTime=new Map(original.series.slice(cursor+1).map(p=>[Date.parse(p.timestamp),p.glucose]));
    const truth=HORIZONS.map(minutes=>{
      const target=cutoff+minutes*60000,value=futureByTime.get(target);
      return {minutes,timestamp:new Date(target).toISOString(),observed:typeof value==='number'&&Number.isFinite(value)?value:null};
    });
    const result={challengeId:randomUUID(),mode,modeLabel:MODES.find(m=>m.id===mode).label,perturbation:changed.metadata,prediction,receipt,
      revealAvailable:truth.some(p=>p.observed!==null)};
    const entry={result:structuredClone(result),truth:structuredClone(truth),expires:timestamp+ttlMs};
    if(sessionCodec) result.challengeToken=sessionCodec.seal(entry);
    else {
      while(sessions.size>=maxChallenges)sessions.delete(sessions.keys().next().value);
      sessions.set(result.challengeId,entry);
    }
    return structuredClone(result);
  }

  function reveal(body){
    requireBody(body,['challengeId','challengeToken']);
    if(typeof body.challengeId!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(body.challengeId))throw new ChallengeError('A valid challengeId from a frozen prediction is required.');
    let entry;
    if(sessionCodec){
      try{entry=sessionCodec.open(body.challengeToken);}catch{throw new ChallengeError('Frozen challenge token is missing or invalid. Freeze a new prediction.',400);}
      if(entry?.result?.challengeId!==body.challengeId)throw new ChallengeError('Token does not belong to this frozen challenge.',400);
      if(entry.result.receipt?.modelSHA256!==modelSHA256)throw new ChallengeError('The model changed after this prediction was frozen. Freeze a new prediction.',409);
      if(!Number.isFinite(entry.expires)||!Array.isArray(entry.truth))throw new ChallengeError('Invalid frozen challenge snapshot.',400);
    }else entry=sessions.get(body.challengeId);
    if(!entry)throw new ChallengeError('Challenge not found. It may have expired, been evicted, or the server may have restarted.',404);
    if(entry.expires<=now()){sessions.delete(body.challengeId);throw new ChallengeError('Challenge expired. Freeze a new prediction before revealing.',410);}
    const {result,truth}=entry;
    const prediction=result.prediction;
    const comparisons=[];
    if(!prediction.abstained){
      for(const observed of truth){
        const frozen=prediction.forecast.find(p=>p.minutes===observed.minutes);
        if(observed.observed===null||!frozen)continue;
        const persistence=prediction.current.glucose;
        comparisons.push({...observed,predicted:frozen.glucose,lower:frozen.lower,upper:frozen.upper,
          absoluteError:round(Math.abs(frozen.glucose-observed.observed)),covered:observed.observed>=frozen.lower&&observed.observed<=frozen.upper,
          persistence,persistenceAbsoluteError:round(Math.abs(persistence-observed.observed))});
      }
    }
    const target=truth.find(p=>p.minutes===120);
    const event=!prediction.abstained&&target&&target.observed!==null?{minutes:120,thresholdMgDl:180,risk:prediction.risk,
      outcome:target.observed>=180,observed:target.observed}:null;
    const available=truth.filter(p=>p.observed!==null).length;
    return structuredClone({challengeId:result.challengeId,mode:result.mode,receipt:result.receipt,abstained:prediction.abstained,
      status:prediction.abstained?'abstained':comparisons.length?'revealed':'future_unavailable',revealAvailable:available>0,
      comparisons,summary:{availableHorizons:comparisons.length,mae:comparisons.length?round(average(comparisons.map(p=>p.absoluteError))):null,
        persistenceMae:comparisons.length?round(average(comparisons.map(p=>p.persistenceAbsoluteError))):null,
        intervalCoverage:comparisons.length?average(comparisons.map(p=>Number(p.covered))):null},event,
      unavailableHorizons:truth.filter(p=>p.observed===null).map(p=>p.minutes),
      comparisonNote:prediction.abstained?'The model abstained; there is no forecast to score.':available?'Scores describe available horizons for this selected synthetic window only. Persistence uses the same (possibly perturbed or carried-forward) current CGM.':'No exact-horizon future observations are available for this replay point.',
      limitations:[...limitations]});
  }

  return {create,reveal,modes:()=>({modes:structuredClone(MODES)})};
}
