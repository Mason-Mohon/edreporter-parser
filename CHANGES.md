# Changes from Streamlit to Flask Version

## Fixed Issues

### 1. ✅ Article Selection for Drawing

**Problem**: Unable to draw rectangles after creating articles
**Solution**: 
- Articles now auto-select when created
- Clear visual feedback (blue highlight + checkmark) shows selected article
- Status bar displays selected article name
- Warning message if you try to draw without selecting an article
- Articles section flashes red if you attempt to draw without selection

### 2. ✅ Unlimited Articles (Streamlit Bug Fixed!)

**Problem**: Streamlit version had a bug preventing more than 4 articles
**Solution**: 
- Complete rewrite with proper list rendering
- No artificial limits
- Scrollable list for many articles
- Each article shows region count

### 3. ✅ Responsive Canvas

**Problem**: Canvas had fixed size leaving empty space
**Solution**:
- Canvas now fills available screen space
- Responsive layout with flexbox
- Proper scaling for different screen sizes
- No wasted space

### 4. ✅ Click-and-Drag Drawing

**Problem**: Had to manually enter coordinates
**Solution**:
- Fabric.js integration for interactive canvas
- Click and drag to draw rectangles
- Real-time visual feedback while drawing
- Regions shown with colored borders

### 5. ✅ Terminal Logging

**Problem**: No debugging information
**Solution**:
- Comprehensive logging to terminal
- Timestamps on all operations
- Error tracking with stack traces
- See exactly what's happening

## UI Improvements

### Better Visual Feedback

1. **Selected Article Indication**:
   - Blue background with white text
   - Checkmark icon
   - Box shadow for emphasis
   - Status bar shows selection

2. **Article Counter**: Shows total number of articles (0-unlimited)

3. **Region Counter**: Each article shows how many regions it has

4. **Info Alert**: Reminds users to select an article before drawing

5. **Status Messages**: 
   - "Selected: A1 - Title. Draw regions on the PDF."
   - "⚠️ Select an article first before drawing regions"
   - Real-time feedback for all operations

### Drawing Experience

- Crosshair cursor over PDF
- Dashed outline while drawing
- Solid colored border when complete
- Region labels show article ID and order
- Automatic addition to selected article

## Technical Improvements

### Architecture

- **Backend**: Flask REST API (clean separation)
- **Frontend**: Vanilla JavaScript + Fabric.js
- **State Management**: Explicit, event-driven
- **No Re-rendering**: Only updates what changed

### Performance

- Fast page loads
- Instant UI updates
- Efficient canvas rendering
- No Streamlit overhead

### Stability

- No Streamlit quirks or bugs
- Predictable behavior
- Proper error handling
- Graceful degradation

## How to Use

### Drawing Regions (Fixed!)

1. **Create Article**: Click "+ New" button
2. **Article Auto-Selects**: Blue highlight shows it's selected
3. **Draw Region**: Click and drag on PDF canvas
4. **Repeat**: Create more articles, select them, draw more regions

### Visual Cues

- **Blue Highlight** = Selected article
- **Checkmark** = Selected article
- **Status Bar** = Shows current selection
- **Region Count** = Shows regions per article
- **Article Counter** = Shows total articles

### Tips

- Always check which article is selected (blue highlight)
- Status bar confirms your selection
- If drawing doesn't work, check if an article is selected
- Click any article to select it
- Articles auto-select when created

## Files Changed

### New Files

```
webapp/
├── app.py                    # Flask application
├── routes.py                 # API endpoints with logging
├── config.py                 # Configuration
├── logger.py                 # Logging setup
├── templates/
│   ├── base.html             # Base layout
│   └── index.html            # Main UI with article counter
└── static/
    ├── css/
    │   └── main.css          # Responsive styles
    └── js/
        ├── app.js            # Main app logic
        ├── canvas.js         # Drawing with warnings
        └── articles.js       # Article management (fixed!)
```

### Modified Files

- `pyproject.toml`: Changed from Streamlit to Flask dependencies
- `.gitignore`: Added Flask-specific entries

### Unchanged Files (Reused!)

All core processing modules work without changes:
- `app/core/segment_model.py`
- `app/core/storage.py`
- `app/core/pdf_io.py`
- `app/core/heuristics.py`
- `app/core/ocr.py`
- `app/core/extraction.py`
- `app/core/export_docx.py`

## Running the App

```bash
# Start Flask (with logging)
uv run flask --app webapp.app run --debug

# Open in browser
http://localhost:5000
```

## Debugging

Watch the terminal for logs:
```
[2026-01-07 10:00:00] INFO - Loading PDF list
[2026-01-07 10:00:05] INFO - Created article: A1
[2026-01-07 10:00:10] INFO - Added region to article A1
[2026-01-07 10:00:15] INFO - Saving annotations
```

Browser console also shows detailed logs:
```
[App] Initializing application
[Articles] Creating new article
[Articles] Created article: A1
[Canvas] Started drawing rectangle
[Canvas] Region added successfully
```

## Migration Notes

If you have existing annotations from Streamlit version:
- ✅ They work perfectly with Flask version
- ✅ Same JSON format
- ✅ No conversion needed
- ✅ Just load and use

## Summary

The Flask version fixes all major issues:
- ✅ Unlimited articles (no more 4-article limit!)
- ✅ Click-and-drag drawing (way easier!)
- ✅ Clear article selection (know what you're drawing!)
- ✅ Responsive layout (no wasted space!)
- ✅ Terminal logging (debug everything!)
- ✅ Better UX overall

Everything that worked before still works, but now it's faster, more stable, and has the features you requested!
