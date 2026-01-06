"""Page viewer component for navigating PDF pages.

This module provides controls for page navigation and rendering.
"""

import streamlit as st
from pathlib import Path
from PIL import Image

from app.core.pdf_io import render_page, get_page_count


def render_page_navigation(pdf_path: str | Path, key_prefix: str = "nav") -> int:
    """Render page navigation controls.
    
    Args:
        pdf_path: Path to PDF file
        key_prefix: Prefix for widget keys to avoid conflicts
        
    Returns:
        Current page index (0-based)
    """
    page_count = get_page_count(pdf_path)
    
    # Initialize page index in session state
    page_key = f"{key_prefix}_current_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    # Ensure page index is valid
    if st.session_state[page_key] >= page_count:
        st.session_state[page_key] = 0
    
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
    
    with col1:
        if st.button("⬅️ Prev", key=f"{key_prefix}_prev", disabled=st.session_state[page_key] == 0):
            st.session_state[page_key] = max(0, st.session_state[page_key] - 1)
            st.rerun()
    
    with col2:
        # Page selector
        new_page = st.selectbox(
            "Page",
            range(page_count),
            index=st.session_state[page_key],
            format_func=lambda x: f"Page {x + 1} of {page_count}",
            key=f"{key_prefix}_select"
        )
        if new_page != st.session_state[page_key]:
            st.session_state[page_key] = new_page
            st.rerun()
    
    with col3:
        if st.button("Next ➡️", key=f"{key_prefix}_next", disabled=st.session_state[page_key] >= page_count - 1):
            st.session_state[page_key] = min(page_count - 1, st.session_state[page_key] + 1)
            st.rerun()
    
    with col4:
        # Jump to page input
        jump_to = st.number_input(
            "Jump",
            min_value=1,
            max_value=page_count,
            value=st.session_state[page_key] + 1,
            step=1,
            key=f"{key_prefix}_jump",
            label_visibility="collapsed"
        )
        if jump_to - 1 != st.session_state[page_key]:
            st.session_state[page_key] = jump_to - 1
            st.rerun()
    
    return st.session_state[page_key]


def render_page_viewer(
    pdf_path: str | Path,
    page_index: int,
    dpi: int = 200,
    canvas_width: int = 1000
) -> Image.Image:
    """Render a PDF page to an image.
    
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        dpi: Resolution for rendering
        canvas_width: Target width for display
        
    Returns:
        PIL Image of the rendered page
    """
    # Render page at specified DPI
    page_image = render_page(pdf_path, page_index, dpi)
    
    return page_image


def get_canvas_dimensions(page_image: Image.Image, target_width: int = 1000) -> tuple[int, int]:
    """Calculate canvas dimensions maintaining aspect ratio.
    
    Args:
        page_image: PIL Image of the page
        target_width: Target width for display
        
    Returns:
        Tuple of (width, height)
    """
    aspect_ratio = page_image.height / page_image.width
    target_height = int(target_width * aspect_ratio)
    return target_width, target_height

