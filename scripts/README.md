# Research document and video sources

Documents are generated from frozen `research-model.json`, `research-metrics.json`, `research-freeze.json` and the separate synthetic V4 result. The primary model hash must agree before generation succeeds. Authoring tools are optional for running the application.

```bash
python -m pip install reportlab pypdf pillow pymupdf
python scripts/build_research_docs.py --auth-status configured-unverified
python scripts/build_v4_report.py
python scripts/build_transcripts.py
```

The current auth status is `configured-unverified`: Supabase is connected with email confirmation enabled, public signup/recovery are disabled until email delivery is configured, and Google OAuth is disabled. Do not change the status to verified without real flow evidence.

`research_presentation_content.json` contains the 22-slide narration source. `research_doc_layout.py` draws the navy/cyan PDFs. `build_research_docs.py` substitutes measured values and creates the 22-page presentation, four-page architecture, six-page challenge supplement, narration, README, model/data card and runbook. Screenshots are `docs/assets/dashboard-research.png`, `record-research.png`, `evidence-research.png` and `robustness-research.png`.

The older `build_docs.py` dispatches to the research builder when research metrics exist. `build_upgrade_docs.py` can re-extract the current six-page supplement without preserving old-model claims. Historical synthetic layout/content files remain source history; do not run them to replace current evidence.

## Narration and video

The current script is approximately 4,100 words. Measure actual audio duration instead of assuming a speaking rate. The narration is disclosed as synthesized, not a recording of a team member.

```powershell
./scripts/narrate.ps1 -Narration ./docs/narration.json -AudioDirectory ./work/audio -Rate 2
```

```bash
python scripts/build_video.py --pdf docs/AURA_Twin_Presentation.pdf --narration docs/narration.json --audio work/audio --output docs/AURA_Twin_Walkthrough.mp4
python scripts/build_transcripts.py
```

The main video builder enforces a 1,200-second minimum. `--minimum-seconds 0` is only for an explicitly supplementary recording, never for the required main demonstration. The builder writes chapter metadata and a `.chapters.json` sidecar. The transcript includes timing only when chapter titles match the current narration.

Render and inspect every page, confirm the spoken metrics, probe the finished duration, decode the complete MP4 and inspect playback before release. Any material model, target or account-status change requires matching narration and PDF updates. Screenshot-only replacements do not change narration.

These tools do not upload, publish or submit. Dataset terms and authoring-library licenses remain separate from the application MIT license.
