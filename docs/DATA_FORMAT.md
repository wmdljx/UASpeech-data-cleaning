# File and field reference

The four reconstruction tables are frozen inputs, each with 8,415 rows except
`source_files.tsv` (33 source videos). `release.json` records their hashes and the
upstream data revision. Packaging changes do not change approved sample intervals.

| File | Fields used for reconstruction |
|---|---|
| `frame_index.tsv` | `utterance_id`, `source_key`, `begin_frame`, `end_frame_exclusive` |
| `manifest.csv` | `audio_path`, `video_path`, `camera_audio_path`, expected sample/frame counts and rates |
| `audio_actions.tsv` | `operation`, input/output paths and hashes, sample interval or video-clock recipe |
| `source_files.tsv` | `source_key`, `path`, `sha256`, `frames`, `fps_num/den`, `channel`, `clock_slope`, `clock_intercept_s` |

IDs join the word-level tables. `speaker`, `block`, `word_id`, `word_class` and
`text` describe the utterance. `block` is the word/audio group; `source_key` is
the actual video and can name a different group, notably for M07. `split` retains
the inherited experimental label; this tool does not define a new evaluation protocol.
All file paths are relative to the specified input/output root.

## Frames and camera speech

Frames are zero-based decoded source-frame ordinals, with half-open bounds
`[begin_frame,end_frame_exclusive)`. The frame count is `end-begin`; source rate
is 30000/1001 fps. Full-frame outputs retain that rate and order, rather than the
old 25-fps mouth representation. `channel=1` selects the second channel of the
first embedded audio stream, without mixing the speech with synchronization tones.

The mapping is `video_time = clock_slope * decoded_audio_time + clock_intercept_s`.
For camera samples on the video timeline, output sample `i` is read at:

```text
source_sample = ((video_start_s + i/16000 - clock_intercept_s) / clock_slope) * 16000
```

Camera-channel audio is decoded in full to 16 kHz before cropping/interpolation.
The recorded mapping handles offsets between decoded audio and frame time; camera
speech being a reference does not imply that every decoder has zero offset.

## Word-audio operations

| `operation` | Meaning |
|---|---|
| `keep` | Retain selected original microphone PCM. |
| `crop` | Slice microphone samples at `[begin_sample,end_sample_exclusive)`. |
| `camera_crop` | Slice the full decoded camera speech channel at the recorded sample bounds. |
| `camera_clock_interpolate` | Replay the mapping above with linear interpolation, rounding and PCM16 clipping. |

All outputs are mono PCM16 at 16 kHz. `output_pcm_sha256` covers decoded PCM bytes,
not the WAV header. A mismatch is an error. Historical clock interpolation includes
zero fill outside recorded bounds; this replays the approved output and does not
authorize filling missing target speech in new samples. Microphone audio is not
time-stretched to match the video. Leading/trailing silence and frame quantization
can produce different word-WAV and video durations.

## Historical fields are not new approval decisions

`interval_source`, `boundary_approval_status`, `canonical_origin`, `master_revision`
and `historical_action` preserve provenance. Some contain earlier stage names such
as `candidate`; they do not override the final exported interval, nor establish a
new individual human sign-off. `original_index_missing` marks reconstructed original
index gaps. `cut_included` is the raw-cut membership flag. `historical_roi_included`
and `historical_roi_exclusion_reason` describe the old mouth-video experiment;
only M16_B3_CW24 is excluded from that historical experiment, not from raw cuts.

The historical audit (6,246 records), original index inventory (6,286 rows), and
current output (8,415 records) are distinct populations. Detailed audit tables
remain in the [archived full version](https://github.com/wmdljx/UASpeech-data-cleaning/tree/archive/detailed-2026-11-13).
