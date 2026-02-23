"""Tests for pdfdiff.reporter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdfdiff.comparator import ComparisonResult, PageResult
from pdfdiff.reporter import write_html, write_json, write_text


@pytest.fixture
def sample_results() -> list[ComparisonResult]:
    """Two sample ComparisonResults: one pass, one fail."""
    return [
        ComparisonResult(
            test_name="good.pdf",
            ref_name="good_page_*.png",
            pages=[PageResult(page=1, ssim_score=0.995, passed=True)],
            ref_page_count=1,
            test_page_count=1,
        ),
        ComparisonResult(
            test_name="bad.pdf",
            ref_name="bad_page_*.png",
            pages=[
                PageResult(page=1, ssim_score=0.85, passed=False),
                PageResult(page=2, ssim_score=0.92, passed=False),
            ],
            ref_page_count=2,
            test_page_count=2,
        ),
    ]


@pytest.fixture
def error_result() -> ComparisonResult:
    return ComparisonResult(
        test_name="broken.pdf",
        ref_name="",
        pages=[],
        ref_page_count=0,
        test_page_count=0,
        status="error",
        error_message="Failed to render",
    )


@pytest.fixture
def missing_ref_result() -> ComparisonResult:
    return ComparisonResult(
        test_name="orphan.pdf",
        ref_name="",
        pages=[],
        ref_page_count=0,
        test_page_count=0,
        status="missing_reference",
        error_message="No reference images found",
    )


class TestWriteJson:
    """Tests for write_json()."""

    @pytest.mark.unit
    def test_creates_file(self, tmp_path: Path, sample_results):
        path = write_json(sample_results, tmp_path)
        assert path.exists()
        assert path.name == "comparison_results.json"

    @pytest.mark.unit
    def test_valid_json(self, tmp_path: Path, sample_results):
        path = write_json(sample_results, tmp_path)
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.unit
    def test_json_structure(self, tmp_path: Path, sample_results):
        path = write_json(sample_results, tmp_path)
        data = json.loads(path.read_text())
        first = data[0]
        assert first["test_name"] == "good.pdf"
        assert first["passed"] is True
        assert first["overall_ssim"] == pytest.approx(99.5, abs=0.1)
        assert len(first["pages"]) == 1

    @pytest.mark.unit
    def test_json_error_result(self, tmp_path: Path, error_result):
        path = write_json([error_result], tmp_path)
        data = json.loads(path.read_text())
        assert data[0]["status"] == "error"
        assert data[0]["error_message"] == "Failed to render"

    @pytest.mark.unit
    def test_creates_output_dir(self, tmp_path: Path, sample_results):
        nested = tmp_path / "a" / "b"
        path = write_json(sample_results, nested)
        assert path.exists()


class TestWriteText:
    """Tests for write_text()."""

    @pytest.mark.unit
    def test_creates_file(self, tmp_path: Path, sample_results):
        path = write_text(sample_results, tmp_path)
        assert path.exists()
        assert path.name == "comparison_results.txt"

    @pytest.mark.unit
    def test_contains_pass_fail(self, tmp_path: Path, sample_results):
        path = write_text(sample_results, tmp_path)
        text = path.read_text()
        assert "[PASS]" in text
        assert "[FAIL]" in text
        assert "1/2 passed" in text

    @pytest.mark.unit
    def test_error_result_text(self, tmp_path: Path, error_result):
        path = write_text([error_result], tmp_path)
        text = path.read_text()
        assert "Error: Failed to render" in text

    @pytest.mark.unit
    def test_missing_ref_text(self, tmp_path: Path, missing_ref_result):
        path = write_text([missing_ref_result], tmp_path)
        text = path.read_text()
        assert "No reference found" in text

    @pytest.mark.unit
    def test_page_count_mismatch_noted(self, tmp_path: Path):
        result = ComparisonResult(
            test_name="mismatch.pdf",
            ref_name="ref",
            pages=[PageResult(page=1, ssim_score=0.99, passed=True)],
            ref_page_count=2,
            test_page_count=3,
        )
        path = write_text([result], tmp_path)
        text = path.read_text()
        assert "Page count mismatch" in text


class TestWriteHtml:
    """Tests for write_html()."""

    @pytest.mark.unit
    def test_creates_file(self, tmp_path: Path, sample_results):
        path = write_html(sample_results, tmp_path)
        assert path.exists()
        assert path.name == "comparison_results.html"

    @pytest.mark.unit
    def test_html_contains_results(self, tmp_path: Path, sample_results):
        path = write_html(sample_results, tmp_path)
        html = path.read_text()
        assert "good.pdf" in html
        assert "bad.pdf" in html
        assert "1/2" in html

    @pytest.mark.unit
    def test_html_with_diff_images(self, tmp_path: Path, sample_results):
        # Create a fake diff image file
        fake_diff = tmp_path / "bad_page_1_diff.png"
        fake_diff.write_bytes(b"fake")
        diff_images = {"bad.pdf": [fake_diff]}
        path = write_html(sample_results, tmp_path, diff_images)
        html = path.read_text()
        assert "bad_page_1_diff.png" in html

    @pytest.mark.unit
    def test_html_error_styling(self, tmp_path: Path, error_result):
        path = write_html([error_result], tmp_path)
        html = path.read_text()
        assert 'class="result error"' in html
