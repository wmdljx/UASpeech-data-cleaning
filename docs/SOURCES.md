# Sources, claim scope and implementation provenance

Checked on 2026-11-03. The source checks below are automated/file-based and
assistant-assisted cross-checks; this document does not invent a human sign-off.
The owners retain final scientific and publication approval. Restricted source
documents and media are not copied into this repository.

| Evidence ID | Source / locator | Supports |
|---|---|---|
| E1 | [Official UASpeech page](https://speechtechnology.web.illinois.edu/uaspeech/), opening description and access conditions | Current website reports 16 dysarthric speakers; original 19; access/redistribution restrictions. Does not enumerate current complete IDs. |
| E2 | [Kim et al. (2008)](https://www.isca-archive.org/interspeech_2008/kim08c_interspeech.html), Sections 2.1–2.2; [PDF](https://www.isca-archive.org/interspeech_2008/kim08c_interspeech.pdf) | Recording apparatus, eighth microphone and DTMF fed to camera, block/word design. The original 19-person description is not a current inventory. |
| E3 | Licensed package `UASpeech_original_FM/UASpeech/readme_UASpeech.txt`, Directories / Naming Convention / Train-Test Split; original audio/video/index files | Usual M1 tones/M2–M8 speech; original indices automatically extracted and not manually verified; locally inspected speaker memberships and original index counts. |
| E3b | [Independent UASpeech preparation recipe](https://github.com/ffxiong/uaspeech/blob/master/s5/local/prepare_uaspeech_data.sh), speaker-set declarations | Independent support for the same 15 dysarthric and 13 control IDs; does not prove local video availability. |
| E4 | Frozen historical 6,246-record audit; portable [legacy_audit.csv](../metadata/legacy_audit.csv) | Historical affected-record counts, categories and processing decisions, not a new quality census of the eleven-speaker set. |
| E5 | Approved master revision `master_v3_media_published_20260912`; master fingerprints in [release.json](../metadata/release.json) | Final source identities, approved boundaries, paired-audio identity and historical ROI membership. |
| E6 | Original-index inventory and final supplemental-index flags; [frame_index.tsv](../metadata/frame_index.tsv), [speaker_availability.csv](../metadata/speaker_availability.csv) | 6,286 original index rows; 2,129 reconstructed missing indices; final 8,415 records. |
| E7 | Decoder/header checks of all 37 source DivX files; speech-channel checks and stored 33-source mappings | Stereo 44.1-kHz streams, nominal 30000/1001 fps, explicit speech-channel selection and clock mapping. Tone dominance is not asserted universally. |
| E8 | Tests and isolated reconstruction runs described in [VERIFICATION.md](VERIFICATION.md) | What this portable implementation has actually been tested to reproduce. |

## Distinguishing findings from release mechanics

The authors' current manuscript and earlier laboratory reports informed the
organization of findings. Numbers were checked against the actual audit and
master tables rather than treating prose as the sole authority. Historical repair
descriptions were translated into English for this package; the archived audit
fingerprint is preserved. The approved data was not changed during packaging.

The October Clean and Babble nine-cell experiment plans pin the same three AV
manifests as the current approved release. Startup provenance for all 18 runs
contains 54 matching split-file hashes. The audio-only Whisper manifests are a
separate view and do not imply identical audio preprocessing for every item.

## Implementation sources and deliberate changes

- Word-audio replay retains the verified source/crop/clock arithmetic of the
  accepted internal reconstruction stages 66/70/80/93. All 82 changed PCM outputs
  are checked by hash. It is not a new denoising or speech-generation method.
- NCC retrieval follows the accepted stage-90 waveform re-audit principles:
  4-kHz signals, mean-centered normalized correlation and separated candidate peaks.
  The small public example is not presented as the entire historical search workflow.
- The new full-frame cutter selects approved source ordinals and re-encodes them
  with an explicitly selected, clock-mapped speech track. It does not reproduce
  the prior mouth-ROI representation or include AV-HuBERT/dlib code or models.
- The screenshot uses the existing review interface. Its synthetic waveform
  display is labeled; no original faces, playable audio, video, or true corpus
  waveform payloads are redistributed. Review source/SQLite records stay private.

Versioned metadata, source hashes and the read-only inventory script support
independent checking. They are not a claim that all semantic decisions have been
independently replicated by a second annotator.

## References and development assistance

Kim, H., Hasegawa-Johnson, M., Perlman, A., Gunderson, J., Huang, T., Watkin, K.,
and Frame, S. (2008). *Dysarthric Speech Database for Universal Access Research*.
Interspeech, 1741–1744. [Official bibliographic record](https://www.isca-archive.org/interspeech_2008/kim08c_interspeech.html).

Repository packaging and documentation were AI-assisted. The scientific-writing
procedure from Scientific Agent Skills guided source/claim separation and bounded
verification statements; it is **not evidence for the alignment results**:
Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. (2026).
*Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*.
[arXiv:2609.00065](https://arxiv.org/abs/2609.00065).

Code licensing and contributor attribution remain pending owner confirmation.
No individual is added to the scientific author list by this development note.
