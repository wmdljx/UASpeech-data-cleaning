# Corpus contents and source-channel conventions

## Population and availability are version-specific

[The official UASpeech website](https://speechtechnology.web.illinois.edu/uaspeech/)
currently reports 16 dysarthric speakers, compared with 19 in the original
publication, following permission withdrawals and/or damaged data. It does not
publish a current complete speaker-ID inventory on that page. Our licensed input
package contains **15 dysarthric and 13 control speaker directories**. We do not
guess an additional identity or treat a missing local file as evidence that no
other corpus copy contains it.

The nested-set figure in the [README](../README.md) describes this inspected
package **before our reconstruction**:

| Availability | Speaker IDs |
|---|---|
| Audio, no local video: 3 dysarthric speakers | F03, M01, M04 |
| Audio and video, no supplied frame-index files: 3 | M05, M09, M10 |
| Audio and video, with at least some supplied indices: 9 | F02, F04, F05, M07, M08, M11, M12, M14, M16 |
| Audio-only controls in this package: 13 | CF02, CF03, CF04, CF05, CM01, CM04, CM05, CM06, CM08, CM09, CM10, CM12, CM13 |

The audio population is independently consistent with the explicit speaker lists
in [Xiong's UASpeech preparation recipe](https://github.com/ffxiong/uaspeech/blob/master/s5/local/prepare_uaspeech_data.sh).
The video and index memberships were checked directly against both supplied
video-package directories. Their machine-readable form is
[speaker_availability.csv](../metadata/speaker_availability.csv).

There are **37 DivX files for 12 speakers**: three nominal blocks per speaker,
plus a second M07 B2 file. File presence does not establish a correct or complete
recording. In particular, the available M10 material did not provide a verified
target B2 recording, so M10 is not in our eleven-speaker reconstruction.

## Words and supplied indices

For a consolidated account of each speaker's coverage gap and reconstruction
outcome, see [speaker coverage, major issues and repairs](../README.md#speaker-coverage-major-issues-and-repairs).

The full recording protocol has three blocks of 255 utterances. Each contains
10 digits, 26 radio-alphabet words, 19 commands, 100 common words and 100
block-specific uncommon words. The first 155 items repeat across blocks; the
300 uncommon items do not. Thus **765 utterances are not 765 distinct word
types**. The common B1/B3 development and B2 test convention is documented in
the supplied README and the linked preparation recipe. See
[Kim et al. (2008), Sections 2.1–2.2](https://www.isca-archive.org/interspeech_2008/kim08c_interspeech.pdf)
for the recording design.

Our source package contains 25 original frame-index files and 6,286 indexed rows:

| Speaker | B1 | B2 | B3 | Total |
|---|---:|---:|---:|---:|
| F02 | 255 | 254 | absent | 509 |
| F04 | 255 | 255 | 254 | 764 |
| F05 | 255 | 255 | 255 | 765 |
| M07 | 255 | 255 | 255 | 765 |
| M08 | 255 | 255 | 255 | 765 |
| M11 | 255 | 255 | 171 | 681 |
| M12 | 255 | 252 | absent | 507 |
| M14 | 255 | 255 | 255 | 765 |
| M16 | 255 | 255 | 255 | 765 |

The bundled `readme_UASpeech.txt` states that the supplied frame indices were
automatically extracted from DTMF audio and had not been manually verified.
Their presence is therefore not a correctness guarantee. The **6,246 historical
experimental records** audited in this project are a different baseline; do not
use that number as the original-index file count.

## Array recordings, embedded speech and synchronization beeps

The apparatus used an eight-channel recording system. According to the bundled
README, M1 was generally reserved for DTMF synchronization tones; M2–M8 are the
usual seven speech channels. The delivered word WAVs separate these channels.
Some speakers have fewer available microphone channels. Our target word recording
is **M7**, a channel identifier in the word filename, not a seventh video track.

The original paper explains that the eighth microphone's speech signal and the
DTMF tones were fed to the video camera. Accordingly, **camera audio** in this
repository means the speech signal embedded in the original DivX, not an assumed
independent microphone built into the camera. The beep signal provides
synchronization cues; it is not the target speech.

All 37 inspected DivX files have one video stream and one stereo audio stream:
the reported video rate is 30000/1001 fps and the embedded audio rate is 44.1 kHz.
In most files, the first audio channel (`c0`, zero-based) carries DTMF and the
second (`c1`) carries speech. This is **not a universal channel-order rule**:
spot checks of M09's three recordings did not show the same tone-dominated first
channel. The supplied `DVtone` companion WAVs also vary and are not used as an
unverified replacement for the embedded speech.

Our per-source metadata explicitly selects `channel=1` for all 33 long-video
sources used by the reconstruction. For one such source, this extracts the
second channel without mixing in the first:

```bash
ffmpeg -i source.divx -map 0:a:0 -af 'pan=mono|c0=c1' -ar 16000 -c:a pcm_s16le speech.wav
```

Do not replace this channel selection with a generic stereo-to-mono downmix.
Also distinguish the video-frame clock from the decoded-audio clock: the stored
clock mapping and reconstruction recipe handle applicable offsets. Calling the
embedded audio the synchronization reference does not assert zero timing error
in every container or decoder.

## Recheck your source package

From the repository root, run the read-only inventory tool:

```bash
python tools/inspect_source_package.py --raw-root /path/to/uaspeech_ORIGIN
python tools/inspect_source_package.py --raw-root /path/to/uaspeech_ORIGIN --probe
```

The expected root contains `UASpeech_original_FM`, `UASpeech_original_C`,
`UASpeech_video_0` and `UASpeech_video_1`. The default mode counts speaker IDs,
microphone filenames and original-index rows. `--probe` additionally reads
video/audio headers using ffprobe. Both print JSON to standard output and never
modify source files. Header inspection does not identify which channel contains
speech, establish lexical correctness, or prove that nominal recording blocks
are distinct.

The official access and redistribution restrictions remain applicable. These
links and aggregate inventory checks do not redistribute the source corpus.
