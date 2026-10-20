# Local and hosted research demonstration

AURA serves bundled de-identified research observations and unrelated synthetic EHR context. It is not a clinical upload service. The current React research workspace and the historical synthetic application have separate model/API identities.

## Local build

Requires Node.js **22.12 or newer**. The configured hosted runtime is Node.js 24.

```bash
npm ci
npm run build
npm start
```

Open `http://localhost:4173`. The historical synthetic dashboard is retained at `http://localhost:4173/legacy/index.html` and must remain labelled legacy. `PORT` and `HOST` can be supplied through the shell. `npm start` and `npm run dev` load the optional ignored `.env.auth.local` file through Node's `--env-file-if-exists` option. Direct `node server.mjs` does not load that file automatically.

Current research health: `/api/research/health`. The older `/api/health` explicitly reports the legacy synthetic API and points to the research health endpoint. Do not verify a research deployment by checking only the old endpoint.

## Authentication configuration

Demo mode requires no account. Supabase integration reads only these public/provider settings:

- `AURA_SUPABASE_URL`: HTTPS project origin under `supabase.co`.
- `AURA_SUPABASE_PUBLISHABLE_KEY`: the provider's publishable browser key, never a service-role secret.
- `AURA_GOOGLE_AUTH_ENABLED`: enables the public Google action after provider configuration. It is now true in Vercel production and preview; real account-flow verification remains pending.
- `AURA_PUBLIC_AUTH_EMAIL_ENABLED`: true only after public email delivery is configured and verified. It currently remains false.

Current status: Supabase public configuration is connected and email confirmation is enabled. The Google provider is enabled, confirmed through public provider settings after credentials were saved securely. Custom SMTP is not configured. Public email sign-up and recovery are intentionally disabled until email delivery is configured; existing accounts use the real provider. Complete account-flow verification remains pending. Without valid configuration, the application reports sign-in unavailable. It must not simulate a successful login. Configure provider redirect URLs for the exact local and deployed origins and the callback/reset routes used by the frontend. Email confirmation, reset delivery and Google OAuth depend on provider setup and must be tested as real flows before being claimed complete.

The current PDFs and 23:52 video were recorded while Google was unconfigured. Their configuration description is historical; this section records the current authentication status.

Account sessions, a local browser replay trail and a server challenge session are different state boundaries. The replay trail is browser-local, bounded to 20 entries and excludes challenge transport tokens. Provider-backed identity alone does not create a clinical record database.

## Vercel build and API

`node scripts/build_site.mjs` builds the React/Vite application, copies legacy static assets and copies current submission documents into `dist/`. The repository's `vercel.json` routes `/api/` to the Node handler and includes packaged `data/*.json` artifacts. The function's configured maximum duration is 30 seconds.

The hosted adapter requires `AURA_CHALLENGE_KEY`: exactly 64 hexadecimal characters encoding 32 cryptographically random bytes. All instances in a deployment must receive the same secret. Keep it in the hosting environment, never in source, receipts, video or public documentation. Missing or malformed keys fail closed. Redeploy after setting or rotating environment values.

## Freeze and reveal across instances

Local challenge sessions use process memory, limited to 128 sessions with a one-hour lifetime. A restart discards them.

Hosted instances use AES-256-GCM encrypted and authenticated portable tokens, with a random 12-byte IV and application context. The token contains the frozen result and observed comparison values. Reveal validates its identifier, expiry and model binding; it does not recompute a supposedly frozen prediction. Rotating the key or replacing the bound model invalidates older sessions.

Receipt export excludes the transport token. Model/input hashes and an offline numerical verifier support reproducibility; they are not author signatures or independently trusted timestamps. The dataset is public, so hiding future values in the UI is not secure study blinding.

The research API accepts only bundled participant identifiers. Its runtime physically truncates input to the requested prefix. The legacy local development API and the research API are distinct; do not imply arbitrary real-patient uploads are supported.

## Verify a current release

```bash
npm test
npm run test:data
node scripts/verify_research_receipt.mjs path/to/receipt.json
```

After deployment, anonymously request `/api/research/health` and verify `aura-research-1.0.0` and its current hash. Load the React workspace, freeze/reveal a research prediction and download a token-free receipt for offline reproduction. Confirm SPA deep links, PDFs and the current MP4 in a signed-out browser. A successful build alone is not evidence that these flows work.

## Verified current deployment

The [canonical site](https://aura-twin-black-squad.vercel.app) was verified against release commit `664bc5e7be882153285c31281d2e4c9c25157ecc`, Vercel deployment `dpl_2L1qRGTATeVAU46JcDg5kgsnyUKF` (READY), frontend `index-CUQ3klm5.js` and research model SHA-256 `a4371ed5c7c768bf2d210917d6e7bf28ce89da7147ead0a98c14f48568abf432`.

The [GitHub CI run](https://github.com/DuvvuruDeepakReddy18/aura-twin-black-squad/actions/runs/39391935412) passed 58 JavaScript and 16 Python tests. Anonymous production checks confirmed the homepage, legacy route, current PDFs and MP4. An actual production API freeze/reveal receipt passed offline reproduction, including recorded future truth. The [sample receipt](SAMPLE_RESEARCH_RECEIPT.json) contains no transport token.

Live browser QA loaded participant 001, the current model and the 3D research scene. The **Generate review summary** action displayed “Structured review summary downloaded,” but its payload/file opening was not verified. The browser's receipt-download file also has not been confirmed on the filesystem. Those checks are distinct from successful API receipt verification. Supabase and its Google provider are configured, while public email signup/recovery remains disabled pending SMTP/email delivery. No end-to-end authentication success, including Google sign-in, is inferred.

The [verification record](VERIFICATION.md) records the exact completed checks and remaining limits.

Application response headers restrict content sources, MIME sniffing and referrer behavior. These controls and de-identification do not constitute a clinical security, HIPAA or DPDP certification. Do not enter private patient information into the demo.
