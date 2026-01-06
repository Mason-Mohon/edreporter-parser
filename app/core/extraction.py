"""Text extraction orchestrator.

This module coordinates text extraction from PDFs, trying PDF text layer
first and falling back to OCR when needed, based on quality heuristics.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.segment_model import AnnotationDoc, Region
from app.core.pdf_io import extract_text_in_bbox, crop_page_region
from app.core.ocr import ocr_image_crop, TesseractNotFoundError
from app.core.heuristics import should_fallback_to_ocr, cleanup_text, calculate_quality_score


@dataclass
class RegionExtraction:
    """Metadata about how a region was extracted.
    
    Attributes:
        region_id: ID of the region
        page_index: Page number
        method: Extraction method used (pdf_text or ocr)
        quality_score: Quality score (0-1)
        text_length: Length of extracted text
        ocr_confidence: OCR confidence if applicable (0-100)
    """
    region_id: str
    page_index: int
    method: Literal["pdf_text", "ocr"]
    quality_score: float
    text_length: int
    ocr_confidence: float = 0.0


@dataclass
class ExtractedText:
    """Extracted text for an article with metadata.
    
    Attributes:
        article_id: ID of the article
        text: Complete extracted text
        regions_metadata: Metadata for each region
    """
    article_id: str
    text: str
    regions_metadata: list[RegionExtraction]


def extract_region_text(
    pdf_path: str | Path,
    page_index: int,
    region: Region,
    dpi: int,
    prefer_pdf_text: bool,
    ocr_lang: str,
    tesseract_psm: int
) -> tuple[str, RegionExtraction]:
    """Extract text from a single region.
    
    Args:
        pdf_path: Path to PDF file
        page_index: Page number
        region: Region to extract
        dpi: DPI for rendering
        prefer_pdf_text: Whether to try PDF text first
        ocr_lang: OCR language code
        tesseract_psm: Tesseract PSM mode
        
    Returns:
        Tuple of (extracted_text, metadata)
    """
    text = ""
    method: Literal["pdf_text", "ocr"] = "pdf_text"
    ocr_confidence = 0.0
    
    # Try PDF text layer first if preferred
    if prefer_pdf_text:
        try:
            text = extract_text_in_bbox(pdf_path, page_index, region.bbox, dpi)
            
            # Check quality
            if should_fallback_to_ocr(text):
                # PDF text is poor quality, try OCR
                method = "ocr"
                text = _ocr_region(pdf_path, page_index, region, dpi, ocr_lang, tesseract_psm)
                ocr_confidence = 85.0  # Placeholder, could get real confidence
            else:
                method = "pdf_text"
        except Exception as e:
            print(f"PDF text extraction failed for region {region.region_id}: {e}")
            # Fall back to OCR
            method = "ocr"
            text = _ocr_region(pdf_path, page_index, region, dpi, ocr_lang, tesseract_psm)
    else:
        # OCR directly
        method = "ocr"
        text = _ocr_region(pdf_path, page_index, region, dpi, ocr_lang, tesseract_psm)
    
    # Calculate quality score
    quality_score = calculate_quality_score(text)
    
    # Create metadata
    metadata = RegionExtraction(
        region_id=region.region_id,
        page_index=page_index,
        method=method,
        quality_score=quality_score,
        text_length=len(text),
        ocr_confidence=ocr_confidence,
    )
    
    return text, metadata


def _ocr_region(
    pdf_path: str | Path,
    page_index: int,
    region: Region,
    dpi: int,
    ocr_lang: str,
    tesseract_psm: int
) -> str:
    """Perform OCR on a region.
    
    Args:
        pdf_path: Path to PDF file
        page_index: Page number
        region: Region to OCR
        dpi: DPI for rendering
        ocr_lang: OCR language code
        tesseract_psm: Tesseract PSM mode
        
    Returns:
        Extracted text
    """
    try:
        # Crop the region
        crop_img = crop_page_region(pdf_path, page_index, region.bbox, dpi)
        
        # Perform OCR
        text = ocr_image_crop(crop_img, psm=tesseract_psm, lang=ocr_lang)
        
        return text
    except TesseractNotFoundError:
        raise  # Re-raise this so caller knows Tesseract is missing
    except Exception as e:
        print(f"OCR failed for region {region.region_id}: {e}")
        return ""


def build_article_text(
    annotation_doc: AnnotationDoc,
    pdf_path: str | Path,
    apply_cleanup: bool = True
) -> dict[str, ExtractedText]:
    """Extract text for all articles in the annotation document.
    
    Args:
        annotation_doc: Annotation document with regions and articles
        pdf_path: Path to PDF file
        apply_cleanup: Whether to apply text cleanup heuristics
        
    Returns:
        Dictionary mapping article_id to ExtractedText
    """
    results: dict[str, ExtractedText] = {}
    
    # Get settings
    settings = annotation_doc.settings
    dpi = settings.dpi
    prefer_pdf_text = settings.prefer_pdf_text_layer
    ocr_lang = settings.ocr_lang
    tesseract_psm = 6  # Default PSM mode
    
    # Process each article
    for article_id in annotation_doc.articles.keys():
        # Get regions for this article, sorted by order
        regions = annotation_doc.get_regions_for_article(article_id)
        
        if not regions:
            # No regions for this article
            results[article_id] = ExtractedText(
                article_id=article_id,
                text="",
                regions_metadata=[]
            )
            continue
        
        # Extract text from each region
        article_text_parts = []
        regions_metadata = []
        
        for page_index, region in regions:
            text, metadata = extract_region_text(
                pdf_path=pdf_path,
                page_index=page_index,
                region=region,
                dpi=dpi,
                prefer_pdf_text=prefer_pdf_text,
                ocr_lang=ocr_lang,
                tesseract_psm=tesseract_psm
            )
            
            article_text_parts.append(text)
            regions_metadata.append(metadata)
        
        # Concatenate text from all regions
        full_text = "\n\n".join(article_text_parts)
        
        # Apply cleanup if requested
        if apply_cleanup:
            full_text = cleanup_text(full_text)
        
        # Store result
        results[article_id] = ExtractedText(
            article_id=article_id,
            text=full_text,
            regions_metadata=regions_metadata
        )
    
    return results


def re_extract_region(
    pdf_path: str | Path,
    page_index: int,
    region: Region,
    dpi: int,
    force_ocr: bool = False,
    ocr_lang: str = "eng",
    tesseract_psm: int = 6
) -> tuple[str, RegionExtraction]:
    """Re-extract a single region (useful for manual correction).
    
    Args:
        pdf_path: Path to PDF file
        page_index: Page number
        region: Region to extract
        dpi: DPI for rendering
        force_ocr: Force OCR even if PDF text is available
        ocr_lang: OCR language code
        tesseract_psm: Tesseract PSM mode
        
    Returns:
        Tuple of (extracted_text, metadata)
    """
    return extract_region_text(
        pdf_path=pdf_path,
        page_index=page_index,
        region=region,
        dpi=dpi,
        prefer_pdf_text=not force_ocr,
        ocr_lang=ocr_lang,
        tesseract_psm=tesseract_psm
    )

