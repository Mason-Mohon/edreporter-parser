Below is a **detailed design specification** you can paste into Cursor. It’s written so Cursor can implement it end-to-end with repo-wide context assumptions kept minimal.

---

## Design Spec: Human-in-the-Loop PDF Article Segmentation → OCR/Extraction → DOCX Export

### 1) Goal

Build a local app that processes **multi-column publication PDFs** (4-column layout, articles split across pages via “continued on page X”), enabling a fast **manual segmentation pass** (draw regions, assign to article IDs/colors, set reading order, enter title/subtitle), then **extract text (PDF text layer if good) or OCR crops**, present per-article editable text, and export **one .docx per PDF**.

### 2) Input/Output Requirements

#### Inputs

* Root folder: `data/`
* Structure: `data/<year>/<pdf files>.pdf` (year is a folder name, e.g., `1986`, `1991`, etc.)
* PDFs may be:

  * text-based (have selectable text) but messy (wrong column ordering)
  * image-based scans (need OCR)

#### Outputs

* For each input PDF:

  * Save a `.docx` with the **same base filename** in an output directory that mirrors the input structure:

    * Input: `data/1986/1986_3-March_EdReporter.pdf`
    * Output: `out/1986/1986_3-March_EdReporter.docx`
* Additionally save a sidecar annotation file:

  * `out/1986/1986_3-March_EdReporter.annotations.json`
* Optionally also save a plain text/markdown export (recommended for later NLP/RAG):

  * `out/1986/1986_3-March_EdReporter.md`

### 3) Non-Goals (for MVP)

* Full automatic article detection and continuation linking.
* Perfect title OCR. Titles/subtitles are typed by user.
* Automatic hyphenation/line-wrap cleanup beyond basic heuristics.

### 4) Proposed Tech Stack

#### Python + package management

* Python 3.11+ (or 3.12)
* Use **uv** for dependency management and running scripts.

#### UI

Pick one (spec assumes Streamlit for MVP speed):

* **Streamlit**: fastest to build interactive PDF viewer + annotation workflow.

  * Note: Streamlit is not great at native canvas drawing; use a component:

    * `streamlit-drawable-canvas` OR a custom HTML canvas component.

Alternative (more polished):

* **PySide6 (Qt)** for a true desktop annotation tool (more work, best UX).

This spec targets **Streamlit MVP** with a canvas annotation component.

#### PDF rendering / extraction

* `pymupdf` (fitz) for:

  * rendering pages to images
  * extracting text blocks from PDF layer
  * cropping regions precisely for OCR fallback

#### OCR

* Option A: `pytesseract` + installed Tesseract binary (simple, offline).
* Option B: `easyocr` (heavier, no external binary, decent).
* Option C: `ocrmypdf` (pipeline style; less interactive).
  MVP: **pytesseract** (explicit dependency note: user must install system tesseract).

#### DOCX export

* `python-docx`

### 5) Repository Layout

```
project_root/
  data/
    1986/
      issue1.pdf
      issue2.pdf
    1987/
      ...
  out/
    1986/
      issue1.docx
      issue1.annotations.json
      issue1.md
  app/
    main.py
    ui/
      viewer.py
      annotate.py
      editor.py
    core/
      pdf_io.py
      segment_model.py
      extraction.py
      ocr.py
      export_docx.py
      storage.py
      heuristics.py
  pyproject.toml
  README.md
```

### 6) Data Model (Annotations JSON)

Annotations are the “ground truth map” created during labeling.

**Top-level schema**

```json
{
  "schema_version": "1.0",
  "source_pdf": "data/1986/1986_3-March_EdReporter.pdf",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "pages": {
    "0": {
      "regions": [
        {
          "region_id": "uuid",
          "article_id": "A1",
          "order": 1,
          "bbox": { "x": 120, "y": 210, "w": 340, "h": 980 },
          "type": "body",
          "notes": ""
        }
      ]
    }
  },
  "articles": {
    "A1": {
      "title": "North Carolina School District Revises Sex Education Program",
      "subtitle": "",
      "author": "",
      "tags": [],
      "color": "#RRGGBB",
      "reading_hint": "top-to-bottom"
    }
  },
  "settings": {
    "dpi": 200,
    "ocr_lang": "eng",
    "prefer_pdf_text_layer": true
  }
}
```

**Notes**

* `page` keys are strings of 0-based page index.
* `bbox` coordinates are in **image pixel space** for the rendered page at chosen DPI.
* `article_id` is a short label: `A1`, `A2`, `A3`… (stable and user-friendly).
* `order` defines reading order within an article across regions/pages.

### 7) Workflow

#### 7.1 Batch selection / iteration

* App scans `data/**/**/*.pdf` where the first level under `data` is treated as `year`.
* Sidebar:

  * dropdown Year (from subfolders)
  * dropdown PDF in that year
  * “Next PDF” / “Prev PDF”
* On selecting a PDF:

  * load existing annotations if present in `out/<year>/<name>.annotations.json`
  * if not found, initialize empty annotation model

#### 7.2 Stage A: Labeling / Segmentation Mode

UI layout:

* Left: rendered page image with canvas overlay
* Right: article list + region list + metadata fields

User actions:

* Draw rectangle (region) on canvas
* Assign region to:

  * existing Article ID (hotkeys 1–9 map to recent articles)
  * or “New Article” button creates next `A#`
* Set region `order` (auto increments within article; user can edit)
* Choose `type`: body / header / footer / image-caption (MVP only uses body; keep field for future)
* Enter per-article metadata:

  * title (required for export)
  * subtitle (optional)
  * author (optional)
  * tags (optional)

UX accelerators:

* “Duplicate region to next page” (for consistent column widths)
* “Snap width” presets (4-column layout → 4 guides)
* “Auto-order” button within article (sort by page asc, y asc, x asc)

#### 7.3 Stage B: Extraction/OCR + Editing Mode

For selected PDF, user clicks:

* “Build Article Text”
  This triggers:

1. For each region in each article ordered by `order`:

   * attempt **PDF text-layer extraction** within the region:

     * use PyMuPDF to get text blocks/words within bbox
     * assemble in natural reading order (y then x)
   * compute quality heuristics:

     * if extracted text length < threshold or too many weird chars → fallback OCR
2. OCR fallback:

   * crop region image at DPI
   * run Tesseract with config tuned for column text:

     * `--psm 6` (single uniform block of text) or `--psm 4` (column)
     * allow user to switch PSM in settings
3. Concatenate region texts with separators:

   * insert newline between regions
   * optional page marker: `[p.2]` (toggle)

Then the app displays per-article:

* editable text area
* “Re-OCR selected region” button
* “Apply cleanup” button (basic heuristics)

Finally:

* “Export DOCX” (writes one docx for entire PDF)

### 8) Export Format (DOCX)

Single `.docx` per PDF containing all articles in that issue, in a consistent structure:

For each article (in Article ID order or sorted by first region page):

* Title (Heading 1)
* Subtitle (Heading 2 if present)
* Optional author line (italic)
* Body text paragraphs

Also include an appendix section:

* “Source PDF” filename
* For each article: list of (page, region bbox, extraction mode used per region: pdf_text vs ocr)

### 9) Text Cleanup Heuristics (MVP)

Implement simple, deterministic cleanup:

* Normalize whitespace:

  * collapse 3+ newlines to 2
  * trim trailing spaces
* Fix hyphenation:

  * replace `word-\nnext` → `wordnext` when both sides are letters
* Fix line breaks in paragraphs:

  * if a line ends without punctuation and next line starts lowercase → join with space
* Keep paragraph breaks when:

  * blank line exists
  * line ends with `.?!:"` etc.

### 10) Quality Heuristics (PDF text vs OCR)

Define a function `should_fallback_to_ocr(text: str) -> bool`:

* fallback if:

  * `len(text.strip()) < 40`
  * ratio of non-alphanumeric characters > 0.35
  * contains many isolated single letters (likely layout confusion)
  * contains repeated column bleed markers (e.g. many “  ” or broken words)

Store per-region extraction mode in the output model for transparency.

### 11) Configuration

Provide a simple config object with defaults:

* `DPI=200` (user adjustable; 200–300 typical)
* `PREFER_PDF_TEXT_LAYER=True`
* `TESSERACT_PSM=6`
* `OCR_LANG="eng"`
* output root = `out/`

Expose these settings in sidebar.

### 12) Implementation Details by Module

#### `core/pdf_io.py`

* `list_pdfs(data_root="data") -> dict[year, list[path]]`
* `render_page(pdf_path, page_index, dpi) -> PIL.Image`
* `extract_text_in_bbox(pdf_path, page_index, bbox_pdf_coords) -> str`

  * Careful: bbox is in image pixels; must convert to PDF coordinate space.
  * Provide conversion helpers.

#### `core/segment_model.py`

* dataclasses:

  * `BBox`, `Region`, `Article`, `AnnotationDoc`
* methods:

  * add_article()
  * add_region(page, bbox, article_id)
  * reorder_region(region_id, new_order)
  * serialize/deserialize json

#### `core/extraction.py`

* `build_article_text(annotation_doc, pdf_path) -> dict[article_id, text]`
* calls pdf text extraction first; fallback OCR.

#### `core/ocr.py`

* `ocr_image_crop(pil_image, psm, lang) -> str`
* optionally allow “re-ocr with different psm” per region.

#### `core/export_docx.py`

* `export_issue_docx(output_path, annotation_doc, article_texts)`
* uses python-docx:

  * Title as Heading 1
  * Body paragraphs split on blank lines

#### `core/storage.py`

* paths:

  * `out/<year>/<base>.annotations.json`
  * `out/<year>/<base>.docx`
* helper `ensure_out_dir(year)`

#### `ui/*`

* `viewer.py`: page navigation, zoom, render
* `annotate.py`: canvas draw, assign article, list regions
* `editor.py`: per-article editing, re-ocr buttons, export

### 13) Coordinate Systems (Critical)

You must correctly map between:

* PDF coordinate space (points, origin typically bottom-left in PDF)
* Rendered image pixel space (origin top-left)

Approach:

* Render each page at DPI via PyMuPDF.
* When user draws bbox on image (x,y,w,h) with origin top-left pixels:

  * Convert to PDF rect using the page’s transformation matrix:

    * PyMuPDF provides `page.get_pixmap(matrix=fitz.Matrix(scale, scale))`
    * Store scale used and use inverse matrix to map pixels → PDF coordinates
* Store bboxes in image space for UI; also compute and store PDF-space rect optionally for stable extraction.

MVP simplification:

* Store pixel bboxes + dpi + page size and compute mapping each run consistently.

### 14) uv Setup (pyproject + commands)

Use `uv` with a standard `pyproject.toml`.

Dependencies (suggested):

* streamlit
* streamlit-drawable-canvas (or alternative canvas component)
* pymupdf
* pillow
* pytesseract
* python-docx
* pydantic (optional but helpful)

Provide scripts:

* `uv run streamlit run app/main.py`

Also document system requirements:

* Tesseract installed and accessible on PATH (if using pytesseract)

  * Linux: `tesseract-ocr`
  * Mac: `brew install tesseract`
  * Windows: installer + PATH

### 15) Acceptance Criteria (MVP)

* App can browse `data/<year>/*.pdf` and select an issue.
* User can draw multiple regions on pages and assign them to article IDs.
* Annotations persist to `out/<year>/<base>.annotations.json` and reload correctly.
* “Build Article Text” produces per-article concatenated text using PDF text layer when clean, otherwise OCR.
* User can edit the article text before export.
* “Export DOCX” writes `out/<year>/<base>.docx` with all labeled articles.
* Running again on the same PDF reuses existing annotations.

### 16) Future Enhancements (Post-MVP)

* Auto-suggest column/region rectangles using whitespace and connected components.
* Continuation assistant:

  * detect “continued on page X” text
  * quick jump + highlight candidate blocks
* Per-article export (one docx per article) as an option.
* Better layout-aware text extraction from PDF text layer (block sorting).
* Versioning: keep `annotations.v1.json` history.

---

## Cursor Implementation Notes (important constraints)

* Prioritize correctness of coordinate mapping and persistence.
* Keep all annotation state in a single `AnnotationDoc` object stored in Streamlit session state.
* Ensure extraction is deterministic and reproducible: same DPI + same bbox mapping → same output.
* Make export transparent by recording extraction method (pdf_text vs ocr) per region.

---

If you want, I can also provide:

1. a ready-to-paste `pyproject.toml` for uv, and
2. a minimal “vertical slice” implementation plan (what files to create first, in what order) so Cursor doesn’t wander.
