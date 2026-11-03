"""Replay the four frozen audio operations; no learned enhancement or denoising.

The arithmetic follows the accepted reconstruction recipes (historical stages
66/70/80/93). All reconstructed outputs must match their recorded PCM hash.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import numpy as np

from .common import checked_path, pcm_bytes, pcm_sha, publish_new, separate_roots, sha256, write_pcm_new


def decode_camera(path, channel, cache_dir):
    """Decode the entire selected channel before 16-kHz resampling/cropping.

    Channel numbers are zero-based within the first embedded audio stream.
    Caches are created locally and are not redistributed.
    """
    channel = int(channel)
    if channel < 0:
        raise ValueError("Negative channel")
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"{sha256(path)}_ch{channel}_16k.wav"
    if dest.exists():
        return np.frombuffer(pcm_bytes(dest), dtype="<i2")
    with tempfile.TemporaryDirectory(dir=cache_dir) as folder:
        temp = Path(folder) / "camera.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
                        "-i", str(path), "-map", "0:a:0", "-af", f"pan=mono|c0=c{channel}",
                        "-ar", "16000", "-c:a", "pcm_s16le", str(temp)], check=True)
        pcm_bytes(temp)
        try:
            publish_new(temp, dest)
        except FileExistsError:
            pass  # Another worker published the same source/channel.
    return np.frombuffer(pcm_bytes(dest), dtype="<i2")


def on_video_clock(camera, samples, video_start_s, slope, intercept_s):
    """Replay video_time = slope * decoded_audio_time + intercept.

    This retained interpolation is for camera fallback recordings, not for
    stretching the original microphone recordings. Historical out-of-range
    samples are zero-filled; the final PCM hash still must match.
    """
    slope = float(slope)
    if (not np.isfinite(slope) or slope <= 0 or int(samples) <= 0
            or not np.isfinite(float(video_start_s)) or not np.isfinite(float(intercept_s))):
        raise ValueError("Invalid clock mapping")
    times = float(video_start_s) + np.arange(int(samples)) / 16000
    positions = (times - float(intercept_s)) / slope * 16000
    values = np.interp(positions, np.arange(len(camera)), camera, left=0, right=0)
    return np.rint(values).clip(-32768, 32767).astype("<i2").tobytes()


def reconstruct_one(action, raw_root, output_root, cache_dir):
    separate_roots(raw_root, output_root)
    source = checked_path(raw_root, action["input_path"])
    if sha256(source) != action["input_sha256"]:
        raise ValueError(f"Source fingerprint mismatch: {action['utterance_id']}")
    destination = checked_path(output_root, action["output_path"])
    expected = action["output_pcm_sha256"]
    if destination.exists():
        if pcm_sha(pcm_bytes(destination)) != expected:
            raise ValueError("Existing output differs; use a new output directory")
        return destination
    kind = action["operation"]
    if kind in ("keep", "crop"):
        original = pcm_bytes(source)
        begin, end = int(action["begin_sample"]), int(action["end_sample_exclusive"])
        if not 0 <= begin < end <= len(original) // 2:
            raise ValueError("Invalid microphone sample interval")
        data = original[begin * 2:end * 2]
    elif kind == "camera_crop":
        camera = decode_camera(source, action["channel"], cache_dir)
        begin, end = int(action["begin_sample"]), int(action["end_sample_exclusive"])
        if not 0 <= begin < end <= len(camera):
            raise ValueError("Invalid camera sample interval")
        data = camera[begin:end].astype("<i2").tobytes()
    elif kind == "camera_clock_interpolate":
        camera = decode_camera(source, action["channel"], cache_dir)
        data = on_video_clock(camera, int(action["output_samples"]), action["video_start_s"],
                              action["clock_slope"], action["clock_intercept_s"])
    else:
        raise ValueError(f"Unknown audio operation: {kind}")
    if len(data) // 2 != int(action["output_samples"]) or pcm_sha(data) != expected:
        raise ValueError(f"Reconstructed PCM differs from frozen reference: {action['utterance_id']}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
        temp = Path(folder) / "audio.wav"
        write_pcm_new(temp, data)
        publish_new(temp, destination)
    return destination

