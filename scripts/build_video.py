"""Render the actual submission deck with locally synthesized, slide-matched narration."""
import argparse
import json
import pathlib
import subprocess
import wave
import fitz

parser = argparse.ArgumentParser()
parser.add_argument('--pdf', required=True)
parser.add_argument('--narration', required=True)
parser.add_argument('--audio', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--minimum-seconds', type=float, default=1200, help='Required duration; default 20 minutes for the main submission. Use 0 only for an explicitly supplementary video.')
parser.add_argument('--title', default='AURA Twin | Black Squad | Phase 1 prototype walkthrough')
parser.add_argument('--comment', default='Presentation walkthrough with synthesized narration. Open research wearables and separate synthetic EHR context. Research prototype.')
args = parser.parse_args()
audio = pathlib.Path(args.audio).resolve()
output = pathlib.Path(args.output).resolve()
chapters = json.loads(pathlib.Path(args.narration).read_text(encoding='utf-8-sig'))
pdf = fitz.open(args.pdf)
segments = []
timeline = []
elapsed = 0
for chapter in chapters:
    index = int(chapter['slide'])
    page = pdf[index - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1280 / page.rect.width, 720 / page.rect.height), alpha=False)
    still = audio / f'slide-{index:02}.png'
    pix.save(still)
    wav = audio / f'slide-{index:02}.wav'
    with wave.open(str(wav), 'rb') as sound:
        duration = sound.getnframes() / sound.getframerate()
    clip = audio / f'slide-{index:02}.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-loop', '1', '-framerate', '10', '-i', str(still), '-i', str(wav), '-t', str(duration), '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage', '-crf', '27', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(clip)], check=True)
    segments.append(clip)
    timeline.append({'slide': index, 'title': chapter['title'], 'startSeconds': round(elapsed, 2), 'durationSeconds': round(duration, 2)})
    elapsed += duration
    print(f'Encoded {index}: {duration:.1f}s', flush=True)
if elapsed < args.minimum_seconds:
    raise RuntimeError(f'Video narration is only {elapsed / 60:.1f} minutes; required minimum is {args.minimum_seconds / 60:.1f} minutes.')
concat = audio / 'segments.txt'
concat.write_text('\n'.join("file '" + str(p).replace('\\', '/') + "'" for p in segments), encoding='utf-8')
metadata = audio / 'chapters.txt'
lines = [';FFMETADATA1', 'title='+args.title.replace('=', '-').replace(';', ',').replace('#', ''), 'artist=Black Squad', 'comment='+args.comment.replace('=', '-').replace(';', ',').replace('#', '')]
for chapter in timeline:
    title = chapter['title'].replace('=', '-').replace(';', ',').replace('#', '')
    lines += ['[CHAPTER]', 'TIMEBASE=1/1000', f"START={round(chapter['startSeconds'] * 1000)}", f"END={round((chapter['startSeconds'] + chapter['durationSeconds']) * 1000)}", f'title={title}']
metadata.write_text('\n'.join(lines), encoding='utf-8')
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-i', str(metadata), '-map_metadata', '1', '-map_chapters', '1', '-c', 'copy', '-movflags', '+faststart', str(output)], check=True)
output.with_suffix('.chapters.json').write_text(json.dumps({'durationSeconds': elapsed, 'narration': 'Microsoft Zira, local synthesized voice', 'chapters': timeline}, indent=2), encoding='utf-8')
print(f'FINISHED {elapsed / 60:.2f} minutes, {output.stat().st_size / 1e6:.1f} MB: {output}', flush=True)
