"""Small, explicit file contracts. Never modify licensed source recordings."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import wave


def read_table(path):
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t" if path.suffix == ".tsv" else ","))


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def checked_path(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Expected a contained relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path or symlink escapes root")
    return path


def separate_roots(raw_root, output_root):
    raw, output = Path(raw_root).resolve(), Path(output_root).resolve()
    if raw == output or output.is_relative_to(raw) or raw.is_relative_to(output):
        raise ValueError("Raw and output directories must be separate, non-nested trees")


def pcm_bytes(path):
    with wave.open(str(path), "rb") as stream:
        contract = (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getcomptype())
        if contract != (1, 2, 16000, "NONE"):
            raise ValueError(f"Expected mono PCM16 16 kHz WAV; got {contract}")
        data = stream.readframes(stream.getnframes())
        if len(data) != stream.getnframes() * 2:
            raise ValueError("Truncated WAV payload")
        return data


def pcm_sha(data):
    return hashlib.sha256(data).hexdigest()


def write_pcm_new(path, data):
    """Create only; exclusive creation prevents accidental overwrite."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        with wave.open(file, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            stream.writeframes(data)


def publish_new(temporary, destination):
    """Atomic, no-clobber publication. Both files must be on the same filesystem."""
    os.link(temporary, destination)


def write_json_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def select(rows, ids=None, speaker=None):
    ids = set(ids or [])
    unknown = ids - {row["utterance_id"] for row in rows}
    if unknown:
        raise ValueError(f"Unknown IDs: {sorted(unknown)}")
    selected = [row for row in rows if (not ids or row["utterance_id"] in ids)
                and (not speaker or row["speaker"] == speaker)]
    if not selected:
        raise ValueError("Empty sample selection")
    return selected

