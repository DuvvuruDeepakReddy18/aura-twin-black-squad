/** Transparent, browser/Node-compatible inference; no packages, network, or future observations. */
let model;
const CHANNELS = ['glucose', 'hr', 'hrv', 'steps', 'sleep'];
const STATIC = ['age', 'bmi', 'hba1c', 'ldl', 'diabetesYears'];
const bounds = {glucose:[40,500],hr:[25,240],hrv:[1,250],steps:[0,1500],sleep:[0,1]};
const finite = n => typeof n === 'number' && Number.isFinite(n);
const round = (n, digits=3) => Number(n.toFixed(digits));
const mean = a => a.reduce((s,v)=>s+v,0)/a.length;
const sum = a => a.reduce((s,v)=>s+v,0);
const sigmoid = x => 1/(1+Math.exp(-Math.max(-700,Math.min(700,x))));

export function initializeModel(value) {
  if (!value || !Array.isArray(value.featureNames) || value.featureNames.length !== value.mean?.length || value.featureNames.length !== value.scale?.length || !value.regression || !value.classification) {
    throw new TypeError('Invalid model artifact. Load data/model.json before inference.');
  }
  model = value;
  return model.modelVersion;
}

export function validatePatient(patient) {
  const errors = [], warnings = [];
  if (!patient || typeof patient !== 'object' || Array.isArray(patient)) return {valid:false,errors:['Patient must be an object.'],warnings};
  if (typeof patient.id !== 'string' || !patient.id.trim()) errors.push('Patient ID is required.');
  const ranges = {age:[18,100],bmi:[12,65],hba1c:[3,18],ldl:[20,400],diabetesYears:[0,80]};
  for (const name of STATIC) {
    const val=patient.ehr?.[name], [low,high]=ranges[name];
    if (!finite(val) || val<low || val>high) errors.push(`EHR ${name} must be a finite number between ${low} and ${high}.`);
  }
  if (!Array.isArray(patient.series) || patient.series.length === 0) errors.push('A nonempty wearable series is required.');
  else {
    if (patient.series.length > 100000) errors.push('Series exceeds 100,000 points.');
    let previous=-Infinity, missing=0;
    for (let i=0;i<patient.series.length;i++) {
      const row=patient.series[i];
      if (!row || typeof row !== 'object') {errors.push(`Series row ${i} must be an object.`);break;}
      const isoTimestamp=typeof row.timestamp==='string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(row.timestamp);
      const t=isoTimestamp ? Date.parse(row.timestamp) : NaN;
      if (!Number.isFinite(t) || t<=previous) {errors.push(`Series timestamps must be valid and strictly increasing (row ${i}).`);break;}
      if (Number.isFinite(previous) && (t-previous)%300000 !== 0) {errors.push(`Series timestamps must follow a 5-minute grid (row ${i}).`);break;}
      previous=t;
      for (const c of CHANNELS) {
        if (row[c] === null || row[c] === undefined) {missing++;continue;}
        if (!finite(row[c]) || row[c]<bounds[c][0] || row[c]>bounds[c][1] || (c==='sleep' && row[c]!==0 && row[c]!==1)) {
          errors.push(`Invalid ${c} at row ${i}; expected ${bounds[c].join(' to ')}.`);
          break;
        }
      }
      if (errors.length>12) break;
    }
    if (missing) warnings.push(`${missing} missing channel values; short gaps are forward-filled and quality may trigger abstention.`);
    if (patient.series.length < 288) warnings.push('At least 24 hours of history is required for a prediction.');
  }
  return {valid:errors.length===0,errors,warnings};
}

function extract(patient, cursor) {
  const series=patient.series, end=Date.parse(series[cursor].timestamp), start=end-287*300000;
  const available=series.slice(0,cursor+1); // This is the only series slice used for features.
  const last={glucose:120,hr:70,hrv:40,steps:0,sleep:0};
  const seen={}, values=[], raw=[];
  let index=0;
  for (let t=start;t<=end;t+=300000) {
    let exact;
    while(index<available.length && Date.parse(available[index].timestamp)<=t) {
      const row=available[index++], rt=Date.parse(row.timestamp);
      if(rt===t) exact=row;
      for(const c of CHANNELS) if(finite(row[c])) {last[c]=row[c];seen[c]=rt;}
    }
    // Missing interval counts (steps/sleep) are imputed as zero; continuous vitals forward-fill.
    values.push({...last,steps:finite(exact?.steps)?exact.steps:0,sleep:finite(exact?.sleep)?exact.sleep:0});
    raw.push(exact || {});
  }
  const recentRaw=raw.slice(-25);
  const missingCount=sum(recentRaw.map(p=>CHANNELS.filter(c=>!finite(p[c])).length));
  const missing=missingCount/(recentRaw.length*CHANNELS.length);
  const stale=Object.fromEntries(CHANNELS.map(c=>[c,seen[c]===undefined ? null : (end-seen[c])/60000]));
  const historicalMissing=sum(raw.map(p=>CHANNELS.filter(c=>!finite(p[c])).length))/(raw.length*CHANNELS.length);
  const historyMinutes=(end-Date.parse(available[0].timestamp))/60000+5;
  const reasons=[];
  if(historyMinutes<1440) reasons.push('At least 24 hours of history is required.');
  if(stale.glucose===null || stale.glucose>15) reasons.push('CGM is missing or more than 15 minutes stale.');
  if(missing>.2) reasons.push('More than 20% of recent wearable values are missing.');
  if(historicalMissing>.2) reasons.push('More than 20% of the 24-hour wearable history is missing.');
  if(['hr','hrv'].some(c=>stale[c]===null || stale[c]>60)) reasons.push('Heart-rate or HRV channel is more than 60 minutes stale.');
  const g=values.slice(-25).map(p=>p.glucose), recent=values.slice(-12), now=values.at(-1);
  const average=mean(g), hour=new Date(end).getUTCHours()+new Date(end).getUTCMinutes()/60;
  const f=Object.fromEntries(STATIC.map(k=>[k,patient.ehr[k]]));
  Object.assign(f,{glucose:now.glucose,lag30:g.at(-7),lag60:g.at(-13),lag120:g[0],
    mean120:average,std120:Math.sqrt(mean(g.map(v=>(v-average)**2))),slope30:(now.glucose-g.at(-7))/30,slope60:(now.glucose-g.at(-13))/60,
    hrMean60:mean(recent.map(p=>p.hr)),hrvMean60:mean(recent.map(p=>p.hrv)),steps60:sum(recent.map(p=>p.steps)),
    steps24h:sum(values.map(p=>p.steps)),sleep24h:sum(values.map(p=>p.sleep))/12});
  for(let k=1;k<=4;k++) {
    f[`clock${k}Sin`]=Math.sin(k*2*Math.PI*hour/24);
    f[`clock${k}Cos`]=Math.cos(k*2*Math.PI*hour/24);
    for(const s of ['Sin','Cos']) f[`hba1cClock${k}${s}`]=(f.hba1c-6.5)*f[`clock${k}${s}`];
  }
  f.hba1cGlucose=(f.hba1c-6.5)*(now.glucose-120);
  f.hba1cSlope=(f.hba1c-6.5)*f.slope30;
  return {features:f,current:{glucose:now.glucose,hr:now.hr,hrv:now.hrv,steps:f.steps24h,sleep:round(f.sleep24h,2),timestamp:series[cursor].timestamp},
    quality:{score:Math.round(100*(1-Math.max(missing,historicalMissing))),missing:round(missing),historicalMissing:round(historicalMissing),
      stale,status:reasons.length?'insufficient':missing>0||historicalMissing>0?'degraded':'good',reasons,
      note:'Quality is relative to the selected replay time, not wall-clock time.'},abstained:reasons.length>0};
}

function groupedDrivers(features,z) {
  const groups=new Map();
  for(let i=0;i<model.featureNames.length;i++) {
    const feature=model.featureNames[i];
    let name,source,value;
    if(STATIC.includes(feature)){name={age:'Age',bmi:'Body mass index',hba1c:'HbA1c history',ldl:'LDL history',diabetesYears:'Diabetes history'}[feature];source='EHR';value=features[feature];}
    else if(feature.startsWith('hba1c')){name='EHR × wearable interaction';source='Fused';value=features.hba1c;}
    else if(feature.startsWith('clock')){name='Daily timing pattern';source='Wearable';value='Synthetic daily rhythm';}
    else if(feature.startsWith('hrv')){name='Heart-rate variability';source='Wearable';value=round(features.hrvMean60,1);}
    else if(feature.startsWith('hr')){name='Heart rate';source='Wearable';value=round(features.hrMean60,1);}
    else if(feature.startsWith('steps')){name='Activity history';source='Wearable';value=features.steps24h;}
    else if(feature.startsWith('sleep')){name='Sleep history';source='Wearable';value=round(features.sleep24h,1);}
    else {name='CGM level & trajectory';source='Wearable';value=features.glucose;}
    const contribution=z[i]*model.classification.coefficients[i]*model.classification.calibrationSlope;
    const entry=groups.get(name)||{name,value,contribution:0,source};entry.contribution+=contribution;groups.set(name,entry);
  }
  return [...groups.values()].sort((a,b)=>Math.abs(b.contribution)-Math.abs(a.contribution)).map(d=>({...d,contribution:round(d.contribution,4)}));
}

export function infer(patient, cursor=patient?.defaultCursor, scenario={}) {
  if(!model) throw new Error('Model not initialized. Call initializeModel(modelJson).');
  // Validation is scoped to the replay prefix too, so future values cannot affect this prediction.
  if(!Number.isInteger(cursor) || cursor<0 || cursor>=patient?.series?.length) throw new RangeError('Cursor must be a valid series index.');
  const check=validatePatient({...patient,series:patient.series.slice(0,cursor+1)});
  if(!check.valid) throw new TypeError(check.errors.join(' '));
  if(!scenario || typeof scenario!=='object' || Array.isArray(scenario)) throw new TypeError('Scenario must be an object.');
  const mealCarbs=scenario.mealCarbs??0, activityMinutes=scenario.activityMinutes??0;
  if(!finite(mealCarbs)||mealCarbs<0||mealCarbs>150||!finite(activityMinutes)||activityMinutes<0||activityMinutes>90) throw new RangeError('Scenario allows 0–150 g carbohydrate and 0–90 activity minutes.');
  const extracted=extract(patient,cursor);
  const base={...extracted,modelVersion:model.modelVersion,disclaimer:model.disclaimer};
  if(extracted.abstained) return {...base,risk:null,forecast:[],drivers:[],alert:{triggered:false,threshold:model.alertPolicy?.threshold??.5,label:'Unavailable'},
    scenario:{active:false,illustrative:true,label:'Unavailable: insufficient data',baselineRisk:null,glucoseDelta:0}};
  const z=model.featureNames.map((n,i)=>(extracted.features[n]-model.mean[i])/model.scale[i]);
  const logit=sum(z.map((v,i)=>v*model.classification.coefficients[i]))+model.classification.intercept;
  const risk=sigmoid(logit*model.classification.calibrationSlope+model.classification.calibrationIntercept);
  const active=mealCarbs>0||activityMinutes>0;
  const forecast=model.horizons.map((minutes,j)=>{
    const baseline=sum(z.map((v,i)=>v*model.regression.coefficients[j][i]))+model.regression.intercepts[j];
    const delta=(mealCarbs*.55-activityMinutes*.3)*(minutes/60)*Math.exp(1-minutes/60);
    const glucose=baseline+delta, width=model.interval.halfWidths[j];
    return {minutes,glucose:round(glucose),lower:round(glucose-width),upper:round(glucose+width),baseline:round(baseline),illustrative:active};
  });
  const threshold=model.alertPolicy?.threshold??.5;
  return {...base,risk,forecast,drivers:groupedDrivers(extracted.features,z),
    driverExplanation:'Additive contributions to calibrated log-odds relative to training feature means; associations, not causal effects.',
    alert:{triggered:risk>=threshold,threshold,label:risk>=threshold?'Review suggested':'Below review threshold'},
    scenario:{active,illustrative:true,label:active?'Illustrative sensitivity; baseline risk unchanged':'Baseline prediction',baselineRisk:risk,
      glucoseDelta:round(forecast.at(-1).glucose-forecast.at(-1).baseline),
      note:'Arithmetic illustration only, not a trained causal model or treatment recommendation. Shifted bands have no measured scenario coverage.'}};
}
