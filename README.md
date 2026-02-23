# pdfdiff

Visual PDF diffing tool for InDesign workflows. Compare exported PDFs against reference images using SSIM (Structural Similarity Index).

## Why?

When you update InDesign templates or data, you need to verify the output PDFs look correct. Raw pixel diffing produces false positives from anti-aliasing and font hinting differences. **pdfdiff** uses SSIM — a perceptually-aware metric — to catch real visual changes while ignoring rendering noise.

## How it works

1. **`pdfdiff init`** — Render your baseline PDFs to PNG reference images (one per page)
2. **`pdfdiff compare`** — Render new PDFs, compare each page against references using SSIM, generate reports

References are stored as images so the baseline doesn't shift when rendering engines update.

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Usage

```bash
# Step 1: Create reference images from known-good PDFs
pdfdiff init -p ./baseline_pdfs -r ./reference

# Step 2: Compare new exports against references
pdfdiff compare -t ./new_exports -r ./reference -o ./results

# With options
pdfdiff compare -t ./new -r ./ref -o ./out --threshold 95 --format html --dpi 300

# All report formats at once
pdfdiff compare -t ./new -r ./ref -o ./out --format all

# Interactive mode — approve changes and update references
pdfdiff compare -t ./new -r ./ref -o ./out --interactive
```

## Output formats

- **JSON** — machine-readable results (`comparison_results.json`)
- **Text** — terminal-friendly summary (`comparison_results.txt`)
- **HTML** — visual report with embedded diff images (`comparison_results.html`)

## Reference naming convention

Reference images follow the pattern `{pdf_stem}_page_{n}.png`:

```
reference/
├── invoice_page_1.png
├── invoice_page_2.png
├── report_page_1.png
└── report_page_2.png
```

## Development

```bash
# Run tests
pytest

# With coverage
pytest --cov

# Only unit tests
pytest -m unit
```
