# Optional document and video source

The working dashboard and ML pipeline do not depend on these authoring tools. The finished PDFs and MP4 are already in `docs/`.

To join the original walkthrough and Challenge Lab supplement into one upload, preserving both originals:

```bash
python scripts/combine_walkthrough.py --output "AURA-Twin-Walkthrough.mp4"
```

This requires Python, FFmpeg and ffprobe on PATH; it uses no Python packages. It verifies matching stream formats, copies the streams without re-encoding, combines 26 chapters, checks the approximately 25:44 duration, and decodes the result before replacing the chosen output. It also writes a `.chapters.json` sidecar. If `--output` is omitted, the default is `docs/AURA_Twin_Complete_Walkthrough.mp4`. The delivered combined copy is outside the repository to avoid storing a third duplicate video.

To regenerate the PDFs after modifying the deck content:

```bash
python -m pip install reportlab pypdf
python scripts/build_docs.py
```

The v2 supplement is generated separately and does not overwrite the original presentation or narration:

```bash
python scripts/build_upgrade_docs.py
```

It reads `data/stress.json` and writes `docs/AURA_Twin_Challenge_Lab.pdf` plus `docs/narration-upgrade.json`. Re-run `python ml/stress_test.py` first if the stress protocol or model changes. Recheck every numerical claim and slide after regeneration.

To regenerate the supplied narration on Windows, install/enable the Microsoft Zira Desktop voice, then run PowerShell from the repository root:

```powershell
./scripts/narrate.ps1 -Narration ./docs/narration.json -AudioDirectory ./work/audio -Rate 2
```

To assemble slide images and narration into video, install FFmpeg from its official distribution and make `ffmpeg` available on PATH. Then:

```bash
python -m pip install pymupdf
python scripts/build_video.py --pdf docs/AURA_Twin_Presentation.pdf --narration docs/narration.json --audio work/audio --output docs/AURA_Twin_Walkthrough.mp4
```

These tools write local artifacts only. They do not upload, publish or submit anything. Check all slides, narration, final duration and actual playback after changing content. By default, the video builder enforces a 20-minute minimum for the main walkthrough.

For the short **supplementary** v2 video, synthesize its separate narration and explicitly override the main-video minimum:

```powershell
./scripts/narrate.ps1 -Narration ./docs/narration-upgrade.json -AudioDirectory ./work/audio-upgrade -Rate 2
```

```bash
python scripts/build_video.py --pdf docs/AURA_Twin_Challenge_Lab.pdf --narration docs/narration-upgrade.json --audio work/audio-upgrade --output docs/AURA_Twin_Challenge_Lab.mp4 --minimum-seconds 0 --title "AURA Twin | v2 Challenge Lab supplement"
```

The default minimum remains 1,200 seconds for the required main walkthrough. The override is appropriate only for a clearly labeled supplement; the short video does not replace the organizer's minimum-length main video.

Authoring dependencies are separately licensed: ReportLab and pypdf use BSD licenses; PyMuPDF is offered under AGPL/commercial terms; FFmpeg's license depends on the build. Consult their original licenses before changing or redistributing those dependencies. They are not bundled here. The included narration is explicitly synthesized, not a recording of a team member's voice.
