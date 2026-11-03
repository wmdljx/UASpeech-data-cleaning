"""Run from the checkout root, or supply --metadata explicitly."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from .common import checked_path, read_table, select, sha256


def validate(metadata):
    metadata = Path(metadata)
    frames = read_table(metadata / "frame_index.tsv")
    manifest = read_table(metadata / "manifest.csv")
    actions = read_table(metadata / "audio_actions.tsv")
    source_rows = read_table(metadata / "source_files.tsv")
    sources = {row["source_key"]: row for row in source_rows}
    if len(sources) != len(source_rows):
        raise ValueError("Duplicate source keys")
    ids = [row["utterance_id"] for row in frames]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate frame-index IDs")
    for table in (manifest, actions):
        table_ids = [row["utterance_id"] for row in table]
        if len(table_ids) != len(set(table_ids)) or set(table_ids) != set(ids):
            raise ValueError("Tables disagree on sample IDs")
    by_id = {row["utterance_id"]: row for row in frames}
    actions_by_id = {row["utterance_id"]: row for row in actions}
    def relative_name(value):
        # These paths describe outputs/licensed inputs, not files below metadata.
        # Check syntax here; resolved symlink containment is checked at actual IO.
        path = Path(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("Expected nonempty relative metadata path")
    for source in sources.values():
        relative_name(source["path"])
    for row in frames:
        source = sources[row["source_key"]]
        if not 0 <= int(row["begin_frame"]) < int(row["end_frame_exclusive"]) <= int(source["frames"]):
            raise ValueError(f"Invalid frame interval: {row['utterance_id']}")
    known = {"keep", "crop", "camera_crop", "camera_clock_interpolate"}
    for action in actions:
        if action["operation"] not in known or int(action["output_samples"]) <= 0:
            raise ValueError("Invalid audio action")
        relative_name(action["input_path"])
        relative_name(action["output_path"])
    for row in manifest:
        frame = by_id[row["utterance_id"]]
        action = actions_by_id[row["utterance_id"]]
        for field in ("speaker", "block", "text", "split", "source_key"):
            if field in row and field in frame and row[field] != frame[field]:
                raise ValueError(f"Manifest/frame-index mismatch: {row['utterance_id']}: {field}")
        if row["audio_path"] != action["output_path"] or int(row["audio_samples"]) != int(action["output_samples"]):
            raise ValueError(f"Manifest/audio-action mismatch: {row['utterance_id']}")
        if "video_frames" in row and int(row["video_frames"]) != int(frame["end_frame_exclusive"]) - int(frame["begin_frame"]):
            raise ValueError("Raw video frame count must equal the full approved interval, not the historical ROI count")
        for field in ("audio_path", "video_path", "camera_audio_path"):
            if row.get(field):
                relative_name(row[field])
    release_path = metadata / "release.json"
    if release_path.exists():
        release = json.loads(release_path.read_text())
        for filename, info in release.get("files", {}).items():
            path = checked_path(metadata, filename)
            if sha256(path) != info["sha256"]:
                raise ValueError(f"Changed metadata: {filename}")
            if "rows" in info and len(read_table(path)) != int(info["rows"]):
                raise ValueError(f"Wrong declared row count: {filename}")
    return dict(status="PASS", records=len(ids), speakers=len({row["speaker"] for row in frames}),
                audio_operations=dict(Counter(row["operation"] for row in actions)),
                scope="Metadata consistency; not a new content-quality audit")


def main():
    parser = argparse.ArgumentParser(description="Reconstruct word audio and full-frame video from approved indices; no ROI")
    parser.add_argument("--metadata", type=Path, default=Path("metadata"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Check tables and declared fingerprints without corpus media")
    for kind in ("audio", "video"):
        command = commands.add_parser(kind)
        command.add_argument("--raw-root", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--id", action="append", help="Repeat for multiple IDs; without selection, process all")
        command.add_argument("--speaker")
    args = parser.parse_args()
    if args.command == "validate":
        print(json.dumps(validate(args.metadata), indent=2))
        return
    validate(args.metadata)
    cache = args.output / ".cache" / "camera"
    if args.command == "audio":
        from .audio import reconstruct_one
        rows = select(read_table(args.metadata / "audio_actions.tsv"), args.id, args.speaker)
        for row in rows:
            path = reconstruct_one(row, args.raw_root, args.output, cache)
            print(json.dumps({"utterance_id": row["utterance_id"], "audio": str(path)}), flush=True)
    else:
        from .video import cut_one
        sources = {row["source_key"]: row for row in read_table(args.metadata / "source_files.tsv")}
        manifests = {row["utterance_id"]: row for row in read_table(args.metadata / "manifest.csv")}
        for row in select(read_table(args.metadata / "frame_index.tsv"), args.id, args.speaker):
            output = manifests[row["utterance_id"]].get("video_path") or f"video/{row['utterance_id']}.mp4"
            result = cut_one(row, sources[row["source_key"]], args.raw_root, args.output, cache, output)
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()

