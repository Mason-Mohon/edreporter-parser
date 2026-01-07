// Main application logic

// Global application state
window.appState = {
    pdfs: {},
    currentPdf: null,
    currentPage: 0,
    pageCount: 0,
    annotations: null,
    selectedArticle: null,
    extractedTexts: {},
    settings: {
        dpi: 200
    }
};

// Status display
function setStatus(message, isError = false) {
    const statusEl = document.getElementById('status-text');
    statusEl.textContent = message;
    statusEl.style.color = isError ? '#ff4444' : 'white';
    console.log(`[Status] ${message}`);
}

// Initialize application
async function initApp() {
    console.log('[App] Initializing application');
    setStatus('Loading...');
    
    // Initialize canvas
    window.canvasManager.init('pdf-canvas');
    
    // Setup event listeners
    setupEventListeners();
    
    // Load PDFs
    await loadPDFs();
    
    setStatus('Ready');
    console.log('[App] Application initialized');
}

function setupEventListeners() {
    // PDF selector
    document.getElementById('pdf-selector').addEventListener('change', (e) => {
        loadPDF(e.target.value);
    });
    
    // Page navigation
    document.getElementById('prev-page').addEventListener('click', () => {
        if (window.appState.currentPage > 0) {
            loadPage(window.appState.currentPage - 1);
        }
    });
    
    document.getElementById('next-page').addEventListener('click', () => {
        if (window.appState.currentPage < window.appState.pageCount - 1) {
            loadPage(window.appState.currentPage + 1);
        }
    });
    
    // Save button
    document.getElementById('save-btn').addEventListener('click', () => {
        saveAnnotations();
    });
    
    // DPI input
    document.getElementById('dpi-input').addEventListener('change', (e) => {
        window.appState.settings.dpi = parseInt(e.target.value);
        // Reload current page
        if (window.appState.currentPdf) {
            loadPage(window.appState.currentPage);
        }
    });
    
    // Extract button
    document.getElementById('extract-btn').addEventListener('click', () => {
        extractText();
    });
    
    // Export buttons
    document.getElementById('export-docx-btn').addEventListener('click', () => {
        exportFormat('docx');
    });
    
    document.getElementById('export-md-btn').addEventListener('click', () => {
        exportFormat('markdown');
    });
    
    console.log('[App] Event listeners setup');
}

async function loadPDFs() {
    console.log('[App] Loading PDF list');
    setStatus('Loading PDFs...');
    
    try {
        const response = await axios.get('/api/pdfs');
        window.appState.pdfs = response.data;
        
        // Populate selector
        const selector = document.getElementById('pdf-selector');
        selector.innerHTML = '<option value="">Select a PDF...</option>';
        
        Object.keys(response.data).sort().forEach(year => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = year;
            
            response.data[year].forEach(pdfPath => {
                const option = document.createElement('option');
                option.value = pdfPath;
                option.textContent = pdfPath.split('/').pop();
                optgroup.appendChild(option);
            });
            
            selector.appendChild(optgroup);
        });
        
        console.log(`[App] Loaded ${Object.keys(response.data).length} years of PDFs`);
    } catch (error) {
        console.error('[App] Error loading PDFs:', error);
        setStatus('Error loading PDFs', true);
    }
}

async function loadPDF(pdfPath) {
    if (!pdfPath) return;
    
    console.log(`[App] Loading PDF: ${pdfPath}`);
    setStatus('Loading PDF...');
    
    try {
        // Get PDF info
        const infoResponse = await axios.post('/api/pdf/info', { path: pdfPath });
        window.appState.currentPdf = pdfPath;
        window.appState.pageCount = infoResponse.data.page_count;
        window.appState.currentPage = 0;
        
        console.log(`[App] PDF has ${window.appState.pageCount} pages`);
        
        // Load annotations
        const annoResponse = await axios.post('/api/annotations/load', { path: pdfPath });
        window.appState.annotations = annoResponse.data;
        window.appState.selectedArticle = null;
        
        console.log(`[App] Loaded ${Object.keys(window.appState.annotations.articles).length} articles`);
        
        // Update UI
        window.articlesManager.updateArticlesList();
        
        // Load first page
        await loadPage(0);
        
        setStatus(`Loaded: ${infoResponse.data.name}`);
    } catch (error) {
        console.error('[App] Error loading PDF:', error);
        setStatus('Error loading PDF', true);
    }
}

async function loadPage(pageNum) {
    console.log(`[App] Loading page ${pageNum + 1}`);
    setStatus(`Loading page ${pageNum + 1}...`);
    
    window.appState.currentPage = pageNum;
    
    try {
        // Render page
        const response = await axios.post('/api/pdf/page', {
            path: window.appState.currentPdf,
            page: pageNum,
            dpi: window.appState.settings.dpi
        });
        
        // Load onto canvas
        await window.canvasManager.loadPage(
            response.data.image,
            response.data.width,
            response.data.height
        );
        
        // Draw existing regions
        window.canvasManager.drawRegionsForCurrentPage();
        
        // Update regions list
        window.articlesManager.updateRegionsList();
        
        // Update page controls
        updatePageControls();
        
        setStatus(`Page ${pageNum + 1} of ${window.appState.pageCount}`);
        console.log(`[App] Page ${pageNum + 1} loaded`);
    } catch (error) {
        console.error('[App] Error loading page:', error);
        setStatus('Error loading page', true);
    }
}

function updatePageControls() {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const display = document.getElementById('page-display');
    
    prevBtn.disabled = window.appState.currentPage === 0;
    nextBtn.disabled = window.appState.currentPage >= window.appState.pageCount - 1;
    display.textContent = `Page ${window.appState.currentPage + 1} / ${window.appState.pageCount}`;
}

async function saveAnnotations() {
    if (!window.appState.currentPdf || !window.appState.annotations) {
        console.warn('[App] No PDF or annotations to save');
        return;
    }
    
    console.log('[App] Saving annotations');
    setStatus('Saving...');
    
    try {
        const response = await axios.post('/api/annotations/save', {
            path: window.appState.currentPdf,
            annotations: window.appState.annotations
        });
        
        if (response.data.success) {
            setStatus('Saved successfully');
            console.log('[App] Annotations saved');
            setTimeout(() => {
                setStatus(`Page ${window.appState.currentPage + 1} of ${window.appState.pageCount}`);
            }, 2000);
        }
    } catch (error) {
        console.error('[App] Error saving annotations:', error);
        setStatus('Error saving', true);
    }
}

async function extractText() {
    if (!window.appState.currentPdf || !window.appState.annotations) {
        alert('Please load a PDF first');
        return;
    }
    
    if (Object.keys(window.appState.annotations.articles).length === 0) {
        alert('Please create at least one article with regions');
        return;
    }
    
    console.log('[App] Extracting text from all articles');
    setStatus('Extracting text...');
    
    try {
        const response = await axios.post('/api/extract', {
            path: window.appState.currentPdf,
            annotations: window.appState.annotations
        });
        
        if (response.data.success) {
            window.appState.extractedTexts = response.data.extracted;
            
            console.log(`[App] Extracted text for ${Object.keys(response.data.extracted).length} articles`);
            
            // Display extracted texts
            displayExtractedTexts();
            
            // Show export card
            document.getElementById('export-card').style.display = 'block';
            
            setStatus('Extraction complete');
        }
    } catch (error) {
        console.error('[App] Error extracting text:', error);
        setStatus('Error extracting text', true);
        alert('Error extracting text: ' + error.message);
    }
}

function displayExtractedTexts() {
    const container = document.getElementById('extracted-articles');
    
    if (Object.keys(window.appState.extractedTexts).length === 0) {
        container.innerHTML = '<div class="text-muted text-center p-3">No extracted text yet</div>';
        return;
    }
    
    let html = '';
    
    // Sort article IDs
    const sortedIds = Object.keys(window.appState.extractedTexts).sort();
    
    sortedIds.forEach(articleId => {
        const article = window.appState.annotations.articles[articleId];
        const extracted = window.appState.extractedTexts[articleId];
        
        html += `
            <div class="extracted-article">
                <div class="extracted-article-header">
                    ${articleId}: ${article.title || '(no title)'}
                </div>
                <div class="mb-2">
                    <small class="text-muted">
                        ${extracted.text.length} characters, 
                        ${extracted.regions_metadata.length} regions
                    </small>
                </div>
                <textarea class="form-control" rows="10" 
                          id="extracted-${articleId}">${extracted.text}</textarea>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Setup event listeners for text areas
    sortedIds.forEach(articleId => {
        document.getElementById(`extracted-${articleId}`).addEventListener('change', (e) => {
            window.appState.extractedTexts[articleId].text = e.target.value;
            console.log(`[App] Updated text for ${articleId}`);
        });
    });
}

async function exportFormat(format) {
    if (!window.appState.extractedTexts || Object.keys(window.appState.extractedTexts).length === 0) {
        alert('Please extract text first');
        return;
    }
    
    console.log(`[App] Exporting as ${format}`);
    setStatus(`Exporting ${format.toUpperCase()}...`);
    
    const endpoint = format === 'docx' ? '/api/export/docx' : '/api/export/markdown';
    
    try {
        const response = await axios.post(endpoint, {
            path: window.appState.currentPdf,
            annotations: window.appState.annotations,
            extracted: window.appState.extractedTexts
        });
        
        if (response.data.success) {
            console.log(`[App] Export saved to: ${response.data.path}`);
            setStatus(`Exported to ${response.data.path}`);
            alert(`Successfully exported to:\n${response.data.path}`);
        }
    } catch (error) {
        console.error(`[App] Error exporting ${format}:`, error);
        setStatus(`Error exporting ${format}`, true);
        alert(`Error exporting ${format}: ` + error.message);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOM loaded, initializing');
    initApp();
});
