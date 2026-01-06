"""EdReporter PDF Segmentation Tool - Main Application

This is the main entry point for the Streamlit application.
Run with: uv run streamlit run app/main.py
"""

import streamlit as st
from pathlib import Path

from app.core.segment_model import AnnotationDoc
from app.core.storage import (
    list_pdfs,
    load_annotations,
    save_annotations,
)
from app.ui.annotate import render_annotation_interface
from app.ui.editor import render_editor_interface


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "annotation_doc" not in st.session_state:
        st.session_state.annotation_doc = None
    
    if "current_pdf" not in st.session_state:
        st.session_state.current_pdf = None
    
    if "extracted_texts" not in st.session_state:
        st.session_state.extracted_texts = {}
    
    if "config" not in st.session_state:
        st.session_state.config = {
            "dpi": 200,
            "ocr_lang": "eng",
            "tesseract_psm": 6,
            "prefer_pdf_text": True,
        }


def render_sidebar():
    """Render the sidebar with PDF selection and settings."""
    st.sidebar.title("📚 EdReporter")
    st.sidebar.markdown("PDF Article Segmentation Tool")
    
    st.sidebar.divider()
    
    # PDF Selection
    st.sidebar.subheader("Select PDF")
    
    # Scan for PDFs
    pdfs_by_year = list_pdfs("data")
    
    if not pdfs_by_year:
        st.sidebar.error("No PDFs found in `data/` directory")
        st.sidebar.info(
            "Please organize your PDFs as:\n\n"
            "```\n"
            "data/\n"
            "  1986/\n"
            "    file1.pdf\n"
            "    file2.pdf\n"
            "  1987/\n"
            "    ...\n"
            "```"
        )
        return None
    
    # Year selector
    years = sorted(pdfs_by_year.keys())
    selected_year = st.sidebar.selectbox("Year", years, key="year_select")
    
    # PDF selector
    pdfs_in_year = pdfs_by_year[selected_year]
    pdf_names = [pdf.name for pdf in pdfs_in_year]
    
    selected_pdf_name = st.sidebar.selectbox(
        "PDF File",
        pdf_names,
        key="pdf_select"
    )
    
    # Get full path
    selected_pdf = next(pdf for pdf in pdfs_in_year if pdf.name == selected_pdf_name)
    
    # Navigation buttons
    col1, col2 = st.sidebar.columns(2)
    
    current_idx = pdf_names.index(selected_pdf_name)
    
    with col1:
        if st.button("⬅️ Prev", disabled=current_idx == 0):
            st.session_state.pdf_select = pdf_names[current_idx - 1]
            st.rerun()
    
    with col2:
        if st.button("Next ➡️", disabled=current_idx == len(pdf_names) - 1):
            st.session_state.pdf_select = pdf_names[current_idx + 1]
            st.rerun()
    
    st.sidebar.divider()
    
    # Settings
    st.sidebar.subheader("⚙️ Settings")
    
    dpi = st.sidebar.slider(
        "DPI",
        min_value=150,
        max_value=300,
        value=st.session_state.config["dpi"],
        step=10,
        help="Resolution for rendering PDFs. Higher = better quality but slower."
    )
    
    prefer_pdf_text = st.sidebar.checkbox(
        "Prefer PDF Text Layer",
        value=st.session_state.config["prefer_pdf_text"],
        help="Try extracting text from PDF before using OCR"
    )
    
    ocr_lang = st.sidebar.text_input(
        "OCR Language",
        value=st.session_state.config["ocr_lang"],
        help="Tesseract language code (e.g., eng, fra, deu)"
    )
    
    # Update config
    st.session_state.config["dpi"] = dpi
    st.session_state.config["prefer_pdf_text"] = prefer_pdf_text
    st.session_state.config["ocr_lang"] = ocr_lang
    
    st.sidebar.divider()
    
    # Save button
    if st.sidebar.button("💾 Save Annotations", type="primary"):
        save_current_annotations()
    
    # Auto-save info
    st.sidebar.info("💡 Annotations are auto-saved when switching PDFs")
    
    return selected_pdf


def load_pdf(pdf_path: Path):
    """Load a PDF and its annotations.
    
    Args:
        pdf_path: Path to PDF file
    """
    # Save current annotations if switching PDFs
    if (st.session_state.current_pdf is not None and
        st.session_state.current_pdf != pdf_path and
        st.session_state.annotation_doc is not None):
        save_current_annotations()
    
    # Load new PDF
    st.session_state.current_pdf = pdf_path
    
    # Load annotations
    annotation_doc = load_annotations(pdf_path)
    
    # Update settings from config
    annotation_doc.settings.dpi = st.session_state.config["dpi"]
    annotation_doc.settings.ocr_lang = st.session_state.config["ocr_lang"]
    annotation_doc.settings.prefer_pdf_text_layer = st.session_state.config["prefer_pdf_text"]
    
    st.session_state.annotation_doc = annotation_doc
    
    # Clear extracted texts when loading new PDF
    st.session_state.extracted_texts = {}


def save_current_annotations():
    """Save current annotations to disk."""
    if st.session_state.annotation_doc is None:
        return
    
    if st.session_state.current_pdf is None:
        return
    
    try:
        saved_path = save_annotations(
            st.session_state.annotation_doc,
            st.session_state.current_pdf
        )
        st.sidebar.success(f"✅ Saved to {saved_path.name}")
    except Exception as e:
        st.sidebar.error(f"❌ Save failed: {e}")


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="EdReporter PDF Segmentation",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar and get selected PDF
    selected_pdf = render_sidebar()
    
    if selected_pdf is None:
        st.error("No PDFs available. Please add PDFs to the `data/` directory.")
        return
    
    # Load PDF if changed
    if st.session_state.current_pdf != selected_pdf:
        load_pdf(selected_pdf)
    
    # Main content area
    st.title(f"📄 {selected_pdf.name}")
    
    annotation_doc = st.session_state.annotation_doc
    
    if annotation_doc is None:
        st.error("Failed to load annotations")
        return
    
    # Tabs for different modes
    tab_annotate, tab_edit = st.tabs(["📝 Annotate", "✏️ Extract & Edit"])
    
    with tab_annotate:
        render_annotation_interface(
            pdf_path=selected_pdf,
            annotation_doc=annotation_doc,
            dpi=st.session_state.config["dpi"]
        )
    
    with tab_edit:
        render_editor_interface(
            pdf_path=selected_pdf,
            annotation_doc=annotation_doc
        )
    
    # Footer
    st.divider()
    st.markdown(
        "<small>EdReporter PDF Segmentation Tool | "
        "Built with Streamlit, PyMuPDF, and Tesseract</small>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

