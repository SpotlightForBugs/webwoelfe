/**
 * Webwölfe - Village Display Client
 * 
 * SICHERHEIT: Dieses Script zeigt NUR server-gerenderte Bilder an!
 * - Keine Spiellogik im Client
 * - Keine Rollen-Information verfügbar
 * - Bilder werden komplett auf dem Server gerendert
 * - Chrome DevTools Extension können KEINE Vorteile verschaffen
 */

class VillageDisplay {
    constructor(containerId, raumCode) {
        this.container = document.getElementById(containerId);
        this.raumCode = raumCode;
        this.updateInterval = null;
        this.isLoading = false;
        
        if (!this.container) {
            console.warn('Village container nicht gefunden:', containerId);
            return;
        }
        
        this.init();
    }
    
    init() {
        // Erstelle Bild-Element
        this.imgElement = document.createElement('img');
        this.imgElement.className = 'village-image';
        this.imgElement.alt = 'Dorf-Ansicht';
        this.imgElement.style.cssText = `
            width: 100%;
            height: auto;
            border-radius: 12px;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        // Loading-Indicator
        this.loadingElement = document.createElement('div');
        this.loadingElement.className = 'village-loading';
        this.loadingElement.innerHTML = `
            <div class="spinner-border text-danger" role="status">
                <span class="visually-hidden">Wird geladen...</span>
            </div>
            <p class="mt-2 text-muted">Dorf wird gerendert...</p>
        `;
        this.loadingElement.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
        `;
        
        // Error-Element
        this.errorElement = document.createElement('div');
        this.errorElement.className = 'village-error alert alert-warning';
        this.errorElement.style.display = 'none';
        
        this.container.appendChild(this.loadingElement);
        this.container.appendChild(this.imgElement);
        this.container.appendChild(this.errorElement);
        
        // Erste Ladung
        this.loadVillage();
    }
    
    /**
     * Lädt das server-gerenderte Dorf-Bild
     */
    async loadVillage() {
        if (this.isLoading || !this.raumCode) return;
        
        this.isLoading = true;
        this.showLoading(true);
        
        try {
            const response = await fetch(`/api/village/${this.raumCode}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                this.showError(data.error);
                return;
            }
            
            if (data.image) {
                this.imgElement.src = data.image;
                this.imgElement.onload = () => {
                    this.showLoading(false);
                    this.imgElement.style.opacity = '1';
                };
            }
            
            // Speichere Spielstand-Info (nur Phase/Runde, KEINE Rollen!)
            this.currentPhase = data.phase;
            this.currentRunde = data.runde;
            
        } catch (error) {
            console.error('Village laden fehlgeschlagen:', error);
            this.showError('Dorf konnte nicht geladen werden');
        } finally {
            this.isLoading = false;
        }
    }
    
    /**
     * Startet automatisches Aktualisieren
     * @param {number} intervalMs - Aktualisierungsintervall in Millisekunden
     */
    startAutoUpdate(intervalMs = 5000) {
        this.stopAutoUpdate();
        this.updateInterval = setInterval(() => this.loadVillage(), intervalMs);
    }
    
    /**
     * Stoppt automatisches Aktualisieren
     */
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    /**
     * Erzwingt sofortige Aktualisierung (z.B. nach Hinweis)
     */
    forceUpdate() {
        this.loadVillage();
    }
    
    showLoading(show) {
        this.loadingElement.style.display = show ? 'flex' : 'none';
        this.errorElement.style.display = 'none';
    }
    
    showError(message) {
        this.loadingElement.style.display = 'none';
        this.errorElement.style.display = 'block';
        this.errorElement.innerHTML = `
            <i class="fa-solid fa-exclamation-triangle me-2"></i>
            ${message}
        `;
    }
    
    /**
     * Aufräumen
     */
    destroy() {
        this.stopAutoUpdate();
    }
}

// Exportiere für globale Nutzung
window.VillageDisplay = VillageDisplay;
