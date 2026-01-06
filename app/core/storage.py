"""Storage utilities for annotations and output files.

This module handles file I/O for annotation JSON files and ensures
proper directory structure for outputs.
"""

import json
from pathlib import Path

from app.core.segment_model import AnnotationDoc


def get_output_path(pdf_path: str | Path, output_root: str = "out") -> Path:
    """Get the output directory path for a given PDF.
    
    Mirrors the structure of data/ in out/:
    - Input: data/1986/file.pdf
    - Output: out/1986/
    
    Args:
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        Path to the output directory
    """
    pdf_path = Path(pdf_path)
    
    # Extract year from path (assumes data/<year>/file.pdf structure)
    parts = pdf_path.parts
    if "data" in parts:
        data_idx = parts.index("data")
        if data_idx + 1 < len(parts):
            year = parts[data_idx + 1]
            return Path(output_root) / year
    
    # Fallback: use parent directory name
    return Path(output_root) / pdf_path.parent.name


def ensure_out_dir(pdf_path: str | Path, output_root: str = "out") -> Path:
    """Ensure output directory exists for a PDF.
    
    Args:
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        Path to the created output directory
    """
    out_dir = get_output_path(pdf_path, output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def get_annotation_path(pdf_path: str | Path, output_root: str = "out") -> Path:
    """Get the path for the annotation JSON file.
    
    Args:
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        Path to the annotation JSON file
    """
    pdf_path = Path(pdf_path)
    out_dir = get_output_path(pdf_path, output_root)
    return out_dir / f"{pdf_path.stem}.annotations.json"


def get_docx_path(pdf_path: str | Path, output_root: str = "out") -> Path:
    """Get the path for the output DOCX file.
    
    Args:
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        Path to the output DOCX file
    """
    pdf_path = Path(pdf_path)
    out_dir = get_output_path(pdf_path, output_root)
    return out_dir / f"{pdf_path.stem}.docx"


def get_markdown_path(pdf_path: str | Path, output_root: str = "out") -> Path:
    """Get the path for the output Markdown file.
    
    Args:
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        Path to the output Markdown file
    """
    pdf_path = Path(pdf_path)
    out_dir = get_output_path(pdf_path, output_root)
    return out_dir / f"{pdf_path.stem}.md"


def load_annotations(pdf_path: str | Path, output_root: str = "out") -> AnnotationDoc:
    """Load annotations for a PDF, or create empty if not found.
    
    Args:
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        AnnotationDoc instance
    """
    pdf_path = Path(pdf_path)
    annotation_path = get_annotation_path(pdf_path, output_root)
    
    if annotation_path.exists():
        with open(annotation_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return AnnotationDoc.from_dict(data)
    else:
        # Create new empty annotation doc
        return AnnotationDoc(source_pdf=str(pdf_path))


def save_annotations(
    annotation_doc: AnnotationDoc,
    pdf_path: str | Path,
    output_root: str = "out"
) -> Path:
    """Save annotations to JSON file.
    
    Args:
        annotation_doc: The annotation document to save
        pdf_path: Path to the source PDF
        output_root: Root output directory
        
    Returns:
        Path to the saved annotation file
    """
    pdf_path = Path(pdf_path)
    
    # Ensure output directory exists
    ensure_out_dir(pdf_path, output_root)
    
    # Get output path
    annotation_path = get_annotation_path(pdf_path, output_root)
    
    # Write JSON
    with open(annotation_path, "w", encoding="utf-8") as f:
        json.dump(annotation_doc.to_dict(), f, indent=2, ensure_ascii=False)
    
    return annotation_path


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

