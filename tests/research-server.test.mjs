import test, {before, after} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createAppServer} from '../server.mjs';
import {verifyResearchReceipt} from '../scripts/verify_research_receipt.mjs';

let server, origin, participant;
const bytes=readFileSync(new URL('../data/research-model.json',import.meta.url));
const hash=createHash('sha256').update(bytes).digest('hex');
const json=async path=>{
  const response=await fetch(origin+path);
  assert.equal(response.status,200,path);
  return response.json();
};
const post=async(path,body)=>{
  const response=await fetch(origin+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  assert.equal(response.status,200,`${path}: ${response.status}`);
  return response.json();
};
before(async()=>{
  server=createAppServer({sessionKey:'ad'.repeat(32),allowExternalPatients:false});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  origin=`http://127.0.0.1:${server.address().port}`;
  participant=(await json('/api/research/patients')).patients[0];
});
after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));});

test('research API exposes the frozen model, actual evaluation and source identities consistently',async()=>{
  const [health,metrics,manifest,card]=await Promise.all(['/api/research/health','/api/model/metrics','/api/model/audit','/api/model/card'].map(json));
  for(const record of [health,metrics,manifest,card])assert.equal(record.modelSHA256,hash);
  assert.equal(health.composite,true);
  assert.equal(metrics.testParticipants,3);
  assert.equal(card.primaryFamily,metrics.primaryFamily);
  assert.equal(card.target.definition,metrics.target.definition);
  const ids=Object.values(metrics.splits).flat();
  assert.equal(new Set(ids).size,ids.length);
  assert.equal(metrics.models.primary.windows,metrics.testWindows);
  assert.equal(metrics.models.primary.confusionMatrix.flat().reduce((s,n)=>s+n,0),metrics.testWindows);
  assert(participant.prediction.contract.dataUsed.length>0);
  assert(!('series' in participant),'The roster must not carry every full recording.');
});

test('same-cutoff ablations and scenario sensitivity keep original history unchanged',async()=>{
  const input={patientId:participant.id,cursor:participant.defaultCursor};
  const original=await post('/api/research/predict',input);
  const ablation=await post('/api/research/ablation/predict',input);
  assert.equal(Object.keys(ablation.models).length,5);
  const primary=ablation.models[ablation.primaryFamily];
  assert.deepEqual(primary.forecast,original.forecast);
  assert.equal(primary.risk,original.risk);
  for(const output of Object.values(ablation.models)){
    assert.equal(output.contract.predictionTimestamp,original.contract.predictionTimestamp);
    assert(Date.parse(output.contract.latestUsedTimestamp)<=Date.parse(output.contract.predictionTimestamp));
  }
  const scenario=await post('/api/research/scenario',{...input,scenario:{glucoseOffset:10,hrOffset:5}});
  assert.equal(scenario.uncertaintyValidated,false);
  assert.deepEqual(scenario.baseline.forecast,original.forecast);
  assert.deepEqual((await post('/api/research/predict',input)).forecast,original.forecast);
  const inputs=await json(`/api/research/patients/${participant.id}/inputs?cursor=${participant.defaultCursor}`);
  assert(inputs);
});

test('hosted research replay supports encrypted freeze/reveal and offline reproduction',async()=>{
  const challenge=await post('/api/research/challenge',{patientId:participant.id,cursor:participant.defaultCursor,mode:'short_gap'});
  assert(challenge.challengeToken);
  const reveal=await post('/api/research/challenge/reveal',{challengeId:challenge.challengeId,challengeToken:challenge.challengeToken});
  const {challengeToken,...exported}=challenge;
  const data=name=>JSON.parse(readFileSync(new URL(`../data/research-${name}.json`,import.meta.url)));
  const verified=verifyResearchReceipt({schemaVersion:2,challenge:exported,reveal},{
    patients:data('patients'),truth:data('truth'),modelBytes:bytes,
  });
  assert.equal(verified.verified,true);
  assert(reveal.comparisons.every(row=>Date.parse(row.observedTimestamp)>Date.parse(challenge.receipt.cutoffTimestamp)));
});

test('research input boundary rejects injected records and undeclared scenario inputs',async()=>{
  for(const [path,body] of [
    ['/api/research/predict',{patientId:participant.id,patient:{}}],
    ['/api/research/predict',{patientId:participant.id,cursor:-1}],
    ['/api/research/scenario',{patientId:participant.id,scenario:{insulin:2}}],
    ['/api/research/challenge',{patientId:participant.id,mode:'invented'}],
  ]){
    const response=await fetch(origin+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    assert.equal(response.status,400,path);
  }
});
