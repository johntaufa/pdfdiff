"""Image comparison using SSIM (Structural Similarity Index).

SSIM is perceptually aware: it catches real visual changes while
ignoring insignificant rendering noise like anti-aliasing or font
hinting differences that are common in InDesign PDF exports.

A pixel-level diff overlay is generated separately for visualisation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 99.0  # percent


@dataclass
class PageResult:
    """Result of comparing a single page."""

    page: int
    ssim_score: float
    passed: bool
    diff_overlay: Optional[np.ndarray] = None

    @property
    def similarity_pct(self) -> float:
        """SSIM as a 0-100 percentage."""
        return self.ssim_score * 100


@dataclass
class ComparisonResult:
    """Result of comparing an entire PDF against its reference."""

    test_name: str
    ref_name: str
    pages: list[PageResult]
    ref_page_count: int
    test_page_count: int
    status: str = "completed"  # completed | error | missing_reference
    error_message: Optional[str] = None

    @property
    def overall_ssim(self) -> float:
        """Average SSIM across all compared pages (0-100)."""
        if not self.pages:
            return 0.0
        return sum(p.similarity_pct for p in self.pages) / len(self.pages)

    @property
    def passed(self) -> bool:
        """True if every compared page passed AND page counts match."""
        return (
            all(p.passed for p in self.pages)
            and self.ref_page_count == self.test_page_count
            and self.status == "completed"
        )


def _ensure_same_size(
    img1: np.ndarray, img2: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Resize images to the same dimensions (using the larger of each axis)."""
    if img1.shape == img2.shape:
        return img1, img2

    h = max(img1.shape[0], img2.shape[0])
    w = max(img1.shape[1], img2.shape[1])
    img1_resized = cv2.resize(img1, (w, h), interpolation=cv2.INTER_AREA)
    img2_resized = cv2.resize(img2, (w, h), interpolation=cv2.INTER_AREA)
    return img1_resized, img2_resized


def compare_images(
    ref_img: np.ndarray,
    test_img: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
) -> PageResult:
    """Compare two images using SSIM and produce a diff overlay.

    Args:
        ref_img: Reference image (H, W, 3) RGB.
        test_img: Test image (H, W, 3) RGB.
        threshold: Pass/fail threshold as a percentage (0-100).

    Returns:
        A PageResult with SSIM score, pass/fail, and a diff overlay image.
    """
    ref, test = _ensure_same_size(ref_img, test_img)

    # Convert to grayscale for SSIM
    ref_gray = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY)
    test_gray = cv2.cvtColor(test, cv2.COLOR_RGB2GRAY)

    # SSIM returns (score, full_image_ssim_map)
    score, ssim_map = ssim(ref_gray, test_gray, full=True)

    passed = bool((score * 100) >= threshold)

    # Build diff overlay — highlight regions where SSIM is low
    diff_mask = ((1 - ssim_map) * 255).astype(np.uint8)
    _, thresh_mask = cv2.threshold(diff_mask, 15, 255, cv2.THRESH_BINARY)

    # Create red overlay on the reference image
    overlay = ref.copy()
    overlay[thresh_mask > 0] = [255, 0, 0]
    blended = cv2.addWeighted(ref, 0.6, overlay, 0.4, 0)

    return PageResult(
        page=0,  # caller sets the actual page number
        ssim_score=float(score),
        passed=passed,
        diff_overlay=blended,
    )


def compare_page_lists(
    ref_images: list[np.ndarray],
    test_images: list[np.ndarray],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[PageResult]:
    """Compare two ordered lists of page images.

    Only compares up to min(len(ref), len(test)) pages.

    Args:
        ref_images: Reference page images.
        test_images: Test page images.
        threshold: Pass/fail threshold (0-100).

    Returns:
        List of PageResult, one per compared page.
    """
    results: list[PageResult] = []
    pages_to_compare = min(len(ref_images), len(test_images))

    for i in range(pages_to_compare):
        result = compare_images(ref_images[i], test_images[i], threshold)
        result.page = i + 1
        logger.info(
            "Page %d: SSIM %.2f%% — %s",
            result.page,
            result.similarity_pct,
            "PASS" if result.passed else "FAIL",
        )
        results.append(result)

    return results
