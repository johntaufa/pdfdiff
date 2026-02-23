# CLAUDE.md

## Project Overview

**pdfdiff** — a Python CLI tool for visually diffing InDesign PDF exports against reference images using SSIM (Structural Similarity Index).

## Architecture

```
src/pdfdiff/
├── __init__.py       # Package metadata
├── renderer.py       # PDF → image conversion (PyMuPDF)
├── comparator.py     # SSIM comparison + diff overlay generation
├── reporter.py       # JSON / text / HTML report output
└── cli.py            # CLI entry point + orchestration
```

**Key design decisions:**
- References stored as PNGs (not PDFs) for stable baselines
- SSIM for perceptually-aware comparison (ignores anti-aliasing noise)
- PyMuPDF instead of poppler — faster, no external binary deps, better InDesign support
- Pixel diff used only for visual overlay, not scoring

## Commands

```bash
# Install
pip install -e ".[dev]"

# Initialise references from PDFs
pdfdiff init -p ./pdfs -r ./reference

# Compare test PDFs against references
pdfdiff compare -t ./test -r ./reference -o ./results
pdfdiff compare -t ./test -r ./reference -o ./results --format html --threshold 95
pdfdiff compare -t ./test -r ./reference -o ./results --format all --interactive

# Run tests
pytest
pytest --cov
pytest -m unit
pytest -m integration
```

## Testing

- Uses pytest with fixtures that generate PDFs on the fly via reportlab
- Shared fixtures in `tests/conftest.py`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`

## Standard Workflow

1. Read codebase, write a plan to `tasks/todo.md`
2. Check in with user before starting
3. Work through todos, marking complete as you go
4. Add review section to `tasks/todo.md`
5. Commit periodically
