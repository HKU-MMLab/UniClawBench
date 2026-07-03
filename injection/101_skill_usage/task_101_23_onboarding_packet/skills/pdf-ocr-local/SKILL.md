---
name: pdf-ocr-local
description: Extract text from scanned or image-heavy PDFs using available local OCR/PDF tooling, then preserve page references for downstream analysis.
---

# Local PDF OCR Skill

Use the source documents already available in the workspace. Do not request external OCR credentials. Use local tools that are already available, such as `pdftotext`, Python PDF libraries, image conversion tools, or OCR binaries if present.

## Workflow

1. Inventory the PDF pages and identify text-native versus scanned/image-heavy pages.
2. Extract text with available local tools.
3. For weak OCR pages, record the page number and the confidence/uncertainty in your notes.
4. Preserve page references in the final packet so the user can verify important facts.
5. When the user requests Word/PDF output, use available document tooling and validate that required sections are present.

Never expose credentials in outputs.
