# PyMuPDF PDF Parser - Clawdbot Skill

A [Clawdbot](https://github.com/clawdbot/clawdbot) skill for fast, lightweight PDF parsing using [PyMuPDF](https://pymupdf.readthedocs.io/) (fitz). Ideal for quick text extraction when speed matters.

## Features

- **Fast processing** — Parses PDFs in ~1 second per page
- **Lightweight** — Single pip dependency, no heavy models
- **Markdown output** — Clean text extraction with page markers
- **JSON output** — Simple structured text per page
- **Image extraction** — Optional embedded image extraction
- **NixOS compatible** — Includes notes for libstdc++ issues

## Runtime

The task workspace injects this skill and provides PyMuPDF during setup. Run
the parser directly from the skill directory; do not install packages during
the user task.

### NixOS users

If you hit `libstdc++` import errors:

```bash
export LD_LIBRARY_PATH=/nix/store/<your-gcc-lib-path>/lib
```

See `pymupdf-pdf/references/pymupdf-notes.md` for details.

## Usage

### Quick start

```bash
# Run from the skill directory
./scripts/pymupdf_parse.py /path/to/document.pdf
```

### Options

```bash
./scripts/pymupdf_parse.py /path/to/document.pdf --format json
./scripts/pymupdf_parse.py /path/to/document.pdf --format both --images
./scripts/pymupdf_parse.py /path/to/document.pdf --outroot ./my-output
```

| Option | Default | Description |
|--------|---------|-------------|
| `--format` | `md` | Output format: `md`, `json`, or `both` |
| `--outroot` | `./pymupdf-output` | Output root directory |
| `--images` | off | Extract embedded images |
| `--tables` | off | Extract line-based table approximation |
| `--lang` | `en` | Language hint (stored in JSON metadata) |

## Output

Creates a per-document folder under the output root:

```
./pymupdf-output/
└── document-name/
    ├── output.md      # Markdown with page markers
    ├── output.json    # Simple JSON (~1KB, text per page)
    ├── images/        # Extracted images (if --images)
    └── tables.json    # Line-based tables (if --tables)
```

### Output quality

PyMuPDF produces **fast, minimal output**:
- Plain text extraction (no layout preservation)
- Simple JSON with text per page
- Optional image extraction

**Best for:** Quick text extraction, batch processing, or when speed matters.

## Comparison with MinerU

| Aspect | PyMuPDF | MinerU |
|--------|---------|--------|
| Speed | Fast (~1s/page) | Slower (~15-30s/page) |
| JSON output | Minimal (~1KB, text only) | Rich (~50KB+, layout data) |
| Image extraction | Optional | Automatic |
| Layout preservation | Basic | Excellent |
| Dependencies | Light, provided by task setup | Heavy (~20GB models) |

**Use PyMuPDF when:** Speed matters or for simple text extraction.  
**Use MinerU when:** Quality and structure matter more than speed.

## License

Apache 2.0

## Contributing

Issues and PRs welcome. Please test changes with various PDF types before submitting.

## Related

- [MinerU PDF Parser Skill](https://github.com/kesslerio/MinerU-PDF-Parser-Clawdbot-Skill) — Rich, layout-aware alternative
- [PyMuPDF](https://pymupdf.readthedocs.io/) — The underlying PDF library
- [Clawdbot](https://github.com/clawdbot/clawdbot) — The AI agent framework
