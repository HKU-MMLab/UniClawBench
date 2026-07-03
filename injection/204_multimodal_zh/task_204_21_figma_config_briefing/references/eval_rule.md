# Hidden Evaluation Rule — Figma Config Personalized Briefing

## 1. Grading Philosophy

Judge whether the executor produced a source-grounded, personalized Config
briefing, not merely a polished event summary. A high score requires all of:

- correct event facts and section cues from the official Config homepage
- real webpage screenshots saved under the required names
- explicit use of both public-source inputs: `my_design_interests.json` and the
  three portfolio screenshots
- a concrete comparison between the user's restrained SaaS / design-systems
  portfolio and Config's bolder conference visual language
- recommendations tied to the user's staff-level design-systems goal and
  no-travel constraint

Do not reward generic conference blurbs, confident prose, polished HTML, or
agent self-reporting when source grounding is absent. Chinese or English
answers are both acceptable. Grade semantic accuracy after normalizing curly
apostrophes, dash styles, capitalization, and `SF` vs `San Francisco`.

## 2. Task Contract

The executor must open `https://config.figma.com/`, inspect public sources
under `/tmp_workspace/clawbench/sources/`, and produce exactly these required
deliverables under `/tmp_workspace/results/`:

- `config_highlights.md`
- `config_moodboard.html`
- `config_hero.png`
- `config_sections.png`

`config_highlights.md` must include an event overview, a list of homepage
content highlights / sections, references to the screenshots, and personalized
recommendations. `config_moodboard.html` must be a one-page visual briefing
summarizing the homepage visual language and highlighting 3-5 focus areas for
the user.

Extra supporting files are acceptable, but they do not replace the four named
deliverables above. The two screenshot files must be actual image captures from
the official Config webpage, not generated mockups, copied portfolio images, or
blank placeholders.

## 3. Locked Ground Truth

Use `references/ground_truth.json` as the authoritative snapshot. The public
Config webpage may change after the snapshot date (`source_accessed_on:
2026-04-23`); grade against the hidden snapshot facts and fixtures, not against
future live-page edits.

Canonical homepage facts:

- official URL: `https://config.figma.com/`
- title cue: `Figma Config 2026 | June 23-25 - Moscone Center SF`
- theme: `Figma's conference for people who build products`
- dates: `June 23-25, 2026`
- location: `San Francisco, CA / Moscone Center`
- attendance mode: `In person & virtual`

Canonical homepage sections and sub-sections:

- `Featured speakers`
- `Why attend`
- `What you'll learn`
- `What to expect`
- `Who you'll meet`
- `Config Commons`
- `Watch parties`
- `Community events`

Canonical content cues:

- future of design and product development
- newest Figma products and features
- keynotes, hands-on demos, and deep-dive product design sessions
- over 10,000 designers, developers, marketers, and product leaders
- Config Commons for badge pickup, swag, and community meetup on Tuesday,
  June 23
- watch parties for people not attending in person
- community events such as hikes or happy hours

Canonical visual-language cues:

- black background with Kelly / bright green and white
- oversized typography and high-contrast hero art
- flower-like / glyph illustration motifs
- green glyphs / flower forms on black, with green and white text

Public-source profile that must inform recommendations:

- user name / role: Lin, senior product designer at a B2B SaaS company
- location and constraint: based in Shanghai; cannot travel internationally for
  an in-person conference this year; remote or community-based participation is
  more realistic
- career goal: move into a staff-level design systems / product platform role
  within 12 months
- priority topics: design systems for product teams, designer-developer handoff
  and component workflows, interactive prototyping and onboarding motion,
  AI-assisted product workflows
- strengths: structured product UI, componentized thinking, clear dashboard and
  workflow layouts
- gaps: bolder visual storytelling, more expressive brand-forward presentation,
  showing motion and interaction more convincingly
- portfolio screenshots: structured SaaS dashboard; token / component library
  and developer handoff notes; dark onboarding motion prototype with cyan /
  teal accents, still product-grid driven rather than poster-like

Strict pass expectation is folded into these facts: a passing answer must match
the hidden snapshot on the core event facts, use real screenshots, and show
personalized reasoning from both the JSON profile and the portfolio images. A
briefing that only looks good or only repeats generic design-conference advice
is below the pass threshold.

## 4. Source-Selection and Target-Resolution Rules

The only public personalization sources are:

- `/tmp_workspace/clawbench/sources/my_design_interests.json`
- `/tmp_workspace/clawbench/sources/my_portfolio_screenshots/portfolio_dashboard_overview.png`
- `/tmp_workspace/clawbench/sources/my_portfolio_screenshots/portfolio_design_system_library.png`
- `/tmp_workspace/clawbench/sources/my_portfolio_screenshots/portfolio_onboarding_motion.png`

The supervisor may use browser transcripts, saved text snapshots, screenshots,
or other visible trace evidence to decide whether the official Config site was
actually opened. However, final grading of event facts uses the hidden snapshot
in `ground_truth.json`.

Do not require exact speaker names, agenda titles, session times, ticket
status, or ticket price unless they are present in the hidden snapshot or in
the executor's official-page evidence. If the executor includes named speakers,
workshops, session titles, schedules, local watch-party locations, or detailed
product-launch claims, those details must be explicitly supported by the
snapshot / trace. Unsupported agenda or session specifics are hallucinations
even when the surrounding recommendation is plausible.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — Required deliverables and basic usability.** Award 0.025 for each
  required file present at `/tmp_workspace/results/` with the exact required
  name: `config_highlights.md`, `config_moodboard.html`, `config_hero.png`,
  and `config_sections.png`. Markdown / HTML must be readable; screenshots
  must be non-empty image files. Extra files do not compensate for missing
  required names.

- **0.13 — Homepage fact accuracy.** Award 0.04 each for the correct theme,
  dates, location, and attendance mode; award 0.02 for correctly identifying
  the official event as Config / Figma Config 2026. Full credit requires no
  contradictory event fact in the public-facing deliverables. If a fact is
  omitted but appears only in a screenshot, do not award the corresponding
  text-credit unless the briefing itself communicates it.

- **0.12 — Real homepage sections and content cues.** Award 0.02 each for
  correctly naming or clearly paraphrasing at least six of the eight canonical
  section / subsection names. Award up to 0.04 within this line for accurately
  summarizing at least two official content cues, such as newest products and
  features, hands-on demos, deep-dive product design sessions, 10,000+
  attendees, Config Commons, watch parties, or community events. Do not credit
  invented agenda tracks as official sections.

- **0.14 — Screenshot evidence.** Award 0.07 for `config_hero.png` if it is a
  real Config homepage screenshot showing the hero area with the theme and / or
  date-location-attendance facts plus the black high-contrast visual style.
  Award 0.07 for `config_sections.png` if it is a real Config homepage
  screenshot showing a meaningful non-hero content area such as Featured
  Speakers, Why Attend, Config Commons, Watch Parties, or Community Events.
  Deduct within each half if a cookie banner or viewport crop obscures the
  primary evidence, and give zero for generated mockups, portfolio images,
  unrelated pages, or screenshots that cannot be visually tied to Config.

- **0.14 — Visual-language analysis.** Award 0.04 for identifying the black +
  Kelly / bright green + white palette; 0.03 for oversized / editorial
  typography; 0.03 for bold glyph / flower-like illustration motifs; 0.02 for
  high-contrast / event-identity or motion-led presentation; and 0.02 for
  distinguishing actual homepage visual observations from generic "modern /
  clean / innovative" adjectives.

- **0.13 — User-personalization evidence.** Award 0.04 for using the JSON
  profile's role and staff-level design-systems / product-platform goal; 0.04
  for using the Shanghai / cannot-travel constraint; 0.04 for using at least
  two priority topics or growth gaps from the JSON; 0.04 for using concrete
  observations from at least two portfolio screenshots; and 0.02 for naming the
  portfolio direction as structured B2B SaaS / dashboard / design-system /
  component workflow work rather than a generic "designer portfolio".

- **0.12 — Portfolio-vs-Config comparison.** Award up to 0.06 for explaining
  where the user's work is similar to Config, such as system thinking, product
  building, components, or design-development collaboration. Award up to 0.06
  for explaining differences, especially the user's restrained blue / teal
  product UI versus Config's bolder black / green conference branding,
  oversized typography, and more expressive event-style storytelling.

- **0.12 — Actionable focus recommendations.** Award 0.03 each for up to four
  recommendations that are both official-homepage grounded and user-relevant:
  newest Figma products / features; hands-on demos; deep-dive product design
  sessions; Featured Speakers / design-development crossover; watch parties or
  community events for remote participation; Config Commons / community
  mechanics as brand / storytelling learning. Full credit requires at least
  one remote or community participation recommendation because the user cannot
  travel. Speculative topics from the user's interests, such as AI workflows,
  may be useful framing but do not earn official-homepage grounding unless
  clearly labeled as a user-interest lens rather than an official session.

Total: `0.10 + 0.13 + 0.12 + 0.14 + 0.14 + 0.13 + 0.12 + 0.12 = 1.00`.

## 6. Scoring Policy / Score Caps

Apply the rubric first, then apply all applicable caps by taking the minimum.
A capped score below `0.90` cannot pass, even if the uncapped rubric total is
high.

- **Cap at 0.30 — No usable required briefing.** Both narrative deliverables
  are missing / unreadable, or neither `config_highlights.md` nor
  `config_moodboard.html` is present under `/tmp_workspace/results/`.
- **Cap at 0.35 — Official site not evidenced.** There is no visible trace of
  opening `https://config.figma.com/` or otherwise obtaining official homepage
  evidence, regardless of how plausible the written summary sounds.
- **Cap at 0.40 — Core event facts wrong.** The deliverables state a materially
  wrong date, year, venue, city, theme, or attendance mode, or conflate Config
  2026 with a different event.
- **Cap at 0.45 — Screenshot failure.** Both required screenshot files are
  missing, blank, non-image files, unrelated to Config, generated mockups, or
  copied from non-webpage sources.
- **Cap at 0.60 — Generic conference blurb.** The answer could apply to almost
  any design or tech conference and lacks concrete Config facts, section names,
  visual cues, and source-specific recommendations.
- **Cap at 0.60 — Missing user-personalization evidence.** The briefing does
  not demonstrate use of `my_design_interests.json` and does not cite or
  describe portfolio screenshot evidence beyond generic praise.
- **Cap at 0.65 — Ungrounded recommendations.** Recommendations are mostly
  generic career advice or speculative themes with no explicit tie to official
  homepage content and the user's profile / portfolio.
- **Cap at 0.70 — Portfolio-vs-Config comparison absent.** The answer does not
  compare the user's current work direction with Config's visual language, even
  if event facts and screenshots are otherwise correct.
- **Cap at 0.75 — Fabricated agenda / session details.** The answer presents
  unsupported named sessions, workshops, times, speaker lineups, product
  launches, local watch-party locations, or travel / ticket claims as official
  Config facts. Use this cap for hallucinated specifics that do not corrupt the
  core date / venue / theme; if they do, also apply the lower core-facts cap.
- **Cap at 0.80 — Remote constraint ignored.** The recommendations do not
  address the user's inability to attend in person and omit virtual,
  watch-party, or community-based participation guidance.
- **Cap at 0.84 — Weak source triangulation.** The output has correct event
  facts and acceptable screenshots but uses only one public-source modality
  (JSON profile or screenshots, not both), or gives personalization without
  enough evidence to verify it came from the supplied sources.
- **Cap at 0.84 — Required artifact naming mismatch.** The work is otherwise
  strong but one required filename is absent and only an equivalent / extra
  artifact exists. Exact requested output names are part of the task contract,
  so this remains a continue rather than a pass.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) — stop. Requires correct hidden-snapshot
  event facts, all or effectively all required deliverables, real Config
  screenshots, concrete visual-language analysis, recommendations grounded in
  official homepage content, and personalized evidence from both the JSON
  profile and portfolio screenshots. A score cap below `0.90` means the run is
  not a pass.
- **Continue** (`0.60 - 0.89` after caps) — request one targeted follow-up when
  the answer is recoverable, such as adding missing screenshot references,
  correcting one omitted event fact, grounding recommendations in the homepage,
  adding the travel / watch-party implication, removing unsupported session
  claims, or explicitly comparing the portfolio screenshots with Config's
  visual language.
- **Fail** (`< 0.60` after caps) — do not request more work. This includes no
  usable deliverables, no evidence of opening the official site, materially
  wrong event facts, missing / fake screenshots, generic conference summaries,
  or advice that ignores the supplied user sources.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — canonical official homepage snapshot,
  visual-language cues, public-source profile, and recommended focus areas.

## 9. Dynamic Content Note

This task depends on a public webpage that may change. Grade against the hidden
snapshot and local fixtures captured in `references/ground_truth.json`, not
against the live page at evaluation time. If the live webpage differs from the
hidden snapshot, do not penalize an executor for following the snapshot facts;
flag the drift separately only if the evaluation harness exposes such a
mismatch.
