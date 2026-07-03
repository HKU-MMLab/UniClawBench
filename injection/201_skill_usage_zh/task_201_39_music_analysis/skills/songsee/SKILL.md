---
name: songsee
description: Generate spectrograms and feature-panel visualizations from audio with the songsee CLI, and pull out music-information-retrieval features such as tempo, key, beat grid, and section boundaries.
metadata:
  clawdbot:
    emoji: "🎵"
    requires:
      bins:
        - python3
---

# Songsee — Audio / Music Analysis Skill

Use this skill when the user provides an audio file (WAV, MP3, FLAC, OGG)
and needs music-information-retrieval (MIR) outputs: tempo (BPM), musical
key, beat grid, structural section boundaries, or spectrogram-style
visualizations.

## When to apply

- "Analyze this song" / "what BPM is this?" / "what key is this in?"
- "Find the verse and chorus" / "give me the song structure"
- "Plot a spectrogram" / "show me the energy over time"
- Any audio file paired with a request that mentions tempo, beat, key,
  chord, section, structure, intro, verse, chorus, bridge, outro, BPM,
  spectrogram, MFCC, chroma, or onset.

## Recommended approach

The skill leans on standard MIR techniques, implemented directly with
`numpy` and `scipy` if a dedicated `songsee` CLI is not on the PATH.
Both routes are acceptable. If the CLI is missing, fall back to the
in-process Python recipe below — do not silently skip the analysis.

### 1. Tempo (BPM)

- Compute an onset-strength envelope: rectified short-time energy
  difference, smoothed with a 10–20 ms window.
- Autocorrelate the onset envelope; pick the peak in the 0.3–1.2 s lag
  range (corresponds to 50–200 BPM).
- Round to one decimal. Report a tempo confidence ratio (peak / mean).
- For a 4-on-the-floor track the autocorrelation peak should land at
  the expected beat period (e.g. 0.46 s for 130 BPM).

### 2. Musical key

- Build a 12-bin chroma vector by mapping each FFT bin to its pitch class
  via `pc = round(12 * log2(f / C0)) mod 12` with C0 = 16.3516 Hz.
- Aggregate chroma over the whole track (or use overlapping windows and
  average).
- Cross-correlate the normalized chroma against the Krumhansl–Schmuckler
  major and minor key profiles (rotated through all 12 root notes).
- Report the key as `<tonic> <mode>` (e.g. `C major`, `A minor`) using
  the highest-correlation profile. Mention the relative-major /
  relative-minor sibling if the second-best score is within 0.05 of the
  best — they are musically interchangeable in many tracks.

### 3. Section structure

- Compute frame-level RMS energy (windows of ~0.5 s).
- Optionally compute a self-similarity matrix on chroma + MFCCs and
  detect novelty peaks; for short tracks the RMS curve alone is usually
  enough to find boundaries.
- Label sections with the conventional pop-song lexicon: `intro`,
  `verse`, `chorus`, `bridge`, `outro`. A typical short demo will have
  3–6 sections in source order.
- Express section boundaries as `start_sec` / `end_sec` floats; rounded
  to one decimal is fine.

### 4. Output format

Two artefacts are expected when the user asks for a structured analysis:

- A human-readable Markdown file (e.g. `analysis.md`) with the BPM,
  detected key, a section table (start, end, label, duration), and a
  short prose summary of the musical character.
- A machine-readable `sections.json` companion with at minimum:
  ```json
  {
    "bpm": 132.0,
    "key": "E major",
    "sections": [
      {"start": 0.0, "end": 8.0, "label": "intro"},
      {"start": 8.0, "end": 24.0, "label": "verse"}
    ]
  }
  ```

## Anti-patterns

- Reporting integer BPM when the user could benefit from one decimal of
  precision (e.g. 119.8 vs 120.0). Round to one decimal place.
- Silently halving / doubling the tempo. Cross-check against the onset
  spacing on the audible kick / snare pattern.
- Using a single dominant pitch class to declare the key. The key is a
  scale, not a single note — always use a 7-note profile fit.
- Calling everything "verse / chorus" without considering intro and
  outro. Most tracks open and close with sub-energy material that
  deserves its own label.
- Inventing chord progressions or lyrics. Chord transcription is a
  separate, harder MIR task; only report it if the user explicitly asks
  AND the audio is unambiguous.

## Quick recipe (Python fallback)

```python
import numpy as np
from scipy.io import wavfile
sr, x = wavfile.read('song.wav')
x = x.astype(np.float32) / 32768.0
# tempo via onset autocorrelation
abs_x = np.abs(x); win = int(0.01*sr)
env = np.convolve(abs_x, np.ones(win)/win, mode='same')
hop = int(0.005*sr); env_ds = env[::hop]
diff = np.maximum(np.diff(env_ds), 0)
ac = np.correlate(diff, diff, 'full')[len(diff)-1:]
lag = int(np.argmax(ac[int(60/200/0.005):int(60/50/0.005)])) + int(60/200/0.005)
bpm = 60.0 / (lag * 0.005)
```
