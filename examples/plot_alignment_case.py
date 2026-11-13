"""Plot a documented interval error using locally held, licensed UASpeech media.

Install the package and matplotlib first. The output is a local inspection figure,
not a permission to redistribute corpus-derived material. No upload is performed.
This example compares old and corrected intervals in the same source video.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import tempfile

import numpy as np

from uaspeech_cut.__main__ import validate
from uaspeech_cut.audio import decode_camera, on_video_clock, reconstruct_one
from uaspeech_cut.common import checked_path, pcm_bytes, publish_new, read_table, separate_roots, sha256


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RATE = 16000
PANEL_LABELS = (
    "Word-level microphone recording",
    "Video speech audio — original frame index",
    "Video speech audio — corrected frame index",
)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--raw-root", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True, help="New local PNG; never uploaded")
    result.add_argument("--metadata", type=Path, default=ROOT / "metadata")
    result.add_argument("--case", type=Path, default=Path(__file__).with_name("alignment_case.json"))
    return result


def output_path(path, raw_root, repo_root=ROOT):
    """Allow explicit local outputs, but not input trees or public repo assets."""
    path, repo_root = Path(path).resolve(), Path(repo_root).resolve()
    if path.suffix.lower() != ".png":
        raise ValueError("Output must be a PNG file")
    if path.exists():
        raise FileExistsError(f"Output already exists: {path}")
    if path.is_relative_to(repo_root):
        relative = path.relative_to(repo_root)
        if len(relative.parts) < 2 or relative.parts[0] not in {"local", "outputs"}:
            raise ValueError("Inside this repository, save figures under ignored local/ or outputs/ only")
    separate_roots(raw_root, path.parent)
    return path


def read_case(case_path, metadata):
    case = json.loads(Path(case_path).read_text(encoding="utf-8"))
    uid = case["utterance_id"]
    frame = next(row for row in read_table(Path(metadata) / "frame_index.tsv") if row["utterance_id"] == uid)
    action = next(row for row in read_table(Path(metadata) / "audio_actions.tsv") if row["utterance_id"] == uid)
    source = next(row for row in read_table(Path(metadata) / "source_files.tsv") if row["source_key"] == case["source_key"])
    if frame["source_key"] != case["source_key"]:
        raise ValueError("This example requires both intervals to use the same source video")
    if action["operation"] != "keep":
        raise ValueError("The example requires an unchanged microphone recording")
    for prefix in ("original", "corrected"):
        begin, end = case[f"{prefix}_begin_frame"], case[f"{prefix}_end_frame_exclusive"]
        if type(begin) is not int or type(end) is not int or not 0 <= begin < end <= int(source["frames"]):
            raise ValueError(f"Invalid {prefix} interval")
    if (case["corrected_begin_frame"], case["corrected_end_frame_exclusive"]) != (
        int(frame["begin_frame"]), int(frame["end_frame_exclusive"])
    ):
        raise ValueError("Case metadata does not match the frozen corrected interval")
    return case, frame, action, source


def camera_interval(camera, begin, end, source):
    fps = Fraction(int(source["fps_num"]), int(source["fps_den"]))
    start = float(Fraction(begin, 1) / fps)
    count = round(Fraction((end - begin) * SAMPLE_RATE, 1) / fps)
    slope, intercept = float(source["clock_slope"]), float(source["clock_intercept_s"])
    if fps <= 0 or count <= 0 or not np.isfinite(slope) or slope <= 0 or not np.isfinite(intercept):
        raise ValueError("Invalid source clock")
    first = (start - intercept) / slope * SAMPLE_RATE
    last = (start + (count - 1) / SAMPLE_RATE - intercept) / slope * SAMPLE_RATE
    if first < 0 or last > len(camera) - 1:
        raise ValueError("Interval exceeds recorded audio; this plot does not pad missing samples")
    return np.frombuffer(on_video_clock(camera, count, start, slope, intercept), dtype="<i2")


def waveform_bins(samples, bins=1400):
    """Per-panel peak scaling and min/max display bins; no shifts or length padding."""
    values = np.asarray(samples, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or bins < 1:
        raise ValueError("Expected a finite, nonempty mono waveform and positive bin count")
    peak = float(np.max(np.abs(values)))
    normalized = values / peak if peak else values.copy()
    edges = np.linspace(0, len(values), min(int(bins), len(values)) + 1, dtype=int)
    low = np.minimum.reduceat(normalized, edges[:-1])
    high = np.maximum.reduceat(normalized, edges[:-1])
    times = (edges[:-1] + edges[1:]) / (2 * SAMPLE_RATE)
    return times, low, high


def render(destination, case, word, source, signals):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}")
    # Matplotlib is optional: importing this module and running its data tests
    # do not require it. Use a headless backend for local command-line execution.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    durations = [len(values) / SAMPLE_RATE for values in signals]
    fps = Fraction(int(source["fps_num"]), int(source["fps_den"]))
    intervals = ["Original microphone audio; unchanged"] + [
        f"Source frames [{case[f'{kind}_begin_frame']}, {case[f'{kind}_end_frame_exclusive']})"
        for kind in ("original", "corrected")
    ]
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11}):
        fig, axes = plt.subplots(3, 1, figsize=(11, 7.2), sharex=True, sharey=True)
        for ax, values, title, detail, duration, color in zip(
            axes, signals, PANEL_LABELS, intervals, durations, ("#315eae", "#c36835", "#16806d")
        ):
            time, low, high = waveform_bins(values)
            ax.fill_between(time, low, high, color=color, linewidth=0, alpha=0.88)
            ax.axhline(0, color="#c5ccd3", lw=0.6, zorder=0)
            ax.set_title(title, loc="left", fontsize=12, fontweight="semibold", pad=19)
            ax.text(0, 1.04, f"{detail} · {duration:.3f} s", transform=ax.transAxes, fontsize=9, color="#55616e")
            ax.set_ylim(-1.08, 1.08)
            ax.set_yticks([-1, 0, 1])
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="x", alpha=0.14)
        axes[-1].set_xlim(0, max(durations))
        axes[-1].set_xlabel("Time since each clip starts (seconds)")
        fig.suptitle(f"{case['utterance_id']} — {word}", x=0.11, y=0.98, ha="left", fontsize=17, fontweight="bold")
        fig.supylabel("Amplitude (each panel scaled to its own peak)", x=0.02, fontsize=10)
        fig.text(0.11, 0.04, "Recorded waveforms; min–max display bins. No manual time shift or equal-length padding.", fontsize=9)
        fig.text(0.11, 0.015, f"Source-frame rate: {fps.numerator}/{fps.denominator} fps. Video audio uses the stored source-clock mapping.", fontsize=9)
        fig.subplots_adjust(left=0.11, right=0.98, top=0.86, bottom=0.13, hspace=0.78)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix=".waveform-figure-", dir=destination.parent) as folder:
                temporary = Path(folder) / "figure.png"
                fig.savefig(temporary, dpi=160, facecolor="white")
                publish_new(temporary, destination)
        finally:
            plt.close(fig)


def main():
    args = parser().parse_args()
    destination = output_path(args.output, args.raw_root)
    validate(args.metadata)
    case, frame, action, source = read_case(args.case, args.metadata)
    if case.get("original_index_relative_path"):
        original_index = checked_path(args.raw_root, case["original_index_relative_path"])
        if sha256(original_index) != case["original_index_sha256"]:
            raise ValueError("Original index fingerprint differs from the documented case")
        line = original_index.read_text().splitlines()[int(case["original_index_line"]) - 1].split()
        expected = [case["utterance_id"], str(case["original_begin_frame"]),
                    str(case["original_end_frame_exclusive"])]
        if line != expected:
            raise ValueError("Documented original index row does not match the source file")
    source_path = checked_path(args.raw_root, source["path"])
    if sha256(source_path) != source["sha256"]:
        raise ValueError("Source video fingerprint differs from the approved source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    cache = checked_path(destination.parent, ".waveform_cache")
    camera = decode_camera(source_path, source["channel"], cache)
    with tempfile.TemporaryDirectory(prefix=".waveform-word-", dir=destination.parent) as folder:
        word_path = reconstruct_one(action, args.raw_root, Path(folder), cache)
        word = np.frombuffer(pcm_bytes(word_path), dtype="<i2").copy()
    signals = [word] + [camera_interval(camera, case[f"{kind}_begin_frame"],
                                      case[f"{kind}_end_frame_exclusive"], source)
                        for kind in ("original", "corrected")]
    render(destination, case, frame["text"], source, signals)
    print(f"Saved local licensed-data figure: {destination}")
    print("No media were uploaded. Do not commit or redistribute the figure or its audio cache without permission.")


if __name__ == "__main__":
    main()
