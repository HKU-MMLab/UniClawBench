# Design Critique — Onboarding Flow Iteration 4

**Reviewers:** Tomas Hsu, Ari Goldwyn, Maya Patel
**Designer:** Jess Park

## What works

- The progress indicator at the top is finally clear about which step you're on.
  The previous version had a bug where the active dot was the same color as the
  upcoming dots; this iteration fixes that with a clearer contrast.
- Dropping the optional "How did you hear about us?" field meaningfully shortens
  the perceived form length.
- The illustration on step 2 reinforces the "you're almost done" moment without
  feeling overly cartoony.

## Concerns

- The Continue button on step 3 sits below the fold on a 13" laptop. We've made
  this mistake before. Move it up by ~80px, or shrink the form intro copy.
- The error state on the email field is currently red text plus a red border —
  that combination may not pass WCAG AA contrast on some monitors. Worth checking
  with the accessibility tooling.
- The animation on step 4 ("Loading your workspace…") is 3.2 seconds, which is
  long enough that some users will assume the app froze. Consider replacing with
  a stepwise progress indicator.

## Suggested next iteration

- Try a single-page version where steps 1–3 are stacked, with the verification
  step still being its own page. Hypothesis: fewer page transitions reduces
  abandonment.
- Bring back the "skip for now" option on step 5 (settings preferences) — the
  team data shows 38% of users never go back to fill these in, but they're not
  blocking, so making them mandatory just adds friction.
