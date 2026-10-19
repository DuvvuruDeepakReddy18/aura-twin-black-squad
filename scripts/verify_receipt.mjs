/** Offline reproducibility check; not a signature or third-party certification. */
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {initializeModel} from '../lib/model.mjs';
import {createChallengeLab} from '../lib/challenge.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));

export function verifyReceipt(payload, {patients,modelBytes}) {
  if(payload?.schemaVersion!==1||!payload.challenge?.receipt) throw new Error('Expected a version 1 Challenge lab export with a challenge and receipt.');
  const supplied=payload.challenge,receipt=supplied.receipt;
  const model=JSON.parse(modelBytes.toString('utf8'));
  const modelHash=createHash('sha256').update(modelBytes).digest('hex');
  if(receipt.modelSHA256!==modelHash) throw new Error('Model file fingerprint differs from the receipt. Use the same data/model.json as the challenge.');
  const patient=patients.find(p=>p.id===receipt.patientId);
  if(!patient) throw new Error('The receipt patient is not in the packaged synthetic cohort.');
  const cursor=patient.series.findIndex(row=>row.timestamp===receipt.cutoffTimestamp);
  if(cursor<0) throw new Error('The receipt cutoff is not in this patient’s recorded timeline.');
  if(receipt.cursor!==cursor) throw new Error('Receipt cursor does not match its recorded cutoff.');
  initializeModel(model);
  const lab=createChallengeLab({patients,model,modelFileBytes:modelBytes});
  const reproduced=lab.create({patientId:patient.id,cursor,mode:supplied.mode});
  for(const key of ['inputSHA256','modelVersion','hashFormat','hashEncoding','featureWindow','latestUsedTimestamp']) {
    if(!isDeepStrictEqual(receipt[key],reproduced.receipt[key])) throw new Error(`Receipt ${key} does not match the reproduced inputs.`);
  }
  for(const key of ['mode','prediction','perturbation','modeLabel','revealAvailable']) {
    if(!isDeepStrictEqual(supplied[key],reproduced[key])) throw new Error(`Frozen ${key} differs from a fresh offline calculation.`);
  }
  if(payload.reveal!==null && payload.reveal!==undefined) {
    const observed=payload.reveal;
    if(observed.challengeId!==supplied.challengeId) throw new Error('Reveal belongs to a different challenge.');
    if(!isDeepStrictEqual(observed.receipt,receipt)) throw new Error('Reveal receipt differs from the frozen receipt.');
    const reproducedReveal=lab.reveal({challengeId:reproduced.challengeId});
    for(const key of ['mode','abstained','status','revealAvailable','comparisons','summary','event','unavailableHorizons']) {
      if(!isDeepStrictEqual(observed[key],reproducedReveal[key])) throw new Error(`Revealed ${key} does not match the original synthetic future.`);
    }
  }
  return {verified:true,patientId:patient.id,mode:supplied.mode,cutoffTimestamp:receipt.cutoffTimestamp,
    modelSHA256:modelHash,revealVerified:payload.reveal!=null,
    note:'Inputs, frozen output and any revealed scores are reproducible from this repository. This does not authenticate the author or creation timestamp, prove secrecy of public future data, or establish clinical accuracy.'};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href) {
  try {
    if(!process.argv[2]) throw new Error('Usage: node scripts/verify_receipt.mjs "path/to/AURA-challenge.json"');
    const file=readFileSync(resolve(process.argv[2]));
    if(file.length>2_000_000) throw new Error('Receipt exceeds the 2 MB limit.');
    const result=verifyReceipt(JSON.parse(file.toString('utf8')),{patients:JSON.parse(readFileSync(resolve(root,'data/patients.json'),'utf8')),modelBytes:readFileSync(resolve(root,'data/model.json'))});
    console.log(JSON.stringify(result,null,2));
  } catch(error) {console.error(`Receipt verification failed: ${error.message}`);process.exitCode=1;}
}
