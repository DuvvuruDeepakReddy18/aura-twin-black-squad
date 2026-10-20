"""Regenerate transcripts from current narration; add timings only when titles match."""
from pathlib import Path
import json,subprocess

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'

def stamp(seconds):
    return f'{int(seconds)//60:02d}:{seconds%60:04.1f}'

def main():
    model_path=ROOT/'data/research-model.json'
    if not model_path.exists():model_path=ROOT/'data/model.json'
    model=json.loads(model_path.read_text(encoding='utf-8'))
    source=json.loads((DOCS/'narration.json').read_text(encoding='utf-8'))
    if model['modelVersion'] not in '\n'.join(x['text'] for x in source):
        raise RuntimeError('Current narration does not identify the active model.')
    timed=None
    chapters=DOCS/'AURA_Twin_Walkthrough.chapters.json'
    if chapters.exists():
        candidate=json.loads(chapters.read_text(encoding='utf-8'))['chapters']
        if [x['title'] for x in candidate]==[x['title'] for x in source]:timed=candidate
    status='Current narration source. Final recording timestamps are not yet available for these chapter titles.'
    if timed:
        media=DOCS/'AURA_Twin_Walkthrough.mp4'
        if media.exists():
            try:
                actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(media)],text=True).strip())
                status=f'Current recording duration: {stamp(actual)} ({actual:.6f} seconds). Chapter starts below match the current narrated slides. Narration uses Microsoft Zira, a locally synthesized voice.'
            except (OSError,ValueError,subprocess.CalledProcessError):
                status='Chapter starts match the current narrated slides. Confirm the final MP4 duration separately.'
    body=f"# Current walkthrough transcript\n\nModel: `{model['modelVersion']}`.\n\n{status}\n"
    for i,row in enumerate(source):
        start=f" — {stamp(timed[i]['startSeconds'])}" if timed else ''
        body+=f"\n## {row['slide']}. {row['title']}{start}\n\n{row['text']}\n"
    (DOCS/'VIDEO_TRANSCRIPT.md').write_text(body,encoding='utf-8')
    supplement=json.loads((DOCS/'narration-upgrade.json').read_text(encoding='utf-8'))
    body=f"# Challenge Lab supplement narration source\n\nModel: `{model['modelVersion']}`. These six excerpts match the current supplement PDF. They are included in the full main walkthrough; this document does not claim a separate supplement MP4 exists.\n"
    for row in supplement:body+=f"\n## {row['slide']}. {row['title']}\n\n{row['text']}\n"
    (DOCS/'VIDEO_TRANSCRIPT_UPGRADE.md').write_text(body,encoding='utf-8')
    print('Updated both transcripts. Current matching chapter timings:',bool(timed))

if __name__=='__main__':main()
