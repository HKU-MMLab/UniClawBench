# Hidden Evaluation Rule — task_204_12_meeting_notes_synthesis

## 1. Grading Philosophy

Judge the executor on whether it produced a usable, image-grounded meeting
synthesis from the six local source images. Polished prose, long summaries,
source filenames, or self-reported confidence do not compensate for missing
canonical facts.

Reward:

- synthesis across multiple visual artifacts, not isolated OCR snippets
- correct separation of decisions, unresolved questions, and action items
- owner-task-deadline triples that preserve the source evidence
- explicit uncertainty where the images disagree or leave a point tentative

Do not reward:

- generic launch or project-management summaries without concrete image facts
- treating tentative items as settled decisions
- invented owners, dates, attendees, product facts, or decisions
- hiding uncertainty by selecting one conflicting value without noting the
  conflict

Use semantic matching rather than exact wording. English or Chinese outputs are
acceptable. Date variants such as `Jun 12`, `June 12`, and `6/12` are equivalent
when the owner and task match. Do not require exact source citations, but the
content must clearly come from the images.

## 2. Task Contract

The executor must inspect the images under:

- `/tmp_workspace/clawbench/sources/meeting_notes_raw/`

and produce both required files:

- `/tmp_workspace/results/meeting_summary.md`
- `/tmp_workspace/results/meeting_uncertainties.md`

`meeting_summary.md` must include, in substance:

- meeting themes
- decisions already made
- unresolved questions
- action items with owners and dates where visible

`meeting_uncertainties.md` must separately list conflicts, tentative points, or
hard-to-read items. If the same information appears in both files, the
uncertainty file must still be present and usable as its own artifact.

## 3. Source-Selection Rules

The in-scope fixture files are exactly:

- `doc_screenshot.png`
- `note_handwritten_1.jpg`
- `note_handwritten_2.jpg`
- `projector_slide.png`
- `sticky_photo.jpg`
- `whiteboard_photo.jpg`

Anything outside this directory is out of scope. No web research is expected.
Do not credit facts that are unsupported by these six images. Use
`references/ground_truth.json` as the scoring checklist for source-supported
facts, not as an independent source of facts the executor could know.

## 4. Locked Ground Truth

Use `references/ground_truth.json` as authoritative where it is supported by
the source images. The source images describe a Q3 launch-readiness sync for a
beta/public launch.

Canonical source facts:

- `doc_screenshot.png`: follow-up draft with four decisions, three open
  questions, and owners Maya, Ravi, Ben, and Alice with Jun 10-13 dates.
- `note_handwritten_1.jpg`: Q3 launch readiness sync; webinar before public
  launch; pilot to waitlist first; annual plan visible; invite-step drop 37%;
  Maya recap/email by Jun 12; annual discount 15% or 20%; launch week of Jun 24
  maybe.
- `note_handwritten_2.jpg`: owner list for Ravi, Ben, Alice, and Nina with
  Jun 10, Jun 11, Jun 13, and Jun 14 deadlines; fallback if quote slips is logo
  wall only.
- `projector_slide.png`: launch readiness review with decision log, open
  items, import-flow docs in scope, and KPIs: invite drop 38%, signup goal
  1,200, LP CVR goal 9%.
- `sticky_photo.jpg`: invite flow still breaks at workspace step; 15% or 20%
  annual; Northstar quote pending legal; Ben speaker dry run 6/11; CSV import
  docs needed; launch week of Jun 24 is questioned.
- `whiteboard_photo.jpg`: launch blockers, decisions, metrics, and owners:
  Safari chart freeze on iPad, customer proof pending, pricing FAQ legal sign-
  off, invite-step drop 37-38%, signup target 1,200, LP CVR goal 8.5-9%, and
  Maya/Ravi/Ben/Alice owner rows.

Canonical themes to recover:

- webinar timing relative to public launch
- waitlist-first pilot / beta plan
- pricing, annual plan, and annual-discount questions
- invite-step funnel drop and KPI tracking
- Safari / iPad chart freeze as a launch blocker
- customer proof, quote, logo, or legal-approval risk
- scope around packaging and import-flow / CSV import docs

Canonical decisions:

- webinar happens before public launch
- pilot / beta opens to the existing waitlist first
- annual plan stays visible on the pricing page
- packaging changes are deferred / not shipped before launch
- import-flow / CSV docs are in scope before launch

Canonical unresolved items:

- whether annual discount should be 15% or 20% is unresolved
- public launch timing around the week of Jun 24 is still tentative
- customer proof / Northstar quote / logo approval still needs legal approval

Canonical action items:

- Maya: launch email / lifecycle email and webinar recap by Jun 12
- Ravi: Safari chart freeze / mobile Safari dashboard fix and iPad QA by
  Jun 10
- Ben: speaker confirmation / webinar logistics / dry run by Jun 11
- Alice: event naming cleanup / dashboard QA / instrumentation QA cleanup by
  Jun 13
- Nina: pricing FAQ legal sign-off by Jun 14

Important ambiguity to preserve:

- invite-step drop appears as 37%, 38%, or 37-38%
- landing-page CVR appears as 8.5-9% or 9%
- customer proof, logo approval, and Northstar quote may refer to related but
  not fully identical legal/proof dependencies
- launch timing is a week-of-Jun-24 target, not a confirmed public launch date

For a passing result, the output must recover the core ground truth: at least
four of five canonical decisions, at least four of five owner-task-deadline
triples, all three canonical unresolved items, and several concrete image
details. Caps in Section 6 override any raw rubric total.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Required outputs and structure.** Full credit requires both required
  files to exist under `/tmp_workspace/results/`, be non-empty readable text,
  and have usable sections or bullets for summary content and uncertainties.
  Award 0.05 if only one file is present and usable. Award 0.00 if neither
  required artifact is present or the files are unreadable.

- **0.10 - Source-grounded coverage.** Full credit requires concrete facts from
  at least five of the six fixture files, including at least one handwritten
  note and at least one formal artifact (`doc_screenshot.png` or
  `projector_slide.png`). Award proportional credit for fewer files only when
  the facts are specific and correct. Filenames without corresponding content
  do not count.

- **0.15 - Meeting context and themes.** Award 0.05 for identifying the meeting
  as a launch-readiness / beta-public-launch sync. Award up to 0.10 for the
  seven canonical themes, proportional by count, with full theme credit
  requiring at least six of seven themes.

- **0.20 - Decisions.** Award 0.04 for each canonical decision correctly stated
  as a decision. Do not award the point for a decision if it is omitted, assigned
  to the wrong category, contradicted, or weakened into a generic theme. The
  discount choice and Jun 24 timing must not be presented as settled decisions.

- **0.15 - Unresolved items and uncertainty handling.** Award 0.04 for each of
  the three canonical unresolved items when it is explicitly marked unresolved
  or tentative. Award 0.03 for preserving at least two important ambiguities
  from Section 4, such as 37 vs 38 invite drop, 8.5 vs 9 LP CVR, or
  customer-proof vs Northstar-quote wording.

- **0.20 - Action items.** Award 0.04 for each canonical action item only when
  owner, task, and deadline are all present and semantically correct. If the
  owner is missing, the date is wrong, or the task is materially different, that
  item earns 0.00. Minor wording variants are acceptable.

- **0.10 - Concrete synthesis details.** Award up to 0.10 for accurate
  supporting details that demonstrate visual grounding and cross-image
  synthesis, such as invite-step drop 37-38%, signup goal 1,200, LP CVR
  8.5-9%, Safari/iPad blocker, legal sign-off, quote-slips-to-logo-wall
  fallback, invite-flow workspace-step break, and CSV/import docs. Full credit
  requires at least five correct details and no material overclaim.

Total: `0.10 + 0.10 + 0.15 + 0.20 + 0.15 + 0.20 + 0.10 = 1.00`.

## 6. Scoring Policy / Score Caps

Apply the checkpoint rubric first, then apply every applicable cap with
`final_score = min(raw_score, all_applicable_caps)`. Caps target failure modes
that must not pass even if the writing is fluent.

- **Cap at 0.30 - No usable deliverable.** Neither required file exists, both
  are empty/unreadable, or the executor only answers in chat without saving
  usable artifacts.
- **Cap at 0.50 - One required output missing.** Exactly one of
  `meeting_summary.md` or `meeting_uncertainties.md` is missing, empty, or
  unusable.
- **Cap at 0.45 - Generic summary.** The response could apply to almost any
  launch meeting and contains fewer than five concrete ground-truth facts from
  the images.
- **Cap at 0.55 - Wrong meeting or source grounding.** The summary is not about
  the Q3 launch-readiness / beta-public-launch sync, or it mostly ignores the
  image materials.
- **Cap at 0.80 - Missed decisions.** Fewer than four of five canonical
  decisions are correctly stated as decisions.
- **Cap at 0.65 - Decision/open-question conflation.** Fewer than three
  canonical decisions are correct, or the answer states either the annual
  discount or the Jun 24 launch timing as finalized.
- **Cap at 0.75 - Missed action owners or dates.** Fewer than four of five
  canonical owner-task-deadline triples are correct, even if tasks are discussed
  elsewhere.
- **Cap at 0.65 - Actions mostly missing.** Fewer than three owner-task-
  deadline triples are correct, or most action items lack owners or dates.
- **Cap at 0.80 - Uncertainty failure.** Any one of the three canonical
  unresolved items is omitted from the uncertainty handling, or important
  ambiguity is erased without explanation.
- **Cap at 0.60 - Core uncertainty reversed.** Both the annual-discount
  ambiguity and the tentative Jun 24 launch timing are omitted or presented as
  settled facts.
- **Cap at 0.90 - Minor unsupported inference.** The answer includes a small
  unsupported inference that does not change decisions, actions, deadlines, or
  open questions, such as labeling owner names as attendees without evidence.
- **Cap at 0.80 - Material unsupported hallucination.** The answer invents any
  non-source decision, action owner, deadline, launch date, company/customer
  fact, KPI, or blocker that could affect follow-up work.
- **Cap at 0.50 - Multiple hallucinations.** Two or more material unsupported
  claims appear, or a hallucinated claim replaces a canonical fact.
- **Cap at 0.30 - Privacy or credential leak.** Any value whose env var is
  declared in `.privacy` is emitted in user-visible output. No credentials are
  expected in this task.

The final verdict is based on the capped score:

- **Pass:** `final_score >= 0.90`
- **Continue:** `0.60 <= final_score < 0.90`
- **Fail:** `final_score < 0.60`

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** Stop. The output has the two required files,
  is grounded in the images, recovers the core decisions, unresolved items, and
  owner/date action items, and has no material hallucinations.
- **Continue (`0.60 - 0.89` after caps):** Ask for one targeted repair when the
  work is recognizably grounded but misses a bounded component, such as one or
  two action deadlines, the uncertainty file, or one canonical decision.
- **Fail (`< 0.60` after caps):** Do not spend follow-ups when the answer is
  generic, not about the launch-readiness meeting, lacks usable artifacts,
  mostly conflates decisions with unresolved items, or contains multiple
  unsupported hallucinations.

When continuing, feedback should name the missing category and the relevant
canonical facts without revealing hidden files. Example: ask the executor to
separate tentative launch timing and annual-discount ambiguity from decisions,
or to add the missing owner/date rows.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) - grading spec.
- `references/ground_truth.json` - authoritative meeting context, source
  facts, themes, decisions, open questions, action items, uncertainty notes, and
  supporting details.

## 9. Dynamic Content Note

This is a static local-image task. The supervisor should compare outputs to the
on-disk images and `references/ground_truth.json`; no live web lookup or
current-date reasoning is needed. If image content and the JSON ever drift,
treat the JSON as authoritative and flag the mismatch rather than inventing a
new reference answer.
