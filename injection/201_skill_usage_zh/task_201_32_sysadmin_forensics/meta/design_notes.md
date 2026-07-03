# Internal design notes — task_101_32_sysadmin_forensics

Not injected into runtime. Captures construction history that should not
appear in `references/eval_rule.md`.

## Rubric provenance

- Original v3 policy: a skill_usage task with zero evidence of consulting
  the declared skill cannot reach full score. Previously enforced via a
  0.89 cap on missing reads of `sysadmin-toolbox` or `claw-shell`.
  Re-expressed in the current eval as a single 0.65 cap when neither
  declared skill is consulted, per the streamlined cap policy
  (extreme-failure-only, ≤ 0.7).
- Earlier iterations (iter1/iter2) used multiple 0.85–0.89 caps for
  missing CSV / JSON / phase coverage. These overlapped the rubric and
  have been removed in favor of letting the rubric weights carry that
  signal; only fabricated-sources, no-deliverables, scope-blowout, and
  credential-leak caps remain.

## Confirmed vs noise design

The two noise events (`203.0.113.77` failed password spray and
`deploy from 10.0.0.45` successful internal login) are intentional
signals to test whether the executor distinguishes background traffic
from the actual compromise. The previous 0.88 cap for misclassifying
them was redundant with the 0.17 IOC checkpoint and was removed.

## Skill fork

See `meta/skill_fork_manifest.json` — both `sysadmin-toolbox` and
`claw-shell` are declared as required skills. Trace evidence of either
SKILL.md being read counts as consultation.

## Round 2 hardening (2026-04-30) — pass→continue conversion
- Currently pass 1.0; add 2 strict anchors.
- Added §5 CPs "Cleanup-action IOC reference precision" 0.08, "MITRE ATT&CK technique tagging" 0.07.
- Added GT fields cleanup_action_target_iocs_required + min_cleanups_with_ioc_reference + mitre_phase_tagging_required + min_phases_with_mitre_tag + mitre_acceptable_techniques.
- Shaved 0.15 total from existing weights.
- Target: opus 1.0 → ~0.77 (loses 0.08 if cleanups don't reference IOCs + 0.07 if MITRE tagging absent).

## Review pass (2026-04-30)
Per review_record.md Task 32 user feedback:
1. **Tightened content checks; provided GT for supervisor.** GT now includes
   `expected_timeline_events` (exact list of 12 anchored events with per-event
   phase + source_file + verbatim anchor substring) and
   `expected_per_phase_anchors` (which anchor strings belong in which phase).
   Eval §5 CP1/CP2/CP5 now grade against these explicit anchors, not vague
   "≥X/Y" thresholds.
2. **Removed "at least 12" lenient threshold.** Prompt now says
   "find every relevant event ... exactly 12 in-scope timeline events ...
   must contain all 12 events — every one." Eval §5 CP1 requires all 12
   anchors verbatim, CP5 requires exactly 12 evidence.csv rows. Missing any
   one event → 0 on that checkpoint.
3. **Strict per-phase anchor coverage.** §5 CP2 (0.13) checks that every
   phase listed in `expected_per_phase_anchors` is present and contains
   all expected anchors; any missing phase or wrong-phase placement → 0.
4. **5/5 cleanup IOC references (was 4/5).** Bumped
   `min_cleanups_with_ioc_reference` from 4 → 5; `cleanup_minimum` array
   updated so each of the 5 actions references a specific IOC string
   (e.g., `/home/alice/.ssh/id_rsa`, `/tmp/pwn.sh`, the full crontab line,
   `198.51.100.4`, `/tmp/alice_id_rsa`+`/tmp/notes.log`). §5 CP9 stepped
   credit: 5/5 → 0.08, 4/5 → 0.04, ≤3 → 0.
5. **English prompt + skill in first paragraph.** Task YAML rewritten so
   that the first paragraph names `sysadmin-toolbox` and `claw-shell`
   skills explicitly. No brackets. All ENGLISH.
6. **GT canonical event count consolidated to 12.** Dropped one of the
   redundant persistence-syslog anchors from the previous 13-event list to
   match the prompt-stated count of 12 (kept the cron persistence history
   anchor + setuid syslog audit anchor — see `expected_timeline_events`).
7. **§5 sum still = 1.00**: 0.11+0.13+0.10+0.08+0.13+0.15+0.10+0.05+0.08+0.07.
