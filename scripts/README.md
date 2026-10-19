# Optional document and video source

The working dashboard and ML pipeline do not depend on these authoring tools. The finished PDFs and MP4 are already in `docs/`.

To regenerate the PDFs after modifying the deck content:

```bash
python -m pip install reportlab pypdf
python scripts/build_docs.py
```

To regenerate the supplied narration on Windows, install/enable the Microsoft Zira Desktop voice, then run PowerShell from the repository root:

```powershell
./scripts/narrate.ps1 -Narration ./docs/narration.json -AudioDirectory ./work/audio -Rate 2
```

To assemble slide images and narration into video, install FFmpeg from its official distribution and make `ffmpeg` available on PATH. Then:

```bash
python -m pip install pymupdf
python scripts/build_video.py --pdf docs/AURA_Twin_Presentation.pdf --narration docs/narration.json --audio work/audio --output docs/AURA_Twin_Walkthrough.mp4
```

These tools write local artifacts only. They do not upload, publish or submit anything. Check all slides, narration, final duration and actual playback after changing content. The video builder refuses to output a combined video shorter than 20 minutes.

Authoring dependencies are separately licensed: ReportLab and pypdf use BSD licenses; PyMuPDF is offered under AGPL/commercial terms; FFmpeg's license depends on the build. Consult their original licenses before changing or redistributing those dependencies. They are not bundled here. The included narration is explicitly synthesized, not a recording of a team member's voice.
