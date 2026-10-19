import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {randomUUID,createHash} from 'node:crypto';
import {createChallengeLab,hashCanonicalJson} from '../lib/challenge.mjs';
import {initializeModel,infer} from '../lib/model.mjs';
import {createAppServer} from '../server.mjs';

const read=name=>JSON.parse(readFileSync(new URL(`../data/${name}.json`,import.meta.url),'utf8'));
const model=read('model'),patients=read('patients'),patient=patients[0],cursor=patient.defaultCursor;
initializeModel(model);
const make=options=>createChallengeLab({patients,model,...options});

test('baseline freezes the original inference and stable semantic input/model hashes',()=>{
  const lab=make(),input={patientId:patient.id,cursor,mode:'baseline'},first=lab.create(input),second=lab.create(input);
  assert.notEqual(first.challengeId,second.challengeId);
  assert.deepEqual(first.prediction,infer(patient,cursor,{}));
  assert.equal(first.receipt.inputSHA256,second.receipt.inputSHA256);
  assert.equal(first.receipt.modelSHA256,hashCanonicalJson(model));
  assert.equal(first.receipt.inputSHA256,hashCanonicalJson({patientId:patient.id,cursor,ehr:patient.ehr,series:patient.series.slice(0,cursor+1)}));
  assert(Date.parse(first.receipt.latestUsedTimestamp)<=Date.parse(first.receipt.cutoffTimestamp));
  assert.equal(hashCanonicalJson({b:2,a:1}),hashCanonicalJson({a:1,b:2}));
});

test('future values are physically excluded from inference, input hashes, and the frozen prediction',()=>{
  const altered=structuredClone(patients);
  const originalFreeze=make().create({patientId:patient.id,cursor});
  for(let i=cursor+1;i<altered[0].series.length;i++)altered[0].series[i].glucose=300;
  let calls=0;
  const lab=createChallengeLab({patients:altered,model,inferPrediction:(prefix,index,scenario)=>{
    calls++;assert.equal(prefix.series.length,cursor+1);return infer(prefix,index,scenario);
  }});
  const frozen=lab.create({patientId:patient.id,cursor});
  assert.deepEqual(frozen.prediction,originalFreeze.prediction);
  assert.equal(frozen.receipt.inputSHA256,originalFreeze.receipt.inputSHA256);
  const revealed=lab.reveal({challengeId:frozen.challengeId});
  assert.equal(calls,1,'Reveal must not invoke inference again.');
  assert(revealed.comparisons.every(p=>p.observed===300));
});

test('a reveal scores frozen values against unmodified future truth without rerunning inference',()=>{
  const local=structuredClone(patients),lab=createChallengeLab({patients:local,model});
  const frozen=lab.create({patientId:patient.id,cursor});
  const first=lab.reveal({challengeId:frozen.challengeId});
  frozen.prediction.forecast[0].glucose=9999;
  frozen.receipt.patientId='tampered response';
  local[0].series[cursor+6].glucose=499;
  first.comparisons[0].predicted=9999;
  const again=lab.reveal({challengeId:frozen.challengeId});
  assert.equal(again.comparisons[0].observed,patient.series[cursor+6].glucose);
  assert.equal(again.comparisons[0].predicted,infer(patient,cursor).forecast[0].glucose);
  assert.equal(again.receipt.patientId,patient.id);
  assert.equal(again.summary.availableHorizons,4);
  assert.equal(again.event.outcome,patient.series[cursor+24].glucose>=180);
  assert.equal(again.event.risk,infer(patient,cursor).risk);
});

test('gap, dropout, and bias modes perturb only historical CGM and use the same safety behavior',()=>{
  const before=JSON.stringify(patients),lab=make();
  const clean=lab.create({patientId:patient.id,cursor}),short=lab.create({patientId:patient.id,cursor,mode:'short_gap'});
  assert.equal(short.prediction.abstained,false);assert.equal(short.prediction.quality.stale.glucose,10);
  assert.equal(short.prediction.current.glucose,patient.series[cursor-2].glucose);assert.equal(short.perturbation.changedPoints,2);
  const dropout=lab.create({patientId:patient.id,cursor,mode:'cgm_dropout'});
  assert.equal(dropout.prediction.abstained,true);assert.equal(dropout.prediction.risk,null);assert.equal(dropout.prediction.quality.stale.glucose,30);
  const revealed=lab.reveal({challengeId:dropout.challengeId});
  assert.deepEqual(revealed.comparisons,[]);assert.equal(revealed.summary.mae,null);assert.equal(revealed.event,null);
  const bias=lab.create({patientId:patient.id,cursor,mode:'cgm_bias'});
  assert.equal(bias.prediction.current.glucose,clean.prediction.current.glucose+30);assert.equal(bias.perturbation.changedPoints,25);
  assert.notEqual(bias.receipt.inputSHA256,clean.receipt.inputSHA256);
  assert.deepEqual(lab.reveal({challengeId:bias.challengeId}).comparisons.map(p=>p.observed),lab.reveal({challengeId:clean.challengeId}).comparisons.map(p=>p.observed));
  assert.equal(JSON.stringify(patients),before);
});

test('missing future horizons are reported without fabricated scores or an exact-horizon event',()=>{
  const lab=make(),nearEnd=lab.create({patientId:patient.id,cursor:patient.series.length-10});
  const partial=lab.reveal({challengeId:nearEnd.challengeId});
  assert.equal(partial.summary.availableHorizons,1);assert.deepEqual(partial.unavailableHorizons,[60,90,120]);assert.equal(partial.event,null);
  const last=lab.create({patientId:patient.id,cursor:patient.series.length-1});
  assert.equal(last.revealAvailable,false);
  const empty=lab.reveal({challengeId:last.challengeId});
  assert.equal(empty.status,'future_unavailable');assert.equal(empty.summary.mae,null);assert.equal(empty.summary.intervalCoverage,null);
});

test('sessions expire, capacity is bounded, and malformed requests fail explicitly',()=>{
  let time=1000;
  const lab=make({now:()=>time,ttlMs:100,maxChallenges:2});
  const first=lab.create({patientId:patient.id}),second=lab.create({patientId:patient.id});
  lab.create({patientId:patient.id});
  assert.throws(()=>lab.reveal({challengeId:first.challengeId}),e=>e.status===404);
  time=1100;
  assert.throws(()=>lab.reveal({challengeId:second.challengeId}),e=>e.status===410);
  for(const body of [{},{patientId:patient.id,mode:'invented'},{patientId:patient.id,cursor:-1},{patientId:patient.id,cursor:null},{patientId:patient.id,cursor:1.1},{patientId:patient.id,patient:{}},{patientId:patient.id,mode:null}])assert.throws(()=>lab.create(body),e=>e.status===400);
  assert.throws(()=>lab.create({patientId:'absent'}),e=>e.status===404);
  assert.throws(()=>lab.reveal({challengeId:'not-a-uuid'}),e=>e.status===400);
  assert.throws(()=>lab.reveal({challengeId:randomUUID()}),e=>e.status===404);
  assert.throws(()=>make({maxChallenges:129}),RangeError);
});

test('HTTP Challenge Lab freezes and reveals through the existing JSON boundary',async()=>{
  const server=createAppServer();
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  const post=(path,body)=>fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  try{
    const modes=await(await fetch(base+'/api/challenge/modes')).json();assert.equal(modes.modes.length,4);
    const response=await post('/api/challenge',{patientId:patient.id,cursor,mode:'baseline'});assert.equal(response.status,200);
    const frozen=await response.json();
    const rawHash=createHash('sha256').update(readFileSync(new URL('../data/model.json',import.meta.url))).digest('hex');
    assert.equal(frozen.receipt.modelSHA256,rawHash);
    assert.deepEqual(frozen.receipt.hashEncoding,{model:'raw-file-bytes',input:'canonical-json-sorted-keys-v1'});
    const stressResponse=await fetch(base+'/api/stress');assert.equal(stressResponse.status,200);
    const stress=await stressResponse.json();assert.equal(stress.modelSHA256,rawHash);assert.equal(stress.cases.length,4);
    const reveal=await post('/api/challenge/reveal',{challengeId:frozen.challengeId});assert.equal(reveal.status,200);
    assert.equal((await reveal.json()).summary.availableHorizons,4);
    assert.equal((await post('/api/challenge',{patientId:patient.id,mode:'unknown'})).status,400);
    assert.equal((await post('/api/challenge/reveal',{challengeId:'broken'})).status,400);
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
