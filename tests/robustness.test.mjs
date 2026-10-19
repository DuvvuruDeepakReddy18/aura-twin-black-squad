import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {initializeModel,infer} from '../lib/model.mjs';

const read=name=>JSON.parse(readFileSync(new URL(`../data/${name}.json`,import.meta.url),'utf8'));
const model=read('model'),patients=read('patients');
initializeModel(model);

test('clock-free forecasts are invariant to shifting the absolute recording time',()=>{
  assert(!model.featureNames.some(name=>/clock|hourOfDay|mealPlan|future/i.test(name)));
  for(const patient of patients){
    const baseline=infer(patient,patient.defaultCursor);
    const shifted=structuredClone(patient);
    for(const row of shifted.series)row.timestamp=new Date(Date.parse(row.timestamp)+7*3600000).toISOString();
    const result=infer(shifted,shifted.defaultCursor);
    assert.deepEqual(result.forecast,baseline.forecast,patient.id);
    assert.equal(result.risk,baseline.risk,patient.id);
    assert.deepEqual(result.drivers,baseline.drivers,patient.id);
  }
});

test('unavailable meal plans and simulator labels are never used as prediction features',()=>{
  const patient=patients[0],baseline=infer(patient,patient.defaultCursor);
  const altered=structuredClone(patient);
  altered.mealPlan=[{timestamp:altered.series[patient.defaultCursor+6].timestamp,carbs:150}];
  altered.routine='a different schedule';
  for(const row of altered.series){row.latentMealResponse=999;row.futureGlucose=499;row.nextMealMinutes=1;}
  const result=infer(altered,patient.defaultCursor);
  assert.deepEqual(result,baseline);
});

test('legacy inference still reproduces its archived Python output',()=>{
  const legacy=read('baseline-v1/model'),cohort=read('baseline-v1/patients'),parity=read('baseline-v1/parity');
  initializeModel(legacy);
  try{
    for(const expected of parity){
      const actual=infer(cohort.find(p=>p.id===expected.id),expected.cursor);
      assert(Math.abs(actual.risk-expected.risk)<1e-10);
      for(let i=0;i<4;i++)assert(Math.abs(actual.forecast[i].glucose-expected.forecast[i])<.00051);
    }
  }finally{initializeModel(model);}
});
