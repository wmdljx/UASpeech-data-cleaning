import importlib.util
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np


SPEC = importlib.util.spec_from_file_location(
    "plot_alignment_case", Path(__file__).resolve().parents[1] / "examples" / "plot_alignment_case.py"
)
plot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plot)


class PlotDataTests(unittest.TestCase):
    def test_bins_preserve_extrema_and_input_without_padding(self):
        data = np.array([-32768, 32767, -4, 0, 2], dtype=np.int16)
        original = data.copy()
        times, low, high = plot.waveform_bins(data, bins=2)
        np.testing.assert_array_equal(data, original)
        np.testing.assert_allclose(low, [-1, -4 / 32768])
        np.testing.assert_allclose(high, [32767 / 32768, 2 / 32768])
        self.assertEqual(len(times), 2)
        self.assertGreater(times[0], 0)
        self.assertLess(times[-1], len(data) / plot.SAMPLE_RATE)
        time, low, high = plot.waveform_bins(np.zeros(3), bins=100)
        self.assertEqual(len(time), 3)
        self.assertTrue(np.all(low == 0) and np.all(high == 0))

    def test_clock_interval_length_and_out_of_bounds_fail(self):
        source = dict(fps_num=25, fps_den=1, clock_slope=1, clock_intercept_s=0)
        camera = np.arange(3200, dtype=np.int16)
        actual = plot.camera_interval(camera, 1, 3, source)
        np.testing.assert_array_equal(actual, camera[640:1920])
        with self.assertRaises(ValueError):
            plot.camera_interval(camera, 4, 6, source)

    def test_output_guards_and_required_output(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            plot.parser().parse_args(["--raw-root", "raw"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, raw = root / "repo", root / "raw"
            self.assertEqual(plot.output_path(repo / "local" / "case.png", raw, repo), repo / "local" / "case.png")
            for target in (repo / "docs" / "case.png", raw / "case.png", repo / "local" / "case.svg"):
                with self.assertRaises(ValueError):
                    plot.output_path(target, raw, repo)
            existing = root / "output" / "case.png"
            existing.parent.mkdir()
            existing.touch()
            with self.assertRaises(FileExistsError):
                plot.output_path(existing, raw, repo)
            with self.assertRaises(FileExistsError):
                plot.render(existing, {}, "word", {}, [])


if __name__ == "__main__":
    unittest.main()
