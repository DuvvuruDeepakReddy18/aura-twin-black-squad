import test from 'node:test';
import assert from 'node:assert/strict';
import {publicAuthConfig} from '../lib/auth-config.mjs';
import {prefixAt, qualityAt, personalBaseline, inputsAt, perturbResearch} from '../lib/research-data.mjs';
import {createResearchService} from '../lib/research-service.mjs';
import {createSessionCodec} from '../lib/session-token.mjs';
import {verifyResearchReceipt} from '../scripts/verify_research_receipt.mjs';

// Deliberately constructed test fixture, never served as research or demo data.
const fixture = {id:'TEST-ONLY', sourceParticipantId:'TEST', ehr:{source:'test fixture'}, defaultCursor:300,
  series:Array.from({length:340},(_,i)=>({timestamp:new Date(Date.UTC(2020,0,1)+i*300000).toISOString(),glucose:100+i/100,hr:65,hrv:null}))};
const artifact = {modelVersion:'test-only-model',targetDefinition:'test target'};
const modelBytes = Buffer.from(JSON.stringify(artifact));
const stub = {infer(patient,cursor) {
  assert.equal(patient.series.length,cursor+1,'Service must physically exclude future observations');
  return {available:true,forecast:[30,60,90,120].map(minutes=>({minutes,glucose:100,lower:90,upper:110})),risk:.2,riskThreshold:.5};
}};
const build = extra => createResearchService({patients:[fixture],truth:{TEST:fixture.series.map(({timestamp,glucose})=>({timestamp,glucose}))},model:artifact,modelBytes,metrics:{},provenance:{},manifest:{},runtime:stub,...extra});

test('auth config exposes only a valid public key and never service credentials',()=>{
  assert.equal(publicAuthConfig({}).enabled,false);
  assert.equal(publicAuthConfig({AURA_SUPABASE_URL:'https://example.supabase.co',AURA_SUPABASE_PUBLISHABLE_KEY:'sb_secret_not_for_clients'}).enabled,false);
  assert.equal(publicAuthConfig({AURA_SUPABASE_URL:'https://example.supabase.co.evil.test',AURA_SUPABASE_PUBLISHABLE_KEY:'sb_publishable_abcdefghijkl'}).enabled,false);
  const result=publicAuthConfig({AURA_SUPABASE_URL:'https://example.supabase.co',AURA_SUPABASE_PUBLISHABLE_KEY:'sb_publishable_abcdefghijkl',SUPABASE_SERVICE_ROLE_KEY:'PRIVATE'});
  assert.equal(result.enabled,true);
  assert(!JSON.stringify(result).includes('PRIVATE'));
  assert.equal(result.googleEnabled,false);
});
test('prefix validation rejects future or unsorted timestamps; baseline never sees future changes',()=>{
  const changed=structuredClone(fixture);
  changed.series[301].glucose=9999;
  assert.deepEqual(personalBaseline(fixture,300),personalBaseline(changed,300));
  assert.equal(prefixAt(changed,300).series.length,301);
  changed.series[200].timestamp=changed.series[302].timestamp;
  assert.throws(()=>prefixAt(changed,300),/timestamps/);
});
test('quality describes missing data as missing rather than zero and perturbations are deterministic',()=>{
  const quality=qualityAt(fixture,300);
  assert.equal(quality.streams[2].status,'unavailable');
  assert.equal(quality.streams[2].minutesSinceObservation,null);
  const gap=perturbResearch(fixture,300,'short_gap');
  assert.equal(gap.patient.series.length,301);
  assert.equal(gap.patient.series.at(-1).glucose,null);
  assert.equal(qualityAt(gap.patient,300).streams[0].observed,22);
  assert.deepEqual(perturbResearch(fixture,300,'noise'),perturbResearch(fixture,300,'noise'));
  assert.equal(fixture.series[300].glucose,103);
});
test('input inspection includes the oldest lag endpoint and distinguishes unused context',()=>{
  const input=inputsAt(fixture,300,360);
  assert.equal(input.observations.length,73);
  assert.equal(input.observations[0].timestamp,fixture.series[228].timestamp);
  assert.equal(input.preprocessingContext.length,3);
  assert.equal(input.preprocessingContext[0].timestamp,fixture.series[225].timestamp);
  const patient={...fixture,researchContext:{hba1c:5.6,timingAssumption:'Collection time unknown.'}};
  const service=build({patients:[patient],model:{...artifact,featureNames:['glucose','lag360']}});
  const result=service.patientRoute(fixture.id,'inputs',new URLSearchParams({cursor:'300'}));
  assert.equal(result.researchContext.hba1c,5.6);
  assert.deepEqual(result.usedFeatureNames,['glucose','lag360']);
  assert.equal(result.matchedResearchContextUsed,false);
  assert.equal(result.syntheticEhrUsed,false);
});
test('summary distinguishes CGM source time from its aligned availability time',()=>{
  const patient=structuredClone(fixture);
  const sourceTimestamp=new Date(Date.parse(patient.series[300].timestamp)-7*60000).toISOString();
  patient.series[300].sourceTimestamp=sourceTimestamp;
  const summary=build({patients:[patient]}).list().patients[0];
  assert.equal(summary.latest.glucose.timestamp,sourceTimestamp);
  assert.equal(summary.latest.glucose.alignedTimestamp,patient.series[300].timestamp);
  assert.equal(summary.latest.glucose.carriedForward,true);
  assert.equal(summary.latest.glucose.minutesSinceObservation,7);
  const quality=qualityAt(patient,300);
  assert.match(quality.note,/including CGM carried forward/);
  assert.equal(quality.streams[0].minutesSinceObservation,7);
});
test('summary honors a requested replay cursor without reusing the default snapshot',()=>{
  const service=build();
  assert.equal(service.list().patients[0].prediction.cursor,300);
  const earlier=service.patientRoute(fixture.id,'summary',new URLSearchParams({cursor:'280'}));
  assert.equal(earlier.prediction.cursor,280);
  assert.equal(earlier.replayTimestamp,fixture.series[280].timestamp);
  assert.equal(service.list().patients[0].prediction.cursor,300);
});
test('research freeze survives instances, reveals original snapshot, and rejects tampered or cross-model tokens',()=>{
  const sessionCodec=createSessionCodec('c1'.repeat(32));
  const first=build({sessionCodec,now:()=>1000}).freeze({patientId:fixture.id,cursor:300});
  const second=build({sessionCodec,now:()=>2000,runtime:{infer(){throw Error('Do not rerun on reveal');}}});
  const input={challengeId:first.challengeId,challengeToken:first.challengeToken};
  const reveal=second.reveal(input);
  assert.equal(reveal.comparisons.length,4);
  assert.equal(reveal.comparisons[3].predicted,100);
  assert.equal(reveal.comparisons[3].observed,103.24);
  assert.throws(()=>second.reveal({...input,challengeToken:first.challengeToken.slice(0,-5)+'AAAAA'}));
  assert.throws(()=>build({sessionCodec,now:()=>3601000}).reveal(input),e=>e.status===410);
  assert.throws(()=>build({sessionCodec,modelBytes:Buffer.from('{}')}).reveal(input),e=>e.status===409||e.status===410);
});
test('research API accepts registered data only, bounds sensitivity and separates true observations',()=>{
  const service=build();
  assert.throws(()=>service.predict({patientId:fixture.id,patient:fixture}),/Unknown input/);
  assert.throws(()=>service.predict({patientId:'not registered'}),e=>e.status===404);
  assert.throws(()=>service.scenario({patientId:fixture.id,scenario:{glucoseOffset:100}}),/offsets/);
  assert.throws(()=>service.scenario({patientId:fixture.id,scenario:{insulin:1}}),/Unknown input/);
  const scenario=service.scenario({patientId:fixture.id,scenario:{glucoseOffset:10}});
  assert.equal(scenario.uncertaintyValidated,false);
  assert.equal(fixture.series[300].glucose,103);
  const list=service.list();
  assert.equal(list.counts.participants,1);
  assert(!('series' in list.patients[0]));
});
test('replay scores exact recorded outcomes rather than forward-filled grid values',()=>{
  const actualTime = new Date(Date.parse(fixture.series[324].timestamp) + 120000).toISOString();
  const service = build({truth:{TEST:[{timestamp:actualTime,glucose:160}]}});
  const frozen = service.freeze({patientId:fixture.id,cursor:300});
  const reveal = service.reveal({challengeId:frozen.challengeId});
  assert.equal(reveal.comparisons.length,1);
  assert.equal(reveal.comparisons[0].minutes,120);
  assert.equal(reveal.comparisons[0].observed,160);
  assert.equal(reveal.comparisons[0].observedTimestamp,actualTime);
  assert.equal(reveal.comparisons[0].absoluteError,60);
});
test('rise event keeps a clean fixed reference and separates altered-input probability',()=>{
  const target={kind:'rise',threshold:20,horizonMinutes:120,toleranceSeconds:150};
  const runtime={infer(patient,cursor) {
    const row=patient.series[cursor];
    return {...stub.infer(patient,cursor),current:{glucose:row.glucose,sourceTimestamp:row.timestamp},
      risk:row.glucose>120?.15:.4,riskThreshold:.18,alert:row.glucose<=120,eventDefinition:target};
  }};
  const service=build({runtime,truth:{TEST:[{timestamp:fixture.series[324].timestamp,glucose:140}]}});
  const challenge=service.freeze({patientId:fixture.id,cursor:300,mode:'cgm_bias'});
  const reveal=service.reveal({challengeId:challenge.challengeId});
  assert.equal(reveal.event.referenceGlucose,103);
  assert.equal(reveal.event.modelInputReferenceGlucose,133);
  assert.equal(reveal.event.risk,.4);
  assert.equal(reveal.event.perturbedRisk,.15);
  assert.equal(reveal.event.outcome,true);
  assert.equal(reveal.event.perturbedReferenceOutcome,false);
  assert.equal(reveal.event.observedChange,37);
  assert.equal(reveal.comparisons[0].persistence,133);
  const context={patients:[fixture],truth:{TEST:[{timestamp:fixture.series[324].timestamp,glucose:140}]},modelBytes,runtime};
  const payload={schemaVersion:2,challenge,reveal};
  assert.equal(verifyResearchReceipt(payload,context).verified,true);
  const changed=structuredClone(payload);
  changed.reveal.event.outcome=false;
  assert.throws(()=>verifyResearchReceipt(changed,context),/Revealed event differs/);
});
test('reveal withholds an event result when the forecast abstains',()=>{
  const runtime={infer(patient,cursor) {
    return {...stub.infer(patient,cursor),available:false,current:{glucose:null},eventDefinition:{kind:'rise',threshold:20,horizonMinutes:120}};
  }};
  const service=build({runtime});
  const challenge=service.freeze({patientId:fixture.id,cursor:300,mode:'cgm_dropout'});
  const reveal=service.reveal({challengeId:challenge.challengeId});
  assert.equal(reveal.event,null);
  assert.deepEqual(reveal.comparisons,[]);
  assert.equal(reveal.summary.mae,null);
});

test('offline research verifier detects changed inputs, forecasts and revealed outcomes',()=>{
  const service=build();
  const challenge=service.freeze({patientId:fixture.id,cursor:300,mode:'noise'});
  const payload={schemaVersion:2,challenge,reveal:service.reveal({challengeId:challenge.challengeId})};
  const context={patients:[fixture],truth:{TEST:fixture.series},modelBytes,runtime:stub};
  assert.equal(verifyResearchReceipt(payload,context).verified,true);
  for(const mutate of [
    value=>{value.challenge.prediction.forecast[0].glucose=111;},
    value=>{value.challenge.receipt.inputSHA256='0'.repeat(64);},
    value=>{value.reveal.comparisons[0].observed=222;},
    value=>{value.challenge.inputWindow[0].glucose=333;},
  ]) {
    const changed=structuredClone(payload);mutate(changed);
    assert.throws(()=>verifyResearchReceipt(changed,context),/differs|reproduce/);
  }
});
