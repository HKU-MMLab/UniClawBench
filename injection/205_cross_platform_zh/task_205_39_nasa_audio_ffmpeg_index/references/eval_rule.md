# Hidden Evaluation Rule — task_205_39_nasa_audio_ffmpeg_index

## 1. Grading Philosophy

Grade from saved audio files, `clip_manifest.json`, waveform PNG,
report, transcript/tool evidence, and hidden `ground_truth.json`.

## 2. Task Contract

Required outputs:
- `/tmp_workspace/results/clip_manifest.json`
- `/tmp_workspace/results/clips/clip_01.mp3`, `clip_02.mp3`, `clip_03.mp3`
- `/tmp_workspace/results/nasa_audio_briefing.mp3`
- `/tmp_workspace/results/nasa_audio_waveform.png`
- `/tmp_workspace/results/nasa_audio_report.md`

## 3. Checkpoint Rubric

Checkpoints, total 1.00:
- 0.14 Required outputs and media validity: files exist, are non-empty,
  `ffprobe` can read the MP3 outputs, and waveform is a valid PNG.
- 0.22 Segment extraction: each clip is cut from the expected source
  file, in the requested order, with duration within
  `duration_tolerance_seconds` of ground truth.
- 0.16 Compilation correctness: final briefing concatenates the three
  clips in expected order, with total duration close to the sum of target
  durations and no extra long silence.
- 0.14 Manifest completeness: JSON lists source file, source title,
  start_seconds, duration_seconds, output_file, measured_duration, and
  sha256 or size for each generated clip.
- 0.10 Waveform/contact evidence: waveform or spectrogram image
  represents the final compilation or the three clips, not an unrelated
  placeholder.
- 0.10 Report quality: report names the three NASA clips, gives source
  page/provenance, explains the editing command or workflow, and notes
  final duration.
- 0.08 CLI/tool evidence: transcript/tool usage shows ffmpeg/ffprobe or
  equivalent media tooling used; a text-only answer cannot earn this.
- 0.06 Cross-artifact consistency across manifest, filenames, report,
  and measured durations.

## 4. Scoring Policy / Score Caps

Caps:
- Cap at 0.55 if the final compilation MP3 is missing or unreadable.
- Cap at 0.65 if fewer than three individual clips are produced.
- Cap at 0.75 if outputs are copied full source files rather than
  trimmed segments.
- Cap at 0.50 if the task uses unrelated audio sources.
