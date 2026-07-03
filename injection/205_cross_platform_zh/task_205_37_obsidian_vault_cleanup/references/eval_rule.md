# Hidden Evaluation Rule — task_205_37_obsidian_vault_cleanup

## 1. Grading Philosophy

Grade from the cleaned vault, cleanup report, screenshot/tool evidence,
and `ground_truth.json`. The input vault is based on real public Vite
documentation Markdown imported from GitHub; do not treat it as an
invented toy note set. The executor may reorganize and annotate copies,
but should preserve the substantive Vite documentation content and
provenance comments.

## 2. Task Contract

Required outputs:
- `/tmp_workspace/results/project_vault_cleaned/`
- `/tmp_workspace/results/project_vault_cleaned/INDEX.md`
- `/tmp_workspace/results/project_vault_cleaned/duplicates.md`
- `/tmp_workspace/results/project_vault_cleaned/orphans.md`
- `/tmp_workspace/results/vault_cleanup_report.md`
- `/tmp_workspace/results/obsidian_cleanup.png`

## 3. Checkpoint Rubric

Checkpoints, total 1.00:
- 0.14 Required outputs and preservation: cleaned vault exists, keeps
  the imported Vite docs content/provenance in reorganized form, and
  does not simply replace the vault with a single summary.
- 0.18 Index quality: `INDEX.md` links to the main Vite guide/config
  topics: features, env-and-mode, build, dependency pre-bundling,
  static deploy, troubleshooting, plugin usage/API, server options, and
  build options.
- 0.18 Link handling: fixes included relative links such as the
  using-plugins -> api-plugin relationship, and documents unresolved
  Vite docs links whose target page was not imported rather than
  inventing missing notes.
- 0.14 Duplicate handling: identifies the repeated env-and-mode import
  between `Imported Vite Docs/guide-env-and-mode.md` and
  `Review Queue/local-env-mode-notes.md` in `duplicates.md`, with a
  keep/merge recommendation.
- 0.12 Orphan/low-link handling: identifies low-link or standalone docs
  such as troubleshooting/build-options in `orphans.md` or explains why
  they remain intentionally standalone.
- 0.10 Tag normalization: adds or normalizes a consistent Vite tag
  vocabulary with at least four useful tags such as guide/config/plugin
  and build/deploy categories.
- 0.08 Obsidian evidence: screenshot or transcript evidence shows the
  cleaned vault/index opened in the real Obsidian app. A screenshot of a
  terminal/file manager alone does not earn full GUI credit.
- 0.06 Cleanup report: report gives inspected note count, broken links,
  duplicate groups, tag normalization, and remaining unresolved issues.

## 4. Scoring Policy / Score Caps

Caps:
- Cap at 0.55 if no cleaned vault directory is saved.
- Cap at 0.70 if the Vite docs are summarized but the cleaned vault does
  not preserve the imported documentation pages.
- Cap at 0.82 if file content is good but there is no real Obsidian GUI
  evidence.
