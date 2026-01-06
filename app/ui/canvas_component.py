"""Custom HTML/JavaScript canvas component for PDF annotation.

This module provides an interactive canvas for drawing bounding boxes
on PDF page images using Streamlit's components API.
"""

import streamlit.components.v1 as components
from typing import Optional
from pathlib import Path
from PIL import Image
import base64
from io import BytesIO


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string for embedding in HTML.
    
    Args:
        image: PIL Image to convert
        
    Returns:
        Base64 encoded image string
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def drawable_canvas(
    page_image: Image.Image,
    existing_regions: list[dict],
    canvas_width: int = 1000,
    canvas_height: Optional[int] = None,
    key: str = "canvas"
) -> Optional[dict]:
    """Render an interactive canvas for drawing bounding boxes.
    
    Args:
        page_image: PIL Image of the PDF page
        existing_regions: List of existing regions to display
                         Each region dict should have: bbox (x,y,w,h), color, label
        canvas_width: Width of the canvas in pixels
        canvas_height: Height of the canvas (auto-calculated if None)
        key: Unique key for the component
        
    Returns:
        Dictionary with drawn bbox if a new region was drawn, None otherwise
        Format: {"x": float, "y": float, "w": float, "h": float}
    """
    # Calculate canvas height to maintain aspect ratio
    if canvas_height is None:
        aspect_ratio = page_image.height / page_image.width
        canvas_height = int(canvas_width * aspect_ratio)
    
    # Resize image to fit canvas
    display_image = page_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    img_base64 = image_to_base64(display_image)
    
    # Scale factors for converting display coords to original coords
    scale_x = page_image.width / canvas_width
    scale_y = page_image.height / canvas_height
    
    # Convert existing regions to display coordinates
    display_regions = []
    for region in existing_regions:
        bbox = region.get("bbox", {})
        display_regions.append({
            "x": bbox.get("x", 0) / scale_x,
            "y": bbox.get("y", 0) / scale_y,
            "w": bbox.get("w", 0) / scale_x,
            "h": bbox.get("h", 0) / scale_y,
            "color": region.get("color", "#3498db"),
            "label": region.get("label", ""),
        })
    
    # HTML/JS component
    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
            }}
            #canvas {{
                border: 2px solid #ccc;
                cursor: crosshair;
                display: block;
            }}
            .instructions {{
                font-family: Arial, sans-serif;
                font-size: 12px;
                padding: 5px;
                background: #f0f0f0;
                margin-bottom: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="instructions">
            Click and drag to draw a region. Right-click on a region to delete it.
        </div>
        <canvas id="canvas" width="{canvas_width}" height="{canvas_height}"></canvas>
        
        <script>
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            
            // Load and draw background image
            const bgImage = new Image();
            bgImage.src = '{img_base64}';
            
            // Existing regions
            const existingRegions = {display_regions};
            
            // Drawing state
            let isDrawing = false;
            let startX, startY;
            let currentRect = null;
            
            bgImage.onload = function() {{
                redraw();
            }};
            
            function redraw() {{
                // Clear canvas
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Draw background image
                ctx.drawImage(bgImage, 0, 0, canvas.width, canvas.height);
                
                // Draw existing regions
                existingRegions.forEach(region => {{
                    drawRect(region.x, region.y, region.w, region.h, region.color, region.label);
                }});
                
                // Draw current rectangle being drawn
                if (currentRect) {{
                    drawRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h, '#ff0000', '', true);
                }}
            }}
            
            function drawRect(x, y, w, h, color, label, dashed = false) {{
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                
                if (dashed) {{
                    ctx.setLineDash([5, 5]);
                }} else {{
                    ctx.setLineDash([]);
                }}
                
                ctx.strokeRect(x, y, w, h);
                
                // Draw semi-transparent fill
                ctx.fillStyle = color + '20';  // Add alpha
                ctx.fillRect(x, y, w, h);
                
                // Draw label
                if (label) {{
                    ctx.fillStyle = color;
                    ctx.font = 'bold 14px Arial';
                    ctx.fillText(label, x + 5, y + 20);
                }}
            }}
            
            canvas.addEventListener('mousedown', (e) => {{
                const rect = canvas.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
                isDrawing = true;
            }});
            
            canvas.addEventListener('mousemove', (e) => {{
                if (!isDrawing) return;
                
                const rect = canvas.getBoundingClientRect();
                const currentX = e.clientX - rect.left;
                const currentY = e.clientY - rect.top;
                
                const x = Math.min(startX, currentX);
                const y = Math.min(startY, currentY);
                const w = Math.abs(currentX - startX);
                const h = Math.abs(currentY - startY);
                
                currentRect = {{ x, y, w, h }};
                redraw();
            }});
            
            canvas.addEventListener('mouseup', (e) => {{
                if (!isDrawing) return;
                isDrawing = false;
                
                if (currentRect && currentRect.w > 5 && currentRect.h > 5) {{
                    // Convert back to original image coordinates
                    const scaledRect = {{
                        x: currentRect.x * {scale_x},
                        y: currentRect.y * {scale_y},
                        w: currentRect.w * {scale_x},
                        h: currentRect.h * {scale_y}
                    }};
                    
                    // Send to Streamlit
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        key: '{key}',
                        value: scaledRect
                    }}, '*');
                }}
                
                currentRect = null;
                redraw();
            }});
            
            canvas.addEventListener('mouseleave', () => {{
                if (isDrawing) {{
                    isDrawing = false;
                    currentRect = null;
                    redraw();
                }}
            }});
            
            // Prevent context menu on right-click
            canvas.addEventListener('contextmenu', (e) => {{
                e.preventDefault();
            }});
        </script>
    </body>
    </html>
    """
    
    # Render component
    result = components.html(component_html, height=canvas_height + 40, scrolling=False)
    
    return result


def display_page_with_regions(
    page_image: Image.Image,
    regions: list[dict],
    canvas_width: int = 1000,
    canvas_height: Optional[int] = None
) -> None:
    """Display a PDF page with regions (read-only, no interaction).
    
    Args:
        page_image: PIL Image of the PDF page
        regions: List of regions to display
        canvas_width: Width of the canvas in pixels
        canvas_height: Height of the canvas (auto-calculated if None)
    """
    # Calculate canvas height to maintain aspect ratio
    if canvas_height is None:
        aspect_ratio = page_image.height / page_image.width
        canvas_height = int(canvas_width * aspect_ratio)
    
    # Resize image to fit canvas
    display_image = page_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    img_base64 = image_to_base64(display_image)
    
    # Scale factors for converting display coords to original coords
    scale_x = page_image.width / canvas_width
    scale_y = page_image.height / canvas_height
    
    # Convert existing regions to display coordinates
    display_regions = []
    for region in regions:
        bbox = region.get("bbox", {})
        display_regions.append({
            "x": bbox.get("x", 0) / scale_x,
            "y": bbox.get("y", 0) / scale_y,
            "w": bbox.get("w", 0) / scale_x,
            "h": bbox.get("h", 0) / scale_y,
            "color": region.get("color", "#3498db"),
            "label": region.get("label", ""),
        })
    
    # HTML component (read-only)
    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
            }}
            #canvas {{
                border: 2px solid #ccc;
                display: block;
            }}
        </style>
    </head>
    <body>
        <canvas id="canvas" width="{canvas_width}" height="{canvas_height}"></canvas>
        
        <script>
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            
            const bgImage = new Image();
            bgImage.src = '{img_base64}';
            
            const regions = {display_regions};
            
            bgImage.onload = function() {{
                ctx.drawImage(bgImage, 0, 0, canvas.width, canvas.height);
                
                regions.forEach(region => {{
                    ctx.strokeStyle = region.color;
                    ctx.lineWidth = 2;
                    ctx.setLineDash([]);
                    ctx.strokeRect(region.x, region.y, region.w, region.h);
                    
                    ctx.fillStyle = region.color + '20';
                    ctx.fillRect(region.x, region.y, region.w, region.h);
                    
                    if (region.label) {{
                        ctx.fillStyle = region.color;
                        ctx.font = 'bold 14px Arial';
                        ctx.fillText(region.label, region.x + 5, region.y + 20);
                    }}
                }});
            }};
        </script>
    </body>
    </html>
    """
    
    components.html(component_html, height=canvas_height + 10, scrolling=False)

