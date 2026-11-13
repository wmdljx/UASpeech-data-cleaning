# Build the corrected word clips

## Install

Use a licensed UASpeech copy. No source audio or video is downloaded by this tool.
The repository is still private; access and code-license approval are separate
from UASpeech permission. Linux and Python 3.10 are the reference environment;
other operating systems have not been verified.

```bash
git clone https://github.com/wmdljx/UASpeech-data-cleaning.git
cd UASpeech-data-cleaning
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tested.txt
python -m pip install -e .
ffmpeg -version
ffprobe -version
python -m uaspeech_cut validate
```

Install FFmpeg separately with libx264 and AAC encoding support. The pinned
Python packages provide a reference environment, not a promise that every FFmpeg
version decodes identically: reconstructed word PCM is verified by checksum.
Keep this checkout after the editable installation. Commands find its metadata
even from another working directory. If using a standalone wheel, provide
`--metadata /path/to/checkout/metadata` before the subcommand; a wheel alone does
not include the dataset tables.

The source root must preserve the original paths:

```text
uaspeech_ORIGIN/
├── UASpeech_original_FM/UASpeech/audio/original/<speaker>/...
├── UASpeech_video_0/UASpeech/video/<speaker>/...
└── UASpeech_video_1/UASpeech/video/<speaker>/...
```

Only files used by the selected records are required. Do not rename videos to
implement block permutations: `source_key` already selects the correct file.

## First sample, then all records

```bash
python -m uaspeech_cut check --raw-root /path/to/uaspeech_ORIGIN --output ./outputs --id F04_B3_UW14
python -m uaspeech_cut build --raw-root /path/to/uaspeech_ORIGIN --output ./outputs --id F04_B3_UW14
```

`check` verifies metadata, source-file hashes, required streams, encoders and any
existing selected outputs, without building media. `build` repeats that preflight
automatically. Use `--speaker F04` instead of `--id` for one speaker. Repeat
`--id` to select multiple words. Omit both to build all 8,415 records:

```bash
python -m uaspeech_cut build --raw-root /path/to/uaspeech_ORIGIN --output ./outputs --workers 2
```

The output directory must be outside the source tree; neither tree may contain
the other. No GPU is needed. The default is one video-source worker; `--workers`
accepts 1–4. Each worker cuts up to eight words from a shared sequential decode
(`--batch-size 1..8`). There is no approximate keyframe seeking. Grouped decoding
reduces repeated work but does not promise a fixed runtime or speedup. Sources
are hashed once per unchanged file per invocation. Do not edit inputs during a run.

## Outputs and resume

```text
outputs/
├── audio/F04/F04_B3_UW14.wav       # paired word audio, mono PCM16, 16 kHz
├── video/F04_B3_UW14.mp4           # full picture, with camera speech
├── camera_audio/F04_B3_UW14.wav    # camera speech before AAC encoding
├── receipts/F04_B3_UW14.video.json # source, interval and output checksums
├── reports/build-*.json           # built/skipped/failed/pending sample IDs
└── .cache/camera/                 # local decoded source-channel cache
```

The MP4 soundtrack is camera speech, **not** the paired word WAV. Training code
should use `manifest.csv`'s `audio_path` for the paired audio. The manifest describes
expected outputs; a successful build report tells you what exists for this run.

Rerun the same command to continue: complete matching outputs are verified and
skipped. Existing files are never silently overwritten. A partial video/WAV/receipt
set, changed recipe or checksum mismatch produces an error. Move only that sample's
listed outputs aside and retry; complete other samples remain reusable. A hard
termination may leave a `.cut-*` temporary directory and no final report for that
invocation; the next run checks the published per-sample receipts. Do not run two
builders against the same output directory at once.

Free disk space is reported during preflight, but output size is not reliably
predicted. Ensure enough space for videos, decoded camera audio and temporary
batches. Disk/encoding failures produce a nonzero exit and, for handled build
failures, a report. Keep reports local: they can contain local paths and errors.

## Common errors

| Error | What to do |
|---|---|
| Missing source | Point `--raw-root` at the folder above the original package directories; preserve filenames. |
| Source checksum mismatch | The file is not the approved source. Verify your authorized copy; do not disable the guard. |
| Missing FFmpeg/encoder | Install FFmpeg/ffprobe with libx264 and AAC, and put them on PATH. |
| Reconstructed PCM differs | Check the source and decoder version against the reference environment; do not accept approximate audio silently. |
| Existing output differs/incomplete | Move the named sample's outputs aside or use a new output folder. |
| No module named uaspeech_cut | Activate the environment and run `python -m pip install -e .` in the checkout. |

## Verification scope

The 2026-11-13 smoke test installed this package in a fresh Python 3.10 environment
with NumPy 1.23.5, SciPy 1.10.1 and FFmpeg/ffprobe 6.1.1. Nine real samples across
six speakers and seven source videos were reconstructed, covering all four word-audio
operations, M07 source reassignment and M05/M09 recovered indices. A second run
verified and skipped all nine. Two real F02 cuts produced identical decoded video
frame hashes and camera PCM to the previous single-clip implementation.
A fresh clone from GitHub was installed and used outside the checkout to build
the lawyer sample and then skip it after checksum verification. All 13 automated
tests passed in that checkout. Full preflight passed for all 8,415 records,
covering 33 source videos and 8,409 required input files; this was an input check,
not a full rendering of 8,415 clips.

Run `python -m unittest discover -s tests -v` and `python tools/check_release.py`.
Tests cover audio recipes, source-frame identity, batched versus single cutting,
resume, changed outputs and preflight errors. The original package verification
reproduced all 82 modified word-audio outputs with matching PCM hashes. Full-frame
cutting is distinct from the previous 25-fps mouth-video experiment: all 8,415
source intervals are eligible, while `historical_roi_included` preserves the
8,414-member historical experiment subset.

Metadata consistency and software tests are not a new semantic audit of every
word. Full-dataset rendering and visual inspection with this portable batch cutter
are not claimed. H.264/AAC output is lossy; bit-identical MP4s across encoders are
not promised. See [formats](DATA_FORMAT.md) and [methods](METHODS.md).
