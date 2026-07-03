# Hidden Evaluation Rule — task_203_15_embodiment_long_horizon_ppt

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should care most about whether the executor read the shuffled paper set, selected the correct long-horizon + hierarchical planning papers, and produced a presentation-quality PPT. PPT quality is central: even correct paper selection should not pass if the deck has unreadable text, broken layout, or unusable figures.

## 2. Task Contract

The public task asks for a paper-reading PPT using the provided template style, an Embodiment System roadmap placing all candidate papers into grounded & interactive, closed-loop recovery, long-horizon + hierarchical planning, and generalization, then a focused section on the two papers best suited to long-horizon + hierarchical planning. Each selected paper needs motivation, method, and experiment coverage. Final deliverables are `/tmp_workspace/results/long_horizon_paper_reading.pptx` and `/tmp_workspace/results/selection_note.md`.

Completion means both requested files exist, the deck opens, all candidate papers are accounted for in the roadmap, the selected papers are justified, and the deck is suitable for group discussion.

## 3. Source-Selection and Target-Resolution Rules

Paper filenames are intentionally obfuscated. The executor must infer paper identities and categories from the paper content, not from hidden mapping. The expected main long-horizon + hierarchical planning papers are Hi Robot and MEM. Generalization/open-ended agent papers such as Voyager should appear in the roadmap but should not be the main long-horizon section.

## 4. Ground-Truth Snapshot

Hidden ground truth maps the 10 obfuscated PDFs to paper titles. The expected main selections are Hi Robot and MEM. Hidden references also include a template/reference deck for style and a paper mapping for supervisor verification.

## 5. Checkpoint Rubric

- 0.15 Roadmap coverage: reads the candidate set and provides a roadmap placing all 10 papers into the four requested blocks.
- 0.20 Main-paper selection: selects Hi Robot and MEM as the main long-horizon + hierarchical planning papers, with a defensible selection note.
- 0.20 Paper understanding: accurately covers motivation, method, and experiment for both selected papers.
- 0.10 Category discipline: correctly keeps generalization/open-ended agent papers such as Voyager in the roadmap rather than making them the main long-horizon section.
- 0.25 PPT quality: opens cleanly, uses the template visual language, has readable typography, no visible text overflow/clipping, readable figures, coherent slide titles, and professional density.
- 0.10 Deliverables: final files are saved at the requested paths and are internally consistent.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failures that make the deck unusable, unauditable, or clearly about the wrong paper set. PPT quality is a core requirement, so severe visual defects should restrict the total score even when paper selection is partially correct.

If the PPT is not usable for a group presentation because of widespread overflow, unreadable typography, broken layout, corrupt files, or heavily stretched/cropped figures, cap at 0.65; for a corrupt or mostly unreadable deck, cap at 0.50. If neither Hi Robot nor MEM is selected as a main paper, cap at 0.55. If the deck ignores the candidate-paper roadmap and covers only a small subset of the corpus, cap at 0.70. If paper content is mostly hallucinated or not traceable to the provided PDFs, cap at 0.60.

## 7. Continue vs Fail Guidance

Prefer `continue` when deliverables are missing, the deck has not been exported/saved correctly, the roadmap is incomplete, or layout quality can still be fixed. Prefer `fail` when the final deck is corrupt, substantially unreadable, selects the wrong papers with no recovery, or omits the central requested roadmap/selected-paper structure.

## 8. Hidden Reference Assets

- `ground_truth.json`: expected selection, category anchors, and quality checkpoints.
- `paper_mapping.json`: hidden PDF-title mapping.
- `group5_reference_deck.pptx`: style/quality anchor, not an exact-slide template requirement.

## 9. Dynamic Content Note

The paper set is static. Do not accept source substitutions unless the provided PDFs are genuinely inaccessible. Style matching is qualitative: require professional coherence with the template, not pixel-perfect copying.
