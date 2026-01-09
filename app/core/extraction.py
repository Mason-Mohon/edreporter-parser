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
    from webapp.logger import logger
    
    text = ""
    method: Literal["pdf_text", "ocr"] = "pdf_text"
    ocr_confidence = 0.0
    
    logger.info(f"Extracting text from region {region.region_id[:8]} on page {page_index}")
    logger.debug(f"  Region bbox: {region.bbox.to_dict()}, DPI: {dpi}")
    
    # Try PDF text layer first if preferred
    if prefer_pdf_text:
        try:
            text = extract_text_in_bbox(pdf_path, page_index, region.bbox, dpi)
            
            logger.debug(f"  PDF text extracted: {len(text)} chars")
            
            # Check quality
            if should_fallback_to_ocr(text):
                logger.info(f"  PDF text quality poor, falling back to OCR")
                # PDF text is poor quality, try OCR
                method = "ocr"
                text = _ocr_region(pdf_path, page_index, region, dpi, ocr_lang, tesseract_psm)
                ocr_confidence = 85.0  # Placeholder, could get real confidence
                logger.debug(f"  OCR text: {len(text)} chars")
            else:
                method = "pdf_text"
                logger.debug(f"  Using PDF text (quality OK)")
        except Exception as e:
            logger.error(f"  PDF text extraction failed: {e}")
            # Fall back to OCR
            method = "ocr"
            text = _ocr_region(pdf_path, page_index, region, dpi, ocr_lang, tesseract_psm)
    else:
        # OCR directly
        logger.info(f"  Using OCR directly (prefer_pdf_text=False)")
        method = "ocr"
        text = _ocr_region(pdf_path, page_index, region, dpi, ocr_lang, tesseract_psm)
    
    # Calculate quality score
    quality_score = calculate_quality_score(text)
    
    logger.info(f"  Extraction complete: method={method}, quality={quality_score:.2f}, length={len(text)}")
    
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
    from webapp.logger import logger
    
    results: dict[str, ExtractedText] = {}
    
    # Get settings
    settings = annotation_doc.settings
    dpi = settings.dpi
    prefer_pdf_text = settings.prefer_pdf_text_layer
    ocr_lang = settings.ocr_lang
    tesseract_psm = 6  # Default PSM mode
    
    logger.info(f"Building article text for {len(annotation_doc.articles)} articles")
    logger.info(f"Settings: DPI={dpi}, prefer_pdf_text={prefer_pdf_text}, ocr_lang={ocr_lang}")
    
    # Process each article
    for article_id in annotation_doc.articles.keys():
        article = annotation_doc.articles[article_id]
        logger.info(f"Processing article {article_id}: {article.title or '(no title)'}")
        
        # Get regions for this article, sorted by order
        regions = annotation_doc.get_regions_for_article(article_id)
        
        if not regions:
            logger.warning(f"  No regions found for article {article_id}")
            # No regions for this article
            results[article_id] = ExtractedText(
                article_id=article_id,
                text="",
                regions_metadata=[]
            )
            continue
        
        logger.info(f"  Processing {len(regions)} regions")
        
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
            logger.debug(f"  Applying text cleanup")
            full_text = cleanup_text(full_text)
        
        logger.info(f"  Article {article_id} complete: {len(full_text)} characters total")
        
        # Store result
        results[article_id] = ExtractedText(
            article_id=article_id,
            text=full_text,
            regions_metadata=regions_metadata
        )
    
    logger.info(f"Text extraction complete for all {len(results)} articles")
    
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

