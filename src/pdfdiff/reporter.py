"""Report generation for comparison results.

Supports JSON, text, and HTML output formats.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from pdfdiff.comparator import ComparisonResult

logger = logging.getLogger(__name__)


def _result_to_dict(result: ComparisonResult) -> dict:
    """Serialise a ComparisonResult to a JSON-safe dict."""
    return {
        "test_name": result.test_name,
        "ref_name": result.ref_name,
        "status": result.status,
        "passed": result.passed,
        "overall_ssim": round(result.overall_ssim, 2),
        "ref_page_count": result.ref_page_count,
        "test_page_count": result.test_page_count,
        "error_message": result.error_message,
        "pages": [
            {
                "page": p.page,
                "ssim_pct": round(p.similarity_pct, 2),
                "passed": p.passed,
            }
            for p in result.pages
        ],
    }


def write_json(results: List[ComparisonResult], output_dir: Path) -> Path:
    """Write results as a JSON file.

    Returns:
        Path to the written JSON file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "comparison_results.json"

    data = [_result_to_dict(r) for r in results]
    path.write_text(json.dumps(data, indent=2))
    logger.info("JSON report: %s", path)
    return path


def write_text(results: List[ComparisonResult], output_dir: Path) -> Path:
    """Write results as a plain-text report.

    Returns:
        Path to the written text file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "comparison_results.txt"

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    lines: list[str] = []
    lines.append(f"Comparison Results: {passed}/{total} passed")
    lines.append("-" * 50)

    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        lines.append(f"[{icon}] {r.test_name}")

        if r.status == "error":
            lines.append(f"    Error: {r.error_message}")
        elif r.status == "missing_reference":
            lines.append(f"    No reference found")
        else:
            lines.append(f"    SSIM: {r.overall_ssim:.2f}%")
            if r.ref_page_count != r.test_page_count:
                lines.append(
                    f"    Page count mismatch: ref={r.ref_page_count} test={r.test_page_count}"
                )
            for p in r.pages:
                status = "ok" if p.passed else "DIFF"
                lines.append(f"      Page {p.page}: {p.similarity_pct:.2f}% [{status}]")

    text = "\n".join(lines) + "\n"
    path.write_text(text)
    logger.info("Text report: %s", path)
    return path


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PDF Diff Report</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: .5rem; }}
  .summary {{ font-size: 1.1rem; margin-bottom: 1.5rem; }}
  .result {{ border: 1px solid #ddd; border-radius: 6px; padding: 1rem; margin-bottom: 1rem; }}
  .result.pass {{ border-left: 4px solid #22c55e; }}
  .result.fail {{ border-left: 4px solid #ef4444; }}
  .result.error {{ border-left: 4px solid #f59e0b; }}
  .filename {{ font-weight: 600; font-size: 1.05rem; }}
  .pages {{ margin-top: .5rem; font-size: .9rem; color: #555; }}
  .diff-img {{ max-width: 100%; margin-top: .5rem; border: 1px solid #eee; }}
</style>
</head>
<body>
<h1>PDF Diff Report</h1>
<div class="summary">{passed}/{total} comparisons passed</div>
{cards}
</body>
</html>
"""

_CARD_TEMPLATE = """\
<div class="result {css_class}">
  <div class="filename">{icon} {name}</div>
  <div>SSIM: {ssim}% &middot; Status: {status}</div>
  <div class="pages">{page_detail}</div>
  {images_html}
</div>
"""


def write_html(
    results: List[ComparisonResult],
    output_dir: Path,
    diff_images: dict[str, list[Path]] | None = None,
) -> Path:
    """Write results as an HTML report.

    Args:
        results: Comparison results.
        output_dir: Directory for the report.
        diff_images: Optional mapping of test_name → list of diff image paths.

    Returns:
        Path to the written HTML file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for r in results if r.passed)
    cards: list[str] = []

    for r in results:
        if r.passed:
            css_class, icon = "pass", "&#x2705;"
        elif r.status == "error":
            css_class, icon = "error", "&#x26A0;"
        else:
            css_class, icon = "fail", "&#x274C;"

        page_lines = []
        for p in r.pages:
            tag = "ok" if p.passed else "DIFF"
            page_lines.append(f"Page {p.page}: {p.similarity_pct:.2f}% [{tag}]")
        page_detail = "<br>".join(page_lines) if page_lines else ""

        images_html = ""
        if diff_images and r.test_name in diff_images:
            imgs = diff_images[r.test_name]
            images_html = "".join(
                f'<img class="diff-img" src="{img.name}" alt="diff page">'
                for img in imgs
            )

        cards.append(
            _CARD_TEMPLATE.format(
                css_class=css_class,
                icon=icon,
                name=r.test_name,
                ssim=f"{r.overall_ssim:.2f}",
                status=r.status,
                page_detail=page_detail,
                images_html=images_html,
            )
        )

    html = _HTML_TEMPLATE.format(
        passed=passed, total=len(results), cards="\n".join(cards)
    )
    path = output_dir / "comparison_results.html"
    path.write_text(html)
    logger.info("HTML report: %s", path)
    return path
