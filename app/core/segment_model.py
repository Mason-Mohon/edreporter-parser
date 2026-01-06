"""Data models for PDF annotation and segmentation.

This module defines the core data structures for storing annotation data,
including regions, articles, and the complete annotation document.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Bounding box in pixel space (origin: top-left).
    
    Attributes:
        x: Left coordinate in pixels
        y: Top coordinate in pixels
        w: Width in pixels
        h: Height in pixels
    """
    x: float
    y: float
    w: float
    h: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


class Region(BaseModel):
    """A segmented region on a PDF page.
    
    Attributes:
        region_id: Unique identifier for this region
        article_id: ID of the article this region belongs to
        order: Reading order within the article (1-indexed)
        bbox: Bounding box coordinates in pixel space
        type: Type of content (body, header, footer, image-caption)
        notes: Optional notes about this region
    """
    region_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    article_id: str
    order: int
    bbox: BBox
    type: Literal["body", "header", "footer", "image-caption"] = "body"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "region_id": self.region_id,
            "article_id": self.article_id,
            "order": self.order,
            "bbox": self.bbox.to_dict(),
            "type": self.type,
            "notes": self.notes,
        }


class Article(BaseModel):
    """Article metadata.
    
    Attributes:
        title: Article title (required for export)
        subtitle: Optional subtitle
        author: Optional author name
        tags: Optional tags/keywords
        color: Display color for UI (hex format)
        reading_hint: Reading order hint (top-to-bottom, left-to-right, etc.)
    """
    title: str = ""
    subtitle: str = ""
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    color: str = "#3498db"  # Default blue
    reading_hint: str = "top-to-bottom"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "tags": self.tags,
            "color": self.color,
            "reading_hint": self.reading_hint,
        }


class PageAnnotations(BaseModel):
    """Annotations for a single page.
    
    Attributes:
        regions: List of regions on this page
    """
    regions: list[Region] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "regions": [r.to_dict() for r in self.regions]
        }


class Settings(BaseModel):
    """Global settings for the annotation document.
    
    Attributes:
        dpi: DPI used for rendering pages
        ocr_lang: Tesseract language code
        prefer_pdf_text_layer: Whether to prefer PDF text over OCR
    """
    dpi: int = 200
    ocr_lang: str = "eng"
    prefer_pdf_text_layer: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dpi": self.dpi,
            "ocr_lang": self.ocr_lang,
            "prefer_pdf_text_layer": self.prefer_pdf_text_layer,
        }


class AnnotationDoc(BaseModel):
    """Complete annotation document for a PDF.
    
    Attributes:
        schema_version: Version of the annotation schema
        source_pdf: Path to the source PDF file
        created_at: ISO-8601 timestamp of creation
        updated_at: ISO-8601 timestamp of last update
        pages: Dictionary mapping page indices (as strings) to annotations
        articles: Dictionary mapping article IDs to article metadata
        settings: Global settings
    """
    schema_version: str = "1.0"
    source_pdf: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    pages: dict[str, PageAnnotations] = Field(default_factory=dict)
    articles: dict[str, Article] = Field(default_factory=dict)
    settings: Settings = Field(default_factory=Settings)

    def add_article(self, article_id: str | None = None) -> str:
        """Add a new article.
        
        Args:
            article_id: Optional article ID. If None, auto-generate (A1, A2, ...).
            
        Returns:
            The article ID that was created.
        """
        if article_id is None:
            # Auto-generate next article ID
            existing_nums = []
            for aid in self.articles.keys():
                if aid.startswith("A") and aid[1:].isdigit():
                    existing_nums.append(int(aid[1:]))
            next_num = max(existing_nums, default=0) + 1
            article_id = f"A{next_num}"
        
        if article_id not in self.articles:
            # Generate a distinct color for this article
            colors = [
                "#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
                "#1abc9c", "#e67e22", "#34495e", "#16a085", "#c0392b",
            ]
            color_idx = len(self.articles) % len(colors)
            
            self.articles[article_id] = Article(color=colors[color_idx])
            self.updated_at = datetime.utcnow().isoformat()
        
        return article_id

    def add_region(
        self,
        page_index: int,
        bbox: BBox,
        article_id: str,
        order: int | None = None,
        region_type: Literal["body", "header", "footer", "image-caption"] = "body",
    ) -> str:
        """Add a region to a page.
        
        Args:
            page_index: 0-based page index
            bbox: Bounding box in pixel space
            article_id: Article this region belongs to
            order: Reading order (auto-increments if None)
            region_type: Type of region
            
        Returns:
            The region_id that was created.
        """
        page_key = str(page_index)
        
        # Ensure page exists
        if page_key not in self.pages:
            self.pages[page_key] = PageAnnotations()
        
        # Ensure article exists
        if article_id not in self.articles:
            self.add_article(article_id)
        
        # Auto-generate order if not provided
        if order is None:
            # Find max order for this article across all pages
            max_order = 0
            for page_annot in self.pages.values():
                for region in page_annot.regions:
                    if region.article_id == article_id:
                        max_order = max(max_order, region.order)
            order = max_order + 1
        
        # Create region
        region = Region(
            article_id=article_id,
            order=order,
            bbox=bbox,
            type=region_type,
        )
        
        self.pages[page_key].regions.append(region)
        self.updated_at = datetime.utcnow().isoformat()
        
        return region.region_id

    def delete_region(self, region_id: str) -> bool:
        """Delete a region by ID.
        
        Args:
            region_id: The region to delete
            
        Returns:
            True if deleted, False if not found
        """
        for page_annot in self.pages.values():
            for i, region in enumerate(page_annot.regions):
                if region.region_id == region_id:
                    page_annot.regions.pop(i)
                    self.updated_at = datetime.utcnow().isoformat()
                    return True
        return False

    def reorder_region(self, region_id: str, new_order: int) -> bool:
        """Change the reading order of a region.
        
        Args:
            region_id: The region to reorder
            new_order: New order value
            
        Returns:
            True if reordered, False if not found
        """
        for page_annot in self.pages.values():
            for region in page_annot.regions:
                if region.region_id == region_id:
                    region.order = new_order
                    self.updated_at = datetime.utcnow().isoformat()
                    return True
        return False

    def get_regions_for_article(self, article_id: str) -> list[tuple[int, Region]]:
        """Get all regions for an article, sorted by order.
        
        Args:
            article_id: The article ID
            
        Returns:
            List of (page_index, region) tuples sorted by reading order
        """
        regions: list[tuple[int, Region]] = []
        
        for page_key, page_annot in self.pages.items():
            page_idx = int(page_key)
            for region in page_annot.regions:
                if region.article_id == article_id:
                    regions.append((page_idx, region))
        
        # Sort by order, then by page, then by y position
        regions.sort(key=lambda x: (x[1].order, x[0], x[1].bbox.y))
        
        return regions

    def auto_order_article(self, article_id: str) -> None:
        """Auto-order regions within an article by page, y, then x.
        
        Args:
            article_id: The article to reorder
        """
        regions = self.get_regions_for_article(article_id)
        
        # Sort by page, y, x
        regions.sort(key=lambda x: (x[0], x[1].bbox.y, x[1].bbox.x))
        
        # Reassign orders
        for i, (_, region) in enumerate(regions, start=1):
            region.order = i
        
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        pages_dict = {}
        for page_key, page_annot in self.pages.items():
            pages_dict[page_key] = page_annot.to_dict()
        
        articles_dict = {}
        for article_id, article in self.articles.items():
            articles_dict[article_id] = article.to_dict()
        
        return {
            "schema_version": self.schema_version,
            "source_pdf": self.source_pdf,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "pages": pages_dict,
            "articles": articles_dict,
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnnotationDoc:
        """Create from dictionary (JSON deserialization).
        
        Args:
            data: Dictionary containing annotation data
            
        Returns:
            AnnotationDoc instance
        """
        # Parse pages
        pages = {}
        for page_key, page_data in data.get("pages", {}).items():
            regions = []
            for region_data in page_data.get("regions", []):
                bbox = BBox(**region_data["bbox"])
                region = Region(
                    region_id=region_data["region_id"],
                    article_id=region_data["article_id"],
                    order=region_data["order"],
                    bbox=bbox,
                    type=region_data.get("type", "body"),
                    notes=region_data.get("notes", ""),
                )
                regions.append(region)
            pages[page_key] = PageAnnotations(regions=regions)
        
        # Parse articles
        articles = {}
        for article_id, article_data in data.get("articles", {}).items():
            articles[article_id] = Article(**article_data)
        
        # Parse settings
        settings = Settings(**data.get("settings", {}))
        
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            source_pdf=data["source_pdf"],
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            pages=pages,
            articles=articles,
            settings=settings,
        )

