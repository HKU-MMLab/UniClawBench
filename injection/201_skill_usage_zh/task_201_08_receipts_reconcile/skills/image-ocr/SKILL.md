---
name: image-ocr
description: "Extract text from images using Tesseract OCR"
metadata:
  {
    "openclaw":
      {
        "emoji": "👁️",
        "requires": { "bins": ["tesseract"] },
      },
  }
---

# Image OCR

Extract text from images using Tesseract OCR. Supports multiple languages and image formats including PNG, JPEG, TIFF, and BMP.

## Commands

```bash
# Extract text from an image (default: English)
tesseract "screenshot.png" stdout -l eng

# Extract text with a specific language
tesseract "document.jpg" stdout -l deu+eng --psm 6
```

## Runtime

The task workspace provides `tesseract` during setup. If it is unavailable,
report the missing command as an environment problem instead of installing
packages during the user task.
