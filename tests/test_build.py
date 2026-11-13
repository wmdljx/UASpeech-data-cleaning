import csv
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from uaspeech_cut.batch import cut_batch, existing_video
from uaspeech_cut.build import build, preflight
from uaspeech_cut.common import pcm_bytes, pcm_sha, run_hasher, sha256, write_pcm_new
from uaspeech_cut.video import cut_one, probe


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root/'raw'
        self.raw.mkdir()
        self.out = self.root/'outputs'
        self.source = self.raw/'source.mkv'
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-n',
                        '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=30000/1001:duration=2',
                        '-f', 'lavfi', '-i', 'aevalsrc=0.1*sin(2*PI*500*t)|0.2*sin(2*PI*1000*t):s=16000:d=2',
                        '-c:v', 'ffv1', '-c:a', 'pcm_s16le', str(self.source)], check=True)
        n = int(next(s for s in probe(self.source)['streams'] if s['codec_type']=='video')['nb_read_frames'])
        self.src = dict(source_key='TEST_B1', path='source.mkv', sha256=sha256(self.source), frames=str(n),
                        fps_num='30000', fps_den='1001', channel='1', clock_slope='1', clock_intercept_s='0')
        self.rows, self.actions, self.manifests = [], {}, {}
        for i, (begin, end) in enumerate([(4,14), (12,22), (38,47)]):
            uid = f'TEST_B1_D{i}'
            word = (np.arange(8000) % 30000).astype('<i2').tobytes()
            write_pcm_new(self.raw/f'{uid}.wav', word)
            self.rows.append(dict(utterance_id=uid, speaker='TEST', source_key='TEST_B1',
                                  begin_frame=str(begin), end_frame_exclusive=str(end)))
            self.actions[uid] = dict(utterance_id=uid, operation='keep', input_path=f'{uid}.wav',
                                    input_sha256=sha256(self.raw/f'{uid}.wav'), output_path=f'audio/TEST/{uid}.wav',
                                    begin_sample='0', end_sample_exclusive='8000', output_samples='8000',
                                    output_pcm_sha256=pcm_sha(word))
            self.manifests[uid] = dict(utterance_id=uid, speaker='TEST', source_key='TEST_B1',
                                      audio_path=f'audio/TEST/{uid}.wav', video_path=f'video/{uid}.mp4',
                                      camera_audio_path=f'camera_audio/{uid}.wav', audio_samples='8000', video_frames=str(end-begin))
        self.metadata = self.root/'metadata'
        self.metadata.mkdir()
        for name, rows in [('frame_index.tsv', self.rows), ('audio_actions.tsv', list(self.actions.values())),
                           ('manifest.csv', list(self.manifests.values())), ('source_files.tsv', [self.src])]:
            with (self.metadata/name).open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t' if name.endswith('.tsv') else ',')
                writer.writeheader(); writer.writerows(rows)
        (self.metadata/'release.json').write_text(json.dumps(dict(revision='test', files={})))

    def test_batch_matches_single_and_source_frames(self):
        self.out.mkdir()
        cut_batch(self.rows, self.src, self.manifests, self.raw, self.out, run_hasher())
        def pixels(path):
            p = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0',
                                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
            return np.frombuffer(p.stdout, np.uint8).reshape(-1,120,160,3).astype(float)
        source = pixels(self.source)
        for row in self.rows:
            uid = row['utterance_id']
            cut_one(row, self.src, self.raw, self.root/'single', self.root/'single/cache')
            batched = pixels(self.out/f'video/{uid}.mp4')
            single = pixels(self.root/f'single/video/{uid}.mp4')
            np.testing.assert_array_equal(batched, single)
            nearest = [int(np.argmin(np.mean((source-frame)**2, axis=(1,2,3)))) for frame in batched]
            self.assertEqual(nearest, list(range(int(row['begin_frame']), int(row['end_frame_exclusive']))))
            self.assertEqual(pcm_bytes(self.out/f'camera_audio/{uid}.wav'), pcm_bytes(self.root/f'single/camera_audio/{uid}.wav'))
            self.assertTrue(existing_video(row, self.src, self.manifests[uid], self.out))

    def test_build_resume_and_incomplete_run(self):
        first = self.rows[0]['utterance_id']
        result = build(self.metadata, self.raw, self.out, ids=[first])
        self.assertEqual(result['counts']['built'], 1)
        before = sha256(self.out/f'video/{first}.mp4')
        result = build(self.metadata, self.raw, self.out, workers=2)
        self.assertEqual(result['counts'], dict(built=2, skipped=1, failed=0, pending=0))
        result = build(self.metadata, self.raw, self.out)
        self.assertEqual(result['counts']['skipped'], 3)
        self.assertEqual(before, sha256(self.out/f'video/{first}.mp4'))
        with (self.out/f'video/{first}.mp4').open('ab') as f:
            f.write(b'corruption')
        with self.assertRaisesRegex(ValueError, 'checksum differs'):
            build(self.metadata, self.raw, self.out)

    def test_preflight_missing_and_partial_outputs(self):
        self.source.rename(self.raw/'renamed.mkv')
        with self.assertRaisesRegex(ValueError, 'Missing source'):
            build(self.metadata, self.raw, self.out, check_only=True)
        self.assertFalse(self.out.exists())
        (self.raw/'renamed.mkv').rename(self.source)
        first = self.rows[0]['utterance_id']
        write_pcm_new(self.out/f'camera_audio/{first}.wav', b'\0\0')
        with self.assertRaisesRegex(ValueError, 'Incomplete video'):
            build(self.metadata, self.raw, self.out, check_only=True)

    def test_failure_report_and_retry(self):
        with patch('uaspeech_cut.build.cut_batch', side_effect=ValueError('simulated encoder failure')):
            with self.assertRaisesRegex(ValueError, 'Build incomplete'):
                build(self.metadata, self.raw, self.out)
        report = json.loads(next((self.out/'reports').glob('*.json')).read_text())
        self.assertEqual(report['counts']['failed'], 3)
        result = build(self.metadata, self.raw, self.out)
        self.assertEqual(result['counts']['built'], 3)

    def test_source_change_and_limits(self):
        h = run_hasher()
        old = h(self.source)
        with self.source.open('ab') as f:
            f.write(b'changed')
        self.assertNotEqual(h(self.source), old)
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            build(self.metadata, self.raw, self.out, check_only=True)
        with self.assertRaisesRegex(ValueError, 'workers'):
            build(self.metadata, self.raw, self.out, workers=0)
