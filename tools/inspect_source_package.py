#!/usr/bin/env python3
"""Read-only inventory of an authorized UASpeech source package; JSON to stdout.

No media is decoded or written. --probe reads container headers with ffprobe.
The inventory describes the supplied local copy, not worldwide availability.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess


SPEAKER = re.compile(r"^(?:C)?[FM]\d+$")
WORD_WAV = re.compile(r"^((?:C)?[FM]\d+)_B[123]_[A-Z0-9]+_(M\d+)\.wav$")
INDEX_ROW = re.compile(r"^\s*((?:C)?[FM]\d+_B[123]_[A-Z0-9]+)\s+(\d+)\s+(\d+)\s*$")


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_index(path: Path, root: Path) -> dict:
    ids = []
    malformed = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        match = INDEX_ROW.fullmatch(line)
        if match:
            ids.append(match.group(1))
        elif re.match(r"^\s*(?:C)?[FM]\d+_B[123]_", line):
            malformed.append(line_number)
    return {
        "path": relative(path, root),
        "rows": len(ids),
        "unique_utterance_ids": len(set(ids)),
        "malformed_data_line_numbers": malformed,
    }


def probe(path: Path, timeout: float) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=timeout,
    )
    streams = json.loads(result.stdout)["streams"]
    return {
        "video": [
            {k: s.get(k) for k in ("index", "codec_name", "width", "height", "r_frame_rate", "avg_frame_rate", "nb_frames")}
            for s in streams if s.get("codec_type") == "video"
        ],
        "audio": [
            {k: s.get(k) for k in ("index", "codec_name", "channels", "sample_rate")}
            for s in streams if s.get("codec_type") == "audio"
        ],
    }


def inspect(root: Path, with_probe: bool = False, timeout: float = 30.0) -> dict:
    audio_roots = [
        (root / "UASpeech_original_FM/UASpeech/audio/original", "dysarthric"),
        (root / "UASpeech_original_C/UASpeech/audio/original", "control"),
    ]
    video_roots = [root / f"UASpeech_video_{part}/UASpeech/video" for part in (0, 1)]
    missing = [relative(p, root) for p in [*(p for p, _ in audio_roots), *video_roots] if not p.is_dir()]
    if missing:
        raise ValueError("Expected source-package directories are missing: " + ", ".join(missing))
    if with_probe and not shutil.which("ffprobe"):
        raise ValueError("--probe requires ffprobe on PATH")

    speakers = {}
    for directory, group in audio_roots:
        for folder in sorted(directory.iterdir()):
            if not folder.is_dir() or not SPEAKER.fullmatch(folder.name):
                continue
            microphones = Counter()
            for wav in folder.glob("*.wav"):
                match = WORD_WAV.fullmatch(wav.name)
                if match and match.group(1) == folder.name:
                    microphones[match.group(2)] += 1
            speakers[folder.name] = {
                "speaker": folder.name, "group": group,
                "audio_files": sum(microphones.values()),
                "audio_microphone_counts": dict(sorted(microphones.items())),
                "videos": [], "legacy_indices": [],
            }

    for directory in video_roots:
        for folder in sorted(directory.iterdir()):
            if not folder.is_dir() or not SPEAKER.fullmatch(folder.name):
                continue
            record = speakers.setdefault(folder.name, {
                "speaker": folder.name,
                "group": "control" if folder.name.startswith("C") else "dysarthric",
                "audio_files": 0, "audio_microphone_counts": {},
                "videos": [], "legacy_indices": [],
            })
            for video in sorted(folder.glob("*.divx")):
                if video.name.startswith("."):
                    continue
                item = {"path": relative(video, root)}
                if with_probe:
                    item["streams"] = probe(video, timeout)
                record["videos"].append(item)
            for index in sorted(folder.glob("*_frame_index.txt")):
                if not index.name.startswith("."):
                    record["legacy_indices"].append(read_index(index, root))

    records = [speakers[k] for k in sorted(speakers)]
    audio = [r["speaker"] for r in records if r["audio_files"]]
    audiovisual = [r["speaker"] for r in records if r["audio_files"] and r["videos"]]
    indexed = [r["speaker"] for r in records if r["audio_files"] and r["videos"] and any(i["rows"] for i in r["legacy_indices"])]
    return {
        "scope": "Locally supplied package only; existence is not correctness or completeness.",
        "probe_performed": with_probe,
        "sets": {"audio": audio, "audio_and_video": audiovisual, "audio_video_and_some_index": indexed},
        "counts": {
            "audio_speakers": len(audio), "audio_and_video_speakers": len(audiovisual),
            "indexed_speakers": len(indexed),
            "dysarthric_audio_speakers": sum(r["group"] == "dysarthric" and r["audio_files"] > 0 for r in records),
            "control_audio_speakers": sum(r["group"] == "control" and r["audio_files"] > 0 for r in records),
            "divx_files": sum(len(r["videos"]) for r in records),
            "legacy_index_files": sum(len(r["legacy_indices"]) for r in records),
            "legacy_index_rows": sum(i["rows"] for r in records for i in r["legacy_indices"]),
        },
        "speakers": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--probe", action="store_true", help="Read DivX stream metadata with ffprobe; no media extraction")
    parser.add_argument("--probe-timeout", type=float, default=30.0, help="Maximum seconds per ffprobe call (default: 30)")
    args = parser.parse_args()
    if args.probe_timeout <= 0:
        parser.error("--probe-timeout must be positive")
    try:
        result = inspect(args.raw_root.resolve(), args.probe, args.probe_timeout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Inventory failed: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
