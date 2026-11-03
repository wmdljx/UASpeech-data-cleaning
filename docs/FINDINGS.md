# Findings, denominators and repair decisions

The primary account is simple: use the original long video's embedded speech as
the synchronization reference, retain valid word recordings, repair their video
associations, and reconstruct missing indices. Change word audio only where the
approved source/content checks require it. [Sources E4–E6](SOURCES.md)

## Historical mismatches

The frozen historical audit contains 6,246 records for nine speakers. It confirms
1,246 affected records (19.9488%). This is not the error rate of the entire
official UASpeech distribution, nor the residual error rate of our current data.
The original recordings, original indices, historical processed subset and later
laboratory outputs are distinct stages; a processing error is not automatically
an error introduced by the corpus creators.

| Speaker | Historical records | Confirmed affected | Percentage | Dominant observation |
|---|---:|---:|---:|---|
| F02 | 509 | 256 | 50.29% | Cascade-like word/video interval shift, particularly B2 |
| F04 | 764 | 182 | 23.82% | Cascade-like word/video interval shift, particularly B3 |
| F05 | 761 | 19 | 2.50% | Isolated content or interval problems |
| M07 | 765 | 765 | 100.00% | Cross-block video-source association |
| M08 | 765 | 3 | 0.39% | Isolated content or interval problems |
| M11 | 655 | 1 | 0.15% | Historical excluded item; not the later supplemental audit |
| M12 | 499 | 1 | 0.20% | Isolated audio/content issue |
| M14 | 765 | 13 | 1.70% | Local boundary or coverage problems |
| M16 | 763 | 6 | 0.79% | Local boundary or coverage problems |
| Total | 6,246 | 1,246 | 19.95% | Non-overlapping affected-record total |

F02/F04's 438 total affected records include 431 assigned specifically to the
cascade category (253 and 178). Combined with M07's 765 source-association records,
the systematic categories total 1,196/6,246 (19.15%). The remaining 50 are other
historical categories. Audio changes overlap these categories; they are not an
additional quantity to add to 1,246.

M07's main block permutation has local exceptions: B1 audio uses B3 video for
249 records and B2 video for six; B2 audio uses B1 video for all 255; B3 audio uses
B2 video for 211 and B1 video for 44. Always use each row's `source_key`.
This identifies the corrected associations, not proof of a particular file-renaming
mistake by the original data collector.

## Missing indices and additional coverage

The inspected original index files contain 6,286 rows for nine speakers. The
historical experimental audit has 6,246 records and its released AV subset had
6,245 pairs. They are not interchangeable baselines.

| Speaker | Reconstructed previously missing indices |
|---|---:|
| F02 | 256 |
| F04 | 1 |
| M05 | 765 |
| M09 | 765 |
| M11 | 84 |
| M12 | 258 |
| Total | 2,129 |

M05 and M09 have complete three-block recordings but no original word frame
indices in our source package. Each contributes 765 records. F02 and M12 also
lack B3's 255 original indices; additional historical exclusions account for
their earlier experimental totals of 509 and 499. Some previously indexed
records were absent from the older experimental subset and were restored too.
Thus “missing original index” is different from “missing from the old experiment.”

The reconstruction contains 11 × 765 = 8,415 approved intervals. M10 is excluded
because the actual target B2 recording was not verified among the available
files. We do not claim it cannot exist in another corpus copy.

## Small audio and boundary exceptions

Some recordings contained staff prompts, conversation or non-target attempts.
Overlong recordings were reviewed rather than automatically truncated by a
duration threshold. Where the original word recording contained the target,
approved non-target material could be removed. Where the correct utterance was
only reliably identified in the video's speech reference, the corresponding
camera-track segment was used. Local overlaps and incomplete onset/offset
coverage were resolved through the same listening, waveform and frame review.

The current paired-audio recipes contain 8,333 `keep`, 43 `crop`, six `camera_crop`
and 33 `camera_clock_interpolate` operations. These **82 changed PCM outputs are
transformation counts**, not an independent error census. The earlier nine-speaker
audit's 41 revised audio files is a different historical scope.

The historical mouth-localization exclusion `M16_B3_CW24` is retained as a flag.
This no-ROI package still provides its valid full-frame interval. It does not
silently change the approved historical 8,414-pair ROI experiment population.

The [sample-level audit](../metadata/legacy_audit.csv) and
[speaker statistics](../metadata/speaker_statistics.csv) retain historical scope
and statuses. Their historical dispositions are not current build instructions.
