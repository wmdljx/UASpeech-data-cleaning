# Alignment method and evidence

## Reference and matching

We use the speech channel embedded in a long DivX video to locate the matching
word recording on the video timeline. Word-level microphone audio is the primary
query unless inspection identifies non-target material or the wrong utterance.
The original apparatus fed a speech microphone and synchronization tones to the
camera: "camera speech" describes the embedded speech track, not necessarily a
microphone built into the camera. Speech and tones must not be downmixed together.

The matching example converts both signals to 4 kHz, subtracts the mean and
computes normalized cross-correlation with FFT correlation and running sums.
For each candidate offset, the score is the absolute dot product of the centered
waveforms divided by their norms. Absolute correlation allows polarity inversion.
Separated peaks give alternative candidates; silence has no usable correlation.
The score is waveform similarity, not a probability of correct word identity.

The homepage diagram summarizes the decisions: compare the existing interval,
retain a valid match, or search all recording blocks of the same speaker and
review a new location. Missing indices enter the search directly. Historical
supplemental checks also computed local and global matches for every sample;
their 0.30 low-correlation flag was stage-specific, not a universal pass threshold.
Word order, neighboring intervals and source identity help reject wrong repeats
and overlaps. Ambiguous cases were listened to and checked frame by frame with
our custom review tool. That tool and its review database are not distributed here.

## Try the matching example

After installation, use authorized mono PCM16/16-kHz query and full camera-speech
WAVs. Select the speech channel from `source_files.tsv`, for example:

```bash
ffmpeg -i source.divx -map 0:a:0 -af 'pan=mono|c0=c1' -ar 16000 -c:a pcm_s16le speech.wav
python examples/match_waveforms.py word.wav speech.wav --start 100 --end 150 --clock-slope 1.000 --clock-intercept -0.04
```

The times/clock values above are illustrative: use the source's recorded values.
Results are candidate start positions, not approved start/end boundaries. Matching
does not edit the final tables. To reconstruct the published repairs, run `build`;
there is no need to repeat discovery or manual review.

## Homepage example: F04_B3_UW14, lawyer

The original `F04_B3_frame_index.txt`, line 173, lists frames 18354–18509.
The final interval is [18282,18350); the adjacent Missouri recording is
[18353,18505). Source word labels are LAWYER and MISSOURI in `F04_word.mlf`.
The original index does not explicitly document its zero/one-based convention;
replaying its bounds in this repository's convention cannot explain away a
whole-word shift through a one-frame ambiguity.

The plot compares the unchanged 2.262-s word recording, the 5.172-s old camera
interval and the 2.269-s corrected interval. Rows start at their own clip boundaries
and are scaled to their own peaks. No denoising, fitted time shift or stretching
is used. The script verifies the source/index hashes and approved metadata;
`examples/alignment_case.json` stores the case identifiers and bounds.

```bash
python -m pip install -e '.[plot]'
python examples/plot_alignment_case.py --raw-root /path/to/uaspeech_ORIGIN --output ./local/lawyer.png
```

## Sources and scope

- [UASpeech official site](https://speechtechnology.web.illinois.edu/uaspeech/): access and corpus description. Website population counts and the inspected source files are not interchangeable inventories.
- [Kim et al., Interspeech 2008](https://www.isca-archive.org/interspeech_2008/kim08c_interspeech.html), Sections 2.1–2.2: recording apparatus and word/block design.
- Authorized package `readme_UASpeech.txt`, word lists, microphone WAVs, DivX files and original indices: source inventory and channel conventions. The supplied README says original indices were automatically extracted and not manually verified.
- [Archived audit and source account](https://github.com/wmdljx/UASpeech-data-cleaning/tree/archive/detailed-2026-11-13): the 6,246-record historical audit, per-speaker statistics, original index inventory and implementation provenance.
- `metadata/release.json`: approved master revision and fingerprints; four current reconstruction tables are unchanged by the packaging simplification.

The 19.95% figure describes affected records in the historical nine-speaker audit,
not an error rate for all official recordings or the residual error rate of the
current set. The 2,129 recovered indices are a separate count. The M07 mapping is
predominant, not universal: use per-row source keys. Audio replacement/cropping
counts overlap historical issue categories and must not be added to them.
High waveform similarity alone does not prove correct lexical content, and the
historical reviews were not independently double-annotated. This repository
replays the final decisions; it does not claim automatic reproduction of every
historical human judgment.
