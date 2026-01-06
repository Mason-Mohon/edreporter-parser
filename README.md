# EdReporter PDF Segmentation Tool

A human-in-the-loop tool for segmenting multi-column publication PDFs, extracting article text via OCR or PDF text layer, and exporting to DOCX format.

## Features

- **Manual PDF segmentation**: Draw regions on PDF pages and assign them to articles
- **Smart text extraction**: Uses PDF text layer when clean, falls back to OCR when needed
- **Article management**: Organize articles with titles, subtitles, authors, and tags
- **DOCX export**: Generate well-formatted Word documents with all articles
- **Persistent annotations**: Save and reload your work as JSON files

## Prerequisites

### System Requirements

1. **Python 3.13+**
2. **Tesseract OCR** (required for OCR functionality)

#### Installing Tesseract

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Linux (Arch):**
```bash
sudo pacman -S tesseract
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
Add Tesseract to your PATH after installation.

Verify installation:
```bash
tesseract --version
```

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory

2. **Install dependencies using uv:**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

## Usage

### Running the Application

```bash
uv run streamlit run app/main.py
```

The app will open in your default web browser (usually at http://localhost:8501).

### Workflow

1. **Select a PDF**:
   - Choose a year from the dropdown
   - Select a PDF file from that year
   - Existing annotations will be loaded automatically

2. **Annotate (Segmentation)**:
   - Switch to the "Annotate" tab
   - Draw rectangles on the PDF to define article regions
   - Assign regions to articles (create new articles as needed)
   - Enter article metadata (title, subtitle, author, tags)
   - Set reading order for regions
   - Save annotations frequently

3. **Extract & Edit**:
   - Switch to the "Extract & Edit" tab
   - Click "Build Article Text" to extract text from all regions
   - Review and edit extracted text for each article
   - Apply cleanup heuristics if needed
   - Re-OCR individual regions if text quality is poor

4. **Export**:
   - Click "Export DOCX" to generate a Word document
   - Output will be saved to `out/<year>/<filename>.docx`
   - A markdown version is also generated for reference

## Directory Structure

```
edreporter/
├── data/              # Input PDFs organized by year
│   ├── 1986/
│   ├── 1987/
│   └── ...
├── out/               # Output directory (auto-created)
│   ├── 1986/
│   │   ├── issue.docx
│   │   ├── issue.annotations.json
│   │   └── issue.md
│   └── ...
├── app/               # Application code
│   ├── main.py        # Streamlit entry point
│   ├── core/          # Core logic modules
│   └── ui/            # UI components
└── pyproject.toml     # Dependencies
```

## Configuration

Settings can be adjusted in the sidebar:

- **DPI**: Rendering resolution (default: 200, recommended: 150-300)
- **OCR Language**: Tesseract language code (default: eng)
- **Tesseract PSM**: Page segmentation mode (default: 6)
  - PSM 4: Single column of text
  - PSM 6: Uniform block of text
- **Prefer PDF Text Layer**: Try PDF text extraction before OCR (default: True)

## Output Files

For each processed PDF, the following files are generated:

1. **`.docx`**: Word document with all articles
2. **`.annotations.json`**: Annotation data (regions, articles, metadata)
3. **`.md`**: Plain text/markdown export (optional)

## Troubleshooting

### "Tesseract not found" error
Ensure Tesseract is installed and available in your PATH. Test with:
```bash
tesseract --version
```

### Poor OCR quality
- Increase DPI (try 250-300)
- Try different Tesseract PSM modes
- Ensure the PDF region is precisely drawn around the text

### Coordinate mapping issues
- Keep DPI consistent between annotation and extraction
- Save annotations before switching DPI settings
- Reload annotations after changing DPI

### Application not starting
- Ensure Python 3.13+ is installed: `python --version`
- Verify all dependencies are installed: `uv sync`
- Check for port conflicts (default port 8501)

## Development

Run with hot reload for development:
```bash
uv run streamlit run app/main.py --server.runOnSave true
```

## License

[Specify your license here]

## Contributing

[Specify contribution guidelines if applicable]

