# Hidden Evaluation Rule — task_203_19_RL_blog

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when needed to identify the intended target, enforce source use, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should care most about whether the executor reads the eight obfuscated PDFs, identifies the correct paper-to-section mapping, and produces a usable, visually polished HTML paper-reading blog on reward hacking and reward misspecification. The final article should follow the reference blog's coherent seven-section mainline while remaining grounded in the provided PDFs rather than filename guesses or unrelated online sources.

Figure quality is a first-class grading target, not a cosmetic detail. The task explicitly asks for an image-rich paper-reading blog built from clear screenshots of figures or tables cropped directly from the papers. A blog whose screenshots are black, cropped, low-resolution, mismatched with the surrounding paragraph, or substantially worse than the provided reference blog assets should be penalized heavily even if the text is mostly correct. Correct paper selection alone is not enough if the HTML is unstyled, formula rendering is broken, figures are unreadable/misleading, or the article is not coherent.

## 2. Task Contract

The public task asks for a paper-reading HTML blog using candidate PDFs from `/tmp_workspace/clawbench/sources/papers/` and the page-template assets (CSS, JavaScript, and MathJax rendering dependencies) from `/tmp_workspace/clawbench/sources/assets/`; note that `sources/assets/` does not contain prepared figure images, so every figure must be screenshotted from the candidate PDFs. The final blog must be saved under `/tmp_workspace/results/RL_blog/`, include its corresponding assets, place HTML-referenced images under `/tmp_workspace/clawbench/results/assets/images` when using that path convention, and cite the source paper for each figure. A selection note must be saved as `/tmp_workspace/results/selection_note.md` explaining why each paper was selected for each section.

Completion means the requested files exist, the HTML opens with styling and MathJax formulas, the article is image-rich, the eight papers are correctly identified from content rather than filename guesses, the seven requested concept sections are covered, the figures are clear and context-matched, and the selection note is consistent with the blog.

## 3. Source-Selection and Target-Resolution Rules

Paper filenames are intentionally obfuscated. The executor must infer paper identities and roles from the PDF contents. The expected main papers are:

- paper_01.pdf: Amodei et al. (2016), *Concrete Problems in AI Safety* — expected in 1. Reward functions and specification gaps.
- paper_02.pdf: Geirhos et al. (2020), *Shortcut Learning in Deep Neural Networks* — expected in 2. Shortcut learning as a source of hacking.
- paper_03.pdf: Pan et al. (2022), *The Effects of Reward Misspecification: Mapping and Mitigating Misaligned Models* — expected in 3. Reward hacking in RL environments.
- paper_04.pdf: Everitt et al. (2019), *Reward Tampering Problems and Solutions in Reinforcement Learning* — expected in 1. Reward functions and specification gaps.
- paper_05.pdf: Gao et al. (2023), *Scaling Laws for Reward Model Overoptimization* — expected in 4. Reward hacking in RLHF for LLMs.
- paper_06.pdf: Pan et al. (2024), *Feedback Loops With Language Models Drive In-Context Reward Hacking* — expected in 5. Evaluator and in-context reward hacking.
- paper_07.pdf: Wen et al. (2024), *Language Models Learn to Mislead Humans via RLHF* — expected in 4. Reward hacking in RLHF for LLMs.
- paper_08.pdf: Denison et al. (2024), *Sycophancy to Subterfuge: Investigating Reward Tampering in Language Models* — expected in 6. Generalization of hacking skills, 7. Detection and mitigation.

The blog does not need to reproduce every detail in the reference HTML. It should focus on the requested mainline, may briefly mention adjacent background ideas when helpful, and should not add unrelated papers to the core references.

## 4. Ground-Truth Snapshot

Hidden ground truth maps the eight obfuscated PDFs to paper titles and expected sections. The expected conceptual outline is:

1. Reward functions and specification gaps
   - Required ideas: define reward hacking as optimizing the specified reward while missing true intent; explain proxy objectives and specification gaps; include reward tampering as a related failure mode.
   - Expected papers: paper_01.pdf, paper_04.pdf.
2. Shortcut learning as a source of hacking
   - Required ideas: show how models exploit spurious features; connect shortcuts to reward proxies; distinguish robust task features from cheap correlates.
   - Expected papers: paper_02.pdf.
3. Reward hacking in RL environments
   - Required ideas: examples of reward misspecification in RL tasks; agents exploit environment or metric loopholes; mapping and mitigation of misaligned models.
   - Expected papers: paper_03.pdf.
4. Reward hacking in RLHF for LLMs
   - Required ideas: reward models are proxy objectives; overoptimization can reduce true preference quality; misleading or sycophantic behavior may emerge under RLHF.
   - Expected papers: paper_05.pdf, paper_07.pdf.
5. Evaluator and in-context reward hacking
   - Required ideas: LLM-as-judge/evaluator feedback can be exploited; models infer visible scoring patterns from context; feedback loops can drive in-context reward hacking.
   - Expected papers: paper_06.pdf.
6. Generalization of hacking skills
   - Required ideas: hacking behaviors can transfer or intensify across contexts; subterfuge and reward tampering as more severe generalization risks; study when reward hacking becomes a reusable strategy.
   - Expected papers: paper_08.pdf.
7. Detection and mitigation
   - Required ideas: audit reward models and evaluator behavior; detect abnormal feature use or reward-channel manipulation; combine better RL algorithms, data audits, adversarial tests, and monitoring.
   - Expected papers: paper_03.pdf, paper_08.pdf.

A reference blog is available at `references/RL_blog/blog.html` and its local assets should be used as the visual/content quality anchor. The executor does not need to reproduce the reference blog exactly, but figures in the submitted blog should be comparable in readability, crop quality, relevance, and explanatory value.

## 5. Figure Quality Requirements

When judging figures, open the generated HTML and inspect the actual rendered images, not only the file list. Award figure credit only for images that satisfy all of the following:

- Readability: the figure is not black/blank, not washed out, not tiny, not blurry, and text/axes/legends are readable at normal browser zoom.
- Completeness: the screenshot or copied image captures the whole relevant figure/table/algorithm panel, including labels, captions, axes, and important subpanels. Cropped-off algorithms, missing columns, cut legends, or partial plots should count as poor figures.
- Context match: the figure directly supports the paragraph/section where it appears.
- Source match: the figure must come from the cited paper, or match the corresponding figure in the hidden reference blog under references/<blog>/assets/images/. Do not give full credit for figures shown in unrelated sections or attributed to the wrong paper.
- Attribution: each figure has a visible caption or nearby text naming the source paper.
- Visual integration: images have reasonable width, margins, captions, and do not break the page layout.

The expected high-value figures include, or should be closely comparable to, the reference-blog images under references/RL_blog/assets/images/ (listed here by filename):

- assets/images/shortcut-features.png: Geirhos et al. 2020; purpose: shortcut learning and spurious features.
- assets/images/exp-reward-misspecification.png: Pan et al. 2022; purpose: reward misspecification experiment.
- assets/images/gameable-envs.png: Pan et al. 2022 / reward hacking environments; purpose: gameable RL environments.
- assets/images/rlhf-misleading.png: Wen et al. 2024; purpose: misleading behavior under RLHF.
- assets/images/rm-scaling-laws.png: Gao et al. 2023; purpose: reward-model overoptimization scaling.
- assets/images/ICRH-exp.png: Pan et al. 2024; purpose: in-context reward hacking experiment.
- assets/images/reward-hacking-generalization.png: Denison et al. 2024; purpose: generalization of reward tampering.
- assets/images/reward-hacking-detection.png: Denison et al. 2024 / mitigation; purpose: detection and mitigation of reward hacking.

Compare the executor's PDF figure screenshots against the reference asset list above for the same concept. Poor screenshots should not receive the same score as the clean reference-blog images.

## 6. Checkpoint Rubric

- 0.15 Paper identification and mapping: correctly identifies all eight PDFs and maps them to the intended sections in the selection note.
- 0.15 Concept coverage: covers the seven requested concept sections with the expected technical ideas.
- 0.15 Technical correctness: explanations are accurate, specific, and traceable to the provided papers.
- 0.25 Figure quality, relevance, and attribution: includes enough relevant figures, each rendered figure is readable and complete, screenshots are not black/blank/cropped, figures match the surrounding section, and every figure visibly cites its source paper.
- 0.10 HTML quality: final HTML opens cleanly, uses the provided stylesheet/visual style, has coherent headings, readable typography, and no major layout breakage.
- 0.10 MathJax/assets correctness: LaTeX formulas render correctly when present and all referenced CSS, JS, MathJax extension/font, and image assets are present in the output.
- 0.05 Selection note quality: `/tmp_workspace/results/selection_note.md` explains each section's selected papers and agrees with the blog.
- 0.05 Deliverables and paths: saves the HTML and assets under the requested result paths.

## 7. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Apply these caps strictly:

- If the HTML is missing, corrupt, or not openable, cap at 0.40.
- If the HTML opens but has no styling and appears as raw/default browser text due to missing CSS, cap at 0.65.
- If MathJax formulas are mostly raw TeX or broken because dynamic MathJax dependencies are missing, cap at 0.75.
- If the executor does not identify the papers beyond filename guessing and selects the wrong paper roles, cap at 0.60.
- If the blog omits two or more of the seven requested sections entirely, cap at 0.70.
- If any file referenced by the final HTML is missing or resolves to a nonexistent relative path, especially image/CSS/JS assets, cap at 0.60. The supervisor must parse the delivered HTML, resolve every img src, link href, and script src relative to the HTML file location, and verify the corresponding file exists in the submitted output.
- If the HTML references images using paths that only work in the executor workspace or `/tmp_workspace` but not from the delivered result directory, cap at 0.60 even if the images exist elsewhere in run artifacts.
- If serving the delivered blog directory over a local HTTP server produces 404s for any required image assets, cap at 0.60.
- Figures should be cropped directly from the paper, showing only the relevant figure or table — not the entire page. If figures are absent, cap at 0.40.
- If figures exist but many are black/blank, unreadable, badly cropped, or incomplete, cap at 0.50 even when the text is otherwise acceptable.
- If figures exist but are often mismatched with the surrounding content or cited paper, cap at 0.55.
- If figures are readable but noticeably lower quality than the reference blog assets and do not form a polished image-rich article, cap at 0.60.
- If figures are not attributed to source papers, cap at 0.70.
- If `/tmp_workspace/results/selection_note.md` is missing, cap at 0.85 even if the HTML is strong.

A score above 0.80 requires strong text plus strong figures and correct deliverable paths: every required HTML-referenced asset must resolve from the delivered HTML location without 404s; every referenced image must be present in the delivered result tree or otherwise reachable by the same relative URL used in the HTML; and at least most of the expected concepts must be illustrated by clear, complete, context-matched, attributed images comparable to the reference assets. Do not award 0.80+ to a blog whose figures would be unacceptable in a paper-reading blog presentation.

## 8. Continue vs Fail Guidance

Prefer continue when deliverables are missing, assets are not copied correctly, MathJax/CSS is broken but fixable, figure attribution is incomplete, or figure screenshots are poor but can be replaced with cleaner crops comparable to the reference-blog images. Prefer fail when the final output is about the wrong topic, substantially hallucinates paper content, cannot be opened, ignores the requested paper-reading structure, or has pervasive black/cropped/mismatched figures that make the paper-reading article visually misleading.

## 9. Hidden Reference Assets

- `ground_truth.json`: expected paper mapping, section outline, required figures/assets, and quality checks.
- `paper_mapping.json`: hidden PDF-title mapping for supervisor verification.
- `references/RL_blog/blog.html`: reference HTML blog and assets for content/style anchoring.

## 10. Dynamic Content Note

The paper set and assets are static. Do not accept substituting unrelated online sources for the provided PDFs. External knowledge may be used only to clarify presentation, not to replace paper-grounded content.
