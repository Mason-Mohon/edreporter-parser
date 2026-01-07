"""API routes for EdReporter Flask application."""

import base64
from io import BytesIO
from pathlib import Path
from flask import jsonify, request, session, send_file

from app.core.segment_model import AnnotationDoc, BBox
from app.core.storage import (
    list_pdfs, load_annotations, save_annotations,
    get_docx_path, get_markdown_path, ensure_out_dir
)
from app.core.pdf_io import render_page, get_page_count
from app.core.extraction import build_article_text
from app.core.export_docx import export_issue_docx, export_markdown
from .logger import logger
from .config import Config


def register_routes(app):
    """Register all API routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    # ============ PDF Management ============
    
    @app.route('/api/pdfs', methods=['GET'])
    def get_pdfs():
        """List all PDFs organized by year."""
        logger.info("Fetching PDF list")
        try:
            pdfs_by_year = list_pdfs(str(Config.DATA_DIR))
            
            # Convert Path objects to strings
            result = {}
            for year, paths in pdfs_by_year.items():
                result[year] = [str(p) for p in paths]
            
            logger.info(f"Found {sum(len(v) for v in result.values())} PDFs across {len(result)} years")
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error listing PDFs: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/pdf/info', methods=['POST'])
    def get_pdf_info():
        """Get information about a specific PDF."""
        data = request.json
        pdf_path = data.get('path')
        
        if not pdf_path:
            return jsonify({'error': 'PDF path required'}), 400
        
        logger.info(f"Getting info for PDF: {pdf_path}")
        
        try:
            page_count = get_page_count(pdf_path)
            return jsonify({
                'path': pdf_path,
                'page_count': page_count,
                'name': Path(pdf_path).name
            })
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/pdf/page', methods=['POST'])
    def render_pdf_page():
        """Render a PDF page as base64 image."""
        data = request.json
        pdf_path = data.get('path')
        page_num = data.get('page', 0)
        dpi = data.get('dpi', Config.DEFAULT_DPI)
        
        if not pdf_path:
            return jsonify({'error': 'PDF path required'}), 400
        
        logger.debug(f"Rendering page {page_num} of {pdf_path} at {dpi} DPI")
        
        try:
            # Render page
            img = render_page(pdf_path, page_num, dpi)
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            logger.debug(f"Rendered page {page_num}, size: {img.size}")
            
            return jsonify({
                'image': f'data:image/png;base64,{img_base64}',
                'width': img.width,
                'height': img.height
            })
        except Exception as e:
            logger.error(f"Error rendering page: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    # ============ Annotation Management ============
    
    @app.route('/api/annotations/load', methods=['POST'])
    def load_annotations_route():
        """Load annotations for a PDF."""
        data = request.json
        pdf_path = data.get('path')
        
        if not pdf_path:
            return jsonify({'error': 'PDF path required'}), 400
        
        logger.info(f"Loading annotations for: {pdf_path}")
        
        try:
            annotation_doc = load_annotations(pdf_path)
            logger.info(f"Loaded {len(annotation_doc.articles)} articles")
            return jsonify(annotation_doc.to_dict())
        except Exception as e:
            logger.error(f"Error loading annotations: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/annotations/save', methods=['POST'])
    def save_annotations_route():
        """Save annotations for a PDF."""
        data = request.json
        pdf_path = data.get('path')
        annotations_data = data.get('annotations')
        
        if not pdf_path or not annotations_data:
            return jsonify({'error': 'PDF path and annotations required'}), 400
        
        logger.info(f"Saving annotations for: {pdf_path}")
        
        try:
            # Reconstruct annotation document
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            # Save
            saved_path = save_annotations(annotation_doc, pdf_path)
            
            logger.info(f"Saved annotations to: {saved_path}")
            return jsonify({'success': True, 'path': str(saved_path)})
        except Exception as e:
            logger.error(f"Error saving annotations: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/article/new', methods=['POST'])
    def create_article():
        """Create a new article."""
        data = request.json
        annotations_data = data.get('annotations')
        
        if not annotations_data:
            return jsonify({'error': 'Annotations required'}), 400
        
        logger.info("Creating new article")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            article_id = annotation_doc.add_article()
            
            logger.info(f"Created article: {article_id}")
            return jsonify({
                'success': True,
                'article_id': article_id,
                'annotations': annotation_doc.to_dict()
            })
        except Exception as e:
            logger.error(f"Error creating article: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/article/update', methods=['POST'])
    def update_article():
        """Update article metadata."""
        data = request.json
        annotations_data = data.get('annotations')
        article_id = data.get('article_id')
        updates = data.get('updates', {})
        
        if not annotations_data or not article_id:
            return jsonify({'error': 'Annotations and article_id required'}), 400
        
        logger.info(f"Updating article: {article_id}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            if article_id not in annotation_doc.articles:
                return jsonify({'error': 'Article not found'}), 404
            
            article = annotation_doc.articles[article_id]
            
            # Update fields
            if 'title' in updates:
                article.title = updates['title']
            if 'subtitle' in updates:
                article.subtitle = updates['subtitle']
            if 'author' in updates:
                article.author = updates['author']
            if 'tags' in updates:
                article.tags = updates['tags']
            if 'color' in updates:
                article.color = updates['color']
            
            logger.info(f"Updated article {article_id}: {updates.keys()}")
            return jsonify({
                'success': True,
                'annotations': annotation_doc.to_dict()
            })
        except Exception as e:
            logger.error(f"Error updating article: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/article/delete', methods=['POST'])
    def delete_article():
        """Delete an article and its regions."""
        data = request.json
        annotations_data = data.get('annotations')
        article_id = data.get('article_id')
        
        if not annotations_data or not article_id:
            return jsonify({'error': 'Annotations and article_id required'}), 400
        
        logger.info(f"Deleting article: {article_id}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            if article_id not in annotation_doc.articles:
                return jsonify({'error': 'Article not found'}), 404
            
            # Delete all regions for this article
            regions_to_delete = []
            for page_annot in annotation_doc.pages.values():
                for region in page_annot.regions:
                    if region.article_id == article_id:
                        regions_to_delete.append(region.region_id)
            
            for region_id in regions_to_delete:
                annotation_doc.delete_region(region_id)
            
            # Delete article
            del annotation_doc.articles[article_id]
            
            logger.info(f"Deleted article {article_id} and {len(regions_to_delete)} regions")
            return jsonify({
                'success': True,
                'annotations': annotation_doc.to_dict()
            })
        except Exception as e:
            logger.error(f"Error deleting article: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/region/add', methods=['POST'])
    def add_region():
        """Add a new region."""
        data = request.json
        annotations_data = data.get('annotations')
        page_index = data.get('page_index')
        bbox_data = data.get('bbox')
        article_id = data.get('article_id')
        
        if not all([annotations_data, page_index is not None, bbox_data, article_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        logger.info(f"Adding region to article {article_id} on page {page_index}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            bbox = BBox(**bbox_data)
            region_id = annotation_doc.add_region(
                page_index=page_index,
                bbox=bbox,
                article_id=article_id
            )
            
            logger.info(f"Added region {region_id}")
            return jsonify({
                'success': True,
                'region_id': region_id,
                'annotations': annotation_doc.to_dict()
            })
        except Exception as e:
            logger.error(f"Error adding region: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/region/delete', methods=['POST'])
    def delete_region():
        """Delete a region."""
        data = request.json
        annotations_data = data.get('annotations')
        region_id = data.get('region_id')
        
        if not annotations_data or not region_id:
            return jsonify({'error': 'Annotations and region_id required'}), 400
        
        logger.info(f"Deleting region: {region_id}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            success = annotation_doc.delete_region(region_id)
            
            if not success:
                return jsonify({'error': 'Region not found'}), 404
            
            logger.info(f"Deleted region {region_id}")
            return jsonify({
                'success': True,
                'annotations': annotation_doc.to_dict()
            })
        except Exception as e:
            logger.error(f"Error deleting region: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    # ============ Extraction & Export ============
    
    @app.route('/api/extract', methods=['POST'])
    def extract_text():
        """Extract text from all articles."""
        data = request.json
        pdf_path = data.get('path')
        annotations_data = data.get('annotations')
        
        if not pdf_path or not annotations_data:
            return jsonify({'error': 'PDF path and annotations required'}), 400
        
        logger.info(f"Extracting text from: {pdf_path}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            # Extract text
            results = build_article_text(annotation_doc, pdf_path, apply_cleanup=True)
            
            # Convert to serializable format
            extracted = {}
            for article_id, ext_text in results.items():
                extracted[article_id] = {
                    'text': ext_text.text,
                    'regions_metadata': [
                        {
                            'region_id': r.region_id,
                            'page_index': r.page_index,
                            'method': r.method,
                            'quality_score': r.quality_score,
                            'text_length': r.text_length
                        }
                        for r in ext_text.regions_metadata
                    ]
                }
            
            total_chars = sum(len(ext['text']) for ext in extracted.values())
            logger.info(f"Extracted {total_chars} chars from {len(extracted)} articles")
            
            return jsonify({'success': True, 'extracted': extracted})
        except Exception as e:
            logger.error(f"Error extracting text: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/export/docx', methods=['POST'])
    def export_docx():
        """Export to DOCX format."""
        data = request.json
        pdf_path = data.get('path')
        annotations_data = data.get('annotations')
        extracted_data = data.get('extracted')
        
        if not all([pdf_path, annotations_data, extracted_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        logger.info(f"Exporting DOCX for: {pdf_path}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            # Reconstruct ExtractedText objects
            from app.core.extraction import ExtractedText, RegionExtraction
            article_texts = {}
            for article_id, ext_data in extracted_data.items():
                regions_meta = [
                    RegionExtraction(**r) for r in ext_data['regions_metadata']
                ]
                article_texts[article_id] = ExtractedText(
                    article_id=article_id,
                    text=ext_data['text'],
                    regions_metadata=regions_meta
                )
            
            # Export
            docx_path = get_docx_path(pdf_path)
            export_issue_docx(docx_path, annotation_doc, article_texts)
            
            logger.info(f"Exported DOCX to: {docx_path}")
            return jsonify({'success': True, 'path': str(docx_path)})
        except Exception as e:
            logger.error(f"Error exporting DOCX: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/export/markdown', methods=['POST'])
    def export_md():
        """Export to Markdown format."""
        data = request.json
        pdf_path = data.get('path')
        annotations_data = data.get('annotations')
        extracted_data = data.get('extracted')
        
        if not all([pdf_path, annotations_data, extracted_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        logger.info(f"Exporting Markdown for: {pdf_path}")
        
        try:
            annotation_doc = AnnotationDoc.from_dict(annotations_data)
            
            # Reconstruct ExtractedText objects
            from app.core.extraction import ExtractedText, RegionExtraction
            article_texts = {}
            for article_id, ext_data in extracted_data.items():
                regions_meta = [
                    RegionExtraction(**r) for r in ext_data['regions_metadata']
                ]
                article_texts[article_id] = ExtractedText(
                    article_id=article_id,
                    text=ext_data['text'],
                    regions_metadata=regions_meta
                )
            
            # Export
            md_path = get_markdown_path(pdf_path)
            export_markdown(md_path, annotation_doc, article_texts)
            
            logger.info(f"Exported Markdown to: {md_path}")
            return jsonify({'success': True, 'path': str(md_path)})
        except Exception as e:
            logger.error(f"Error exporting Markdown: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
