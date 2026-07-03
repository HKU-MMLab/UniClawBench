# PDF Source Evidence - RAG Survey

Source PDF: `sources/rag_survey_pack/rag_survey.pdf`

This hidden supervisor aid was curated from the local PDF after inspecting
`pdftotext` output. Table fragments and repeated column headers such as
`Text`/`Sentence` were intentionally removed. The executor only receives the
PDF, not this evidence file.

## E01 - Bibliographic Identity

- Title: `Retrieval-Augmented Generation for Large Language Models: A Survey`
- Authors: Yunfan Gao, Yun Xiong, Xinyu Gao, Kangxiang Jia, Jinliu Pan, Yuxi Bi, Yi Dai, Jiawei Sun, Meng Wang, and Haofen Wang.
- Identifier/version visible in the PDF header: `arXiv:2312.10997v5 [cs.CL] 27 Mar 2024`.

## E02 - Abstract and Objective

- The abstract says LLMs face hallucination, outdated knowledge, and opaque reasoning problems.
- RAG is presented as a solution that incorporates external databases to improve accuracy, credibility, and knowledge updates.
- The survey reviews Naive RAG, Advanced RAG, and Modular RAG.
- The survey examines retrieval, generation, and augmentation techniques, and also covers evaluation frameworks, benchmarks, challenges, and future directions.

## E03 - Scope and Organization

- The introduction states that the paper summarizes three main research paradigms from over 100 RAG studies.
- The stated core stages are `Retrieval`, `Generation`, and `Augmentation`.
- The contribution list says the assessment review covers 26 tasks and nearly 50 datasets.
- Naive RAG is described as an indexing, retrieval, and generation pipeline.
- Advanced RAG improves retrieval quality with pre-retrieval and post-retrieval strategies.
- Modular RAG introduces more flexible modules and non-sequential patterns such as iterative and adaptive retrieval.

## E04 - Evaluation Dimensions

- The survey separates retrieval quality and generation quality.
- Quality scores include context relevance, answer faithfulness, and answer relevance.
- Required abilities include noise robustness, negative rejection, information integration, and counterfactual robustness.
- The survey maps context relevance and noise robustness mainly to retrieval quality, while answer faithfulness, answer relevance, negative rejection, information integration, and counterfactual robustness are important for generation quality.

## E05 - Challenges and Future Work

- Retrieval challenges include precision/recall errors, irrelevant chunks, and missed crucial information.
- Generation challenges include hallucination, irrelevance, toxicity, or bias in outputs not supported by retrieved context.
- Post-retrieval challenges include reranking, context selection/compression, avoiding information overload, and shortening noisy contexts.
- The survey says current RAG evaluation metrics are not yet mature or standardized.
- Future-facing challenges include long-context tradeoffs, robustness to noisy or contradictory retrieval, production engineering concerns, multimodal RAG, and evaluation methods that keep pace with RAG's expansion.
