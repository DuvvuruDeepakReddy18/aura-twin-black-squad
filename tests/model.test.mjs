import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {initializeModel,infer,validatePatient} from '../lib/model.mjs';
const read=name=>JSON.parse(readFileSync(new URL(`../data/${name}.json`,import.meta.url),'utf8'));
const model=read('model'), patients=read('patients'), parity=read('parity'), metrics=read('metrics');
initializeModel(model);
const patient=patients[0],cursor=patient.defaultCursor;

test('all exported display patients are wholly synthetic and held out',()=>{
  const sets=Object.values(metrics.splits).map(ids=>new Set(ids));
  assert.equal(sets[0].size+sets[1].size+sets[2].size,metrics.cohort.patients);
  for(let a=0;a<sets.length;a++)for(let b=a+1;b<sets.length;b++)assert.equal([...sets[a]].filter(id=>sets[b].has(id)).length,0);
  for(const p of patients){assert.equal(p.synthetic,true);assert(sets[2].has(p.id));assert.equal(validatePatient(p).valid,true);}
});

test('JS features, regression, and calibrated probabilities match trained Python pipeline',()=>{
  for(const expected of parity){
    const actual=infer(patients.find(p=>p.id===expected.id),expected.cursor);
    for(const name of model.featureNames)assert(Math.abs(actual.features[name]-expected.features[name])<1e-8,`${name} disagrees for ${expected.id}`);
    assert(Math.abs(actual.risk-expected.risk)<1e-10,`Probability disagrees for ${expected.id}`);
    for(let i=0;i<4;i++)assert(Math.abs(actual.forecast[i].glucose-expected.forecast[i])<.00051);
  }
});

test('future observations cannot change current output or validation',()=>{
  const original=infer(patient,cursor);
  const changed=structuredClone(patient);
  for(let i=cursor+1;i<changed.series.length;i++)changed.series[i]={timestamp:'deliberately invalid future',glucose:999999,hr:null};
  assert.deepEqual(infer(changed,cursor),original);
  const truncated={...patient,series:patient.series.slice(0,cursor+1)};
  assert.deepEqual(infer(truncated,cursor),original);
});

test('the fused prediction responds to EHR changes with the wearable stream held fixed',()=>{
  const baseline=infer(patient,cursor),changed=structuredClone(patient);
  changed.ehr.hba1c=Math.min(12,changed.ehr.hba1c+1);
  const result=infer(changed,cursor);
  assert.notEqual(result.risk,baseline.risk);
  assert.notEqual(result.forecast[3].glucose,baseline.forecast[3].glucose);
  assert.equal(result.current.glucose,baseline.current.glucose);
});

test('insufficient history or stale CGM abstains instead of returning a reassuring risk',()=>{
  const early=infer(patient,80);
  assert.equal(early.abstained,true);assert.equal(early.risk,null);assert.deepEqual(early.forecast,[]);
  const stale=structuredClone(patient);
  for(let i=cursor-4;i<=cursor;i++)stale.series[i].glucose=null;
  const result=infer(stale,cursor);
  assert.equal(result.abstained,true);assert.equal(result.risk,null);assert.equal(result.quality.stale.glucose,25);
});

test('short gaps use only past values and report degraded quality',()=>{
  const gaps=structuredClone(patient);gaps.series[cursor].glucose=null;
  const result=infer(gaps,cursor);
  assert.equal(result.abstained,false);assert.equal(result.quality.status,'degraded');
  assert.equal(result.current.glucose,patient.series[cursor-1].glucose);
  assert.equal(result.quality.stale.glucose,5);
});

test('scenario is explicitly illustrative, changes forecasts, and leaves trained risk unchanged',()=>{
  const baseline=infer(patient,cursor),sensitivity=infer(patient,cursor,{mealCarbs:45,activityMinutes:15});
  assert.equal(sensitivity.scenario.illustrative,true);assert.equal(sensitivity.scenario.active,true);
  assert.equal(sensitivity.risk,baseline.risk);assert(sensitivity.forecast[3].glucose>baseline.forecast[3].glucose);
  assert.equal(baseline.scenario.active,false);assert.throws(()=>infer(patient,cursor,{mealCarbs:-4}),RangeError);
});

test('alerts use the frozen validation threshold and residual intervals cover the requested horizon',()=>{
  const result=infer(patient,cursor);
  assert.equal(result.alert.threshold,metrics.models.fused.alertPolicy.threshold);
  assert.equal(result.alert.triggered,result.risk>=result.alert.threshold);
  assert.deepEqual(result.forecast.map(p=>p.minutes),[30,60,90,120]);
  for(const point of result.forecast)assert(point.lower<point.glucose && point.upper>point.glucose);
  assert.equal(model.event.horizonMinutes,120);assert.equal(model.event.thresholdMgDl,180);
});

test('malformed input is rejected before model arithmetic',()=>{
  const invalid=structuredClone(patient);invalid.ehr.hba1c='7.2';
  assert.equal(validatePatient(invalid).valid,false);assert.throws(()=>infer(invalid,cursor),TypeError);
  assert.throws(()=>infer(patient,-1),RangeError);
  const malformed=structuredClone(patient);malformed.series[20].timestamp=malformed.series[19].timestamp;
  assert.equal(validatePatient(malformed).valid,false);
  const ambiguousTime=structuredClone(patient);ambiguousTime.series[0].timestamp='2026-10-12T00:00:00';
  assert.equal(validatePatient(ambiguousTime).valid,false);
});
