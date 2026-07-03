# PDF Source Evidence - ARES

Source PDF: `sources/papers/ares_rag_evaluation.pdf`

This hidden supervisor aid was curated from the local PDF after inspecting
`pdftotext` output. It keeps only stable evidence needed for grading and omits
raw table extraction noise. The executor only receives the PDF, not this
evidence file.

## E01 - Bibliographic Identity

- Title: `ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems`
- Authors: Jon Saad-Falcon, Omar Khattab, Christopher Potts, and Matei Zaharia.
- Venue visible in the PDF: Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1: Long Papers, pages 338-354.
- Year: 2024.

## E02 - Main Task and Metric Dimensions

- ARES evaluates RAG systems along context relevance, answer faithfulness, and answer relevance.
- It creates synthetic training data and fine-tunes lightweight LM judges for individual RAG components.
- It uses a small human-annotated validation set with prediction-powered inference (PPI) to mitigate prediction errors and provide confidence intervals.

## E03 - Evaluation Scope and Results

- The abstract reports evaluation across eight knowledge-intensive tasks from KILT, SuperGLUE, and AIS.
- The paper compares ARES against RAGAS, a few-shot GPT-3.5 judge, and sampled annotation baselines.
- The table discussion reports that ARES ranked RAG systems more accurately than RAGAS and GPT-3.5 across the explored datasets.
- It reports average Kendall's tau improvements over RAGAS of 0.065 for context relevance and 0.132 for answer relevance.

## E04 - Limitations

- ARES still relies on a small human preference validation set, roughly 150-300 datapoints, with more being better.
- Specialized domains such as law, medicine, and finance may require annotators with domain expertise.
- The LLMs used by ARES benefit from GPUs with substantial memory; the paper cites about 32GB of GPU memory for DeBERTa-v3-Large and FLAN-T5-XXL.
- The evaluation datasets used in the paper are English, and future work should explore other languages.
