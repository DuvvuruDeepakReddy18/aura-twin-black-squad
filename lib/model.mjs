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
const populationStd = values => {const average=mean(values);return Math.sqrt(mean(values.map(value=>(value-average)**2)));};
function quantileLinear(values,probability){
  const sorted=[...values].sort((a,b)=>a-b),position=(sorted.length-1)*probability;
  const low=Math.floor(position),high=Math.ceil(position),weight=position-low,difference=sorted[high]-sorted[low];
  // Match numpy's linear quantile interpolation, including its high-weight form.
  return weight>=.5?sorted[high]-difference*(1-weight):sorted[low]+difference*weight;
}

export function initializeModel(value) {
  if (!value || !Array.isArray(value.featureNames) || !value.featureNames.length || !value.regression || !value.classification) {
    throw new TypeError('Invalid model artifact. Load data/model.json before inference.');
  }
  const revised=value.modelKind==='hist_gradient_boosting'||value.featureNames.includes('priorDayMean120');
  if (revised) {
    if (!Array.isArray(value.horizons) ||
        !Array.isArray(value.featureGroups) || value.featureNames.some(name=>!finite(value.referenceValues?.[name])) ||
        !finite(value.classification.calibrationSlope) || !finite(value.classification.calibrationIntercept)) {
      throw new TypeError('Invalid clock-free model metadata.');
    }
    if(Array.isArray(value.regression.models)){
      if(value.regression.models.length!==value.horizons.length)throw new TypeError('Tree regressors must match the forecast horizons.');
      for(const ensemble of value.regression.models)validateEnsemble(ensemble,value.featureNames.length);
    }
    if(Array.isArray(value.classification.trees))validateEnsemble(value.classification,value.featureNames.length);
  }
  if ((!Array.isArray(value.regression.models)||!Array.isArray(value.classification.trees)) &&
      (value.featureNames.length !== value.mean?.length || value.featureNames.length !== value.scale?.length)) {
    throw new TypeError('Invalid linear model preprocessing parameters.');
  }
  model = value;
  return model.modelVersion;
}

function validateEnsemble(ensemble,featureCount) {
  if(!finite(ensemble?.baseline)||!Array.isArray(ensemble.trees)||!ensemble.trees.length)throw new TypeError('Invalid tree ensemble.');
  for(const tree of ensemble.trees){
    if(!Array.isArray(tree.nodes)||!tree.nodes.length)throw new TypeError('Invalid tree nodes.');
    for(const node of tree.nodes){
      if(!Array.isArray(node)||node.length!==6||!Number.isInteger(node[0])||!finite(node[4]))throw new TypeError('Invalid tree node encoding.');
      if(node[0]===-1)continue;
      if(node[0]<0||node[0]>=featureCount||!finite(node[1])||![node[2],node[3]].every(index=>Number.isInteger(index)&&index>=0&&index<tree.nodes.length))throw new TypeError('Invalid tree split.');
    }
  }
}

/** Exported sklearn leaf values already contain the learning-rate shrinkage. */
function predictEnsemble(ensemble,input) {
  let output=ensemble.baseline;
  for(const tree of ensemble.trees){
    let index=0,visited=0;
    while(true){
      if(++visited>tree.nodes.length)throw new TypeError('Cyclic tree structure.');
      const [feature,threshold,left,right,value,missingLeft]=tree.nodes[index];
      if(feature===-1){output+=value;break;}
      const observed=input[feature];
      index=!finite(observed)?(missingLeft?left:right):observed<=threshold?left:right;
    }
  }
  return output;
}

function calibratedRisk(input) {
  const raw=Array.isArray(model.classification.trees)?predictEnsemble(model.classification,input):
    sum(input.map((value,index)=>(value-model.mean[index])/model.scale[index]*model.classification.coefficients[index]))+model.classification.intercept;
  return sigmoid(raw*model.classification.calibrationSlope+model.classification.calibrationIntercept);
}

function sensitivityDrivers(input,risk) {
  return model.featureGroups.map(group=>{
    const reference=input.slice();
    for(const name of group.features){const index=model.featureNames.indexOf(name);if(index>=0)reference[index]=model.referenceValues[name];}
    const referenceRisk=calibratedRisk(reference);
    return {name:group.name,source:group.source,value:`${group.features.length} features replaced by training medians`,
      contribution:round((risk-referenceRisk)*100,4),referenceRisk,unit:'percentage_points'};
  }).sort((a,b)=>Math.abs(b.contribution)-Math.abs(a.contribution));
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
  if(model.modelKind==='hist_gradient_boosting'||model.featureNames.includes('priorDayMean120')){
    const history=values.map(point=>point.glucose),lag=minutes=>history.at(-1-minutes/5);
    for(const minutes of [15,45,90,180,240,360])f[`lag${minutes}`]=lag(minutes);
    for(const [name,count] of [['30',7],['60',13],['360',73],['24h',288]]){
      const segment=history.slice(-count);f[`mean${name}`]=mean(segment);f[`std${name}`]=populationStd(segment);
    }
    Object.assign(f,{min120:Math.min(...g),max120:Math.max(...g),q25_120:quantileLinear(g,.25),q75_120:quantileLinear(g,.75),
      q10_24h:quantileLinear(history,.1),q50_24h:quantileLinear(history,.5),q90_24h:quantileLinear(history,.9),
      slope15:(now.glucose-lag(15))/15,slope120:(now.glucose-lag(120))/120,
      acceleration30:(now.glucose-lag(30))/30-(lag(30)-lag(60))/30,
      priorDayMean120:mean(history.slice(0,24)),
      hrSlope30:(now.hr-values.at(-7).hr)/30,hrvSlope30:(now.hrv-values.at(-7).hrv)/30,
      hrMean120:mean(values.slice(-24).map(point=>point.hr)),hrvMean120:mean(values.slice(-24).map(point=>point.hrv)),
      steps120:sum(values.slice(-24).map(point=>point.steps)),sleepLast6h:sum(values.slice(-72).map(point=>point.sleep))/12});
    for(const horizon of [30,60,90,120])f[`priorDay${horizon}`]=lag(1440-horizon);
    if(model.featureSet==='trajectory_v3'||model.featureNames.includes('olsSlope30'))addTrajectoryFeatures(f,values);
  }else{
    for(let k=1;k<=4;k++) {
      f[`clock${k}Sin`]=Math.sin(k*2*Math.PI*hour/24);
      f[`clock${k}Cos`]=Math.cos(k*2*Math.PI*hour/24);
      for(const s of ['Sin','Cos']) f[`hba1cClock${k}${s}`]=(f.hba1c-6.5)*f[`clock${k}${s}`];
    }
    f.hba1cGlucose=(f.hba1c-6.5)*(now.glucose-120);
    f.hba1cSlope=(f.hba1c-6.5)*f.slope30;
  }
  return {features:f,current:{glucose:now.glucose,hr:now.hr,hrv:now.hrv,steps:f.steps24h,sleep:round(f.sleep24h,2),timestamp:series[cursor].timestamp},
    quality:{score:Math.round(100*(1-Math.max(missing,historicalMissing))),missing:round(missing),historicalMissing:round(historicalMissing),
      stale,status:reasons.length?'insufficient':missing>0||historicalMissing>0?'degraded':'good',reasons,
      note:'Quality is relative to the selected replay time, not wall-clock time.'},abstained:reasons.length>0};
}

/** Mirrors ml/train_v3.py trajectory_features using the same imputed replay prefix. */
function addTrajectoryFeatures(f,values) {
  const glucose=values.map(point=>point.glucose),recent=glucose.slice(-25);
  const changes=segment=>segment.slice(1).map((value,index)=>value-segment[index]);
  for(const minutes of [5,10,20,25,35,40,50,75,105,150,210,300])f[`lag${minutes}`]=glucose.at(-1-minutes/5);
  for(const minutes of [30,60,120,240]){
    const segment=glucose.slice(-(minutes/5+1)),average=mean(segment),center=(segment.length-1)*2.5;
    const positions=segment.map((_,index)=>index*5-center);
    f[`olsSlope${minutes}`]=sum(segment.map((value,index)=>positions[index]*(value-average)))/sum(positions.map(value=>value*value));
  }
  f.meanDelta30_60=f.mean30-f.mean60;
  f.meanDelta60_120=f.mean60-f.mean120;
  for(const minutes of [30,60,120]){
    const differences=changes(glucose.slice(-(minutes/5+1)));
    f[`riseFraction${minutes}`]=mean(differences.map(value=>Number(value>0)));
    f[`meanAbsChange${minutes}`]=mean(differences.map(Math.abs));
  }
  const last30=glucose.slice(-7),last60=glucose.slice(-13),lastChanges30=changes(last30),recentReverse=[...recent].reverse();
  Object.assign(f,{fallFraction60:mean(changes(last60).map(value=>Number(value<0))),
    maxRise30:Math.max(...lastChanges30),maxFall30:Math.min(...lastChanges30),
    range30:Math.max(...last30)-Math.min(...last30),range60:Math.max(...last60)-Math.min(...last60),
    minutesSinceMax120:recentReverse.indexOf(Math.max(...recent))*5,minutesSinceMin120:recentReverse.indexOf(Math.min(...recent))*5,
    glucoseAboveQ10:f.glucose-f.q10_24h,glucoseAboveMedian:f.glucose-f.q50_24h,
    excessMean120:mean(recent.map(value=>Math.max(0,value-f.q10_24h))),
    timeAbove180_120:mean(recent.map(value=>Number(value>=180))),timeAbove140_120:mean(recent.map(value=>Number(value>=140)))});
  for(const name of ['hr','hrv']){
    const history=values.map(point=>point[name]);
    f[`${name}Mean15`]=mean(history.slice(-3));
    f[`${name}Mean30`]=mean(history.slice(-6));
    f[`${name}Mean24h`]=mean(history);
    f[`${name}Std24h`]=populationStd(history);
    f[`${name}Z30`]=(f[`${name}Mean30`]-f[`${name}Mean24h`])/Math.max(1,f[`${name}Std24h`]);
  }
  let lastWake=-1,lastActivity=-1;
  for(let index=0;index<values.length;index++){
    if(index>0&&values[index-1].sleep>0&&values[index].sleep===0)lastWake=index;
    if(values[index].steps>=50)lastActivity=index;
  }
  const resting=values.filter(point=>point.sleep===0&&point.steps<20),resting30=values.slice(-6).filter(point=>point.sleep===0&&point.steps<20);
  Object.assign(f,{steps15:sum(values.slice(-3).map(point=>point.steps)),steps30:sum(values.slice(-6).map(point=>point.steps)),
    sleepLast60:sum(values.slice(-12).map(point=>point.sleep))/12,
    minutesSinceWake:lastWake<0?1440:(287-lastWake)*5,minutesSinceActivity:lastActivity<0?1440:(287-lastActivity)*5,
    awakeRestingHr24h:resting.length?mean(resting.map(point=>point.hr)):f.hrMean24h,
    awakeRestingHr30:resting30.length?mean(resting30.map(point=>point.hr)):f.hrMean30,
    glucoseMinusPriorDay120:f.glucose-f.priorDay120});
  f.hrAboveResting30=f.awakeRestingHr30-f.awakeRestingHr24h;
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
  const revisedModel=model.modelKind==='hist_gradient_boosting'||model.featureNames.includes('priorDayMean120');
  const treeRegression=Array.isArray(model.regression.models),treeClassification=Array.isArray(model.classification.trees);
  const base={...extracted,modelVersion:model.modelVersion,disclaimer:model.disclaimer,
    ...(revisedModel?{modelKind:model.modelKind||'clock_free',featureSet:model.featureSet||'clock_free_v2',
      regressionKind:treeRegression?'hist_gradient_boosting':'ridge',classificationKind:treeClassification?'hist_gradient_boosting':'logistic_regression',
      driverMethod:'group_reference_sensitivity'}:{})};
  if(extracted.abstained) return {...base,risk:null,forecast:[],drivers:[],alert:{triggered:false,threshold:model.alertPolicy?.threshold??.5,label:'Unavailable'},
    scenario:{active:false,illustrative:true,label:'Unavailable: insufficient data',baselineRisk:null,glucoseDelta:0}};
  const input=model.featureNames.map(name=>extracted.features[name]);
  if(input.some(value=>!finite(value)))throw new TypeError('Model feature extraction produced a missing or non-finite input.');
  const z=treeRegression&&treeClassification?null:input.map((value,i)=>(value-model.mean[i])/model.scale[i]);
  const risk=calibratedRisk(input);
  const active=mealCarbs>0||activityMinutes>0;
  const forecast=model.horizons.map((minutes,j)=>{
    const baseline=treeRegression?predictEnsemble(model.regression.models[j],input):sum(z.map((v,i)=>v*model.regression.coefficients[j][i]))+model.regression.intercepts[j];
    const delta=(mealCarbs*.55-activityMinutes*.3)*(minutes/60)*Math.exp(1-minutes/60);
    const glucose=baseline+delta, width=model.interval.halfWidths[j];
    return {minutes,glucose:round(glucose),lower:round(glucose-width),upper:round(glucose+width),baseline:round(baseline),illustrative:active};
  });
  const threshold=model.alertPolicy?.threshold??.5;
  return {...base,risk,forecast,drivers:revisedModel?sensitivityDrivers(input,risk):groupedDrivers(extracted.features,z),
    driverExplanation:revisedModel?'Probability difference, in percentage points, after replacing one feature group with its training medians. These reference sensitivities are not additive attributions or causal effects; replacement combinations may be unrealistic.':'Additive contributions to calibrated log-odds relative to training feature means; associations, not causal effects.',
    alert:{triggered:risk>=threshold,threshold,label:risk>=threshold?'Review suggested':'Below review threshold'},
    scenario:{active,illustrative:true,label:active?'Illustrative sensitivity; baseline risk unchanged':'Baseline prediction',baselineRisk:risk,
      glucoseDelta:round(forecast.at(-1).glucose-forecast.at(-1).baseline),
      note:'Arithmetic illustration only, not a trained causal model or treatment recommendation. Shifted bands have no measured scenario coverage.'}};
}
