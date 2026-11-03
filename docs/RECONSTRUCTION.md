# Reconstructing clips without ROI processing

## Inputs and outputs

Download UASpeech through the official access process. `--raw-root` points to the
folder containing the distribution directories named in `source_files.tsv` and
`audio_actions.tsv`, for example `UASpeech_original_FM` and `UASpeech_video_0`.
Do not rename source videos to force a block permutation; a record's `source_key`
already identifies the correct video. Source SHA-256 checks detect a different
file even if its filename matches.

Use a different output directory. No audio/video is downloaded from this repository.
The manifest lists expected outputs, not files that already exist on your computer:

```
outputs/
  audio/<speaker>/<utterance_id>.wav     # reconstructed paired word audio
  video/<utterance_id>.mp4               # full frame, not a mouth crop
  camera_audio/<utterance_id>.wav        # video-aligned embedded speech reference
```

## Frame index and video cutting

Intervals are **zero-based decoded-source-frame ordinals** with an exclusive end:
`[begin_frame, end_frame_exclusive)`. The source rate is 30000/1001 frames/s.
The expected cut length is `end_frame_exclusive - begin_frame` frames, not the
historical 25-fps ROI frame count. The cutter retains this source-frame order and
does not perform face detection, ROI cropping, stabilization or 25-fps resampling.
MP4 uses lossy H.264/AAC encoding; the separate camera WAV is the pre-AAC PCM
reference. The conservative implementation decodes from the start to select
ordinal frames reliably, so large batch reconstruction is slower than approximate
keyframe seeking. A completed build is accompanied by a per-clip JSON receipt.

`block` is the word/audio label group; `source_key` identifies the actual video.
They can differ, particularly for M07. Container timestamps and the review's
source ordinal clock are not interchangeable. The embedded speech reference is
mapped using the recorded clock slope/intercept. Its separate WAV and the MP4
audio let the listener check every cut against the original video speech.

The audio recipe and video frame index are **separate approved instructions**.
A later video-only adjustment does not automatically authorize changing the word
audio. Original word audio can include different leading/trailing silence, so
equal total duration is not imposed, and the microphone waveform is not stretched
to fit the video. Frame quantization also limits sub-frame timing precision.

All 8,415 approved intervals are included as raw cuts. `historical_roi_included`
records the old experimental ROI disposition; only `M16_B3_CW24` has value zero.
For exact historical AV experiment membership, filter that flag, but remember
that these full-frame outputs are still not the old mouth-ROI inputs.
`manifest.csv` contains the expected original-frame counts and rate, while
`speaker_statistics.csv` labels the old totals as `historical_roi_pairs`.

## Reproducing modified audio

Each row in `audio_actions.tsv` is an executable recipe. All target word outputs
are mono PCM16 at 16 kHz. The source is identified by relative path and SHA-256;
the expected decoded output is identified by `output_pcm_sha256`.

| Operation | Reproduction |
|---|---|
| `keep` | Preserve the original selected microphone PCM. |
| `crop` | Slice original microphone PCM at `[begin_sample,end_sample_exclusive)`. |
| `camera_crop` | Decode the selected **full** DivX audio channel to 16 kHz, then slice integer samples. Do not trim before resampling. |
| `camera_clock_interpolate` | Reproduce the calibrated video-to-audio clock sampling described below. |

For clock-interpolated historical outputs, the source coordinate for output sample
`i` is:

```text
source_sample = ((video_start_s + i / 16000 - clock_intercept_s) / clock_slope) * 16000
```

The implementation reproduces the historical linear interpolation, integer
rounding, PCM clipping and explicit zero fill outside recorded bounds. Zero fill
is part of replaying those frozen outputs, not an automatic way to approve new
missing speech. A PCM hash mismatch is an error, not permission to accept an
approximately similar result. The relevant recipe may refer to an earlier
approved audio interval when later edits changed only video.

`channel` is zero-based: `1` selects the second decoded audio channel (`c1`).
M7 is a filename/interface-channel identifier, not this zero-based video channel.
The table's `historical_action` is preserved for provenance but can describe only
the last operation; use `operation` and the explicit source fields for replay.

The October audio-only Whisper experiments used a separate original-microphone
manifest. This package supplies the reconstructed **paired** audio, not an
unannounced replacement for that pure-audio protocol.

## Frozen release versus new proposals

The published tables remain fixed inputs. Waveform matching returns candidates;
it does not change any row, approve a cut, or update the released manifest.
Some inherited `interval_source` / `boundary_approval_status` values describe
earlier stages and contain historical words such as `candidate`. They are kept
as provenance, not used to override the later frozen publication record or to
invent individual human approvals.
For a new dataset version, incorporate reviewed changes explicitly, rerun checks
and create a separately identified release. Do not overwrite the original media.
