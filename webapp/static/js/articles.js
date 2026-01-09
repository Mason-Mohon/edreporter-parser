// Article management functionality

class ArticlesManager {
    constructor() {
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // New article button
        document.getElementById('new-article-btn').addEventListener('click', () => {
            this.createNewArticle();
        });
        
        // Article detail inputs
        ['title', 'subtitle', 'author', 'tags', 'color'].forEach(field => {
            const input = document.getElementById(`article-${field}`);
            if (input) {
                input.addEventListener('change', () => {
                    this.updateArticleField(field, input.value);
                });
            }
        });
        
        // Delete article button
        document.getElementById('delete-article-btn').addEventListener('click', () => {
            this.deleteArticle();
        });
        
        console.log('[Articles] Event listeners setup');
    }
    
    async createNewArticle() {
        console.log('[Articles] Creating new article');
        
        try {
            const response = await axios.post('/api/article/new', {
                annotations: window.appState.annotations
            });
            
            if (response.data.success) {
                window.appState.annotations = response.data.annotations;
                window.appState.selectedArticle = response.data.article_id;
                
                console.log(`[Articles] Created article: ${response.data.article_id}`);
                
                // Update UI
                this.updateArticlesList();
                this.showArticleDetails(response.data.article_id);
                
                // Update status
                setStatus(`Article ${response.data.article_id} selected - ready to draw regions`);
                
                // Focus on title input
                setTimeout(() => {
                    document.getElementById('article-title').focus();
                }, 100);
            }
        } catch (error) {
            console.error('[Articles] Error creating article:', error);
            alert('Error creating article: ' + error.message);
        }
    }
    
    updateArticlesList() {
        const list = document.getElementById('articles-list');
        const articles = window.appState.annotations.articles;
        const count = Object.keys(articles).length;
        
        console.log(`[Articles] Updating list with ${count} articles`);
        
        // Update count badge
        document.getElementById('article-count').textContent = `(${count})`;
        
        if (count === 0) {
            list.innerHTML = `
                <div class="list-group-item text-center text-muted">
                    Click "New" to create your first article
                </div>
            `;
            return;
        }
        
        // Sort article IDs
        const sortedIds = Object.keys(articles).sort();
        
        // Build HTML (no limit - this fixes the Streamlit bug!)
        let html = '';
        sortedIds.forEach(articleId => {
            const article = articles[articleId];
            const isActive = articleId === window.appState.selectedArticle;
            
            // Count regions for this article
            let regionCount = 0;
            Object.values(window.appState.annotations.pages).forEach(page => {
                regionCount += page.regions.filter(r => r.article_id === articleId).length;
            });
            
            html += `
                <div class="list-group-item ${isActive ? 'active' : ''}" 
                     onclick="window.articlesManager.selectArticle('${articleId}')"
                     style="cursor: pointer;">
                    <div class="article-color-badge" style="background-color: ${article.color};"></div>
                    <div class="flex-grow-1">
                        <div class="article-title">${articleId}: ${article.title || '(no title)'}</div>
                        <small class="${isActive ? 'text-white-50' : 'text-muted'}">${regionCount} regions</small>
                    </div>
                    ${isActive ? '<i class="bi bi-check-circle-fill"></i>' : ''}
                </div>
            `;
        });
        
        list.innerHTML = html;
    }
    
    selectArticle(articleId) {
        console.log(`[Articles] Selecting article: ${articleId}`);
        
        window.appState.selectedArticle = articleId;
        
        // Update UI
        this.updateArticlesList();
        this.showArticleDetails(articleId);
        
        // Update status to show selected article
        const article = window.appState.annotations.articles[articleId];
        const title = article.title || '(no title)';
        setStatus(`Selected: ${articleId} - ${title}. Draw regions on the PDF.`);
    }
    
    showArticleDetails(articleId) {
        const article = window.appState.annotations.articles[articleId];
        
        if (!article) {
            document.getElementById('article-details').style.display = 'none';
            return;
        }
        
        // Show details panel
        document.getElementById('article-details').style.display = 'block';
        
        // Fill in fields
        document.getElementById('article-title').value = article.title || '';
        document.getElementById('article-subtitle').value = article.subtitle || '';
        document.getElementById('article-author').value = article.author || '';
        document.getElementById('article-tags').value = (article.tags || []).join(', ');
        document.getElementById('article-color').value = article.color || '#3498db';
        
        console.log(`[Articles] Showing details for ${articleId}`);
    }
    
    async updateArticleField(field, value) {
        const articleId = window.appState.selectedArticle;
        if (!articleId) return;
        
        console.log(`[Articles] Updating ${field} for ${articleId}`);
        
        // Process tags
        let updates = {};
        if (field === 'tags') {
            updates.tags = value.split(',').map(t => t.trim()).filter(t => t);
        } else {
            updates[field] = value;
        }
        
        try {
            const response = await axios.post('/api/article/update', {
                annotations: window.appState.annotations,
                article_id: articleId,
                updates: updates
            });
            
            if (response.data.success) {
                window.appState.annotations = response.data.annotations;
                this.updateArticlesList();
                
                // Redraw regions to reflect color change
                if (field === 'color') {
                    window.canvasManager.drawRegionsForCurrentPage();
                }
            }
        } catch (error) {
            console.error('[Articles] Error updating article:', error);
            alert('Error updating article: ' + error.message);
        }
    }
    
    async deleteArticle() {
        const articleId = window.appState.selectedArticle;
        if (!articleId) return;
        
        if (!confirm(`Delete article ${articleId} and all its regions?`)) {
            return;
        }
        
        console.log(`[Articles] Deleting article: ${articleId}`);
        
        try {
            const response = await axios.post('/api/article/delete', {
                annotations: window.appState.annotations,
                article_id: articleId
            });
            
            if (response.data.success) {
                window.appState.annotations = response.data.annotations;
                window.appState.selectedArticle = null;
                
                this.updateArticlesList();
                document.getElementById('article-details').style.display = 'none';
                
                // Redraw canvas
                window.canvasManager.drawRegionsForCurrentPage();
                this.updateRegionsList();
                
                console.log(`[Articles] Article ${articleId} deleted`);
            }
        } catch (error) {
            console.error('[Articles] Error deleting article:', error);
            alert('Error deleting article: ' + error.message);
        }
    }
    
    updateRegionsList() {
        const list = document.getElementById('regions-list');
        const pageKey = String(window.appState.currentPage);
        const pageData = window.appState.annotations.pages[pageKey];
        
        if (!pageData || !pageData.regions || pageData.regions.length === 0) {
            list.innerHTML = `
                <div class="list-group-item text-center text-muted">
                    No regions on this page
                </div>
            `;
            return;
        }
        
        console.log(`[Articles] Updating regions list: ${pageData.regions.length} regions`);
        
        let html = '';
        pageData.regions.forEach((region, idx) => {
            const article = window.appState.annotations.articles[region.article_id];
            const color = article ? article.color : '#999';
            const title = article ? article.title : 'Unknown';
            
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge region-badge" style="background-color: ${color};">
                            ${region.article_id}
                        </span>
                        <small>${title} (order: ${region.order})</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="window.articlesManager.deleteRegion('${region.region_id}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
        });
        
        list.innerHTML = html;
    }
    
    async deleteRegion(regionId) {
        if (!confirm('Delete this region?')) {
            return;
        }
        
        console.log(`[Articles] Deleting region: ${regionId}`);
        
        try {
            const response = await axios.post('/api/region/delete', {
                annotations: window.appState.annotations,
                region_id: regionId
            });
            
            if (response.data.success) {
                window.appState.annotations = response.data.annotations;
                
                // Redraw canvas
                window.canvasManager.drawRegionsForCurrentPage();
                this.updateRegionsList();
                
                console.log(`[Articles] Region ${regionId} deleted`);
            }
        } catch (error) {
            console.error('[Articles] Error deleting region:', error);
            alert('Error deleting region: ' + error.message);
        }
    }
}

// Create global instance
window.articlesManager = new ArticlesManager();
