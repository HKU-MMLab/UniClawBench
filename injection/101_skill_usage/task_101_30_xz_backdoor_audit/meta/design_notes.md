# Design notes — task_101_30_xz_backdoor_audit

Internal-only. Not injected into the executor or supervisor context.

## Construction history

- Initial draft used a single 0.86 cap on missing matrix and a 0.86 cap on
  missing YARA rules, plus a 0.88 cap on matrix-vs-findings disagreement and
  a 0.89 cap on no-skill-read. These were checkpoint restatements rather
  than extreme-failure caps and have been removed in favor of a single
  0.70 cap targeting verified skill usage.
- Earlier rubric also asked the executor to emit a `confidence` value in
  the IOC matrix column; the column header is preserved (the prompt asks
  for it), but the supervisor does not grade or verify the numeric
  confidence — it cannot reliably do so.
- Cap 0.30 for fabricated evidence was added to discourage hallucinated
  IOCs that would otherwise pass the template-fidelity checkpoint.

## Category coverage rationale

The five `required_categories` map to the five distinct evidence surfaces
of the public xz compromise:

1. `m4/build-to-host.m4` — build-system injection.
2. `tests/files/bad-3-corrupt_lzma2.xz` and
   `tests/files/good-large_compressed.lzma` — test-corpus payload.
3. `__ifunc__` / `crc64_resolve` — runtime resolver behavior.
4. `Makefile.in` / `am__test_logs` — generated build recipe.
5. `ChangeLog` / autotools tarball markers — release-vs-git divergence.

Requiring 4 of 5 lets a strong executor miss one surface (typically the
release-vs-git divergence) without losing the category checkpoint outright.

## Skill verification

Both `security-auditor` and `pentest` are workspace-mounted skills.
The executor is expected to consult at least one; the cap targets the
case where neither directory is touched at all, which is the strongest
signal the executor solved the task without using the declared skills.

## Round 1 hardening (2026-04-30)
- Added category_specific_anchors GT field for runtime_resolver + release_vs_git.
- Added §5 CP "Category-specific anchor precision" 0.07 (strict 2-of-2).
- Added §5 CP "Binary IOC byte-locator precision" 0.05.
- Shaved 0.07 from IOC count (0.20→0.13) and 0.05 from Evidence is auditable (0.10→0.05).
- Target: opus 0.85 → ~0.73 (loses ~0.12 if anchors not surfaced + binary locator absent).

## Review pass (2026-04-30)

Applied user review_record.md Task 30 changes:

1. **"5 IOCs" no longer revealed in prompt.** The prompt now says "find all
   the IOCs — there's a known set, please find them all" without naming the
   number 5. The executor must discover the full set; the supervisor still
   knows `min_ioc_count = 5` via GT but it is now an implicit checkpoint.
2. **Removed prescriptive format template.** The prompt no longer dictates
   `### IOC-<n>:` headings, dash-bullet field layout, or any specific
   layout. It simply requests "a clear structured format" and lists the
   four required content elements: artifact, evidence, attribution, impact.
   §5 IOC fidelity CP rewritten to grade the four elements semantically
   under any layout, not the heading template.
3. **Removed CSV deliverable.** `ioc_matrix.csv` was redundant with
   `findings.md` (same per-IOC content, just tabular). Prompt, eval_rule
   §2/§5/§6, and GT all updated to drop matrix references. Only
   `findings.md` and `release_hunt.yar` remain. The 0.15 weight from the
   removed matrix CP is redistributed: +0.02 to IOC count/content
   (0.13→0.15), +0.05 to Category coverage (0.20→0.25), +0.03 to
   Attribution (0.15→0.18), +0.02 to Artifact paths (0.10→0.12), +0.03
   to Evidence auditable (0.05→0.08).
4. **Strict 5/5 implicit category coverage.** `min_required_categories_covered`
   raised from 4 to 5 in GT. §5 Category coverage CP made strict: 5/5 →
   full credit, ≤4/5 → 0.00. This enforces "find them all" without naming
   the number in the prompt.
5. **Strict 5/5 IOC count.** §5 IOC count CP made strict: <5 entries → 0.00.
6. **English prompt.** Prompt was already English; minor cleanup, no
   brackets, skill mention in first paragraph (security-auditor + pentest).
7. **§5 weight verification.** 0.15 + 0.25 + 0.18 + 0.12 + 0.08 + 0.10 +
   0.07 + 0.05 = 1.00. Verified.
8. **Caps unchanged** except "No deliverables" cap reworded from three
   files to two (findings.md or release_hunt.yar). Numeric cap values
   untouched per global rule 11.
