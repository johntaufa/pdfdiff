"""Tests for pdfdiff.comparator."""

from __future__ import annotations

import numpy as np
import pytest

from pdfdiff.comparator import (
    ComparisonResult,
    PageResult,
    compare_images,
    compare_page_lists,
    _ensure_same_size,
)


class TestEnsureSameSize:
    """Tests for _ensure_same_size()."""

    @pytest.mark.unit
    def test_same_size_no_resize(self, white_image: np.ndarray):
        """Identical shapes pass through unchanged."""
        a, b = _ensure_same_size(white_image, white_image.copy())
        assert a.shape == b.shape == white_image.shape

    @pytest.mark.unit
    def test_different_sizes_resized(self):
        """Images with different sizes are resized to the max of each dimension."""
        small = np.zeros((50, 80, 3), dtype=np.uint8)
        large = np.zeros((100, 60, 3), dtype=np.uint8)
        a, b = _ensure_same_size(small, large)
        assert a.shape[:2] == (100, 80)
        assert b.shape[:2] == (100, 80)


class TestCompareImages:
    """Tests for compare_images()."""

    @pytest.mark.unit
    def test_identical_images_score_100(self, white_image: np.ndarray):
        """Two identical images should score ~100% SSIM."""
        result = compare_images(white_image, white_image.copy())
        assert result.ssim_score >= 0.99
        assert result.passed is True

    @pytest.mark.unit
    def test_completely_different_images(
        self, white_image: np.ndarray, black_image: np.ndarray
    ):
        """White vs black should score very low."""
        result = compare_images(white_image, black_image, threshold=50.0)
        assert result.similarity_pct < 50.0
        assert result.passed is False

    @pytest.mark.unit
    def test_minor_noise_high_score(
        self, white_image: np.ndarray, noisy_white_image: np.ndarray
    ):
        """Minor noise should still produce a high SSIM score."""
        result = compare_images(white_image, noisy_white_image, threshold=90.0)
        assert result.similarity_pct > 90.0
        assert result.passed is True

    @pytest.mark.unit
    def test_diff_overlay_generated(
        self, white_image: np.ndarray, black_image: np.ndarray
    ):
        """Diff overlay should be a valid RGB image."""
        result = compare_images(white_image, black_image)
        assert result.diff_overlay is not None
        assert result.diff_overlay.ndim == 3
        assert result.diff_overlay.shape[2] == 3

    @pytest.mark.unit
    def test_threshold_boundary(self, white_image: np.ndarray):
        """Score exactly at threshold should pass."""
        result = compare_images(white_image, white_image.copy(), threshold=100.0)
        # SSIM of identical images is 1.0 → 100%
        assert result.passed is True

    @pytest.mark.unit
    def test_different_sized_images(self):
        """Images of different sizes should still compare successfully."""
        small = np.ones((50, 50, 3), dtype=np.uint8) * 128
        large = np.ones((100, 100, 3), dtype=np.uint8) * 128
        result = compare_images(small, large, threshold=80.0)
        # Same color, just resized — should be very similar
        assert result.similarity_pct > 80.0


class TestComparePageLists:
    """Tests for compare_page_lists()."""

    @pytest.mark.unit
    def test_equal_length_lists(self, white_image: np.ndarray):
        """Comparing two equal-length lists works page by page."""
        refs = [white_image, white_image]
        tests = [white_image.copy(), white_image.copy()]
        results = compare_page_lists(refs, tests)
        assert len(results) == 2
        assert results[0].page == 1
        assert results[1].page == 2
        assert all(r.passed for r in results)

    @pytest.mark.unit
    def test_unequal_length_uses_min(
        self, white_image: np.ndarray, black_image: np.ndarray
    ):
        """Only min(len(ref), len(test)) pages are compared."""
        refs = [white_image, white_image, white_image]
        tests = [white_image.copy()]
        results = compare_page_lists(refs, tests)
        assert len(results) == 1

    @pytest.mark.unit
    def test_empty_lists(self):
        """Empty lists produce no results."""
        assert compare_page_lists([], []) == []


class TestPageResult:
    """Tests for PageResult dataclass."""

    @pytest.mark.unit
    def test_similarity_pct(self):
        """similarity_pct converts 0-1 SSIM to 0-100 percentage."""
        pr = PageResult(page=1, ssim_score=0.95, passed=True)
        assert pr.similarity_pct == 95.0


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    @pytest.mark.unit
    def test_overall_ssim(self):
        """overall_ssim is the average of page percentages."""
        pages = [
            PageResult(page=1, ssim_score=0.90, passed=True),
            PageResult(page=2, ssim_score=0.80, passed=False),
        ]
        cr = ComparisonResult(
            test_name="test.pdf",
            ref_name="ref",
            pages=pages,
            ref_page_count=2,
            test_page_count=2,
        )
        assert cr.overall_ssim == 85.0

    @pytest.mark.unit
    def test_passed_all_pass_same_count(self):
        """passed is True only if all pages pass AND counts match."""
        pages = [PageResult(page=1, ssim_score=0.99, passed=True)]
        cr = ComparisonResult(
            test_name="t.pdf", ref_name="r", pages=pages,
            ref_page_count=1, test_page_count=1,
        )
        assert cr.passed is True

    @pytest.mark.unit
    def test_passed_false_on_page_count_mismatch(self):
        """Different page counts → not passed, even if pages pass."""
        pages = [PageResult(page=1, ssim_score=0.99, passed=True)]
        cr = ComparisonResult(
            test_name="t.pdf", ref_name="r", pages=pages,
            ref_page_count=1, test_page_count=2,
        )
        assert cr.passed is False

    @pytest.mark.unit
    def test_passed_false_on_error_status(self):
        """Error status → not passed."""
        cr = ComparisonResult(
            test_name="t.pdf", ref_name="r", pages=[],
            ref_page_count=0, test_page_count=0,
            status="error",
        )
        assert cr.passed is False

    @pytest.mark.unit
    def test_overall_ssim_empty_pages(self):
        """No pages → overall_ssim is 0."""
        cr = ComparisonResult(
            test_name="t.pdf", ref_name="r", pages=[],
            ref_page_count=0, test_page_count=0,
        )
        assert cr.overall_ssim == 0.0
