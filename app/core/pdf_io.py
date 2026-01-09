"""PDF I/O operations with coordinate mapping.

This module handles PDF rendering, text extraction, and critical
coordinate system conversions between pixel space (UI) and PDF space.
"""

from pathlib import Path
from typing import Tuple

import fitz  # PyMuPDF
from PIL import Image

from app.core.segment_model import BBox


def list_pdfs(data_root: str = "data") -> dict[str, list[Path]]:
    """Scan data directory and return PDFs organized by year.
    
    Args:
        data_root: Root data directory
        
    Returns:
        Dictionary mapping year (string) to list of PDF paths
    """
    data_path = Path(data_root)
    
    if not data_path.exists():
        return {}
    
    pdfs_by_year: dict[str, list[Path]] = {}
    
    # Iterate through year directories
    for year_dir in sorted(data_path.iterdir()):
        if year_dir.is_dir():
            year = year_dir.name
            pdfs = sorted(year_dir.glob("*.pdf"))
            if pdfs:
                pdfs_by_year[year] = pdfs
    
    return pdfs_by_year


def get_page_count(pdf_path: str | Path) -> int:
    """Get the number of pages in a PDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Number of pages
    """
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def get_page_dimensions(pdf_path: str | Path, page_index: int) -> Tuple[float, float]:
    """Get PDF page dimensions in points.
    
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        
    Returns:
        Tuple of (width, height) in points
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    rect = page.rect
    doc.close()
    return (rect.width, rect.height)


def render_page(pdf_path: str | Path, page_index: int, dpi: int = 200) -> Image.Image:
    """Render a PDF page to a PIL Image.
    
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        dpi: Resolution for rendering (default: 200)
        
    Returns:
        PIL Image of the rendered page
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # Calculate scale factor from DPI
    # PDF default is 72 DPI
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    
    # Render page to pixmap
    pix = page.get_pixmap(matrix=matrix)
    
    # Convert to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    doc.close()
    return img


def bbox_pixels_to_pdf(
    bbox_pixels: BBox,
    page_width_points: float,
    page_height_points: float,
    dpi: int
) -> fitz.Rect:
    """Convert a bounding box from pixel space to PDF space.
    
    Pixel space: origin top-left, units in pixels at given DPI
    PDF space: origin bottom-left, units in points (1/72 inch)
    
    Args:
        bbox_pixels: Bounding box in pixel coordinates
        page_width_points: PDF page width in points
        page_height_points: PDF page height in points
        dpi: DPI used for rendering
        
    Returns:
        fitz.Rect in PDF coordinate space
    """
    scale = dpi / 72.0
    
    # Calculate page height in pixels
    page_height_pixels = page_height_points * scale
    
    # Convert pixel coordinates to PDF coordinates
    # Note: Y-axis is flipped (top-left vs bottom-left origin)
    x0 = bbox_pixels.x / scale
    y0 = (page_height_pixels - bbox_pixels.y - bbox_pixels.h) / scale
    x1 = (bbox_pixels.x + bbox_pixels.w) / scale
    y1 = (page_height_pixels - bbox_pixels.y) / scale
    
    return fitz.Rect(x0, y0, x1, y1)


def extract_text_in_bbox(
    pdf_path: str | Path,
    page_index: int,
    bbox_pixels: BBox,
    dpi: int = 200
) -> str:
    """Extract text from PDF text layer within a bounding box.
    
    Uses block-based extraction with proper sorting for multi-column layouts.
    
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        bbox_pixels: Bounding box in pixel coordinates
        dpi: DPI used for coordinate conversion
        
    Returns:
        Extracted text (may be empty or garbled if no text layer)
    """
    from webapp.logger import logger
    
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # Get page dimensions
    page_width = page.rect.width
    page_height = page.rect.height
    
    # Convert pixel bbox to PDF rect
    pdf_rect = bbox_pixels_to_pdf(bbox_pixels, page_width, page_height, dpi)
    
    logger.debug(f"Extracting text from bbox: pixels={bbox_pixels.to_dict()}, pdf_rect={pdf_rect}, dpi={dpi}")
    
    # Extract text blocks for better ordering
    blocks = page.get_text("blocks", clip=pdf_rect)
    
    if not blocks:
        logger.warning(f"No text blocks found in region on page {page_index}")
        doc.close()
        return ""
    
    # Format and sort blocks by position (top-to-bottom, left-to-right)
    text_blocks = []
    for block in blocks:
        if len(block) >= 5 and block[6] == 0:  # Text block (not image)
            x0, y0, x1, y1, text, block_no, block_type = block[:7]
            text_blocks.append({
                "text": text.strip(),
                "y": y0,  # Top position
                "x": x0,  # Left position
            })
    
    # Sort by Y position first (top to bottom), then X position (left to right)
    # Use tolerance for Y to handle same-line text
    text_blocks.sort(key=lambda b: (round(b["y"] / 5) * 5, b["x"]))
    
    # Combine text
    result = "\n".join(block["text"] for block in text_blocks if block["text"])
    
    logger.debug(f"Extracted {len(result)} characters from {len(text_blocks)} blocks")
    
    doc.close()
    return result


def extract_text_blocks_in_bbox(
    pdf_path: str | Path,
    page_index: int,
    bbox_pixels: BBox,
    dpi: int = 200
) -> list[dict]:
    """Extract text blocks from PDF with positioning info.
    
    Properly sorts blocks for multi-column layouts.
    
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        bbox_pixels: Bounding box in pixel coordinates
        dpi: DPI used for coordinate conversion
        
    Returns:
        List of text blocks with positioning information, sorted by reading order
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # Get page dimensions
    page_width = page.rect.width
    page_height = page.rect.height
    
    # Convert pixel bbox to PDF rect
    pdf_rect = bbox_pixels_to_pdf(bbox_pixels, page_width, page_height, dpi)
    
    # Extract text blocks
    blocks = page.get_text("blocks", clip=pdf_rect)
    
    # Format blocks
    formatted_blocks = []
    for block in blocks:
        if len(block) >= 5:  # Ensure it's a text block
            x0, y0, x1, y1, text, block_no, block_type = block[:7]
            if block_type == 0:  # Text block only (not image)
                formatted_blocks.append({
                    "bbox": (x0, y0, x1, y1),
                    "text": text.strip(),
                    "block_no": block_no,
                    "block_type": block_type,
                })
    
    doc.close()
    
    # Sort blocks by y position (top to bottom), then x (left to right)
    # Use tolerance for Y to handle text on same line
    formatted_blocks.sort(key=lambda b: (round(b["bbox"][1] / 5) * 5, b["bbox"][0]))
    
    return formatted_blocks


def crop_page_region(
    pdf_path: str | Path,
    page_index: int,
    bbox_pixels: BBox,
    dpi: int = 200
) -> Image.Image:
    """Crop a region from a rendered PDF page.
    
    This is used for OCR when the PDF text layer is inadequate.
    
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        bbox_pixels: Bounding box in pixel coordinates
        dpi: DPI for rendering
        
    Returns:
        PIL Image of the cropped region
    """
    # Render full page
    page_img = render_page(pdf_path, page_index, dpi)
    
    # Crop the region
    # PIL crop expects (left, top, right, bottom)
    crop_box = (
        int(bbox_pixels.x),
        int(bbox_pixels.y),
        int(bbox_pixels.x + bbox_pixels.w),
        int(bbox_pixels.y + bbox_pixels.h),
    )
    
    cropped = page_img.crop(crop_box)
    return cropped

