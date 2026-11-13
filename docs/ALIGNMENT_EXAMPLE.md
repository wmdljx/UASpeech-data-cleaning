# A wrong video interval: F02_B2_D0 — Zero

The microphone recording contains “Zero” and is retained unchanged. The supplied
frame index points to a later interval in the same source video.

| Record | Source frames |
|---|---|
| Original listed bounds for Zero | 236–344 |
| Corrected Zero interval | [145,232) |
| Corrected neighboring Six interval | [236,340) |

Source: `F02-B2-DV-1.divx`, identified as `F02_B2` in the source table. The old
Zero interval nearly coincides with the corrected Six interval. A one-frame
boundary-convention difference cannot explain this change of word position.

## Reproduce the comparison locally

After installing this repository and FFmpeg:

```bash
python -m pip install matplotlib
python examples/plot_alignment_case.py \
  --raw-root /path/to/uaspeech_ORIGIN \
  --output ./local/F02_B2_D0-waveforms.png
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
that convention. Output durations are about 2.908 s (word audio), 3.604 s (old
video interval), and 2.903 s (corrected video interval).

The script validates source hashes and the corrected frame interval. It refuses
existing outputs and requires local images inside the checkout to go under
ignored `local/` or `outputs/`. Its decoded audio cache is also local. Do not
upload the generated figure or cache without the required permission.

## Evidence

- Original file: `UASpeech_video_0/UASpeech/video/F02/F02_B2_frame_index.txt`,
  line 7, `F02_B2_D0 236 344`. The file fingerprint is recorded in
  [alignment_case.json](../examples/alignment_case.json).
- Corrected word and interval: [frame_index.tsv](../metadata/frame_index.tsv),
  `F02_B2_D0`; neighboring corrected record: `F02_B2_D6`.
- Unchanged word recording: [audio_actions.tsv](../metadata/audio_actions.tsv),
  `F02_B2_D0`, operation `keep`.
- Historical old interval: [legacy_audit.csv](../metadata/legacy_audit.csv).
- Source identity and clock coefficients: [source_files.tsv](../metadata/source_files.tsv),
  `F02_B2`.

This is a documented example, not a random evaluation sample or an estimate of
residual errors. Source-file checks and figure generation were performed on
2026-11-13; the release metadata was not changed.

## Display rights

The bundled UASpeech license permits waveform illustrations in professional
conferences and journals with a citation to Kim et al. (2008); GitHub display is
not explicitly covered by that clause. On 2026-11-13, the project owner confirmed
authorization for GitHub display of this static example figure. The figure,
case metadata and plotting code are included; recordings and decoded caches are
not. This confirmation does not grant readers redistribution rights over their
generated media. The older synthetic illustrations remain labeled in the archived guide.
