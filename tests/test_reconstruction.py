import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from uaspeech_cut.audio import on_video_clock, reconstruct_one
from uaspeech_cut.common import checked_path, pcm_bytes, pcm_sha, separate_roots, sha256, write_pcm_new
from uaspeech_cut.matching import candidates, standardize_resample
from uaspeech_cut.video import cut_one, probe


class AudioAndMatchingTests(unittest.TestCase):
    def test_paths_and_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                checked_path(root, "../outside.wav")
            with self.assertRaises(ValueError):
                checked_path(root, "/outside.wav")
            with self.assertRaises(ValueError):
                separate_roots(root, root / "output")
            (root / "link").symlink_to(root.parent, target_is_directory=True)
            with self.assertRaises(ValueError):
                checked_path(root, "link/outside.wav")
            write_pcm_new(root / "a.wav", b"\x00\x00")
            with self.assertRaises(FileExistsError):
                write_pcm_new(root / "a.wav", b"\x01\x00")

    def test_keep_crop_and_hash_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); raw = root / "raw"; out = root / "out"
            source = raw / "word.wav"
            values = np.arange(100, dtype="<i2").tobytes()
            write_pcm_new(source, values)
            for kind, begin, end in [("keep", 0, 100), ("crop", 7, 73)]:
                data = values[begin * 2:end * 2]
                row = dict(utterance_id=kind, operation=kind, input_path="word.wav",
                           input_sha256=sha256(source), output_path=f"{kind}.wav",
                           begin_sample=str(begin), end_sample_exclusive=str(end),
                           output_samples=str(end-begin), output_pcm_sha256=pcm_sha(data))
                dest = reconstruct_one(row, raw, out, out / "cache")
                self.assertEqual(pcm_bytes(dest), data)
                self.assertEqual(reconstruct_one(row, raw, out, out / "cache"), dest)
                with self.assertRaises(ValueError):
                    reconstruct_one(dict(row, output_pcm_sha256="bad"), raw, out, out / "cache")
                with self.assertRaises(ValueError):
                    reconstruct_one(dict(row, input_sha256="bad"), raw, out, out / "cache")

    def test_camera_recipes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); raw = root / "raw"; out = root / "out"
            source = raw / "source.wav"; camera = np.arange(100, dtype="<i2")
            write_pcm_new(source, camera.tobytes())
            base = dict(utterance_id="x", input_path="source.wav", input_sha256=sha256(source),
                        channel="1", output_samples="10")
            cropped = camera[4:14].tobytes()
            row = dict(base, operation="camera_crop", begin_sample="4", end_sample_exclusive="14",
                       output_path="crop.wav", output_pcm_sha256=pcm_sha(cropped))
            with patch("uaspeech_cut.audio.decode_camera", return_value=camera):
                dest = reconstruct_one(row, raw, out, out / "cache")
                self.assertEqual(pcm_bytes(dest), cropped)
                interpolated = on_video_clock(camera, 10, 4/16000, 1, 0)
                row = dict(base, operation="camera_clock_interpolate", video_start_s=str(4/16000),
                           clock_slope="1", clock_intercept_s="0", output_path="clock.wav",
                           output_pcm_sha256=pcm_sha(interpolated))
                dest = reconstruct_one(row, raw, out, out / "cache")
                self.assertEqual(pcm_bytes(dest), cropped)

    def test_ncc_offset_polarity_and_input_unchanged(self):
        rng = np.random.default_rng(14)
        query = rng.normal(size=800)
        original = query.copy()
        reference = rng.normal(scale=0.01, size=20000)
        reference[8300:9100] = -3 * query + 10
        match = candidates(reference, query, 1, 3)[0]
        self.assertAlmostEqual(match["camera_audio_start_s"], 8300/4000)
        self.assertLess(match["correlation"], -0.999)
        np.testing.assert_array_equal(query, original)
        self.assertEqual(candidates(reference, np.ones(100)), [])
        self.assertEqual(candidates(reference, query, 99, 100), [])
        self.assertEqual(len(standardize_resample(np.arange(16000), 16000)), 4000)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class VideoIntegrationTest(unittest.TestCase):
    def test_original_frame_cut_with_camera_sound(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); raw = root / "raw"; out = root / "out"
            raw.mkdir(); source = raw / "source.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-n",
                            "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=30000/1001:duration=1.2",
                            "-f", "lavfi", "-i", "aevalsrc=0.1*sin(2*PI*500*t)|0.2*sin(2*PI*1000*t):s=16000:d=1.2",
                            "-c:v", "ffv1", "-c:a", "pcm_s16le", str(source)], check=True)
            n = int(next(s for s in probe(source)["streams"] if s["codec_type"] == "video")["nb_read_frames"])
            src = dict(path="source.mkv", sha256=sha256(source), frames=str(n), fps_num="30000",
                       fps_den="1001", channel="1", clock_slope="1", clock_intercept_s="0")
            row = dict(utterance_id="TEST_B1_D1", source_key="TEST_B1", begin_frame="4",
                       end_frame_exclusive="14", publication_disposition="exclude_pending_safe_ROI")
            result = cut_one(row, src, raw, out, out / "cache")
            self.assertEqual((result["video_frames"], result["width"], result["height"]), (10, 160, 120))
            self.assertEqual(result["camera_channel_zero_based"], 1)
            self.assertEqual(result["camera_samples"], round(10 * 1001/30000 * 16000))
            self.assertTrue((out / "video/TEST_B1_D1.mp4").is_file())
            self.assertTrue((out / "camera_audio/TEST_B1_D1.wav").is_file())
            def pixels(path):
                data = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0",
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                      check=True, capture_output=True).stdout
                return np.frombuffer(data, dtype=np.uint8).reshape(-1, 120, 160, 3).astype(float)
            original = pixels(source)
            cut = pixels(out / "video/TEST_B1_D1.mp4")
            nearest = [int(np.argmin(np.mean((original-frame)**2, axis=(1, 2, 3)))) for frame in cut]
            self.assertEqual(nearest, list(range(4, 14)))
            with self.assertRaises(ValueError):
                cut_one(row, src, raw, out, out / "cache")
            saved = json.loads((out / "receipts/TEST_B1_D1.video.json").read_text())
            self.assertEqual(saved, result)


if __name__ == "__main__":
    unittest.main()
