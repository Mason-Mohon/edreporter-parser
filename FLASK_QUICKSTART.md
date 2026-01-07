# Flask EdReporter Quick Start

## Running the Application

```bash
# Start the Flask development server
uv run flask --app webapp.app run --debug

# The app will be available at: http://localhost:5000
```

## What's New

### ✅ Fixed Bugs from Streamlit Version

1. **No Article Limit**: Create unlimited articles - the bug that prevented more than 4 articles is fixed
2. **Responsive Canvas**: Canvas now fills available space with no empty gaps
3. **Click and Drag**: Draw regions by clicking and dragging on the PDF
4. **Terminal Logging**: All operations logged to terminal for debugging

### Features

- **Interactive Canvas**: Click and drag to draw bounding boxes on PDF pages
- **Unlimited Articles**: No limit on number of articles (Streamlit bug is fixed!)
- **Responsive Layout**: Canvas scales to fill screen, no wasted space
- **Real-time Updates**: Changes reflect immediately
- **Terminal Logging**: See all operations in the terminal for debugging

## Workflow

### 1. Start the App

```bash
uv run flask --app webapp.app run --debug
```

Open http://localhost:5000 in your browser.

### 2. Select a PDF

- Use the dropdown at the top to select a PDF
- PDFs are organized by year
- The first page will load automatically

### 3. Create Articles

- Click **"+ New"** in the Articles section
- Enter title, subtitle, author, tags
- Choose a color for the article
- Create as many articles as you need (unlimited!)

### 4. Draw Regions

- Select an article from the list
- Click and drag on the PDF canvas to draw a rectangle
- The region is automatically assigned to the selected article
- Draw regions across multiple pages for multi-page articles

### 5. Extract Text

- Switch to the **"Extract"** tab
- Click **"Build Article Text"**
- System will use PDF text layer or OCR as needed
- Edit extracted text in the text areas

### 6. Export

- Click **"Export DOCX"** or **"Export Markdown"**
- Files are saved to `out/<year>/` directory

### 7. Save

- Click **"Save"** button to persist annotations
- Annotations auto-saved when switching PDFs

## Terminal Logging

All operations are logged to the terminal with timestamps:

```
[2026-01-06 14:00:01] INFO     edreporter.app:24 - EdReporter Flask application initialized
[2026-01-06 14:00:05] INFO     edreporter.routes:35 - Fetching PDF list
[2026-01-06 14:00:05] INFO     edreporter.routes:43 - Found 348 PDFs across 29 years
[2026-01-06 14:00:10] INFO     edreporter.routes:95 - Loading annotations for: data/1986/1986_2-Feb_EdReporter.pdf
[2026-01-06 14:00:15] INFO     edreporter.routes:156 - Creating new article
[2026-01-06 14:00:15] INFO     edreporter.routes:166 - Created article: A1
```

## Key Improvements Over Streamlit

| Feature | Streamlit | Flask |
|---------|-----------|-------|
| Article Limit | Bug: Only 4 articles | ✅ Unlimited |
| Canvas | Static size, empty space | ✅ Responsive, fills screen |
| Drawing | Manual coordinate entry | ✅ Click and drag |
| Logging | Minimal | ✅ Comprehensive terminal logs |
| Performance | Slow re-rendering | ✅ Fast, event-driven |
| Stability | Buggy | ✅ Stable |

## Debugging

Watch the terminal for detailed logging:

- PDF loading and rendering
- Article creation/updates/deletion
- Region addition/deletion
- Text extraction progress
- Export operations
- All errors with stack traces

## Troubleshooting

### Port already in use

```bash
# Kill existing process
pkill -f "flask"

# Or use a different port
uv run flask --app webapp.app run --debug --port 5001
```

### Canvas not loading

- Check browser console (F12)
- Ensure Fabric.js loaded correctly
- Check terminal for errors

### PDF not rendering

- Check file permissions on `data/` directory
- Verify PDF path is correct
- Check terminal logs for errors

### OCR not working

- Verify Tesseract is installed: `tesseract --version`
- Check terminal for OCR errors

## Development

The app runs in debug mode by default:
- Auto-reloads on code changes
- Detailed error pages
- Debug logging enabled

## Architecture

```
Browser (HTML/JS/Fabric.js)
    ↓ HTTP requests
Flask API Endpoints
    ↓ function calls
Core Modules (existing, unchanged)
    ↓ file I/O
PDFs (data/) & Outputs (out/)
```

All your existing core modules are reused without changes:
- `app/core/segment_model.py` - Data models
- `app/core/storage.py` - File I/O
- `app/core/pdf_io.py` - PDF rendering
- `app/core/extraction.py` - Text extraction & OCR
- `app/core/export_docx.py` - DOCX export

## Production Deployment

For production, use gunicorn:

```bash
uv pip install gunicorn
uv run gunicorn -w 4 -b 0.0.0.0:5000 webapp.app:app
```

## Files Created

```
webapp/
├── app.py              # Flask application
├── routes.py           # API endpoints
├── config.py           # Configuration
├── logger.py           # Logging setup
├── templates/
│   ├── base.html       # Base layout
│   └── index.html      # Main UI
└── static/
    ├── css/
    │   └── main.css    # Responsive styles
    └── js/
        ├── app.js      # Main application logic
        ├── canvas.js   # Fabric.js canvas drawing
        └── articles.js # Article management
```

Enjoy the bug-free, fully-functional Flask version! 🎉
