# PDF Source Evidence - RAGAS

Source PDF: `sources/papers/ragas_evaluation.pdf`

This hidden supervisor aid was curated from the local PDF after inspecting
`pdftotext` output. It keeps only stable evidence needed for grading and omits
raw extraction artifacts. The executor only receives the PDF, not this evidence
file.

## E01 - Bibliographic Identity

- Title in the PDF: `RAGAS: Automated Evaluation of Retrieval Augmented Generation`
- Authors: Shahul Es, Jithin James, Luis Espinosa-Anke, and Steven Schockaert.
- Venue visible in the PDF: Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations, pages 150-158.
- Year: 2024.

## E02 - Main Task

- RAGAS is introduced as a framework for reference-free evaluation of Retrieval Augmented Generation pipelines.
- The paper frames RAG systems as having a retrieval module and an LLM-based generation module.
- It says RAG evaluation must consider relevant/focused context retrieval, faithful use of retrieved passages, and generation quality.

## E03 - Metric Suite

- Faithfulness checks whether claims in an answer can be inferred from the retrieved context.
- Answer relevance checks whether an answer directly addresses the question, penalizing incomplete or redundant answers.
- Context relevance checks whether the context contains information needed to answer the question and avoids redundant information.

## E04 - Results, API, and Limitation

- The paper reports that the proposed metrics align more closely with human judgments than two baselines in its experiments.
- It identifies context relevance as the hardest quality dimension to evaluate in the reported comparison.
- RAGAS provides a Python API for loading datasets, evaluating a pipeline with metrics, and exporting results to a pandas dataframe.
- The reproducibility discussion says repeated LLM-based prompt runs can vary because of API changes and neural model randomness.
- The limitations discussion says RAGAS relies heavily on the performance of the LLMs used for evaluation and requires careful review of evaluator-model suitability.
