import {cp, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const root = new URL('../', import.meta.url);
const output = new URL('dist/', root);
await mkdir(output, {recursive: true});
await cp(new URL('public/', root), output, {recursive: true});
await cp(new URL('docs/', root), new URL('docs/', output), {recursive: true});
console.log(`Static dashboard and submission documents prepared in ${fileURLToPath(output)}`);
