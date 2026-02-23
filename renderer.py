"""PDF to image rendering using PyMuPDF (fitz).

Converts PDF pages to numpy arrays at a configurable DPI.
PyMuPDF handles InDesign's complex transparency, vectors, and
embedded fonts more reliably than poppler-based tools.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_DPI = 150


def render_pdf(pdf_path: Path, dpi: int = DEFAULT_DPI) -> List[np.ndarray]:
    """Convert every page of a PDF to an RGB numpy array.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for rendering. 150 is a good balance of speed and
             detail for InDesign exports.

    Returns:
        List of numpy arrays (H, W, 3) in RGB order, one per page.

    Raises:
        FileNotFoundError: If *pdf_path* does not exist.
        RuntimeError: If PyMuPDF cannot open or render the file.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    zoom = dpi / 72  # 72 is PDF's native DPI
    matrix = fitz.Matrix(zoom, zoom)

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF {pdf_path}: {exc}") from exc

    images: List[np.ndarray] = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            images.append(img.copy())  # copy so buffer can be freed
            logger.debug("Rendered page %d of %s (%dx%d)", page_num + 1, pdf_path.name, pix.width, pix.height)
    finally:
        doc.close()

    if not images:
        raise RuntimeError(f"PDF has no pages: {pdf_path}")

    logger.info("Rendered %d page(s) from %s at %d DPI", len(images), pdf_path.name, dpi)
    return images


def load_reference_image(image_path: Path) -> np.ndarray:
    """Load a reference PNG image as an RGB numpy array.

    Args:
        image_path: Path to the PNG file.

    Returns:
        Numpy array (H, W, 3) in RGB order.

    Raises:
        FileNotFoundError: If *image_path* does not exist.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Reference image not found: {image_path}")

    img = Image.open(image_path).convert("RGB")
    return np.array(img)


def save_image(image: np.ndarray, path: Path) -> Path:
    """Save a numpy RGB array as a PNG file.

    Args:
        image: Numpy array (H, W, 3) in RGB order.
        path: Destination file path.

    Returns:
        The path the image was saved to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(str(path))
    logger.debug("Saved image: %s", path)
    return path
