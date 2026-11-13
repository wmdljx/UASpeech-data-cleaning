# Verification and limits

This verifies the portable package, not a new assertion that every utterance is
semantically correct. Restricted test outputs remain outside the tracked files.

## Documentation and plotting update — 2026-11-13

- The shorter homepage preserves the previous version in `DETAILED_GUIDE.md`.
  All 15 dysarthric speakers remain, grouped by supplied intelligibility from
  very low to high; no clinical diagnosis or source data was changed.
- All eight unit/integration tests pass, including three new plotting tests for
  amplitude-bin extrema, clock-mapped durations and local-output guards.
- The real `F02_B2_D0` plot was generated locally from licensed inputs and visually
  checked. Original-index SHA-256/line, source-video SHA-256, unchanged word-audio
  PCM hash and corrected-frame metadata are checked by the script. It displays
  the actual recorded waveforms, not synthetic replacements.
- One real static waveform figure is included after owner confirmation of GitHub
  display authorization on 2026-11-13. Its decoded cache stays local. No original
  audio/video, sample arrays or review database is added to the repository.
- Metadata validation still covers 8,415 records across 11 speakers. This update
  changes presentation and adds a plotting example; it is not a new dataset audit.

## Earlier reconstruction checks

- Exported 8,415 unique approved records for 11 speakers; current master CSV/TSV
  hashes match the source release. Shared frame/source/text/split fields match
  the current master. Historical ROI membership is retained separately.
- Original-package inventory: 28 audio speakers (15 dysarthric + 13 controls),
  12 video speakers, nine indexed speakers, 37 DivX files and 25 original index
  files with 6,286 rows. All 28 exported availability rows were cross-checked.
- Every new manifest video-frame count equals the approved end minus start;
  it is not copied from the old 25-fps ROI manifest. Source bounds are checked.
- New audio code reconstructed all **82 changed word-audio outputs**, plus one
  unchanged recording; all decoded PCM hashes match the frozen paired audio.
- Real full-frame test `F02_B2_D3`: 52 frames at 30000/1001 fps, 720×480,
  with selected camera speech in the MP4 and a separate 27,761-sample WAV.
- Five unit/integration tests cover the four audio recipes, NCC polarity reversal,
  relative-path and overwrite protection, and a generated stereo video's cut.
  The generated output's ten frames match source ordinals 4–13 in order.
- Source code contains no ROI/dlib dependency or review-server code. The review
  image is an actual interface screenshot with clearly labeled synthetic signals
  and no licensed video or real-waveform payloads.

Run:

```bash
python -m uaspeech_cut validate
python -m unittest discover -s tests -v
python examples/synthetic_match.py
python tools/check_release.py
```

System tools used for clip tests: FFmpeg/ffprobe. Python dependencies are listed
in `pyproject.toml`; the tested environment used Python 3.10, NumPy 1.23.5 and
SciPy 1.10.1. Exact PCM replay is checked at runtime rather than assuming decoder
versions are interchangeable.

## Not claimed

- The new raw cutter has not rendered and visually inspected all 8,415 clips.
  Full metadata coverage is not a claim of a completed new full-media build.
- Exact bitwise MP4 identity across encoders is not promised; H.264/AAC encoding
  is lossy. The separate PCM reference avoids AAC ambiguity for waveform checks.
- This package does not reproduce the historical ROI video pixels, include ROI
  quality improvement, or establish a recognition benefit from stabilization.
- High NCC or matching durations do not prove correct word identity. Frame-level
  selection remains limited by recording quality and frame quantization.
- Historical review coverage was not independently double-annotated. No saved
  decision is not universally equivalent to an explicit per-item approval.
- A later post-publication review queue had no saved decisions when inspected;
  it is not counted as an independently completed final quality audit.
- Data licenses and human publication approval are not certified by these tests.

The original training data, authoritative indices, experiments and formal review
databases were not modified while creating this package.
