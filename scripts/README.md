# Document and video source — current model

The finished PDFs are generated from the frozen current model/evidence artifacts. Authoring tools are optional; the dashboard has no dependency on them.

```bash
python -m pip install reportlab pypdf pillow
python scripts/build_docs.py
python scripts/build_upgrade_docs.py
python scripts/build_transcripts.py
```

`build_docs.py` reads current model, metrics and robustness JSON plus `presentation_content.json`, then writes the 22-page presentation, three-page architecture, matching full narration and model/data card. `doc_layout.py` supplies visual layout. It deliberately requires model 3.0.0: changing the model version requires reviewing the claims. Actual screenshots are read from `docs/assets/*-current.png`.

`build_upgrade_docs.py` extracts six checked pages and their matching narration from the current full presentation. It does not regenerate or preserve an old-model result. Source slide numbers are intentionally retained in the PDF. The main narration includes Challenge Lab; a separate short recording is optional. A newly generated deck must be paired with a current video before submission.

For locally synthesized narration on Windows, use Microsoft Zira Desktop:

```powershell
./scripts/narrate.ps1 -Narration ./docs/narration.json -AudioDirectory ./work/audio -Rate 2
```

The source contains about 4,442 words. Check actual audio duration rather than assuming a speaking rate. To encode the full current walkthrough, with FFmpeg on PATH:

```bash
python -m pip install pymupdf
python scripts/build_video.py --pdf docs/AURA_Twin_Presentation.pdf --narration docs/narration.json --audio work/audio --output docs/AURA_Twin_Walkthrough.mp4
```

The main builder enforces a 1,200-second minimum by default. Use `--minimum-seconds 0` only for an explicitly supplementary recording, never to bypass the required main-video duration. It writes chapter metadata and a `.chapters.json` sidecar. Run `python scripts/build_transcripts.py` again afterward to add the matching chapter times and probed video duration to the transcript. Render/inspect all pages, verify narration, probe duration, decode the complete MP4 and inspect playback before uploading.


These tools do not upload, publish or submit anything. The narration is disclosed as synthesized, not a recording of a team member. ReportLab/pypdf/Pillow/PyMuPDF/FFmpeg retain their own licenses; consult their official terms before distributing those authoring dependencies. They are not bundled in the application.
