# EdReporter Quick Start Guide

## Prerequisites

1. **Tesseract OCR must be installed:**
   ```bash
   # Already installed on your system (verified)
   tesseract --version
   ```

2. **Dependencies installed:**
   ```bash
   uv sync
   ```

## Running the Application

```bash
uv run streamlit run app/main.py
```

The application will open in your browser at http://localhost:8501

## Workflow Overview

### 1. Select a PDF
- Use the sidebar to choose a year and PDF file
- Navigate between PDFs with Prev/Next buttons

### 2. Annotate (Segmentation)
Go to the **📝 Annotate** tab:

1. **Create Articles:**
   - Click "➕ New Article" to create a new article
   - Edit the article metadata (title, subtitle, author, tags, color)

2. **Draw Regions:**
   - Click and drag on the PDF page to draw a bounding box
   - The region will automatically be assigned to the currently selected article
   - Regions are numbered by reading order

3. **Manage Regions:**
   - View all regions on the current page in the right sidebar
   - Change reading order numbers
   - Delete regions if needed
   - Use "🔄 Auto-order regions" to sort by position

4. **Multi-page Articles:**
   - Navigate to the next page
   - Draw more regions for the same article (they'll get sequential order numbers)
   - Use "📋 Duplicate all to next page" for consistent column layouts

5. **Save:**
   - Click "💾 Save Annotations" in the sidebar
   - Annotations are auto-saved when switching PDFs

### 3. Extract & Edit
Go to the **✏️ Extract & Edit** tab:

1. **Extract Text:**
   - Click "🔄 Build Article Text"
   - The system will:
     - Try PDF text layer extraction first
     - Fall back to OCR if text quality is poor
     - Apply cleanup heuristics

2. **Review & Edit:**
   - Each article has its own tab
   - View extraction metadata (method used, quality scores)
   - Edit the text directly in the text area
   - Use "🧹 Apply Cleanup" to run heuristics again
   - Use "🔄 Re-extract" to re-run extraction

3. **Export:**
   - Choose DOCX and/or Markdown formats
   - Click "📄 Export Document"
   - Output files go to `out/<year>/`

## Output Files

For each PDF, three files are created in `out/<year>/`:

1. **`.annotations.json`** - Your segmentation data
2. **`.docx`** - Word document with all articles
3. **`.md`** - Plain text/markdown version

## Tips

- **DPI Setting:** 200 is a good default. Increase to 250-300 for better OCR quality
- **Column Layouts:** Use "Duplicate to next page" for consistent 4-column layouts
- **Reading Order:** Auto-order sorts by page → y-position → x-position
- **Quality Check:** Look at the extraction metadata to see which regions used OCR vs PDF text
- **Save Often:** Click Save Annotations periodically, especially before closing

## Example Workflow

1. Open PDF: `data/1986/1986_2-Feb_EdReporter.pdf`
2. Create article "A1" with title "School Board Controversy"
3. Draw region around first column on page 1 (order: 1)
4. Draw region around continuation on page 2 (order: 2)
5. Save annotations
6. Go to Extract & Edit
7. Build article text
8. Review and edit extracted text
9. Export DOCX

## Troubleshooting

### OCR not working
- Verify Tesseract is installed: `tesseract --version`
- Check the error message in the Extract & Edit tab

### Poor text quality
- Increase DPI in sidebar settings
- Try re-extracting individual regions
- Manually edit the text

### Canvas not responding
- Refresh the page
- Check that you've selected an article before drawing

### Annotations not saving
- Check permissions on `out/` directory
- Look for error messages in sidebar after clicking Save

## Validation

The system has been validated with your existing PDFs:
- ✓ 348 PDFs found across 29 years (1986-2014)
- ✓ PDF rendering working
- ✓ Annotation save/load working
- ✓ Tesseract OCR available
- ✓ Text extraction working
- ✓ DOCX/Markdown export working

You're ready to start processing your EdReporter PDFs!

