# Local and hosted demonstration

AURA Twin is a synthetic demonstration. The hosted application accepts only the bundled synthetic patient identifiers. It is not a service for uploading or treating real patients.

The current public application is [aura-twin-black-squad.vercel.app](https://aura-twin-black-squad.vercel.app); source is in [aura-twin-black-squad on GitHub](https://github.com/DuvvuruDeepakReddy18/aura-twin-black-squad). Anonymous requests confirmed model `aura-synthetic-3.0.0`, public PDFs/MP4 and successful hosted freeze/reveal. The token-free receipt from that hosted run also passed the offline verifier. See [VERIFICATION.md](VERIFICATION.md) for completed checks and remaining limits.

## Local use

Run `npm start` with Node.js 20 or newer and open `http://localhost:4173`. The default host is `127.0.0.1`. `PORT` and `HOST` can be supplied through the shell; the application does not automatically load `.env` files.

Local Challenge Lab sessions use a bounded, process-local memory store: at most 128 sessions, with a one-hour lifetime. Restarting the server discards them. The local prediction API also accepts a schema-validated synthetic patient object for development. That capability is disabled in the hosted adapter.

## Vercel configuration

The repository includes `vercel.json`. Its build command, `node scripts/build_site.mjs`, copies `public/` and `docs/` into `dist/`. Static dashboard assets and submission documents are served from that directory. Requests under `/api/` route to the Node.js function in `api/index.mjs`, which uses the same application handler as the local server. The function includes the packaged `data/*.json` files and has a configured 30-second maximum duration.

The hosted adapter requires the deployment environment variable `AURA_CHALLENGE_KEY`. It must encode 32 cryptographically random bytes as exactly 64 hexadecimal characters. All instances in the same deployment must receive the same value. Missing or malformed keys fail closed; the adapter does not silently fall back to process memory.

Generate the secret locally and add it as a Vercel Secret environment variable for each intended environment. Environment changes apply to a new deployment; redeploy after setting or rotating the key. One way to generate an ignored local import file without displaying the key in terminal output is:

```sh
node -e "require('node:fs').writeFileSync('.env.local','AURA_CHALLENGE_KEY='+require('node:crypto').randomBytes(32).toString('hex')+'\n',{flag:'wx'})"
```

This command refuses to overwrite an existing `.env.local`. The file is excluded by `.gitignore`; it is not automatically loaded by the local application. Import the value through Vercel's environment-variable settings, then remove the temporary local file when it is no longer needed. Never put the key in source code, a receipt, a video, a public issue or documentation.

## Freeze and reveal across instances

Vercel function instances are ephemeral and may scale to zero. Process memory therefore cannot be the authority for a later reveal request. The hosted path returns an AES-256-GCM encrypted and authenticated session token containing the original frozen prediction and its recorded future comparison points. Each token uses a random 12-byte initialization vector and an authenticated application context.

Reveal decrypts and validates that snapshot. It checks the challenge identifier, one-hour expiry and current model-file hash. It never runs inference again to reconstruct a supposedly frozen prediction. Changing the deployment key invalidates older tokens. Replacing the model also invalidates a token tied to the earlier model. Start a new challenge after either change.

The browser sends the token back only to reveal the same challenge. Receipt downloads exclude it. The receipt remains an independently reproducible JSON record with raw model-file and canonical input hashes; it is not a digital signature, an independent timestamp or proof of authorship. Transport-token authentication does not change those receipt limitations. The public synthetic dataset also means the reveal workflow is not secure study blinding.

## Hosted boundaries

- The hosted prediction API rejects arbitrary patient objects and accepts only packaged synthetic patient IDs.
- The model and dataset are deployment artifacts. There is no database for patient records, clinical identity system or ingestion connector.
- Care notes remain browser-local demonstration notes; do not enter real personal or clinical information.
- Response headers include a same-origin content security policy, MIME-sniffing protection and a no-referrer policy. These controls do not constitute clinical security or privacy certification.
- Deployment logs and hosting infrastructure are operated by the hosting provider. This application is not intended to receive PHI or other confidential records.

## Verification before sharing

Run `npm test` and `npm run test:data`. Hosted-specific tests check parsed request bodies, rejection of arbitrary patient objects, freeze/reveal across separate handler instances, token tampering, expiry, changed keys, changed models and offline receipt verification after token removal.

After deployment, verify `/api/health` reports the intended model version; load the dashboard, freeze a prediction, reveal its recorded future and download a receipt. Verify the downloaded receipt locally with:

```sh
node scripts/verify_receipt.mjs path/to/receipt.json
```

Verify the public presentation, architecture PDF and video links in a signed-out browser. A successful build alone is not proof that the live model, session transport and documents are accessible. The completed checks and exact published model belong in [VERIFICATION.md](VERIFICATION.md).

Official hosting context: [Vercel function lifecycle](https://vercel.com/docs/functions), [Node.js runtime](https://vercel.com/docs/functions/runtimes/node-js) and [environment variables](https://vercel.com/docs/environment-variables). The application behavior above is defined by this repository's code, not by an implied hosting-provider validation of the model.
