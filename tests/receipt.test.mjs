import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {initializeModel} from '../lib/model.mjs';
import {createChallengeLab} from '../lib/challenge.mjs';
import {verifyReceipt} from '../scripts/verify_receipt.mjs';

const modelBytes=readFileSync(new URL('../data/model.json',import.meta.url));
const model=JSON.parse(modelBytes),patients=JSON.parse(readFileSync(new URL('../data/patients.json',import.meta.url)));
initializeModel(model);
function example(mode='baseline',reveal=true) {
  const lab=createChallengeLab({patients,model,modelFileBytes:modelBytes});
  const challenge=lab.create({patientId:patients[0].id,mode});
  const observed=reveal?lab.reveal({challengeId:challenge.challengeId}):null;
  return {schemaVersion:1,challenge,reveal:observed};
}

test('offline verifier reproduces clean, gap, dropout and biased exports',()=>{
  for(const mode of ['baseline','short_gap','cgm_dropout','cgm_bias']) {
    assert.equal(verifyReceipt(example(mode),{patients,modelBytes}).verified,true);
    assert.equal(verifyReceipt(example(mode,false),{patients,modelBytes}).revealVerified,false);
  }
});

test('offline verifier detects changed inputs, predictions, outcomes and model files',()=>{
  const options={patients,modelBytes};
  let changed=example();changed.challenge.prediction.forecast[0].glucose+=1;
  assert.throws(()=>verifyReceipt(changed,options),/Frozen prediction/);
  changed=example();changed.challenge.receipt.inputSHA256='0'.repeat(64);
  assert.throws(()=>verifyReceipt(changed,options),/inputSHA256/);
  changed=example();changed.reveal.comparisons[0].observed+=1;
  assert.throws(()=>verifyReceipt(changed,options),/Revealed comparisons/);
  changed=example();changed.reveal.challengeId='different';
  assert.throws(()=>verifyReceipt(changed,options),/different challenge/);
  changed=example();changed.challenge.receipt.cursor+=1;
  assert.throws(()=>verifyReceipt(changed,options),/cursor does not match/);
  changed=example();delete changed.challenge.mode;
  assert.throws(()=>verifyReceipt(changed,options),/Frozen mode/);
  changed=example();
  assert.throws(()=>verifyReceipt(changed,{...options,modelBytes:Buffer.concat([modelBytes,Buffer.from(' ')])}),/Model file fingerprint/);
});
