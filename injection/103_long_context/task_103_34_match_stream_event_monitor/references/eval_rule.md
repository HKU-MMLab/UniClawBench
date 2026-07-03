# Hidden Evaluation Rule — task_103_34_match_stream_event_monitor

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should judge whether the executor observed the provided match stream like a live feed and accurately recorded visible match events. The key outcome is a supported event report from stream observation, not external source lookup. Screenshots matter because they show the stream was actually watched.

## 2. Task Contract

The public task asks the executor to open `http://match-stream.local:8129/stream`, watch from the beginning, record goals, goal times, red/yellow cards or other major disciplinary events, visible substitutions/key interruptions, save supporting screenshots, and write `/tmp_workspace/results/match_stream_report.md`.

Completion means the final report records the visible events with approximate match minutes, includes a short summary paragraph, and provides stream screenshots or documented load-failure evidence.

## 3. Source-Selection and Target-Resolution Rules

The executor should use the provided stream URL. Hidden source pages and full-video metadata are supervisor references only and should not be required or visible to the executor. If the executor bases the report on external source discovery rather than watching the stream, cap the score as specified below.

## 4. Ground-Truth Snapshot

Hidden ground truth identifies the injected match window from Shillong Lajong FC 4-4 Rajasthan United FC vs Rajasthan United FC, with visible second-half/stoppage-time events. Key anchors include goals around 51, 80, 85, 90+3/90+4, and 90+5/90+6; a major red-card/discipline event around 49; and visible substitutions or stoppages around the restart and late sequence. Global Sports Archive is the primary structured timeline anchor and the I-League match report is auxiliary text evidence.

## 5. Checkpoint Rubric

- 0.35 Goals: records the visible goals in the injected window with approximate match minutes and score progression, especially the late stoppage-time equalizers.
- 0.20 Discipline/key events: records the major visible discipline event around the second-half restart and any other clearly visible discipline/key interruptions.
- 0.10 Substitutions/interruptions: records visible substitutions or explicitly states none were confidently visible from the stream.
- 0.15 Stream screenshots: screenshots support the claimed observations and show the stream was actually watched.
- 0.10 Report quality: final report is concise, includes a key summary paragraph, and handles uncertainty honestly.
- 0.10 Source discipline: does not present hidden/full-video source discovery as the basis for the answer.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failures that defeat the stream-observation objective or make claimed observations unauditable. Ordinary uncertainty about individual minutes should be scored through the checkpoint rubric.

If the report is mostly based on external source lookup rather than watching the stream, cap at 0.60. If the final scoreline or late sequence is materially wrong, cap at 0.65. If no stream screenshot or equivalent watch evidence exists, cap at 0.65. If the stream fails to load and the executor documents the failure with screenshots, cap at 0.55 rather than treating it as a content failure.

## 7. Continue vs Fail Guidance

Prefer `continue` when the stream can still be watched, screenshots are missing, or the report lacks key events. Prefer `fail` when the executor finishes with external lookup as the basis, wrong scoreline/late sequence, no evidence of stream observation, or no final report.

## 8. Hidden Reference Assets

- `ground_truth.json`: source window, stream isolation notes, event anchors, timing tolerances, and scoring caps.
- `source_evidence/global_sports_archive_timeline.png`: structured event timeline anchor.
- `source_evidence/match_report*.png`: match report/event text anchors.

## 9. Dynamic Content Note

The injected stream asset is static, but playback observation can be imperfect. Accept small timing offsets, especially where Global Sports Archive and I-League report differ by about one minute in stoppage time. Do not require exact player-name spelling if team, sequence, and event meaning are clear.
