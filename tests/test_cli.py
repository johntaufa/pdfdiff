"""Tests for pdfdiff.cli."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from pdfdiff.cli import (
    build_parser,
    compare_directory,
    compare_one,
    init_references,
    main,
    _reference_images_for,
)
from pdfdiff.renderer import render_pdf, save_image


@pytest.fixture
def ref_dir_with_images(tmp_path: Path, sample_pdf: Path) -> Path:
    """Render a sample PDF and save references."""
    ref_dir = tmp_path / "ref"
    ref_dir.mkdir()
    images = render_pdf(sample_pdf)
    for i, img in enumerate(images, 1):
        save_image(img, ref_dir / f"sample_page_{i}.png")
    return ref_dir


@pytest.fixture
def test_dir_with_pdf(tmp_path: Path, sample_pdf: Path) -> Path:
    """Create a test directory with a copy of the sample PDF."""
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    import shutil
    shutil.copy2(sample_pdf, test_dir / "sample.pdf")
    return test_dir


@pytest.fixture
def test_dir_with_modified_pdf(tmp_path: Path, sample_pdf_modified: Path) -> Path:
    """Create a test directory with a modified PDF."""
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    import shutil
    shutil.copy2(sample_pdf_modified, test_dir / "sample.pdf")
    return test_dir


class TestReferenceImageLookup:
    """Tests for _reference_images_for()."""

    @pytest.mark.unit
    def test_finds_matching_refs(self, ref_dir_with_images: Path):
        paths = _reference_images_for(ref_dir_with_images, "sample")
        assert len(paths) == 1
        assert "sample_page_1.png" in paths[0].name

    @pytest.mark.unit
    def test_no_refs_found(self, tmp_path: Path):
        ref_dir = tmp_path / "empty_ref"
        ref_dir.mkdir()
        paths = _reference_images_for(ref_dir, "nonexistent")
        assert paths == []


class TestCompareOne:
    """Tests for compare_one()."""

    @pytest.mark.unit
    def test_identical_pdf_passes(
        self, test_dir_with_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        pdf = test_dir_with_pdf / "sample.pdf"
        result = compare_one(pdf, ref_dir_with_images, output, threshold=95.0, dpi=150)
        assert result.status == "completed"
        assert result.passed is True
        assert result.overall_ssim > 95.0

    @pytest.mark.unit
    def test_modified_pdf_fails(
        self, test_dir_with_modified_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        pdf = test_dir_with_modified_pdf / "sample.pdf"
        result = compare_one(pdf, ref_dir_with_images, output, threshold=99.5, dpi=150)
        assert result.status == "completed"
        # Modified PDF should score lower
        assert result.overall_ssim < 100.0

    @pytest.mark.unit
    def test_missing_reference(self, test_dir_with_pdf: Path, tmp_path: Path):
        empty_ref = tmp_path / "empty_ref"
        empty_ref.mkdir()
        output = tmp_path / "output"
        pdf = test_dir_with_pdf / "sample.pdf"
        result = compare_one(pdf, empty_ref, output, threshold=95.0, dpi=150)
        assert result.status == "missing_reference"

    @pytest.mark.unit
    def test_invalid_pdf(self, tmp_path: Path, ref_dir_with_images: Path):
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        bad_pdf = test_dir / "sample.pdf"
        bad_pdf.write_text("not a pdf")
        output = tmp_path / "output"
        result = compare_one(bad_pdf, ref_dir_with_images, output, threshold=95.0, dpi=150)
        assert result.status == "error"


class TestCompareDirectory:
    """Tests for compare_directory()."""

    @pytest.mark.unit
    def test_compares_all_pdfs(
        self, test_dir_with_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        results = compare_directory(
            test_dir_with_pdf, ref_dir_with_images, output, threshold=95.0, dpi=150
        )
        assert len(results) == 1
        assert results[0].test_name == "sample.pdf"

    @pytest.mark.unit
    def test_empty_test_dir(self, tmp_path: Path, ref_dir_with_images: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        output = tmp_path / "output"
        results = compare_directory(
            empty, ref_dir_with_images, output, threshold=95.0, dpi=150
        )
        assert results == []


class TestInitReferences:
    """Tests for init_references()."""

    @pytest.mark.unit
    def test_creates_reference_images(self, tmp_path: Path, sample_pdf: Path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        import shutil
        shutil.copy2(sample_pdf, pdf_dir / "doc.pdf")

        ref_dir = tmp_path / "refs"
        init_references(pdf_dir, ref_dir, dpi=150)

        refs = list(ref_dir.glob("*.png"))
        assert len(refs) == 1
        assert "doc_page_1.png" in refs[0].name

    @pytest.mark.unit
    def test_no_pdfs_in_dir(self, tmp_path: Path, capsys):
        pdf_dir = tmp_path / "empty"
        pdf_dir.mkdir()
        ref_dir = tmp_path / "refs"
        init_references(pdf_dir, ref_dir, dpi=150)
        captured = capsys.readouterr()
        assert "No PDFs found" in captured.out


class TestBuildParser:
    """Tests for build_parser()."""

    @pytest.mark.unit
    def test_compare_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "compare", "-t", "./test", "-r", "./ref", "-o", "./out"
        ])
        assert args.command == "compare"
        assert args.threshold == 99.0
        assert args.dpi == 150

    @pytest.mark.unit
    def test_init_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["init", "-p", "./pdfs", "-r", "./ref"])
        assert args.command == "init"

    @pytest.mark.unit
    def test_compare_all_options(self):
        parser = build_parser()
        args = parser.parse_args([
            "compare", "-t", "./test", "-r", "./ref", "-o", "./out",
            "--threshold", "85", "--dpi", "300", "--format", "html",
            "--interactive", "-v",
        ])
        assert args.threshold == 85.0
        assert args.dpi == 300
        assert args.format == "html"
        assert args.interactive is True
        assert args.verbose is True


class TestMainFunction:
    """Tests for the main() entry point."""

    @pytest.mark.unit
    def test_compare_json_output(
        self, test_dir_with_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        exit_code = main([
            "compare",
            "-t", str(test_dir_with_pdf),
            "-r", str(ref_dir_with_images),
            "-o", str(output),
            "--format", "json",
            "--threshold", "90",
        ])
        assert exit_code == 0
        json_file = output / "comparison_results.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert len(data) == 1
        assert data[0]["passed"] is True

    @pytest.mark.unit
    def test_compare_text_output(
        self, test_dir_with_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        exit_code = main([
            "compare",
            "-t", str(test_dir_with_pdf),
            "-r", str(ref_dir_with_images),
            "-o", str(output),
            "--format", "text",
        ])
        text_file = output / "comparison_results.txt"
        assert text_file.exists()

    @pytest.mark.unit
    def test_compare_html_output(
        self, test_dir_with_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        exit_code = main([
            "compare",
            "-t", str(test_dir_with_pdf),
            "-r", str(ref_dir_with_images),
            "-o", str(output),
            "--format", "html",
        ])
        html_file = output / "comparison_results.html"
        assert html_file.exists()

    @pytest.mark.unit
    def test_compare_all_formats(
        self, test_dir_with_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        output = tmp_path / "output"
        main([
            "compare",
            "-t", str(test_dir_with_pdf),
            "-r", str(ref_dir_with_images),
            "-o", str(output),
            "--format", "all",
        ])
        assert (output / "comparison_results.json").exists()
        assert (output / "comparison_results.txt").exists()
        assert (output / "comparison_results.html").exists()

    @pytest.mark.unit
    def test_compare_missing_test_dir(self, tmp_path: Path):
        exit_code = main([
            "compare",
            "-t", str(tmp_path / "nope"),
            "-r", str(tmp_path),
            "-o", str(tmp_path / "out"),
        ])
        assert exit_code == 1

    @pytest.mark.unit
    def test_compare_missing_ref_dir(self, tmp_path: Path):
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        exit_code = main([
            "compare",
            "-t", str(test_dir),
            "-r", str(tmp_path / "nope"),
            "-o", str(tmp_path / "out"),
        ])
        assert exit_code == 1

    @pytest.mark.unit
    def test_init_command(self, tmp_path: Path, sample_pdf: Path):
        import shutil
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        shutil.copy2(sample_pdf, pdf_dir / "doc.pdf")

        ref_dir = tmp_path / "refs"
        exit_code = main(["init", "-p", str(pdf_dir), "-r", str(ref_dir)])
        assert exit_code == 0
        assert list(ref_dir.glob("*.png"))

    @pytest.mark.unit
    def test_init_missing_pdf_dir(self, tmp_path: Path):
        exit_code = main([
            "init", "-p", str(tmp_path / "nope"), "-r", str(tmp_path / "ref")
        ])
        assert exit_code == 1

    @pytest.mark.unit
    def test_failed_comparison_returns_nonzero(
        self, test_dir_with_modified_pdf: Path, ref_dir_with_images: Path, tmp_path: Path
    ):
        """When comparisons fail, main() returns exit code 1."""
        output = tmp_path / "output"
        exit_code = main([
            "compare",
            "-t", str(test_dir_with_modified_pdf),
            "-r", str(ref_dir_with_images),
            "-o", str(output),
            "--threshold", "99.99",
            "--format", "json",
        ])
        # Modified PDF against strict threshold should fail
        assert exit_code == 1
