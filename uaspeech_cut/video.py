"""Cut original-resolution frames, retaining the selected embedded speech track.

No face detector, ROI, stabilization, 25-fps sampling or image augmentation.
Video boundaries use zero-based decoded ordinal frames, end exclusive.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
import subprocess
import tempfile

from .audio import decode_camera, on_video_clock
from .common import checked_path, pcm_sha, publish_new, separate_roots, sha256, write_json_new, write_pcm_new


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams",
                             "-show_format", "-of", "json", str(path)],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def cut_one(row, source_info, raw_root, output_root, cache_dir, output_path=None):
    separate_roots(raw_root, output_root)
    uid = row["utterance_id"]
    source = checked_path(raw_root, source_info["path"])
    if sha256(source) != source_info["sha256"]:
        raise ValueError(f"Source fingerprint mismatch: {uid}")
    begin, end = int(row["begin_frame"]), int(row["end_frame_exclusive"])
    if not 0 <= begin < end <= int(source_info["frames"]):
        raise ValueError(f"Frame interval escapes source: {uid}")
    fps = Fraction(int(source_info["fps_num"]), int(source_info["fps_den"]))
    if fps <= 0:
        raise ValueError("Non-positive source frame rate")
    destination = checked_path(output_root, output_path or f"video/{uid}.mp4")
    camera_path = checked_path(output_root, f"camera_audio/{uid}.wav")
    receipt_path = checked_path(output_root, f"receipts/{uid}.video.json")
    for path in (destination, camera_path, receipt_path):
        if path.exists():
            raise ValueError(f"Output already exists; choose a new directory: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    camera = decode_camera(source, int(source_info["channel"]), cache_dir)
    count = end - begin
    # Audio length is quantized to 16-kHz samples; video remains exact frame count.
    camera_samples = round(Fraction(count * 16000, 1) / fps)
    data = on_video_clock(camera, camera_samples, float(Fraction(begin, 1) / fps),
                          source_info["clock_slope"], source_info["clock_intercept_s"])
    with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
        folder = Path(folder)
        wav, temp = folder / "camera.wav", folder / "clip.mp4"
        write_pcm_new(wav, data)
        fps_text = f"{fps.numerator}/{fps.denominator}"
        # Decode from the beginning: input -ss/keyframe seeks do not reliably
        # preserve the indexed ordinal frame. trim selects the approved frames.
        filters = f"trim=start_frame={begin}:end_frame={end},settb=expr={fps.denominator}/{fps.numerator},setpts=N"
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
                   "-i", str(source), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                   "-vf", filters, "-r", fps_text, "-vsync", "1", "-c:v", "libx264",
                   "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2",
                   "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(temp)]
        subprocess.run(command, check=True)
        info = probe(temp)
        videos = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
        audios = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
        if len(videos) != 1 or len(audios) != 1:
            raise ValueError("Expected one video and one speech-audio stream")
        if int(videos[0]["nb_read_frames"]) != count or Fraction(videos[0]["avg_frame_rate"]) != fps:
            raise ValueError("Output frame count or frame rate differs from approved interval")
        receipt = {
            "utterance_id": uid, "source_key": row["source_key"],
            "source_sha256": source_info["sha256"], "begin_frame": begin,
            "end_frame_exclusive": end, "video_frames": count,
            "video_fps_num": fps.numerator, "video_fps_den": fps.denominator,
            "width": videos[0]["width"], "height": videos[0]["height"],
            "camera_channel_zero_based": int(source_info["channel"]),
            "camera_samples": camera_samples, "camera_pcm_sha256": pcm_sha(data),
            "clock_slope": float(source_info["clock_slope"]),
            "clock_intercept_s": float(source_info["clock_intercept_s"]),
            "output_sha256": sha256(temp),
            "policy": "original-resolution-ordinal-cut-with-selected-camera-speech",
            "note": "MP4 is lossy H.264/AAC; camera WAV is the pre-AAC PCM reference. Microphone audio is separate.",
        }
        # The three outputs are not a single transaction; a failed publication
        # never overwrites an existing output. Use a new directory after failure.
        publish_new(temp, destination)
        publish_new(wav, camera_path)
        write_json_new(receipt_path, receipt)
    return receipt

