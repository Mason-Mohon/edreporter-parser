// Canvas drawing functionality using Fabric.js

class CanvasManager {
    constructor() {
        this.canvas = null;
        this.isDrawing = false;
        this.currentRect = null;
        this.regions = [];
        this.scale = 1.0;
        this.backgroundImage = null;
    }
    
    init(canvasId) {
        console.log('[Canvas] Initializing Fabric.js canvas');
        this.canvas = new fabric.Canvas(canvasId, {
            selection: false,
            hoverCursor: 'crosshair',
            defaultCursor: 'crosshair'
        });
        
        // Setup event handlers
        this.setupEventHandlers();
        
        console.log('[Canvas] Canvas initialized');
    }
    
    setupEventHandlers() {
        let origX, origY;
        
        // Mouse down - start drawing
        this.canvas.on('mouse:down', (options) => {
            // Only draw if we have a selected article
            if (!window.appState || !window.appState.selectedArticle) {
                console.warn('[Canvas] No article selected, cannot draw region');
                setStatus('⚠️ Select an article first before drawing regions', true);
                
                // Flash the articles section to draw attention
                const articlesCard = document.querySelector('#articles-list').closest('.card');
                articlesCard.style.border = '3px solid #dc3545';
                setTimeout(() => {
                    articlesCard.style.border = '';
                }, 2000);
                
                return;
            }
            
            this.isDrawing = true;
            const pointer = this.canvas.getPointer(options.e);
            origX = pointer.x;
            origY = pointer.y;
            
            const article = window.appState.annotations.articles[window.appState.selectedArticle];
            
            this.currentRect = new fabric.Rect({
                left: origX,
                top: origY,
                width: 0,
                height: 0,
                fill: 'transparent',
                stroke: article.color,
                strokeWidth: 3,
                selectable: false,
                evented: false,
                strokeDashArray: [5, 5]
            });
            
            this.canvas.add(this.currentRect);
            console.log('[Canvas] Started drawing rectangle');
        });
        
        // Mouse move - update rectangle
        this.canvas.on('mouse:move', (options) => {
            if (!this.isDrawing || !this.currentRect) return;
            
            const pointer = this.canvas.getPointer(options.e);
            
            if (pointer.x < origX) {
                this.currentRect.set({ left: pointer.x });
            }
            if (pointer.y < origY) {
                this.currentRect.set({ top: pointer.y });
            }
            
            this.currentRect.set({
                width: Math.abs(pointer.x - origX),
                height: Math.abs(pointer.y - origY)
            });
            
            this.canvas.renderAll();
        });
        
        // Mouse up - finish drawing
        this.canvas.on('mouse:up', (options) => {
            if (!this.isDrawing) return;
            
            this.isDrawing = false;
            
            if (this.currentRect && this.currentRect.width > 10 && this.currentRect.height > 10) {
                console.log('[Canvas] Rectangle drawn:', {
                    left: this.currentRect.left,
                    top: this.currentRect.top,
                    width: this.currentRect.width,
                    height: this.currentRect.height
                });
                
                // Add region to backend
                this.addRegion(this.currentRect);
            } else {
                console.log('[Canvas] Rectangle too small, discarding');
                this.canvas.remove(this.currentRect);
            }
            
            this.currentRect = null;
        });
    }
    
    async loadPage(pageImageData, width, height) {
        console.log(`[Canvas] Loading page image (${width}x${height})`);
        
        return new Promise((resolve, reject) => {
            fabric.Image.fromURL(pageImageData, (img) => {
                this.backgroundImage = img;
                
                // Set canvas size to match image
                this.canvas.setWidth(width);
                this.canvas.setHeight(height);
                
                // Set background
                this.canvas.setBackgroundImage(img, this.canvas.renderAll.bind(this.canvas), {
                    scaleX: width / img.width,
                    scaleY: height / img.height
                });
                
                console.log('[Canvas] Page loaded successfully');
                resolve();
            }, {crossOrigin: 'anonymous'});
        });
    }
    
    clearRegions() {
        // Remove all regions from canvas
        const objects = this.canvas.getObjects();
        objects.forEach(obj => {
            if (obj.type === 'rect' && obj !== this.currentRect) {
                this.canvas.remove(obj);
            }
        });
        this.regions = [];
        this.canvas.renderAll();
        console.log('[Canvas] Regions cleared');
    }
    
    drawRegions(regions) {
        this.clearRegions();
        
        console.log(`[Canvas] Drawing ${regions.length} regions`);
        
        regions.forEach(region => {
            const article = window.appState.annotations.articles[region.article_id];
            if (!article) return;
            
            const rect = new fabric.Rect({
                left: region.bbox.x,
                top: region.bbox.y,
                width: region.bbox.w,
                height: region.bbox.h,
                fill: 'transparent',
                stroke: article.color,
                strokeWidth: 2,
                selectable: false,
                evented: false
            });
            
            // Add label
            const label = new fabric.Text(`${region.article_id} (${region.order})`, {
                left: region.bbox.x + 5,
                top: region.bbox.y + 5,
                fontSize: 14,
                fill: article.color,
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                selectable: false,
                evented: false
            });
            
            this.canvas.add(rect);
            this.canvas.add(label);
            this.regions.push({ rect, label, regionId: region.region_id });
        });
        
        this.canvas.renderAll();
    }
    
    async addRegion(rect) {
        const articleId = window.appState.selectedArticle;
        const pageIndex = window.appState.currentPage;
        
        const bbox = {
            x: Math.round(rect.left),
            y: Math.round(rect.top),
            w: Math.round(rect.width),
            h: Math.round(rect.height)
        };
        
        console.log('[Canvas] Adding region:', { articleId, pageIndex, bbox });
        
        try {
            const response = await axios.post('/api/region/add', {
                annotations: window.appState.annotations,
                page_index: pageIndex,
                bbox: bbox,
                article_id: articleId
            });
            
            if (response.data.success) {
                window.appState.annotations = response.data.annotations;
                console.log('[Canvas] Region added successfully');
                
                // Redraw regions
                window.articlesManager.updateRegionsList();
                this.drawRegionsForCurrentPage();
                
                // Remove the drawing rectangle
                this.canvas.remove(rect);
            }
        } catch (error) {
            console.error('[Canvas] Error adding region:', error);
            alert('Error adding region: ' + error.message);
            this.canvas.remove(rect);
        }
    }
    
    drawRegionsForCurrentPage() {
        const pageKey = String(window.appState.currentPage);
        const pageData = window.appState.annotations.pages[pageKey];
        
        if (pageData && pageData.regions) {
            this.drawRegions(pageData.regions);
        } else {
            this.clearRegions();
        }
    }
}

// Create global instance
window.canvasManager = new CanvasManager();
