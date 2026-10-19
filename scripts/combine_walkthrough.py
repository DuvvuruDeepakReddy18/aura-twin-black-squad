"""Join the original and v2 videos without re-encoding; requires ffmpeg/ffprobe."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams',
        '-show_chapters', '-of', 'json', str(path)
    ], text=True, encoding='utf-8'))

def escape_metadata(value):
    return str(value).replace('\\', '\\\\').replace('\n', ' ').replace('=', '\\=').replace(';', '\\;').replace('#', '\\#')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs' / 'AURA_Twin_Complete_Walkthrough.mp4')
    args = parser.parse_args()
    inputs = [ROOT / 'docs' / 'AURA_Twin_Walkthrough.mp4', ROOT / 'docs' / 'AURA_Twin_Challenge_Lab.mp4']
    output = args.output.resolve()
    if output in [path.resolve() for path in inputs]:
        raise ValueError('Output must differ from both original videos.')
    output.parent.mkdir(parents=True, exist_ok=True)
    reports = [probe(path) for path in inputs]
    keys = ('codec_type', 'codec_name', 'width', 'height', 'pix_fmt', 'sample_rate', 'channels', 'time_base')
    signatures = [[tuple(stream.get(k) for k in keys) for stream in report['streams'] if stream['codec_type'] in ('video', 'audio')] for report in reports]
    if signatures[0] != signatures[1]:
        raise ValueError('Audio/video formats differ; stream-copy concatenation is not supported.')
    chapters = []
    elapsed = 0.0
    for part, report in enumerate(reports, 1):
        for chapter in report.get('chapters', []):
            chapters.append({
                'title': f"{'Prototype' if part == 1 else 'Challenge Lab'} | {chapter.get('tags', {}).get('title', 'Chapter')}",
                'startSeconds': elapsed + float(chapter['start_time']),
                'endSeconds': elapsed + float(chapter['end_time']),
            })
        elapsed += float(report['format']['duration'])
    with tempfile.TemporaryDirectory(prefix='aura-combine-') as scratch:
        scratch = Path(scratch)
        concat = scratch / 'inputs.txt'
        concat.write_text('\n'.join("file '" + str(path.resolve()).replace('\\', '/').replace("'", "'\\''") + "'" for path in inputs), encoding='utf-8')
        meta = scratch / 'chapters.txt'
        lines = [';FFMETADATA1', 'title=AURA Twin | Complete prototype and Challenge Lab walkthrough', 'artist=Black Squad', 'comment=Locally synthesized narration. Synthetic data only. Research prototype. Original walkthrough followed by v2 supplement.']
        for chapter in chapters:
            lines += ['[CHAPTER]', 'TIMEBASE=1/1000', f"START={round(chapter['startSeconds'] * 1000)}", f"END={round(chapter['endSeconds'] * 1000)}", 'title=' + escape_metadata(chapter['title'])]
        meta.write_text('\n'.join(lines), encoding='utf-8')
        temporary_output = output.with_name(output.stem + '.combining.mp4')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-i', str(meta), '-map', '0:v:0', '-map', '0:a:0', '-map_metadata', '1', '-map_chapters', '1', '-c', 'copy', '-movflags', '+faststart', str(temporary_output)], check=True)
        combined = probe(temporary_output)
        duration = float(combined['format']['duration'])
        if abs(duration - elapsed) > 1.0 or len(combined.get('chapters', [])) != len(chapters):
            raise RuntimeError('Combined duration or chapter count failed verification.')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-xerror', '-i', str(temporary_output), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'], check=True)
        temporary_output.replace(output)
    output.with_suffix('.chapters.json').write_text(json.dumps({'durationSeconds': duration, 'narration': 'Microsoft Zira, local synthesized voice', 'chapters': chapters}, indent=2), encoding='utf-8')
    print(f'Combined and decoded successfully: {duration:.3f} seconds; {len(chapters)} chapters; {output}')

if __name__ == '__main__':
    main()
