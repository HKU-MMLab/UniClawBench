# Hidden Evaluation Rule — task_104_25_olympic_badminton_final_points

## 1. Grading Philosophy

Judge the executor on two concrete outcomes:

1. The written summary identifies the exact five Olympic men's singles
   badminton finals in the locked historical ground truth and reports
   explicit last-point timestamps.
2. The saved video clips visibly contain the actual final scoring rally for
   each final, from serve or rally start through the scoring moment.

Do not award high scores for plausible filenames, polished prose, final-score
lookup, or self-reported confidence unless the clips themselves are auditable.
The known failure mode for this task is saving footage near the end of the
video that shows warm-up, intro graphics, score overlays, post-match
celebration, handshakes, interviews, or medal ceremony rather than the final
point. Those clips do not satisfy the task contract.

## 2. Task Contract

The user asked the executor to search YouTube for the last five Olympic men's
singles badminton finals, actually watch match videos or official highlights,
locate the last point in the deciding/final game, and save both the summary
and clipped video evidence.

Required outputs:

- `/tmp_workspace/results/olympic_finals_summary.md`
- Five `.mp4` clips under
  `/tmp_workspace/results/olympic_final_points/`, one per canonical final

The summary must cover, for each final:

- year / Olympic edition
- finalists and winner
- final match score
- watched source video title or URL
- explicit last-point start and end timestamps in the watched source video
- brief description of the final rally / scoring moment

Filenames may vary, but each required clip should be identifiable by year and
finalists. Source URLs/titles are useful for auditability but are not a
substitute for correct clip content.

## 3. Locked Ground Truth

Grade against `references/ground_truth.json`. The canonical answer set is fixed
and contains exactly these five finals:

| Year | Edition | Winner def. runner-up | Final score | Final-point game | Pre-point score |
| --- | --- | --- | --- | --- | --- |
| 2008 | Beijing 2008 | Lin Dan def. Lee Chong Wei | `21-12, 21-8` | game 2 | Lin Dan leads `20-8` |
| 2012 | London 2012 | Lin Dan def. Lee Chong Wei | `15-21, 21-10, 21-19` | game 3 | Lin Dan leads `20-19` |
| 2016 | Rio 2016 | Chen Long def. Lee Chong Wei | `21-18, 21-18` | game 2 | Chen Long leads `20-18` |
| 2020 | Tokyo 2020 | Viktor Axelsen def. Chen Long | `21-15, 21-12` | game 2 | Axelsen leads `20-12` |
| 2024 | Paris 2024 | Viktor Axelsen def. Kunlavut Vitidsarn | `21-11, 21-11` | game 2 | Axelsen leads `20-11` |

`Tokyo 2020` may appear in videos published or played in calendar year 2021;
the Olympic edition remains `2020`. `2012` is the only three-game final. The
`2016` final is straight games; any `2-1`, third-game, or decider wording for
2016 contradicts the locked ground truth.

Any answer using a different year, semifinal, bronze-medal match, different
winner, different finalist pair, or wrong final score is historically wrong
even if it includes a badminton clip.

## 4. Clip and Timestamp Validation

A valid final-point clip must satisfy all of these conditions for the relevant
year:

- It is from the correct Olympic men's singles final and the correct final
  point game listed in the locked ground truth.
- It visibly shows the final rally from serve, service preparation, or the
  first shot of the final point through the scoring moment.
- It contains enough in-rally footage to distinguish the point from a replay
  montage, a generic end-of-match highlight, or a post-point cutaway.
- It shows or strongly corroborates the match-point context through scoreboard,
  broadcast graphics, player positioning, source timing, or adjacent frames.
- It may include a few seconds of celebration after the scoring moment, but it
  must not consist only of celebration, handshakes, trophy/medal ceremony,
  crowd reaction, title cards, intros, score summaries, or final scoreboard.

Official highlights are acceptable only if the highlighted segment itself
contains the complete final scoring rally. Replay footage is acceptable only if
it clearly depicts the full final point and is tied to the correct match/game.
If sampled frames or direct playback cannot verify more than post-point
footage, treat the clip as invalid.

Timestamp credit requires explicit start and end times for the final-point
segment in the watched source video. A vague statement such as "near the end",
"at match point", or a single timestamp without a clip boundary is not enough
for full timestamp credit.

The supervisor should inspect the saved `.mp4` files directly or sample
representative frames from the beginning, middle, and end of each clip before
awarding clip-validity credit. Do not infer clip validity solely from filename,
duration, summary text, source URL, or executor self-check notes.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Output shape.** Summary markdown exists and covers exactly the five
  canonical years, and five `.mp4` files are present under the required output
  directory with filenames that can be matched to the five finals. Missing the
  summary or having fewer than five matchable clip files receives 0 for this
  line.

- **0.20 - Locked historical facts.** Award 0.04 per final only if the year,
  Olympic edition, finalists, winner, final score, and straight-games /
  three-game characterization all match the locked ground truth. Any wrong
  winner, finalist, score, or final-point game for a final earns 0 for that
  final.

- **0.20 - Last-point timestamp localization.** Award 0.04 per final only if
  the summary gives explicit start and end timestamps that correspond to the
  final scoring rally in the correct final-point game. Timestamps in the wrong
  game, timestamps pointing to pre-match/post-match footage, generic "near the
  end" references, or missing start/end boundaries earn 0 for that final.

- **0.35 - Saved clip visual validity.** Award 0.07 per final only if the
  saved clip visibly contains the actual final scoring rally from serve/rally
  start through the scoring moment and matches the year/finalists/game in the
  locked ground truth. A clip from the correct match that shows only a partial
  rally and still proves the scoring moment may receive at most 0.04 for that
  final. A clip showing the wrong match, wrong game, early-match play,
  warm-up, intro graphics, post-point celebration only, handshakes, crowd
  reaction only, final scoreboard, interview, trophy presentation, or medal
  ceremony receives 0 for that final.

- **0.10 - Source grounding and watching evidence.** Credit requires each
  summary row to name the watched source video by URL or title, plus visible
  trace evidence or output notes showing that the executor watched or processed
  match/highlight video and used video timestamps to make the cuts. Text-only
  lookup, score-page summaries, transcripts, or unsupported claims of watching
  receive 0 for this line.

- **0.05 - Internal consistency and no hallucinated evidence.** Summary rows,
  filenames, timestamps, source claims, rally descriptions, and saved clip
  content should agree. Contradictory source URLs/titles, claimed evidence
  files that do not exist, invented timestamps, or descriptions inconsistent
  with the saved clip zero this line.

## 6. Scoring Policy / Score Caps

Compute the rubric total from section 5, then apply all applicable caps with
`min(raw_score, cap)`. A run can pass only if the capped score is `>= 0.90`.
Any cap below `0.90` makes the verdict `continue` or `fail`, not `pass`.

- **Cap at 0.30 - Missing primary summary.** The summary markdown is absent,
  unreadable, or does not describe Olympic men's singles badminton finals.
- **Cap at 0.35 - Text-only delivery.** No required `.mp4` clip files are
  present under `/tmp_workspace/results/olympic_final_points/`.
- **Cap at 0.45 - Too few finals or clips.** Fewer than four canonical finals
  are covered in the summary, or fewer than four matchable clip files exist.
- **Cap at 0.55 - Wrong match/year/winner.** Any final is replaced by the
  wrong Olympic year, wrong event, non-final match, wrong finalists, or wrong
  winner. If this happens for two or more finals, cap at 0.40.
- **Cap at 0.74 - Wrong score or game format.** Exactly one final has the
  wrong final score, wrong straight-games / three-game characterization, or
  wrong final-point game. If this happens for two or more finals, cap at 0.60.
  This cap applies to any answer that describes the 2016 Chen Long vs Lee
  Chong Wei final as `2-1` or as having a third-game decider.
- **Cap at 0.70 - Missing timestamps.** Exactly one canonical final lacks an
  explicit final-point start/end timestamp. If two or more finals lack
  explicit start/end timestamps, cap at 0.55. If timestamps are absent or
  generic for all finals, cap at 0.40.
- **Cap at 0.80 - One invalid final-point clip.** Exactly one saved clip does
  not show the actual final scoring rally from serve/rally start through the
  scoring moment, even if the summary facts are otherwise correct.
- **Cap at 0.65 - Multiple invalid final-point clips.** Two or more saved clips
  do not show the actual final scoring rally, are from the wrong part of the
  match, or cannot be matched to the summary timestamp.
- **Cap at 0.70 - One post-point-only clip.** Exactly one required clip is
  post-match or post-point material only: celebration after the point,
  handshakes, crowd reaction, final scoreboard, interview, trophy presentation,
  or medal ceremony, with no visible final rally.
- **Cap at 0.50 - Multiple post-match / ceremony-only clips.** Two or more
  required clips are post-point-only, ceremony-only, or otherwise contain no
  final rally. If most or all clips are ceremony/interview/post-match packages,
  cap at 0.35.
- **Cap at 0.75 - Clip verification not possible.** Clip files exist, but the
  supervisor cannot verify from direct playback or sampled frames that they
  contain the final scoring rallies. Do not pass on unverified video files.
- **Cap at 0.60 - Source/timestamp contradictions.** Multiple summary rows cite
  source videos or timestamps that conflict with the visible trace, saved clip
  boundaries, or actual clip content.
- **Cap at 0.45 - No video-grounding evidence.** The visible trace shows only
  score pages, subtitles, web snippets, or prior knowledge, with no evidence of
  watching, downloading, processing, or inspecting match/highlight video.

Clip artifacts are a hard requirement. A historically correct written summary
without five valid final-point clips is not enough for a passing score.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** Use only when all five canonical finals are
  historically correct, all five summaries include explicit final-point
  start/end timestamps, and all five saved clips visibly show the actual final
  scoring rallies.
- **Continue (`0.60 - 0.89` after caps):** Use when the work is mostly
  recoverable, such as one missing/weak timestamp, one invalid or unverifiable
  clip that can be re-cut, or one isolated historical format/score error with
  otherwise correct artifacts.
- **Fail (`< 0.60` after caps):** Use when core task evidence is absent or
  unreliable: missing summary, no clips, wrong years/matches/winners, multiple
  invalid clips, multiple post-match/ceremony-only clips, or no evidence that
  the executor watched video.

Do not ask for a follow-up after a fail-level score. For continue-level scores,
the feedback should name the exact year(s), timestamp(s), or clip(s) that need
re-verification or re-cutting.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - canonical finals, accepted search aliases,
  locked winners/scores, and timestamp logic.

## 9. Dynamic Content Note

YouTube uploads, titles, and available full-match/highlight sources may change.
Do not require one particular URL if the saved clip and timestamp are from a
legitimate video of the correct final. The historical facts and final-point
game listed in the hidden ground truth are static and authoritative. If a live
source conflicts with the hidden ground truth, grade against the hidden ground
truth and flag the source mismatch rather than changing the answer key.
