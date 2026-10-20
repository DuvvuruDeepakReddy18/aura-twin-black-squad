import {cp, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const root = new URL('../', import.meta.url);
const output = new URL('dist/', root);
const build = spawnSync(process.execPath, [fileURLToPath(new URL('node_modules/vite/bin/vite.js', root)), 'build', '--config', 'frontend/vite.config.js'],
  {cwd: fileURLToPath(root), stdio: 'inherit'});
if (build.status !== 0) throw new Error('Frontend build failed; publication stopped.');
await mkdir(output, {recursive: true});
await cp(new URL('public/', root), output, {recursive: true});
await cp(new URL('docs/', root), new URL('docs/', output), {recursive: true});
console.log(`Static dashboard and submission documents prepared in ${fileURLToPath(output)}`);
