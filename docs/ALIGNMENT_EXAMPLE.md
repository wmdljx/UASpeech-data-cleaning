# A wrong video interval: F04_B3_UW14 — lawyer

The microphone recording contains “lawyer” and is retained unchanged. The supplied
frame index points to a later interval in the same source video.

| Record | Source frames |
|---|---|
| Original listed bounds for lawyer | 18354–18509 |
| Corrected lawyer interval | [18282,18350) |
| Corrected neighboring Missouri interval | [18353,18505) |

Source: `F04-B3-DV-1.divx`, identified as `F04_B3` in the source table. The old
lawyer interval nearly coincides with the corrected Missouri interval. A one-frame
boundary-convention difference cannot explain this change of word position.

## Reproduce the comparison locally

After installing this repository and FFmpeg:

```bash
python -m pip install matplotlib
python examples/plot_alignment_case.py \
  --raw-root /path/to/uaspeech_ORIGIN \
  --output ./local/F04_B3_UW14-waveforms.png
```

The three panels show:

1. **Word-level microphone recording:** the unchanged word audio.
2. **Video speech audio — original frame index:** the speech track cut using
   the original listed bounds.
3. **Video speech audio — corrected frame index:** the same source track cut
   using the frozen corrected bounds.

The horizontal axis is seconds from the start of **each clip**, not absolute
recording time. Each waveform is scaled to its own peak to make different
recording levels legible; heights cannot be used to compare recording loudness.
Per-bin minima and maxima retain waveform peaks at display resolution. No extra
time shift, time stretching or padding is fitted to improve similarity; only the
recorded video/audio clock mapping is applied. The signals are not denoised.
Different microphone paths and background noise remain visible even when the
utterance corresponds. No similarity score is presented as a correctness probability.

Video speech is extracted using the recorded speech channel and video/audio
clock mapping. Original listed bounds are replayed using this repository's
zero-based, end-exclusive convention; the supplied index does not itself state
that convention. Output durations are about 2.262 s (word audio), 5.172 s (old
video interval), and 2.269 s (corrected video interval).

The script validates source hashes and the corrected frame interval. It refuses
existing outputs and requires local images inside the checkout to go under
ignored `local/` or `outputs/`. Its decoded audio cache is also local. Do not
upload the generated figure or cache without the required permission.

## Evidence

- Original file: `UASpeech_video_0/UASpeech/video/F04/F04_B3_frame_index.txt`,
  line 173, `F04_B3_UW14 18354 18509`. The file fingerprint is recorded in
  [alignment_case.json](../examples/alignment_case.json).
- Corrected word and interval: [frame_index.tsv](../metadata/frame_index.tsv),
  `F04_B3_UW14`; neighboring corrected record: `F04_B3_UW15`.
- Unchanged word recording: [audio_actions.tsv](../metadata/audio_actions.tsv),
  `F04_B3_UW14`, operation `keep`.
- Historical old interval: [legacy_audit.csv](../metadata/legacy_audit.csv).
- Source identity and clock coefficients: [source_files.tsv](../metadata/source_files.tsv),
  `F04_B3`.

The example was chosen for lower visible background noise and a clear difference
between old and corrected speech patterns; it is not representative sampling.
An exploratory 4-kHz waveform search, allowing candidate starts within ±0.20 s of
each clock-mapped interval start, gave best absolute correlations of 0.104 (old)
and 0.862 (corrected). These searches allow small offsets and are not direct
zero-lag comparisons of the displayed panels. They are neither percentages nor
acceptance thresholds. No filtering was applied to the plotted signals.

This is a documented example, not a random evaluation sample or an estimate of
residual errors. Source-file checks and figure generation were performed on
2026-11-13; the release metadata was not changed.

## Display rights

The bundled UASpeech license permits waveform illustrations in professional
conferences and journals with a citation to Kim et al. (2008); GitHub display is
not explicitly covered by that clause. On 2026-11-13, the project owner confirmed
authorization for GitHub waveform display, then requested a quieter replacement
example. The figure, case metadata and plotting code are included; recordings
and decoded caches are not. This confirmation does not grant readers
redistribution rights over their generated media.

The original Zero example is retained as
[alignment_case_zero.json](../examples/alignment_case_zero.json) and
[its figure](assets/alignment-case.png); pass that JSON through `--case` to
reproduce it. The older synthetic illustrations remain labeled in the archived guide.
