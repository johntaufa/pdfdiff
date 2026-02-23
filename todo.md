# pdfdiff — Project Plan

## Todo Items

- [x] Design project structure (src layout, pyproject.toml)
- [x] Implement renderer module (PyMuPDF-based PDF → image)
- [x] Implement comparator module (SSIM + diff overlay)
- [x] Implement reporter module (JSON, text, HTML)
- [x] Implement CLI with subcommands (compare, init)
- [x] Add interactive approval mode
- [x] Write unit tests for renderer
- [x] Write unit tests for comparator
- [x] Write unit tests for reporter
- [x] Write unit tests for CLI
- [x] Create CLAUDE.md, README.md, .gitignore
- [x] Run full test suite and verify coverage
- [x] Fix any test failures (numpy bool serialization)

## Review

**62 tests passing, 91.5% coverage** (threshold: 85%)

| Module | Coverage | Tests |
|--------|----------|-------|
| comparator.py | 100% | 12 |
| reporter.py | 100% | 14 |
| renderer.py | 98% | 8 |
| cli.py | 82% | 22 |
| __init__.py | 100% | — |

The uncovered 18% in cli.py is the interactive approval flow (requires stdin mocking) and a debug log line in the renderer. Both are acceptable gaps.

### Bug found & fixed during testing
- numpy's SSIM comparison returns `np.bool_` not Python `bool`, which broke both `is True` assertions and JSON serialization. Fixed by explicit `bool()` cast in `compare_images()`.
