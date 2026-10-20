import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createResearchModel,researchFeatures} from '../lib/research-model.mjs';
const root=new URL('../',import.meta.url);
const modelPath=new URL('data/research-model.json',root);
const ready=existsSync(modelPath);
const fixture=()=>({researchContext:{hba1c:5.5,sex:'female'},ehr:{},
  series:Array.from({length:160},(_,i)=>({timestamp:new Date(Date.UTC(2020,0,1)+i*300000).toISOString(),
    sourceTimestamp:new Date(Date.UTC(2020,0,1)+i*300000-120000).toISOString(),
    glucose:100+i%12,hr:70+i%3,hrv:30+i%4,quality:{glucoseAgeMinutes:2}}))});
test('research features are prefix-only and do not infer unknown sex',()=>{
  const patient=fixture();const expected=researchFeatures(patient,100);
  patient.series.splice(101);assert.deepEqual(researchFeatures(patient,100),expected);
  patient.researchContext.sex=null;assert.equal(researchFeatures(patient,100).researchSexMale,null);
});
test('research short-gap carryforward is bounded and leaves source untouched',()=>{
  const patient=fixture();
  patient.series[99].glucose=null;patient.series[100].glucose=null;
  assert.equal(researchFeatures(patient,100).glucose,patient.series[98].glucose);
  assert.equal(patient.series[100].glucose,null);
  for(let i=95;i<=100;i++)patient.series[i].glucose=null;
  assert.equal(researchFeatures(patient,100).glucose,null);
});
test('research exported model matches Python on actual development fixtures',{skip:!ready},()=>{
  const bytes=readFileSync(modelPath),artifact=JSON.parse(bytes),runtime=createResearchModel(artifact);
  const parity=JSON.parse(readFileSync(new URL('data/research-parity.json',root)));
  const patients=JSON.parse(readFileSync(new URL('data/research-patients.json',root)));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),parity.modelSHA256);
  let compared=0;
  for(const sample of parity.cases) {
    const patient=patients.find(p=>p.id===sample.patientId);
    const f=runtime.features(patient,sample.cursor);
    for(const [name,value] of Object.entries(sample.features))
      value===null?assert.equal(f[name],null):assert.ok(Math.abs(f[name]-value)<1e-8,`${name}: ${f[name]} vs${value}`);
    const actual=runtime.infer(patient,sample.cursor);
    if(!actual.available)continue;
    assert.ok(Math.abs(actual.risk-sample.risk)<1e-10);
    for(let i=0;i<4;i++)assert.ok(Math.abs(actual.forecast[i].value-sample.forecast[i])<1e-8);
    assert.deepEqual(runtime.infer({...patient,series:patient.series.slice(0,sample.cursor+1)},sample.cursor),actual);
    compared++;
  }
  assert.ok(compared>=4,'At least four valid actual research windows must match');
});
test('all five frozen research ablation models match Python',{skip:!existsSync(new URL('data/research-ablation-parity.json',root))},()=>{
  const artifacts=JSON.parse(readFileSync(new URL('data/research-ablations.json',root)));
  const parity=JSON.parse(readFileSync(new URL('data/research-ablation-parity.json',root)));
  const patients=JSON.parse(readFileSync(new URL('data/research-patients.json',root)));
  assert.equal(Object.keys(artifacts).length,5);
  for(const [key,artifact] of Object.entries(artifacts)) {
    const runtime=createResearchModel(artifact);let compared=0;
    for(const sample of parity.cases) {
      const patient=patients.find(p=>p.id===sample.patientId),actual=runtime.infer(patient,sample.cursor);
      if(!actual.available)continue;
      assert.ok(Math.abs(actual.risk-sample.models[key].risk)<1e-10,`${key} risk`);
      for(let i=0;i<4;i++)assert.ok(Math.abs(actual.forecast[i].value-sample.models[key].forecast[i])<1e-8,`${key} horizon${i}`);
      compared++;
    }
    assert.ok(compared>=4,`${key}: insufficient valid parity cases`);
  }
});
