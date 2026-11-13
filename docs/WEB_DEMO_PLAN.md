# Interactive viewer — proposal

Not implemented. The first version should help readers inspect repairs and
reconstruct a sample, not add another annotation system.

- **Overview:** the speaker-set figure and grouped speaker table, with filters
  for speaker, recording block and issue type.
- **Sample detail:** the word, original and corrected video source/frames,
  audio action and a link to the supporting record.
- **Waveforms:** three labeled tracks—word-level microphone recording, video
  speech audio from the original index, and video speech audio from the corrected
  index. A shared cursor supports comparison; clip boundaries and time origins
  remain visible. A zoom control allows frame-level inspection.
- **Licensed media stay local:** the hosted page contains metadata only. Readers
  select their own licensed files in the browser or run a local viewer; files
  must not be uploaded, logged, or included in analytics. Playback is opt-in.
- **Reconstruction:** copy a per-sample command or download a filtered index.
  Any future review notes are stored locally and do not silently alter the frozen
  release.

Start with one sample, `F02_B2_D0`, then add the full metadata table. A browser
prototype must test file permissions and local media decoding before promising
support for original DivX files; an optional local service may be needed.

Public waveform images require a separate rights check. The existing manual
review tool and its database are not included in this repository.
