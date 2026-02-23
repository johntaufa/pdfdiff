"""Command-line interface for pdfdiff.

Orchestrates: render PDF → compare against references → generate report.

Reference images are stored as PNGs (one per page) so the baseline is
stable and doesn't shift with rendering engine updates.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import List

from pdfdiff.comparator import (
    ComparisonResult,
    PageResult,
    compare_page_lists,
    DEFAULT_THRESHOLD,
)
from pdfdiff.renderer import load_reference_image, render_pdf, save_image
from pdfdiff.reporter import write_html, write_json, write_text

logger = logging.getLogger(__name__)


def _reference_images_for(ref_dir: Path, stem: str) -> list[Path]:
    """Find reference PNGs for a given PDF stem, sorted by page number.

    Convention: <stem>_page_1.png, <stem>_page_2.png, …
    """
    pattern = f"{stem}_page_*.png"
    paths = sorted(ref_dir.glob(pattern))
    return paths


def _save_diff_images(
    result: ComparisonResult,
    output_dir: Path,
) -> list[Path]:
    """Save diff overlay images for pages that failed."""
    saved: list[Path] = []
    for p in result.pages:
        if not p.passed and p.diff_overlay is not None:
            stem = Path(result.test_name).stem
            name = f"{stem}_page_{p.page}_diff.png"
            path = save_image(p.diff_overlay, output_dir / name)
            saved.append(path)
    return saved


def compare_one(
    test_pdf: Path,
    ref_dir: Path,
    output_dir: Path,
    threshold: float,
    dpi: int,
    interactive: bool = False,
) -> ComparisonResult:
    """Compare a single test PDF against its reference images.

    Args:
        test_pdf: Path to the test PDF.
        ref_dir: Directory containing reference PNGs.
        output_dir: Directory for diff images.
        threshold: SSIM pass/fail threshold (0-100).
        dpi: DPI for rendering the test PDF.
        interactive: If True, prompt user for approval on failures.

    Returns:
        A ComparisonResult.
    """
    stem = test_pdf.stem
    ref_paths = _reference_images_for(ref_dir, stem)

    if not ref_paths:
        return ComparisonResult(
            test_name=test_pdf.name,
            ref_name="",
            pages=[],
            ref_page_count=0,
            test_page_count=0,
            status="missing_reference",
            error_message=f"No reference images found for {stem}",
        )

    # Render test PDF
    try:
        test_images = render_pdf(test_pdf, dpi=dpi)
    except Exception as exc:
        return ComparisonResult(
            test_name=test_pdf.name,
            ref_name=ref_paths[0].name,
            pages=[],
            ref_page_count=len(ref_paths),
            test_page_count=0,
            status="error",
            error_message=str(exc),
        )

    # Load reference images
    ref_images = [load_reference_image(p) for p in ref_paths]

    # Compare
    page_results = compare_page_lists(ref_images, test_images, threshold)

    result = ComparisonResult(
        test_name=test_pdf.name,
        ref_name=f"{stem}_page_*.png",
        pages=page_results,
        ref_page_count=len(ref_images),
        test_page_count=len(test_images),
    )

    # Interactive approval
    if interactive:
        _handle_interactive(result, test_pdf, ref_dir, output_dir, dpi)

    return result


def _handle_interactive(
    result: ComparisonResult,
    test_pdf: Path,
    ref_dir: Path,
    output_dir: Path,
    dpi: int,
) -> None:
    """Prompt user for approval on failed pages and update references."""
    failed_pages = [p for p in result.pages if not p.passed]
    if not failed_pages and result.passed:
        print(f"  ✓ {result.test_name}: exact match, no action needed.")
        return

    if result.ref_page_count != result.test_page_count:
        print(
            f"  ⚠ {result.test_name}: page count changed "
            f"({result.ref_page_count} → {result.test_page_count})"
        )

    # Save diff images so user can review
    diff_paths = _save_diff_images(result, output_dir)
    for dp in diff_paths:
        print(f"  Diff image: {dp}")

    response = input(
        f"  Approve changes for {result.test_name}? [y/n/s(kip)] "
    ).lower().strip()

    if response in ("y", "yes"):
        # Re-render and save as new references
        test_images = render_pdf(test_pdf, dpi=dpi)
        stem = test_pdf.stem
        for i, img in enumerate(test_images, 1):
            save_image(img, ref_dir / f"{stem}_page_{i}.png")
        # Remove old references that exceed new page count
        for old in _reference_images_for(ref_dir, stem):
            page_num = int(old.stem.split("_page_")[-1])
            if page_num > len(test_images):
                old.unlink()
        print(f"  ✓ References updated for {result.test_name}")
    elif response in ("s", "skip"):
        print(f"  ⏭ Skipped {result.test_name}")
    else:
        print(f"  ✗ Changes rejected for {result.test_name}")


def compare_directory(
    test_dir: Path,
    ref_dir: Path,
    output_dir: Path,
    threshold: float,
    dpi: int,
    interactive: bool = False,
) -> list[ComparisonResult]:
    """Compare all PDFs in test_dir against references in ref_dir."""
    test_pdfs = sorted(test_dir.glob("*.pdf"))
    if not test_pdfs:
        logger.warning("No PDFs found in %s", test_dir)
        return []

    results: list[ComparisonResult] = []
    diff_images: dict[str, list[Path]] = {}

    for pdf in test_pdfs:
        print(f"Comparing: {pdf.name}")
        result = compare_one(pdf, ref_dir, output_dir, threshold, dpi, interactive)
        results.append(result)

        # Save diff images
        saved = _save_diff_images(result, output_dir)
        if saved:
            diff_images[result.test_name] = saved

    return results


def init_references(
    pdf_dir: Path, ref_dir: Path, dpi: int
) -> None:
    """Initialise reference images from a directory of PDFs.

    Renders every PDF and saves page images to ref_dir.
    """
    ref_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}")
        return

    for pdf in pdfs:
        print(f"Rendering: {pdf.name}")
        images = render_pdf(pdf, dpi=dpi)
        for i, img in enumerate(images, 1):
            dest = ref_dir / f"{pdf.stem}_page_{i}.png"
            save_image(img, dest)
            print(f"  Saved: {dest.name}")

    print(f"\nInitialised {len(pdfs)} PDF(s) → {ref_dir}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pdfdiff",
        description="Visual PDF diffing tool — compare exported PDFs against reference images using SSIM.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- compare ---
    cmp = sub.add_parser("compare", help="Compare test PDFs against references.")
    cmp.add_argument("-t", "--test-dir", type=Path, required=True, help="Directory containing test PDFs.")
    cmp.add_argument("-r", "--ref-dir", type=Path, required=True, help="Directory containing reference PNGs.")
    cmp.add_argument("-o", "--output", type=Path, required=True, help="Output directory for reports and diffs.")
    cmp.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help=f"SSIM threshold (0-100, default {DEFAULT_THRESHOLD}).")
    cmp.add_argument("--dpi", type=int, default=150, help="Render DPI (default 150).")
    cmp.add_argument("--format", choices=["json", "text", "html", "all"], default="json", help="Report format (default json).")
    cmp.add_argument("--interactive", action="store_true", help="Prompt for approval on failures.")
    cmp.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")

    # --- init ---
    init = sub.add_parser("init", help="Initialise reference images from PDFs.")
    init.add_argument("-p", "--pdf-dir", type=Path, required=True, help="Directory containing source PDFs.")
    init.add_argument("-r", "--ref-dir", type=Path, required=True, help="Directory to store reference PNGs.")
    init.add_argument("--dpi", type=int, default=150, help="Render DPI (default 150).")
    init.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    if args.command == "init":
        if not args.pdf_dir.exists():
            print(f"Error: PDF directory does not exist: {args.pdf_dir}")
            return 1
        init_references(args.pdf_dir, args.ref_dir, args.dpi)
        return 0

    if args.command == "compare":
        if not args.test_dir.exists():
            print(f"Error: Test directory does not exist: {args.test_dir}")
            return 1
        if not args.ref_dir.exists():
            print(f"Error: Reference directory does not exist: {args.ref_dir}")
            return 1

        args.output.mkdir(parents=True, exist_ok=True)

        results = compare_directory(
            args.test_dir,
            args.ref_dir,
            args.output,
            args.threshold,
            args.dpi,
            args.interactive,
        )

        # Write reports
        fmt = args.format
        if fmt in ("json", "all"):
            write_json(results, args.output)
        if fmt in ("text", "all"):
            write_text(results, args.output)
        if fmt in ("html", "all"):
            diff_images: dict[str, list[Path]] = {}
            for r in results:
                stem = Path(r.test_name).stem
                diffs = sorted(args.output.glob(f"{stem}_*_diff.png"))
                if diffs:
                    diff_images[r.test_name] = diffs
            write_html(results, args.output, diff_images)

        # Summary
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        print(f"\nResults: {passed}/{total} passed")

        return 0 if passed == total else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
