"""Text editor interface for extraction, editing, and export.

This module provides the UI for extracting text from regions,
editing the extracted text, and exporting to DOCX.
"""

import streamlit as st
from pathlib import Path
from typing import Dict

from app.core.segment_model import AnnotationDoc
from app.core.extraction import build_article_text, ExtractedText, re_extract_region
from app.core.export_docx import export_issue_docx, export_markdown
from app.core.storage import get_docx_path, get_markdown_path, ensure_out_dir
from app.core.heuristics import cleanup_text
from app.core.ocr import check_tesseract_available


def render_editor_interface(
    pdf_path: str | Path,
    annotation_doc: AnnotationDoc
) -> None:
    """Render the text extraction and editing interface.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
    """
    st.subheader("✏️ Extract & Edit Text")
    
    # Check if Tesseract is available
    if not check_tesseract_available():
        st.error(
            "⚠️ Tesseract OCR is not installed or not found in PATH. "
            "OCR functionality will not work. Please install Tesseract:\n\n"
            "- Linux: `sudo apt-get install tesseract-ocr`\n"
            "- macOS: `brew install tesseract`\n"
            "- Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    
    # Check if there are any articles
    if not annotation_doc.articles:
        st.info("No articles defined yet. Go to the Annotate tab to create articles and regions.")
        return
    
    # Initialize extracted texts in session state
    if "extracted_texts" not in st.session_state:
        st.session_state.extracted_texts = {}
    
    # Extraction controls
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### Text Extraction")
    
    with col2:
        if st.button("🔄 Build Article Text", key="build_text", type="primary"):
            extract_all_articles(pdf_path, annotation_doc)
    
    # Show extraction status
    if st.session_state.extracted_texts:
        st.success(f"✅ Extracted text for {len(st.session_state.extracted_texts)} articles")
    
    st.divider()
    
    # Article tabs for editing
    if st.session_state.extracted_texts:
        render_article_editors(pdf_path, annotation_doc)
        st.divider()
        render_export_controls(pdf_path, annotation_doc)
    else:
        st.info("Click 'Build Article Text' to extract text from all regions.")


def extract_all_articles(pdf_path: str | Path, annotation_doc: AnnotationDoc) -> None:
    """Extract text from all articles.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
    """
    with st.spinner("Extracting text from all regions..."):
        try:
            # Build article texts
            results = build_article_text(
                annotation_doc=annotation_doc,
                pdf_path=pdf_path,
                apply_cleanup=True
            )
            
            # Store in session state
            st.session_state.extracted_texts = results
            
            # Show summary
            total_chars = sum(len(ext.text) for ext in results.values())
            st.success(f"Extracted {total_chars} characters from {len(results)} articles")
            
        except Exception as e:
            st.error(f"Error during extraction: {e}")


def render_article_editors(pdf_path: str | Path, annotation_doc: AnnotationDoc) -> None:
    """Render editors for each article.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
    """
    st.markdown("### Article Text Editors")
    
    extracted_texts: Dict[str, ExtractedText] = st.session_state.extracted_texts
    
    # Create tabs for each article
    article_ids = sorted(annotation_doc.articles.keys())
    
    if len(article_ids) == 1:
        # Single article - no tabs needed
        article_id = article_ids[0]
        render_article_editor(pdf_path, annotation_doc, article_id, extracted_texts.get(article_id))
    else:
        # Multiple articles - use tabs
        tab_labels = []
        for aid in article_ids:
            article = annotation_doc.articles[aid]
            label = f"{aid}: {article.title[:20] if article.title else '(no title)'}"
            tab_labels.append(label)
        
        tabs = st.tabs(tab_labels)
        
        for i, article_id in enumerate(article_ids):
            with tabs[i]:
                render_article_editor(
                    pdf_path,
                    annotation_doc,
                    article_id,
                    extracted_texts.get(article_id)
                )


def render_article_editor(
    pdf_path: str | Path,
    annotation_doc: AnnotationDoc,
    article_id: str,
    extracted_text: ExtractedText | None
) -> None:
    """Render editor for a single article.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
        article_id: Article ID to edit
        extracted_text: Extracted text (may be None if not yet extracted)
    """
    article = annotation_doc.articles[article_id]
    
    # Article info
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"**{article.title or 'Untitled Article'}**")
        if article.subtitle:
            st.markdown(f"*{article.subtitle}*")
    
    with col2:
        if extracted_text:
            st.metric("Extracted Length", f"{len(extracted_text.text)} chars")
    
    with col3:
        if extracted_text:
            avg_quality = sum(r.quality_score for r in extracted_text.regions_metadata) / len(extracted_text.regions_metadata)
            st.metric("Avg Quality", f"{avg_quality:.2f}")
    
    # Show extraction metadata
    if extracted_text:
        with st.expander("📊 Extraction Details"):
            for region_meta in extracted_text.regions_metadata:
                st.markdown(
                    f"- **Page {region_meta.page_index + 1}** | "
                    f"Method: `{region_meta.method}` | "
                    f"Quality: {region_meta.quality_score:.2f} | "
                    f"Length: {region_meta.text_length}"
                )
    
    # Text editor
    if extracted_text:
        # Initialize edited text in session state
        text_key = f"edited_text_{article_id}"
        if text_key not in st.session_state:
            st.session_state[text_key] = extracted_text.text
        
        # Text area
        edited_text = st.text_area(
            "Edit text:",
            value=st.session_state[text_key],
            height=400,
            key=f"textarea_{article_id}"
        )
        
        # Update session state
        st.session_state[text_key] = edited_text
        
        # Update the extracted text object
        extracted_text.text = edited_text
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Apply Cleanup", key=f"cleanup_{article_id}"):
                cleaned = cleanup_text(st.session_state[text_key])
                st.session_state[text_key] = cleaned
                st.success("Cleanup applied")
                st.rerun()
        
        with col2:
            if st.button("🔄 Re-extract", key=f"reextract_{article_id}"):
                # Re-extract this article
                with st.spinner("Re-extracting..."):
                    results = build_article_text(
                        annotation_doc=annotation_doc,
                        pdf_path=pdf_path,
                        apply_cleanup=True
                    )
                    if article_id in results:
                        st.session_state.extracted_texts[article_id] = results[article_id]
                        st.session_state[text_key] = results[article_id].text
                        st.success("Re-extracted")
                        st.rerun()
    else:
        st.info("No text extracted for this article yet.")


def render_export_controls(pdf_path: str | Path, annotation_doc: AnnotationDoc) -> None:
    """Render export controls.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
    """
    st.markdown("### 📤 Export")
    
    # Validation: check if all articles have titles
    missing_titles = []
    for article_id, article in annotation_doc.articles.items():
        if not article.title:
            missing_titles.append(article_id)
    
    if missing_titles:
        st.warning(
            f"⚠️ The following articles are missing titles: {', '.join(missing_titles)}. "
            "Consider adding titles before export."
        )
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        export_docx = st.checkbox("Export DOCX", value=True, key="export_docx")
    
    with col2:
        export_md = st.checkbox("Export Markdown", value=True, key="export_md")
    
    # Export button
    if st.button("📄 Export Document", key="export", type="primary"):
        perform_export(pdf_path, annotation_doc, export_docx, export_md)


def perform_export(
    pdf_path: str | Path,
    annotation_doc: AnnotationDoc,
    export_docx_flag: bool,
    export_md_flag: bool
) -> None:
    """Perform the export operation.
    
    Args:
        pdf_path: Path to PDF file
        annotation_doc: Annotation document
        export_docx_flag: Whether to export DOCX
        export_md_flag: Whether to export Markdown
    """
    extracted_texts: Dict[str, ExtractedText] = st.session_state.extracted_texts
    
    if not extracted_texts:
        st.error("No extracted texts to export. Please build article text first.")
        return
    
    # Ensure output directory exists
    ensure_out_dir(pdf_path)
    
    success_messages = []
    
    try:
        # Export DOCX
        if export_docx_flag:
            with st.spinner("Generating DOCX..."):
                docx_path = get_docx_path(pdf_path)
                export_issue_docx(docx_path, annotation_doc, extracted_texts)
                success_messages.append(f"✅ DOCX: `{docx_path}`")
        
        # Export Markdown
        if export_md_flag:
            with st.spinner("Generating Markdown..."):
                md_path = get_markdown_path(pdf_path)
                export_markdown(md_path, annotation_doc, extracted_texts)
                success_messages.append(f"✅ Markdown: `{md_path}`")
        
        # Show success
        if success_messages:
            st.success("Export completed!")
            for msg in success_messages:
                st.markdown(msg)
    
    except Exception as e:
        st.error(f"Export failed: {e}")

