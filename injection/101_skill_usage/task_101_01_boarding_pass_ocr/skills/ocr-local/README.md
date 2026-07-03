# OCR Skill for OpenClaw

📝 Extract text from images using Tesseract.js OCR.

## Features

- **Multi-language support**: Simplified Chinese, Traditional Chinese, English
- **Easy to use**: Single command to recognize any image
- **Flexible output**: Plain text or JSON format
- **No API key required**: Runs locally with Tesseract.js

## Runtime

The task workspace injects this skill and installs its Node.js dependency
during setup. Run the provided script directly; do not install packages during
the user task.

## Usage

```bash
# Basic usage (Chinese + English)
node {baseDir}/scripts/ocr.js /path/to/image.jpg

# Specify language
node {baseDir}/scripts/ocr.js image.png --lang chi_sim
node {baseDir}/scripts/ocr.js image.png --lang chi_tra+eng
node {baseDir}/scripts/ocr.js image.png --lang eng

# JSON output
node {baseDir}/scripts/ocr.js image.jpg --json
```

## Language Codes

- `chi_sim` - Simplified Chinese
- `chi_tra` - Traditional Chinese
- `eng` - English
- Combine with `+`: `chi_sim+eng`, `chi_tra+eng`

## Examples

### Recognize a screenshot
```bash
node /root/skills/ocr-local/scripts/ocr.js ~/Downloads/screenshot.png
```

### Extract text from a photo of document
```bash
node /root/skills/ocr-local/scripts/ocr.js document.jpg --lang chi_sim+eng
```

### Get structured output with confidence scores
```bash
node /root/skills/ocr-local/scripts/ocr.js image.jpg --json
```

## Notes

- First run downloads Tesseract.js language data (~20MB per language)
- Subsequent runs use cached data
- Works best with clear, high-contrast images
- Handwritten text recognition accuracy may vary
- For best results, ensure images are well-lit and text is clearly visible

## License

MIT License

## Credits

Powered by [Tesseract.js](https://github.com/naptha/tesseract.js)
