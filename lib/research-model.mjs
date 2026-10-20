// Dependency-free inference for the research model. All features use <= cursor.
const finite = value => typeof value === 'number' && Number.isFinite(value);
const mean = a => a.length ? a.reduce((x,y)=>x+y,0)/a.length : null;
const sd = a => a.length ? Math.sqrt(mean(a.map(x=>(x-mean(a))**2))) : null;
const sigmoid = x => 1/(1+Math.exp(-Math.max(-700,Math.min(700,x))));
function causalHistory(patient,cursor) {
  const history=[];let previous=null;
  for(const row of patient.series.slice(Math.max(0,cursor-75),cursor+1)) {
    const item={...row,quality:{...row.quality}};
    if(finite(row.glucose)) previous=row;
    else if(previous) {
      const source=previous.sourceTimestamp??previous.timestamp;
      const age=(Date.parse(row.timestamp)-Date.parse(source))/60000;
      if(age<=15) {
        item.glucose=previous.glucose;item.sourceTimestamp=source;
        item.quality.glucoseAgeMinutes=age;item.carriedForward=true;
      }
    }
    history.push(item);
  }
  return history.slice(-73);
}

export function researchFeatures(patient,cursor) {
  if (!Number.isInteger(cursor)||cursor<72||cursor>=patient.series.length) throw new Error('At least six hours of recorded history are required');
  const history=causalHistory(patient,cursor),last=history.at(-1);
  const f={glucose:last.glucose,glucoseAgeMinutes:last.quality?.glucoseAgeMinutes??null};
  for (const n of [15,30,60,90,120,180,360]) f[`lag${n}`]=history.at(-1-n/5).glucose;
  for (const n of [30,60,120,360]) {
    const values=history.slice(-n/5-1).map(r=>r.glucose),valid=values.filter(finite);
    const xs=values.flatMap((v,i)=>finite(v)?[i*5]:[]);
    const xm=mean(xs),ym=mean(valid);
    const denominator=xs.reduce((s,x)=>s+(x-xm)**2,0);
    Object.assign(f,{[`gMean${n}`]:ym,[`gStd${n}`]:sd(valid),
      [`gMin${n}`]:valid.length?Math.min(...valid):null,[`gMax${n}`]:valid.length?Math.max(...valid):null,
      [`gCoverage${n}`]:valid.length/values.length,
      [`gSlope${n}`]:valid.length>1?xs.reduce((s,x,i)=>s+(x-xm)*(valid[i]-ym),0)/denominator:null});
  }
  const recent=history.slice(-13).map(r=>r.glucose),diff=[];
  for(let i=1;i<recent.length;i++) if(finite(recent[i])&&finite(recent[i-1])) diff.push(recent[i]-recent[i-1]);
  f.gRiseFraction60=diff.length?diff.filter(x=>x>0).length/diff.length:null;
  f.gMeanAbsChange60=mean(diff.map(Math.abs));
  f.gAboveMean360=finite(f.glucose)&&finite(f.gMean360)?f.glucose-f.gMean360:null;
  for(const signal of ['hr','hrv']) for(const n of [30,120,360]) {
    const values=history.slice(-n/5).map(r=>r[signal]).filter(finite);
    f[`${signal}Mean${n}`]=mean(values);f[`${signal}Std${n}`]=sd(values);f[`${signal}Coverage${n}`]=values.length/(n/5);
  }
  f.researchHba1c=patient.researchContext?.hba1c??null;
  f.researchSexMale=({male:1,female:0})[patient.researchContext?.sex]??null;
  for(const name of ['age','bmi','hba1c','ldl']) {
    const item=patient.ehr?.[name],value=typeof item==='object'&&item!==null?item.value:item;
    f[`synthetic${name[0].toUpperCase()+name.slice(1)}`]=finite(value)?value:null;
  }
  return f;
}

function treePredict(ensemble,values) {
  let result=ensemble.baseline;
  for (const tree of ensemble.trees) {
    let index=0;
    for(let depth=0;depth<=tree.nodes.length;depth++) {
      const node=tree.nodes[index];
      if(node[0]===-1){result+=node[4];break;}
      const value=values[node[0]];
      index=!finite(value)?(node[5]?node[2]:node[3]):(value<=node[1]?node[2]:node[3]);
      if(depth===tree.nodes.length) throw new Error('Invalid model tree');
    }
  }
  return result;
}

export function createResearchModel(artifact) {
  if(!artifact||artifact.featureSet!=='big_ideas_history_v1'||!Array.isArray(artifact.featureNames)||
     artifact.regression?.models?.length!==4) throw new Error('Invalid research model artifact');
  const features=(patient,cursor)=>researchFeatures(patient,cursor);
  const probability=values=>artifact.classification?sigmoid(
    artifact.classification.calibrationSlope*treePredict(artifact.classification,values)+artifact.classification.calibrationIntercept):null;
  function infer(patient,cursor) {
    if(!patient||!Array.isArray(patient.series)||!Number.isInteger(cursor)||cursor<0||cursor>=patient.series.length)
      throw new Error('Invalid research patient or cursor');
    const row=patient.series[cursor],prefix=patient.series.slice(Math.max(0,cursor-72),cursor+1);
    const causal=causalHistory(patient,cursor),used=causal.at(-1);
    const recent=prefix.slice(-13),present=recent.filter(r=>finite(r.glucose));
    const missing=recent.length-present.length;
    const usesHr=artifact.featureNames.some(n=>n.startsWith('hr'));
    const outliers=prefix.filter(r=>(finite(r.glucose)&&(r.glucose<40||r.glucose>400))||
      (usesHr&&finite(r.hr)&&(r.hr<30||r.hr>220))||(usesHr&&finite(r.hrv)&&(r.hrv<0||r.hrv>500))).length;
    const previous=prefix.findLast(r=>finite(r.glucose));
    const age=previous?(Date.parse(row.timestamp)-Date.parse(previous.sourceTimestamp??previous.timestamp))/60000:null;
    const hrCoverage=recent.filter(r=>finite(r.hr)).length/recent.length;
    const hrvCoverage=recent.filter(r=>finite(r.hrv)).length/recent.length;
    const coverage=present.length/recent.length;
    const quality={score:Math.round(100*(.8*coverage+.1*hrCoverage+.1*hrvCoverage)),coverage,
      missing,stale:age===null||age>15,glucoseAgeMinutes:age,hrCoverage,hrvCoverage,outliers,
      dimensions:{cgmCoverage:coverage,hrCoverage,hrvCoverage},
      scoreDefinition:'80% recent CGM coverage +10% HR coverage +10% IBI-RMSSD coverage; data availability score, not clinical confidence'};
    let reason=null;
    if(cursor<72) reason='At least six hours of recorded history are required.';
    else if(outliers) reason='Forecast withheld because an input is outside the accepted signal range.';
    else if(!finite(used.glucose)||quality.stale||causal.slice(-13).filter(r=>finite(r.glucose)).length<10||causal.filter(r=>finite(r.glucose)).length<58)
      reason='Forecast withheld because recent CGM observations are insufficient or stale.';
    const current={glucose:used.glucose,hr:row.hr,hrv:row.hrv,activity:null,steps:null,sleep:null,
      sourceTimestamp:used.sourceTimestamp,carriedForward:used.carriedForward??false};
    const contract={predictionTimestamp:row.timestamp,forecastHorizonsMinutes:[30,60,90,120],
      target:artifact.target,inputWindowMinutes:360,inputStart:prefix[0].timestamp,
      latestUsableObservation:used.sourceTimestamp??null,latestUsedTimestamp:row.timestamp,
      dataUsed:artifact.inputSources,model:artifact.modelKind,modelVersion:artifact.modelVersion,
      split:artifact.split,nominalIntervalCoverage:.9,
      uncertainty:'Empirical residual bands from separate calibration participants. Coverage under artificial missingness is not calibrated or guaranteed.',
      timestampNote:patient.timeBasis,matchedContextTimingAssumption:patient.researchContext?.timingAssumption??null};
    const base={available:!reason,reason,modelVersion:artifact.modelVersion,modelKind:artifact.modelKind,
      timestamp:row.timestamp,current,riskThreshold:artifact.alertPolicy.threshold,eventDefinition:artifact.target,
      quality,forecast:[],risk:null,drivers:[],features:{},contract,predictionContract:contract,
      usedFeatureNames:artifact.featureNames,
      source:'Open research replay',syntheticEhrUsed:artifact.featureNames.some(n=>n.startsWith('synthetic')),
      matchedResearchContextUsed:artifact.featureNames.some(n=>n.startsWith('research'))};
    if(reason){quality.status='withheld';return base;}
    const f=features(patient,cursor),values=artifact.featureNames.map(n=>f[n]);
    const risk=probability(values);
    const warnings=[];
    for(let i=0;i<values.length;i++) {
      const range=artifact.trainingRanges[i];
      if(finite(values[i])&&range&& (values[i]<range.low||values[i]>range.high)) warnings.push(artifact.featureNames[i]);
    }
    quality.outsideTrainingRange=warnings;
    quality.status=missing||hrCoverage<.8||hrvCoverage<.5||warnings.length>3?'reduced':'good';
    quality.rangeNote='Observed feature outside train 1st–99th percentile; descriptive shift warning, not a validated OOD detector.';
    const forecast=artifact.regression.models.map((model,i)=>{
      const value=treePredict(model,values),width=artifact.regression.residualQuantiles[i];
      return {minutes:[30,60,90,120][i],value,low:value-width,high:value+width,
        glucose:value,lower:value-width,upper:value+width};
    });
    const drivers=artifact.driverGroups.map(group=>{
      const reference=values.slice();
      for(const i of group.indices) reference[i]=artifact.referenceValues[i];
      const refRisk=probability(reference);
      return {name:group.name,source:group.source,value:group.indices.length,
        contribution:risk===null?null:100*(risk-refRisk),unit:'percentage_points',
        method:'group_reference_sensitivity'};
    }).sort((a,b)=>Math.abs(b.contribution??0)-Math.abs(a.contribution??0));
    return {...base,risk,alert:risk!==null&&risk>=artifact.alertPolicy.threshold,forecast,
      features:Object.fromEntries(artifact.featureNames.map(name=>[name,f[name]])),drivers,contract,
      predictionContract:contract,driverMethod:'group_reference_sensitivity',
      explanationNote:'Risk change after replacing one feature group with training medians. Non-additive model sensitivity; not causality or SHAP.'};
  }
  return {infer,features,artifact};
}
