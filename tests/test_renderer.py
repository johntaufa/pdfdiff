"""Tests for pdfdiff.renderer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pdfdiff.renderer import load_reference_image, render_pdf, save_image


class TestRenderPdf:
    """Tests for render_pdf()."""

    @pytest.mark.unit
    def test_render_returns_list_of_arrays(self, sample_pdf: Path):
        """Rendering a valid PDF returns a non-empty list of numpy arrays."""
        images = render_pdf(sample_pdf)
        assert len(images) == 1
        assert isinstance(images[0], np.ndarray)
        assert images[0].ndim == 3
        assert images[0].shape[2] == 3  # RGB

    @pytest.mark.unit
    def test_render_multipage(self, multipage_pdf: Path):
        """Multi-page PDF returns one array per page."""
        images = render_pdf(multipage_pdf)
        assert len(images) == 3

    @pytest.mark.unit
    def test_render_custom_dpi(self, sample_pdf: Path):
        """Higher DPI produces larger images."""
        images_low = render_pdf(sample_pdf, dpi=72)
        images_high = render_pdf(sample_pdf, dpi=300)
        # Higher DPI → more pixels
        assert images_high[0].shape[0] > images_low[0].shape[0]
        assert images_high[0].shape[1] > images_low[0].shape[1]

    @pytest.mark.unit
    def test_render_file_not_found(self, tmp_dir: Path):
        """FileNotFoundError for missing PDF."""
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            render_pdf(tmp_dir / "nope.pdf")

    @pytest.mark.unit
    def test_render_invalid_file(self, tmp_dir: Path):
        """RuntimeError for a non-PDF file."""
        bad = tmp_dir / "bad.pdf"
        bad.write_text("this is not a pdf")
        with pytest.raises(RuntimeError, match="Failed to open PDF"):
            render_pdf(bad)


class TestLoadReferenceImage:
    """Tests for load_reference_image()."""

    @pytest.mark.unit
    def test_load_png(self, tmp_dir: Path, white_image: np.ndarray):
        """Loading a saved PNG returns the same data."""
        path = save_image(white_image, tmp_dir / "ref.png")
        loaded = load_reference_image(path)
        assert loaded.shape == white_image.shape
        np.testing.assert_array_equal(loaded, white_image)

    @pytest.mark.unit
    def test_load_file_not_found(self, tmp_dir: Path):
        """FileNotFoundError for missing image."""
        with pytest.raises(FileNotFoundError, match="Reference image not found"):
            load_reference_image(tmp_dir / "missing.png")


class TestSaveImage:
    """Tests for save_image()."""

    @pytest.mark.unit
    def test_save_creates_file(self, tmp_dir: Path, white_image: np.ndarray):
        """save_image creates a file on disk."""
        path = save_image(white_image, tmp_dir / "out.png")
        assert path.exists()
        assert path.stat().st_size > 0

    @pytest.mark.unit
    def test_save_creates_parent_dirs(self, tmp_dir: Path, white_image: np.ndarray):
        """save_image creates parent directories automatically."""
        path = save_image(white_image, tmp_dir / "a" / "b" / "c.png")
        assert path.exists()
