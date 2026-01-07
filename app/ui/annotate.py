"""Annotation/segmentation interface for drawing and managing regions.

This module provides the UI for manually segmenting PDFs into article regions.
"""

import streamlit as st
from pathlib import Path
from typing import Optional

from app.core.segment_model import AnnotationDoc, BBox, Article
from app.core.pdf_io import render_page
from app.ui.canvas_component import drawable_canvas
from app.ui.viewer import render_page_navigation


def render_annotation_interface(
    pdf_path: str | Path,
    annotation_doc: AnnotationDoc,
    dpi: int = 200
) -> None:
    """Render the complete annotation interface.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document (will be modified)
        dpi: DPI for rendering
    """
    st.subheader("📝 Annotation Mode")
    
    # Page navigation
    current_page = render_page_navigation(pdf_path, key_prefix="annotate")
    
    # Two columns: canvas on left, controls on right
    col_canvas, col_controls = st.columns([2, 1])
    
    with col_controls:
        render_article_controls(annotation_doc)
        st.divider()
        render_region_controls(annotation_doc, current_page)
    
    with col_canvas:
        render_canvas_with_regions(pdf_path, annotation_doc, current_page, dpi)


def render_article_controls(annotation_doc: AnnotationDoc) -> None:
    """Render controls for managing articles.
    
    Args:
        annotation_doc: Annotation document
    """
    st.markdown("### Articles")
    
    # New article button
    if st.button("➕ New Article", key="new_article"):
        new_id = annotation_doc.add_article()
        st.session_state.selected_article = new_id
        st.success(f"Created article {new_id}")
        st.rerun()
    
    # List existing articles
    if not annotation_doc.articles:
        st.info("No articles yet. Click 'New Article' to create one.")
        return
    
    # Article selector
    article_ids = sorted(annotation_doc.articles.keys())
    
    # Initialize selected article
    if "selected_article" not in st.session_state:
        st.session_state.selected_article = article_ids[0]
    
    # Ensure selected article still exists
    if st.session_state.selected_article not in annotation_doc.articles:
        st.session_state.selected_article = article_ids[0]
    
    selected_article = st.selectbox(
        "Select Article",
        article_ids,
        index=article_ids.index(st.session_state.selected_article),
        format_func=lambda x: f"{x}: {annotation_doc.articles[x].title or '(no title)'}",
        key="article_selector"
    )
    
    if selected_article != st.session_state.selected_article:
        st.session_state.selected_article = selected_article
        st.rerun()
    
    # Article metadata editor
    article = annotation_doc.articles[selected_article]
    
    st.markdown(f"**Edit {selected_article}**")
    
    # Title
    new_title = st.text_input(
        "Title",
        value=article.title,
        key=f"title_{selected_article}"
    )
    if new_title != article.title:
        article.title = new_title
    
    # Subtitle
    new_subtitle = st.text_input(
        "Subtitle",
        value=article.subtitle,
        key=f"subtitle_{selected_article}"
    )
    if new_subtitle != article.subtitle:
        article.subtitle = new_subtitle
    
    # Author
    new_author = st.text_input(
        "Author",
        value=article.author,
        key=f"author_{selected_article}"
    )
    if new_author != article.author:
        article.author = new_author
    
    # Color picker
    new_color = st.color_picker(
        "Color",
        value=article.color,
        key=f"color_{selected_article}"
    )
    if new_color != article.color:
        article.color = new_color
    
    # Tags (comma-separated)
    tags_str = ", ".join(article.tags)
    new_tags_str = st.text_input(
        "Tags (comma-separated)",
        value=tags_str,
        key=f"tags_{selected_article}"
    )
    if new_tags_str != tags_str:
        article.tags = [tag.strip() for tag in new_tags_str.split(",") if tag.strip()]
    
    # Show region count
    regions = annotation_doc.get_regions_for_article(selected_article)
    st.metric("Regions", len(regions))
    
    # Auto-order button
    if len(regions) > 1:
        if st.button("🔄 Auto-order regions", key=f"auto_order_{selected_article}"):
            annotation_doc.auto_order_article(selected_article)
            st.success("Regions reordered")
            st.rerun()


def render_region_controls(annotation_doc: AnnotationDoc, current_page: int) -> None:
    """Render controls for managing regions on current page.
    
    Args:
        annotation_doc: Annotation document
        current_page: Current page index
    """
    st.markdown("### Regions on Current Page")
    
    page_key = str(current_page)
    if page_key not in annotation_doc.pages or not annotation_doc.pages[page_key].regions:
        st.info("No regions on this page. Draw a region on the canvas to add one.")
        return
    
    regions = annotation_doc.pages[page_key].regions
    
    # List regions
    for i, region in enumerate(regions):
        article = annotation_doc.articles.get(region.article_id)
        article_title = article.title if article and article.title else region.article_id
        
        with st.expander(f"Region {i+1}: {article_title} (order {region.order})"):
            st.markdown(f"**Article:** {region.article_id}")
            st.markdown(f"**Type:** {region.type}")
            st.markdown(f"**Order:** {region.order}")
            st.markdown(f"**Bbox:** ({region.bbox.x:.0f}, {region.bbox.y:.0f}, {region.bbox.w:.0f}, {region.bbox.h:.0f})")
            
            # Edit order
            new_order = st.number_input(
                "Change order",
                min_value=1,
                value=region.order,
                key=f"order_{region.region_id}"
            )
            if new_order != region.order:
                annotation_doc.reorder_region(region.region_id, new_order)
                st.rerun()
            
            # Delete button
            if st.button("🗑️ Delete", key=f"delete_{region.region_id}"):
                annotation_doc.delete_region(region.region_id)
                st.success("Region deleted")
                st.rerun()
    
    # Utility: duplicate regions to next page
    if st.button("📋 Duplicate all to next page", key="duplicate_to_next"):
        next_page = current_page + 1
        duplicated = 0
        for region in regions:
            annotation_doc.add_region(
                page_index=next_page,
                bbox=region.bbox,
                article_id=region.article_id,
                order=region.order,
                region_type=region.type
            )
            duplicated += 1
        st.success(f"Duplicated {duplicated} regions to page {next_page + 1}")
        st.rerun()


def render_canvas_with_regions(
    pdf_path: str | Path,
    annotation_doc: AnnotationDoc,
    current_page: int,
    dpi: int
) -> None:
    """Render the canvas with existing regions and handle new region drawing.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
        current_page: Current page index
        dpi: DPI for rendering
    """
    # Render page
    page_image = render_page(pdf_path, current_page, dpi)
    
    # Get existing regions for this page
    page_key = str(current_page)
    existing_regions = []
    
    if page_key in annotation_doc.pages:
        for region in annotation_doc.pages[page_key].regions:
            article = annotation_doc.articles.get(region.article_id)
            color = article.color if article else "#3498db"
            label = f"{region.article_id} ({region.order})"
            
            existing_regions.append({
                "bbox": region.bbox.to_dict(),
                "color": color,
                "label": label,
            })
    
    # Display canvas with existing regions
    st.markdown("**Page Preview:**")
    display_image, scale_x, scale_y = drawable_canvas(
        page_image=page_image,
        existing_regions=existing_regions,
        canvas_width=900,
        key=f"canvas_page_{current_page}"
    )
    
    # Manual region input form
    st.markdown("**Add New Region:**")
    
    with st.form(key=f"region_form_{current_page}"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            x = st.number_input("X", min_value=0, max_value=int(page_image.width), value=100, step=10, key=f"x_{current_page}")
        with col2:
            y = st.number_input("Y", min_value=0, max_value=int(page_image.height), value=100, step=10, key=f"y_{current_page}")
        with col3:
            w = st.number_input("Width", min_value=10, max_value=int(page_image.width), value=300, step=10, key=f"w_{current_page}")
        with col4:
            h = st.number_input("Height", min_value=10, max_value=int(page_image.height), value=400, step=10, key=f"h_{current_page}")
        
        submitted = st.form_submit_button("➕ Add Region")
        
        if submitted:
            bbox_dict = {"x": x, "y": y, "w": w, "h": h}
            handle_new_region(annotation_doc, current_page, bbox_dict)
            st.rerun()


def handle_new_region(annotation_doc: AnnotationDoc, page_index: int, bbox_dict: dict) -> None:
    """Handle a newly drawn region.
    
    Args:
        annotation_doc: Annotation document
        page_index: Page index where region was drawn
        bbox_dict: Dictionary with x, y, w, h keys
    """
    # Get selected article
    selected_article = st.session_state.get("selected_article")
    
    if not selected_article:
        # No article selected, create one
        selected_article = annotation_doc.add_article()
        st.session_state.selected_article = selected_article
    
    # Create bbox
    bbox = BBox(
        x=bbox_dict["x"],
        y=bbox_dict["y"],
        w=bbox_dict["w"],
        h=bbox_dict["h"]
    )
    
    # Add region
    region_id = annotation_doc.add_region(
        page_index=page_index,
        bbox=bbox,
        article_id=selected_article,
    )
    
    st.success(f"Added region to {selected_article}")
    st.rerun()

