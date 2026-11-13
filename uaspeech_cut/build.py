"""Preflight and resumable paired-media reconstruction."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import uuid

from .audio import reconstruct_one
from .batch import cut_batch, existing_video
from .common import (checked_path, pcm_bytes, pcm_sha, read_table, run_hasher,
                     select, separate_roots, write_json_new)


def load_selection(metadata, ids=None, speaker=None):
    metadata = Path(metadata)
    rows = select(read_table(metadata/'frame_index.tsv'), ids, speaker)
    return (rows, {r['utterance_id']: r for r in read_table(metadata/'audio_actions.tsv')},
            {r['utterance_id']: r for r in read_table(metadata/'manifest.csv')},
            {r['source_key']: r for r in read_table(metadata/'source_files.tsv')})


def preflight(rows, actions, manifests, sources, raw_root, output, file_hash):
    separate_roots(raw_root, output)
    errors = []
    for program in ('ffmpeg', 'ffprobe'):
        if not shutil.which(program):
            errors.append(f'Missing {program}; install FFmpeg and add its bin directory to PATH')
    if errors:
        raise ValueError('\n'.join(errors))
    encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'],
                             capture_output=True, text=True, check=True).stdout
    if 'libx264' not in encoders or ' aac ' not in encoders:
        errors.append('FFmpeg must include libx264 and AAC encoders')
    inputs = {}
    selected_sources = {r['source_key']: sources[r['source_key']] for r in rows}
    for source in selected_sources.values():
        inputs[source['path']] = source['sha256']
    for row in rows:
        action = actions[row['utterance_id']]
        path, digest = action['input_path'], action['input_sha256']
        if path in inputs and inputs[path] != digest:
            errors.append(f'Conflicting input checksums for {path}')
        inputs[path] = digest
    for number, (name, digest) in enumerate(inputs.items(), 1):
        path = checked_path(raw_root, name)
        if not path.is_file():
            errors.append(f'Missing source: {name} (check --raw-root and preserve the original folders)')
        elif file_hash(path) != digest:
            errors.append(f'Source checksum mismatch: {name}; obtain the matching original file, do not bypass this check')
        if len(inputs) > 100 and (number % 250 == 0 or number == len(inputs)):
            print(f'Checked {number}/{len(inputs)} source files', flush=True)
    if errors:
        raise ValueError('\n'.join(errors))
    # Header check, not an expensive full-video decode.
    for source in selected_sources.values():
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json',
                                 str(checked_path(raw_root, source['path']))],
                                capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout)['streams']
        audio = [s for s in streams if s['codec_type'] == 'audio']
        if not any(s['codec_type'] == 'video' for s in streams) or not audio or int(audio[0]['channels']) <= int(source['channel']):
            errors.append(f"Video or selected speech channel unavailable: {source['path']}")
    for row in rows:
        uid = row['utterance_id']
        try:
            action = actions[uid]
            dest = checked_path(output, action['output_path'])
            if dest.exists() and pcm_sha(pcm_bytes(dest)) != action['output_pcm_sha256']:
                raise ValueError(f'Existing word-audio checksum differs: {uid}; use a new output folder')
            existing_video(row, sources[row['source_key']], manifests[uid], output)
        except (ValueError, OSError, KeyError) as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError('\n'.join(errors))
    parent = Path(output).resolve()
    while not parent.exists():
        parent = parent.parent
    return dict(status='PASS', records=len(rows), video_sources=len(selected_sources),
                input_files=len(inputs), free_disk_gib=round(shutil.disk_usage(parent).free/2**30, 2),
                note='Source fingerprints, stream headers and existing outputs checked. No media built.')


def build(metadata, raw_root, output, ids=None, speaker=None, workers=1, batch_size=8, check_only=False):
    from .__main__ import validate
    validate(metadata)
    if not 1 <= workers <= 4 or not 1 <= batch_size <= 8:
        raise ValueError('Use --workers 1..4 and --batch-size 1..8')
    rows, actions, manifests, sources = load_selection(metadata, ids, speaker)
    file_hash = run_hasher()
    print('Checking source files and existing outputs...', flush=True)
    result = preflight(rows, actions, manifests, sources, raw_root, output, file_hash)
    print(json.dumps(result), flush=True)
    if check_only:
        return result
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    state = {r['utterance_id']: dict(audio='pending', video='pending') for r in rows}
    groups = defaultdict(list)
    def fail(uid, exc, stage):
        state[uid][stage] = 'failed'
        detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        state[uid]['error'] = str(detail)[-3000:]
    interrupted = False
    try:
        for row in rows:
            uid = row['utterance_id']
            try:
                action = actions[uid]
                existed = checked_path(output, action['output_path']).exists()
                reconstruct_one(action, raw_root, output, output/'.cache/camera', file_hash=file_hash)
                state[uid]['audio'] = 'skipped' if existed else 'built'
                if existing_video(row, sources[row['source_key']], manifests[uid], output):
                    state[uid]['video'] = 'skipped'
                else:
                    groups[row['source_key']].append(row)
            except Exception as exc:
                fail(uid, exc, 'audio' if state[uid]['audio'] == 'pending' else 'video')
        def process_group(key, items):
            items = sorted(items, key=lambda r: int(r['begin_frame']))
            for start in range(0, len(items), batch_size):
                batch = items[start:start+batch_size]
                try:
                    cut_batch(batch, sources[key], manifests, raw_root, output, file_hash)
                    for row in batch:
                        state[row['utterance_id']]['video'] = 'built'
                    print(f'Built {len(batch)} video clips from {key}', flush=True)
                except Exception as exc:
                    for row in batch:
                        uid = row['utterance_id']
                        # A batch may have published some complete clips before a failure.
                        try:
                            if existing_video(row, sources[key], manifests[uid], output):
                                state[uid]['video'] = 'built'
                                continue
                        except Exception:
                            pass
                        fail(uid, exc, 'video')
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(process_group, key, items) for key, items in groups.items()]
            for future in as_completed(futures):
                future.result()
    except KeyboardInterrupt:
        interrupted = True
    counts = Counter()
    for item in state.values():
        if item['audio'] in {'built', 'skipped'} and item['video'] in {'built', 'skipped'}:
            counts['skipped' if item['audio'] == item['video'] == 'skipped' else 'built'] += 1
        elif 'failed' in (item['audio'], item['video']):
            counts['failed'] += 1
        else:
            counts['pending'] += 1
    report = dict(status='PASS' if not interrupted and not counts['failed'] and not counts['pending'] else 'INCOMPLETE',
                  selected=len(rows), counts={k: counts[k] for k in ('built', 'skipped', 'failed', 'pending')},
                  interrupted=interrupted, items=state, metadata_revision=json.loads((Path(metadata)/'release.json').read_text())['revision'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target = output/'reports'/f'build-{stamp}-{uuid.uuid4().hex[:8]}.json'
    write_json_new(target, report)
    print(json.dumps(dict(status=report['status'], **report['counts'], report=str(target))), flush=True)
    if report['status'] != 'PASS':
        raise ValueError(f'Build incomplete; inspect {target} and rerun the same command after resolving errors')
    return report
