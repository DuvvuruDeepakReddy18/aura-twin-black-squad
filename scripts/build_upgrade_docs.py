"""Extract a current six-page Challenge Lab/evidence supplement from the full deck.

Run build_docs.py first. This script does not synthesize or encode any video.
"""
from pathlib import Path
import json
from pypdf import PdfReader, PdfWriter

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'

def main():
    model=json.loads((ROOT/'data/model.json').read_text(encoding='utf-8'))
    narration=json.loads((DOCS/'narration.json').read_text(encoding='utf-8'))
    if model['modelVersion'] not in '\n'.join(row['text'] for row in narration):
        raise RuntimeError('Regenerate the main deck/narration for the current model first.')
    source=PdfReader(DOCS/'AURA_Twin_Presentation.pdf')
    selection=[1,16,17,10,18,22]
    writer=PdfWriter()
    records=[]
    for new_number,old_number in enumerate(selection,1):
        writer.add_page(source.pages[old_number-1])
        row=dict(narration[old_number-1]); row['slide']=new_number
        records.append(row)
    writer.add_metadata({'/Title':'AURA Twin — Current Challenge Lab and robustness evidence','/Author':'Black Squad','/Subject':model['modelVersion']+'; extracted from the current full presentation'})
    with (DOCS/'AURA_Twin_Challenge_Lab.pdf').open('wb') as stream: writer.write(stream)
    (DOCS/'narration-upgrade.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Built current six-page supplement; source slide numbering intentionally retained.')

if __name__=='__main__': main()
