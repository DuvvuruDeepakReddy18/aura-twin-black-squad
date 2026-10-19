"""Small presentation-document prose helpers; preserve commands, links and clinical notation."""
import re

def clean_markdown(body):
    output=[]
    fenced=False
    for line in body.splitlines():
        if line.lstrip().startswith('```'):
            fenced=not fenced
            output.append(line)
            continue
        if fenced:
            output.append(line)
            continue
        parts=re.split(r'(`[^`\n]+`|\]\([^)]+\)|https?://[^\s<>)]+|\blocalhost:\d+\b)',line)
        for i in range(0,len(parts),2):
            part=parts[i].replace('HbA 1 c','HbA1c').replace('HbA1c','__GLYCATED__').replace('MP 4','MP4').replace('MP4','__MEDIA__')
            for version in ('v1','v2','v3'):part=part.replace(version,'__VERSION'+version[-1]+'__')
            # Protect the version placeholders while formatting surrounding prose.
            part=part.replace('__VERSION1__','__ONE__').replace('__VERSION2__','__TWO__').replace('__VERSION3__','__THREE__')
            part=re.sub(r'(?<=[A-Za-z])(?=\d)',' ',part)
            part=re.sub(r'(?<=\d)(?!(?:st|nd|rd|th)\b|e[-+]\d)(?=[A-Za-z])',' ',part)
            part=re.sub(r'(?<=\d)\s+(st|nd|rd|th)\b',r'\1',part)
            part=re.sub(r'(?<=[A-Za-z])(?=\+\d)',' ',part)
            part=re.sub(r'(?<=[A-Za-z])(?=\*\*\d)',' ',part)
            part=re.sub(r'(?<=[A-Za-z%])([,;:])(?=\d)',r'\1 ',part)
            part=part.replace('glucose≥','glucose ≥').replace('final+','final +').replace('Final+','Final +')
            part=part.replace('__GLYCATED__','HbA1c').replace('__MEDIA__','MP4').replace('__ONE__','v1').replace('__TWO__','v2').replace('__THREE__','v3')
            parts[i]=part
        line=''.join(parts)
        if line.startswith('|') and line.endswith('|'):
            line='| '+' | '.join(cell.strip() for cell in line[1:-1].split('|'))+' |'
        output.append(line)
    return '\n'.join(output)+'\n'
