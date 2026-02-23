"""Shared pytest fixtures for pdfdiff tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def white_image() -> np.ndarray:
    """100x100 white RGB image."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 255


@pytest.fixture
def black_image() -> np.ndarray:
    """100x100 black RGB image."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


@pytest.fixture
def noisy_white_image(white_image: np.ndarray) -> np.ndarray:
    """White image with minor noise (simulates rendering jitter)."""
    rng = np.random.default_rng(42)
    noise = rng.integers(-3, 4, size=white_image.shape, dtype=np.int16)
    noisy = np.clip(white_image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


@pytest.fixture
def sample_pdf(tmp_dir: Path) -> Path:
    """Generate a simple single-page PDF using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf_path = tmp_dir / "sample.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, h - 100, "Hello World")
    c.setFont("Helvetica", 12)
    c.drawString(100, h - 140, "This is a test PDF for pdfdiff.")
    c.save()
    return pdf_path


@pytest.fixture
def sample_pdf_modified(tmp_dir: Path) -> Path:
    """Generate a slightly different PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf_path = tmp_dir / "sample.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, h - 100, "Hello World!")  # added exclamation
    c.setFont("Helvetica", 12)
    c.drawString(100, h - 140, "This is a MODIFIED test PDF.")
    c.save()
    return pdf_path


@pytest.fixture
def multipage_pdf(tmp_dir: Path) -> Path:
    """Generate a 3-page PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf_path = tmp_dir / "multipage.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    w, h = letter

    for i in range(1, 4):
        c.setFont("Helvetica-Bold", 24)
        c.drawString(100, h - 100, f"Page {i}")
        if i < 3:
            c.showPage()

    c.save()
    return pdf_path
