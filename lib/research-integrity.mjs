import {createHash} from 'node:crypto';

/** Refuse mixed deployments before exposing predictions or evaluation metrics. */
export function verifyResearchBundle(files, manifest, metrics) {
  const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
  const modelHash=digest(files.model);
  if (modelHash!==manifest.modelSHA256 || modelHash!==metrics.modelSHA256 || modelHash!==manifest.freeze?.modelSHA256) {
    throw Error('Research model and evaluation fingerprints differ.');
  }
  for(const name of ['patients','model','metrics','truth']) {
    const expected=manifest.artifacts?.[`research-${name}.json`]?.sha256;
    if(!expected || digest(files[name])!==expected) throw Error(`Research ${name} fingerprint differs from the evaluation manifest.`);
  }
  if(digest(files.ablations)!==manifest.freeze?.ablationsSHA256) throw Error('Research ablations differ from the frozen comparison.');
  return modelHash;
}
