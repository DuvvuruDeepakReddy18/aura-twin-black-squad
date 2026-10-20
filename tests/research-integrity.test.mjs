import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {verifyResearchBundle} from '../lib/research-integrity.mjs';

const read=name=>readFileSync(new URL(`../data/research-${name}.json`,import.meta.url));
const files=Object.fromEntries(['patients','model','metrics','truth','ablations'].map(name=>[name,read(name)]));
const manifest=JSON.parse(read('manifest'));
const metrics=JSON.parse(files.metrics);

test('bundled research predictions, exact truth and all-five comparisons match the frozen evaluation',()=>{
  assert.equal(verifyResearchBundle(files,manifest,metrics),metrics.modelSHA256);
  for(const name of Object.keys(files)){
    assert.throws(()=>verifyResearchBundle({...files,[name]:Buffer.from('{}')},manifest,metrics),/differ/);
  }
});
test('protocol and source fingerprints survive checkout without silent code changes',()=>{
  const hash=data=>createHash('sha256').update(data).digest('hex');
  assert.equal(hash(read('protocol')),manifest.freeze.protocolSHA256);
  for(const [path,expected] of Object.entries(manifest.freeze.sourceSHA256)){
    const bytes=readFileSync(new URL(`../${path}`,import.meta.url));
    assert.equal(hash(bytes),expected,`Frozen source changed: ${path}`);
  }
});
