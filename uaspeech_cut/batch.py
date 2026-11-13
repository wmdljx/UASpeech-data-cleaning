"""Bounded multi-output decoding and checksum-verified resume, without seeking."""
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import tempfile

from .audio import decode_camera, on_video_clock
from .common import (checked_path, pcm_bytes, pcm_sha, publish_new, separate_roots,
                     sha256, write_json_new, write_pcm_new)
from .video import probe


def paths(row, manifest, output):
    uid = row['utterance_id']
    return (checked_path(output, manifest['video_path']),
            checked_path(output, manifest['camera_audio_path']),
            checked_path(output, f'receipts/{uid}.video.json'))


def contract(row, source):
    begin, end = int(row['begin_frame']), int(row['end_frame_exclusive'])
    fps = Fraction(int(source['fps_num']), int(source['fps_den']))
    return dict(utterance_id=row['utterance_id'], source_key=row['source_key'],
                source_sha256=source['sha256'], begin_frame=begin, end_frame_exclusive=end,
                video_frames=end-begin, video_fps_num=fps.numerator, video_fps_den=fps.denominator,
                camera_channel_zero_based=int(source['channel']),
                camera_samples=round(Fraction((end-begin)*16000, 1)/fps),
                clock_slope=float(source['clock_slope']),
                clock_intercept_s=float(source['clock_intercept_s']))


def existing_video(row, source, manifest, output):
    """Skip only a complete build with matching recipe AND output checksums."""
    video, audio, receipt = paths(row, manifest, output)
    if not any(p.exists() for p in (video, audio, receipt)):
        return False
    if not all(p.is_file() for p in (video, audio, receipt)):
        raise ValueError(f"Incomplete video output for {row['utterance_id']}. Move its video, "
                         "camera_audio and receipt files aside, then rerun. Nothing was overwritten.")
    saved = json.loads(receipt.read_text())
    if not isinstance(saved, dict):
        raise ValueError(f"Invalid receipt: {receipt}; move this sample's outputs aside")
    if any(saved.get(k) != v for k, v in contract(row, source).items()):
        raise ValueError(f"Existing video recipe differs: {row['utterance_id']}; use a new output folder")
    data = pcm_bytes(audio)
    if (sha256(video) != saved.get('output_sha256') or
            pcm_sha(data) != saved.get('camera_pcm_sha256') or
            len(data)//2 != saved['camera_samples']):
        raise ValueError(f"Existing output checksum differs: {row['utterance_id']}; move damaged files aside")
    return True


def cut_batch(rows, source, manifests, raw_root, output, file_hash=sha256):
    """Rows share one source; decode it once into at most 8 independent outputs.

    No approximate seeks: trim uses decoded source-frame ordinals. Publication
    is per clip after frame/audio checks, with a receipt written last.
    """
    if not rows:
        return
    if len(rows) > 8 or any(r['source_key'] != rows[0]['source_key'] for r in rows):
        raise ValueError('A batch must contain at most 8 clips from one source')
    separate_roots(raw_root, output)
    src = checked_path(raw_root, source['path'])
    if file_hash(src) != source['sha256']:
        raise ValueError(f"Source fingerprint mismatch: {source['path']}")
    for row in rows:
        if not 0 <= int(row['begin_frame']) < int(row['end_frame_exclusive']) <= int(source['frames']):
            raise ValueError('Interval outside source')
        for p in paths(row, manifests[row['utterance_id']], output):
            if p.exists():
                raise ValueError(f'Output already exists: {p}')
            p.parent.mkdir(parents=True, exist_ok=True)
    camera = decode_camera(src, source['channel'], Path(output)/'.cache/camera', file_hash=file_hash)
    fps = Fraction(int(source['fps_num']), int(source['fps_den']))
    fps_text = f'{fps.numerator}/{fps.denominator}'
    with tempfile.TemporaryDirectory(prefix='.cut-', dir=output) as temp:
        temp = Path(temp)
        command = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
                   '-filter_threads', '1', '-threads', '2', '-i', str(src)]
        prepared = []
        for i, row in enumerate(rows):
            receipt = contract(row, source)
            data = on_video_clock(camera, receipt['camera_samples'],
                                  float(Fraction(receipt['begin_frame'], 1)/fps),
                                  source['clock_slope'], source['clock_intercept_s'])
            wav, mp4 = temp/f'{i}.wav', temp/f'{i}.mp4'
            write_pcm_new(wav, data)
            command += ['-i', str(wav)]
            receipt['camera_pcm_sha256'] = pcm_sha(data)
            prepared.append((row, receipt, wav, mp4))
        for i, (row, receipt, wav, mp4) in enumerate(prepared):
            filters = (f"trim=start_frame={receipt['begin_frame']}:end_frame={receipt['end_frame_exclusive']},"
                       f'settb=expr={fps.denominator}/{fps.numerator},setpts=N')
            command += ['-map', '0:v:0', '-map', f'{i+1}:a:0', '-vf', filters,
                        '-r', fps_text, '-vsync', '1', '-frames:v', str(receipt['video_frames']),
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-threads', '2', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(mp4)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        for row, receipt, wav, mp4 in prepared:
            streams = probe(mp4)['streams']
            video = [s for s in streams if s['codec_type'] == 'video']
            audio = [s for s in streams if s['codec_type'] == 'audio']
            if (len(video) != 1 or len(audio) != 1 or
                    int(video[0]['nb_read_frames']) != receipt['video_frames'] or
                    Fraction(video[0]['avg_frame_rate']) != fps):
                raise ValueError(f"Encoded video does not match approved interval: {row['utterance_id']}")
            receipt.update(width=video[0]['width'], height=video[0]['height'],
                           output_sha256=sha256(mp4), policy='source-ordinal-batch-cut-v1')
            dest, cam, note = paths(row, manifests[row['utterance_id']], output)
            publish_new(mp4, dest)
            publish_new(wav, cam)
            write_json_new(note, receipt)
