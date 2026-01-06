"""OCR functionality using Tesseract.

This module provides a wrapper around pytesseract for OCR operations
on cropped PDF regions.
"""

from PIL import Image
import pytesseract
from typing import Optional


class TesseractNotFoundError(Exception):
    """Raised when Tesseract is not installed or not found in PATH."""
    pass


def check_tesseract_available() -> bool:
    """Check if Tesseract is available.
    
    Returns:
        True if Tesseract is available, False otherwise
    """
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image_crop(
    image: Image.Image,
    psm: int = 6,
    lang: str = "eng",
    config_extra: str = ""
) -> str:
    """Perform OCR on an image crop using Tesseract.
    
    Args:
        image: PIL Image to OCR
        psm: Tesseract page segmentation mode
             4 = Single column of text
             6 = Uniform block of text (default)
             11 = Sparse text, find as much text as possible
        lang: Language code (default: eng)
        config_extra: Additional Tesseract config options
        
    Returns:
        Extracted text
        
    Raises:
        TesseractNotFoundError: If Tesseract is not installed
    """
    if not check_tesseract_available():
        raise TesseractNotFoundError(
            "Tesseract is not installed or not found in PATH. "
            "Please install Tesseract OCR:\n"
            "  Linux: sudo apt-get install tesseract-ocr\n"
            "  macOS: brew install tesseract\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    
    # Build config string
    config = f"--psm {psm}"
    if config_extra:
        config += f" {config_extra}"
    
    try:
        # Perform OCR
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        return text
    except Exception as e:
        # Return empty string on error rather than failing
        print(f"OCR error: {e}")
        return ""


def ocr_image_crop_with_confidence(
    image: Image.Image,
    psm: int = 6,
    lang: str = "eng"
) -> tuple[str, float]:
    """Perform OCR and get confidence score.
    
    Args:
        image: PIL Image to OCR
        psm: Tesseract page segmentation mode
        lang: Language code
        
    Returns:
        Tuple of (text, confidence) where confidence is 0-100
        
    Raises:
        TesseractNotFoundError: If Tesseract is not installed
    """
    if not check_tesseract_available():
        raise TesseractNotFoundError(
            "Tesseract is not installed or not found in PATH."
        )
    
    config = f"--psm {psm}"
    
    try:
        # Get detailed data
        data = pytesseract.image_to_data(
            image, lang=lang, config=config, output_type=pytesseract.Output.DICT
        )
        
        # Extract text
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        
        # Calculate average confidence
        confidences = [
            float(conf) for conf in data['conf']
            if conf != -1  # -1 means no confidence data
        ]
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return text, avg_confidence
    except Exception as e:
        print(f"OCR error: {e}")
        return "", 0.0


def get_available_languages() -> list[str]:
    """Get list of available Tesseract languages.
    
    Returns:
        List of language codes
    """
    if not check_tesseract_available():
        return []
    
    try:
        langs = pytesseract.get_languages()
        return langs
    except Exception:
        return ["eng"]  # Default fallback

