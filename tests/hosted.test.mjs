import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {createChallengeLab} from '../lib/challenge.mjs';
import {createSessionCodec} from '../lib/session-token.mjs';
import {createAppHandler} from '../server.mjs';
import {initializeModel, infer} from '../lib/model.mjs';
import {verifyReceipt} from '../scripts/verify_receipt.mjs';

const modelBytes=readFileSync(new URL('../data/model.json',import.meta.url));
const model=JSON.parse(modelBytes), patients=JSON.parse(readFileSync(new URL('../data/patients.json',import.meta.url)));
const patient=patients[0], key='a1'.repeat(32);
initializeModel(model);
const lab=options=>createChallengeLab({patients,model,modelFileBytes:modelBytes,sessionCodec:createSessionCodec(key),...options});

test('hosted freeze survives separate instances, preserves original snapshot, and verifies offline without its token',()=>{
  const frozen=lab().create({patientId:patient.id,cursor:patient.defaultCursor});
  const receiving=lab({inferPrediction:()=>{throw new Error('Reveal must never re-run prediction.');}});
  assert.equal(frozen.challengeToken.split('.').length,4);
  assert(!frozen.challengeToken.includes(patient.id));
  const revealed=receiving.reveal({challengeId:frozen.challengeId,challengeToken:frozen.challengeToken});
  assert.equal(revealed.comparisons.length,4);
  assert.equal(revealed.comparisons[3].predicted,frozen.prediction.forecast[3].glucose);
  const {challengeToken,...exported}=frozen;
  const receipt=verifyReceipt({schemaVersion:1,challenge:exported,reveal:revealed},{patients,modelBytes});
  assert.equal(receipt.verified,true);
});

test('portable sessions reject tampering, wrong challenge, different key, model replacement and expiry',()=>{
  const frozen=lab({now:()=>1000}).create({patientId:patient.id,cursor:patient.defaultCursor});
  const input={challengeId:frozen.challengeId,challengeToken:frozen.challengeToken};
  const parts=frozen.challengeToken.split('.'); parts[2]=(parts[2][0]==='A'?'B':'A')+parts[2].slice(1);
  assert.throws(()=>lab({now:()=>1001}).reveal({...input,challengeToken:parts.join('.')}),e=>e.status===400);
  assert.throws(()=>lab().reveal({...input,challengeId:randomUUID()}),e=>e.status===400);
  assert.throws(()=>lab({sessionCodec:createSessionCodec('b2'.repeat(32))}).reveal(input),e=>e.status===400);
  assert.throws(()=>lab().reveal({challengeId:frozen.challengeId}),e=>e.status===400);
  const changedModel={...model,modelVersion:'aura-synthetic-replacement'};
  assert.throws(()=>lab({model:changedModel,modelFileBytes:Buffer.from(JSON.stringify(changedModel))}).reveal(input),e=>e.status===409);
  assert.throws(()=>lab({now:()=>3601000}).reveal(input),e=>e.status===410);
});

async function parsedRequest(handler,url,body){
  const req={method:'POST',url,headers:{'content-type':'application/json'},body};
  let status,content;
  const res={headersSent:false,writeHead(code){status=code;this.headersSent=true;},end(value){content=JSON.parse(value);}};
  await handler(req,res);
  return {status,content};
}

test('hosted handler accepts Vercel parsed requests while rejecting arbitrary patient uploads and malformed JSON',async()=>{
  const handler=createAppHandler({sessionKey:key,allowExternalPatients:false});
  const response=await parsedRequest(handler,'/api/predict',{patientId:patient.id,cursor:patient.defaultCursor});
  assert.equal(response.status,200);
  assert.equal(response.content.risk,infer(patient,patient.defaultCursor).risk);
  assert.equal((await parsedRequest(handler,'/api/predict',{patient})).status,403);
  assert.equal((await parsedRequest(handler,'/api/predict',[])).status,400);
  const frozen=await parsedRequest(handler,'/api/challenge',{patientId:patient.id,cursor:patient.defaultCursor});
  const another=createAppHandler({sessionKey:key,allowExternalPatients:false});
  const revealed=await parsedRequest(another,'/api/challenge/reveal',{challengeId:frozen.content.challengeId,challengeToken:frozen.content.challengeToken});
  assert.equal(revealed.status,200);
  assert.equal(revealed.content.comparisons.length,4);
});
