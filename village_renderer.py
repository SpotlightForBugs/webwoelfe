"""
Webwölfe - Server-Side Village Renderer
Rendert die 3D-Dorfszene komplett auf dem Server.
Clients erhalten nur fertige Bilder - kein Zugang zu Spielzustand!

Verwendet isometrische 2.5D-Darstellung für Performance und Ästhetik.
"""

import io
import math
import base64
import random
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import colorsys


# ============================================================================
# KONFIGURATION
# ============================================================================

VILLAGE_WIDTH = 800
VILLAGE_HEIGHT = 600
BACKGROUND_COLOR = (15, 15, 30)  # Dunkle Nacht
GROUND_COLOR = (35, 40, 50)

# Isometrische Projektion
ISO_ANGLE = 30  # Grad
ISO_SCALE_Y = 0.5  # Vertikale Kompression

# Spieler-Positionen im Kreis
CIRCLE_RADIUS = 200
CIRCLE_CENTER = (VILLAGE_WIDTH // 2, VILLAGE_HEIGHT // 2 + 50)

# Farben
FARBEN = {
    'feuer': [(255, 100, 0), (255, 150, 50), (255, 200, 100), (255, 80, 0)],
    'mond': (255, 255, 200),
    'schatten': (0, 0, 0, 150),
    'lebendig': (100, 130, 200),
    'tot': (80, 80, 90),
    'werwolf_hint': (200, 50, 50),
    'dorf_hint': (100, 200, 100),
    'mystisch': (150, 100, 200),
}


@dataclass
class SpielerVisual:
    """Visuelle Repräsentation eines Spielers"""
    id: int
    name: str
    sitzplatz: int
    ist_am_leben: bool
    # NUR öffentliche Information! Keine Rolle hier!
    aktiver_hinweis: Optional[str] = None
    hinweis_intensitaet: float = 0.0


@dataclass
class DorfSzene:
    """Komplette Dorfszene für Rendering"""
    spieler: List[SpielerVisual]
    phase: str  # 'nacht', 'tag', 'daemmerung'
    runde: int
    aktive_hinweise: Dict[int, Tuple[str, float]]  # spieler_id -> (hinweis_typ, intensität)
    wetter: str = 'klar'  # 'klar', 'nebel', 'sturm'


class VillageRenderer:
    """
    Server-Side 3D Village Renderer
    
    Rendert das Dorf komplett auf dem Server.
    Der Client erhält NUR das fertige Bild - KEINEN Zugriff auf Spielzustand!
    """
    
    def __init__(self):
        self.width = VILLAGE_WIDTH
        self.height = VILLAGE_HEIGHT
        
        # Cache für Sprites (in Produktion: Vorgeladene PNGs)
        self._sprite_cache = {}
        
        # Font für Namen (Fallback auf Default)
        try:
            self._font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self._font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            self._font = ImageFont.load_default()
            self._font_small = self._font
    
    def render_szene(self, szene: DorfSzene) -> bytes:
        """
        Rendert eine komplette Dorfszene und gibt PNG-Bytes zurück.
        
        Args:
            szene: DorfSzene mit allen öffentlichen Informationen
            
        Returns:
            PNG-Bilddaten als Bytes
        """
        # Erstelle Bild
        img = Image.new('RGBA', (self.width, self.height), BACKGROUND_COLOR + (255,))
        draw = ImageDraw.Draw(img)
        
        # 1. Himmel rendern (basierend auf Phase)
        self._render_himmel(img, draw, szene.phase)
        
        # 2. Mond/Sonne rendern
        if szene.phase == 'nacht':
            self._render_mond(img, draw)
        elif szene.phase == 'tag':
            self._render_sonne(img, draw)
        
        # 3. Boden rendern (isometrische Ellipse)
        self._render_boden(img, draw)
        
        # 4. Lagerfeuer rendern
        self._render_lagerfeuer(img, draw, szene.phase)
        
        # 5. Spieler rendern (von hinten nach vorne für korrekte Überlappung)
        spieler_sortiert = self._sortiere_spieler_fuer_rendering(szene.spieler)
        total_spieler = max(len(szene.spieler), 8)
        for spieler in spieler_sortiert:
            hinweis = szene.aktive_hinweise.get(spieler.id)
            self._render_spieler(img, draw, spieler, szene.phase, hinweis, total_spieler)
        
        # 6. Atmosphären-Effekte
        if szene.wetter == 'nebel':
            self._render_nebel(img)
        
        # 7. Overlay für Nacht
        if szene.phase == 'nacht':
            self._render_nacht_overlay(img)
        
        # In PNG konvertieren
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def render_szene_base64(self, szene: DorfSzene) -> str:
        """Rendert Szene und gibt Base64-String für HTML img src zurück"""
        png_bytes = self.render_szene(szene)
        b64 = base64.b64encode(png_bytes).decode('utf-8')
        return f"data:image/png;base64,{b64}"
    
    def _render_himmel(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert den Himmel-Gradienten"""
        if phase == 'nacht':
            # Dunkler Nachthimmel mit Sternen
            for y in range(self.height // 2):
                # Gradient von dunkelblau nach schwarz
                ratio = y / (self.height // 2)
                r = int(10 + ratio * 5)
                g = int(10 + ratio * 15)
                b = int(30 + ratio * 20)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))
            
            # Sterne
            for _ in range(50):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height // 2)
                brightness = random.randint(150, 255)
                size = random.choice([1, 1, 1, 2])
                draw.ellipse([x, y, x + size, y + size], fill=(brightness, brightness, brightness))
                
        elif phase == 'tag':
            # Heller Tageshimmel
            for y in range(self.height // 2):
                ratio = y / (self.height // 2)
                r = int(135 + ratio * 50)
                g = int(180 + ratio * 30)
                b = int(220 + ratio * 20)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        else:
            # Dämmerung
            for y in range(self.height // 2):
                ratio = y / (self.height // 2)
                r = int(80 + ratio * 100)
                g = int(50 + ratio * 80)
                b = int(100 + ratio * 50)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))
    
    def _render_mond(self, img: Image.Image, draw: ImageDraw.Draw):
        """Rendert den Mond"""
        mond_x, mond_y = self.width - 120, 80
        mond_radius = 40
        
        # Mondschein-Glow
        for i in range(20, 0, -1):
            alpha = int(30 * (1 - i / 20))
            glow_color = (255, 255, 200, alpha)
            # Erstelle temporäres Bild für Alpha-Blending
            glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse([
                mond_x - mond_radius - i * 3,
                mond_y - mond_radius - i * 3,
                mond_x + mond_radius + i * 3,
                mond_y + mond_radius + i * 3
            ], fill=glow_color)
            img.paste(Image.alpha_composite(img, glow))
        
        # Mond selbst
        draw.ellipse([
            mond_x - mond_radius, mond_y - mond_radius,
            mond_x + mond_radius, mond_y + mond_radius
        ], fill=FARBEN['mond'])
        
        # Mondkrater (dunklere Flecken)
        krater_positionen = [(mond_x - 10, mond_y - 5), (mond_x + 15, mond_y + 10), (mond_x - 5, mond_y + 15)]
        for kx, ky in krater_positionen:
            draw.ellipse([kx - 5, ky - 5, kx + 5, ky + 5], fill=(220, 220, 180))
    
    def _render_sonne(self, img: Image.Image, draw: ImageDraw.Draw):
        """Rendert die Sonne"""
        sonne_x, sonne_y = 100, 80
        sonne_radius = 35
        
        # Sonnenstrahlen
        for i in range(12):
            winkel = i * 30 * math.pi / 180
            start_x = sonne_x + math.cos(winkel) * (sonne_radius + 10)
            start_y = sonne_y + math.sin(winkel) * (sonne_radius + 10)
            end_x = sonne_x + math.cos(winkel) * (sonne_radius + 30)
            end_y = sonne_y + math.sin(winkel) * (sonne_radius + 30)
            draw.line([(start_x, start_y), (end_x, end_y)], fill=(255, 220, 100), width=3)
        
        # Sonne selbst
        draw.ellipse([
            sonne_x - sonne_radius, sonne_y - sonne_radius,
            sonne_x + sonne_radius, sonne_y + sonne_radius
        ], fill=(255, 230, 120))
    
    def _render_boden(self, img: Image.Image, draw: ImageDraw.Draw):
        """Rendert den isometrischen Boden"""
        cx, cy = CIRCLE_CENTER
        
        # Äußerer Grasbereich
        draw.ellipse([
            cx - CIRCLE_RADIUS - 80,
            cy - (CIRCLE_RADIUS + 80) * ISO_SCALE_Y,
            cx + CIRCLE_RADIUS + 80,
            cy + (CIRCLE_RADIUS + 80) * ISO_SCALE_Y
        ], fill=(40, 60, 40))
        
        # Innerer Erdbereich
        draw.ellipse([
            cx - CIRCLE_RADIUS - 20,
            cy - (CIRCLE_RADIUS + 20) * ISO_SCALE_Y,
            cx + CIRCLE_RADIUS + 20,
            cy + (CIRCLE_RADIUS + 20) * ISO_SCALE_Y
        ], fill=GROUND_COLOR)
        
        # Steinkreis um das Feuer
        for i in range(16):
            winkel = i * 22.5 * math.pi / 180
            x = cx + math.cos(winkel) * 50
            y = cy + math.sin(winkel) * 50 * ISO_SCALE_Y
            stein_groesse = random.randint(6, 10)
            draw.ellipse([
                x - stein_groesse, y - stein_groesse // 2,
                x + stein_groesse, y + stein_groesse // 2
            ], fill=(60, 60, 65))
    
    def _render_lagerfeuer(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert das Lagerfeuer"""
        cx, cy = CIRCLE_CENTER
        
        # Holzscheite
        for i in range(5):
            winkel = i * 72 * math.pi / 180
            x1 = cx + math.cos(winkel) * 15
            y1 = cy + math.sin(winkel) * 15 * ISO_SCALE_Y - 5
            x2 = cx + math.cos(winkel + 0.5) * 25
            y2 = cy + math.sin(winkel + 0.5) * 25 * ISO_SCALE_Y - 5
            draw.line([(x1, y1), (x2, y2)], fill=(80, 50, 30), width=6)
        
        # Feuer (nur nachts und in Dämmerung sichtbar)
        if phase != 'tag':
            # Flammen-Basis
            flammen_punkte = [
                (cx - 20, cy),
                (cx - 10, cy - 30),
                (cx, cy - 50),
                (cx + 10, cy - 30),
                (cx + 20, cy),
            ]
            draw.polygon(flammen_punkte, fill=(255, 100, 0))
            
            # Innere Flamme
            innere_punkte = [
                (cx - 10, cy - 5),
                (cx - 5, cy - 25),
                (cx, cy - 35),
                (cx + 5, cy - 25),
                (cx + 10, cy - 5),
            ]
            draw.polygon(innere_punkte, fill=(255, 180, 50))
            
            # Kern
            draw.ellipse([cx - 5, cy - 20, cx + 5, cy - 10], fill=(255, 255, 150))
            
            # Feuerschein auf Boden
            glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse([
                cx - 60, cy - 30,
                cx + 60, cy + 30
            ], fill=(255, 150, 50, 40))
            img.paste(Image.alpha_composite(img, glow))
    
    def _sortiere_spieler_fuer_rendering(self, spieler: List[SpielerVisual]) -> List[SpielerVisual]:
        """Sortiert Spieler von hinten nach vorne für korrekte Überlappung"""
        def y_position(s: SpielerVisual) -> float:
            winkel = (s.sitzplatz / max(len(spieler), 8)) * 2 * math.pi - math.pi / 2
            return math.sin(winkel)
        
        return sorted(spieler, key=y_position)
    
    def _render_spieler(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        spieler: SpielerVisual,
        phase: str,
        hinweis: Optional[Tuple[str, float]] = None,
        total_spieler: int = 8
    ):
        """Rendert einen einzelnen Spieler"""
        anzahl = max(total_spieler, 8)
        winkel = (spieler.sitzplatz / anzahl) * 2 * math.pi - math.pi / 2

        cx, cy = CIRCLE_CENTER
        tiefenfaktor = 0.65 + 0.35 * ((math.sin(winkel) + 1) / 2)
        radius = CIRCLE_RADIUS * (0.8 + 0.2 * tiefenfaktor)
        x = cx + math.cos(winkel) * radius
        y = cy + math.sin(winkel) * radius * ISO_SCALE_Y

        scale = 0.7 + 0.5 * tiefenfaktor
        
        # Schatten
        if spieler.ist_am_leben:
            draw.ellipse([x - 15 * scale, y + 25 * scale, x + 15 * scale, y + 35 * scale], fill=(0, 0, 0, 80))
        
        # Körper-Farbe basierend auf Zustand
        if not spieler.ist_am_leben:
            koerper_farbe = FARBEN['tot']
        else:
            koerper_farbe = FARBEN['lebendig']
        
        # Hinweis-Effekt
        if hinweis and spieler.ist_am_leben:
            hinweis_typ, intensitaet = hinweis
            koerper_farbe = self._apply_hinweis_farbe(koerper_farbe, hinweis_typ, intensitaet)
        
        if spieler.ist_am_leben:
            # Lebender Spieler - stehend
            
            # Körper (Robe)
            robe_punkte = [
                (x - 12 * scale, y + 25 * scale),  # Unten links
                (x - 15 * scale, y - 5 * scale),   # Taille links
                (x - 8 * scale, y - 25 * scale),   # Schulter links
                (x, y - 30 * scale),       # Kopf-Ansatz
                (x + 8 * scale, y - 25 * scale),   # Schulter rechts
                (x + 15 * scale, y - 5 * scale),   # Taille rechts
                (x + 12 * scale, y + 25 * scale),  # Unten rechts
            ]
            draw.polygon(robe_punkte, fill=koerper_farbe, outline=(50, 50, 60))

            # Kopf
            kopf_y = y - 40 * scale
            draw.ellipse([x - 10 * scale, kopf_y - 10 * scale, x + 10 * scale, kopf_y + 10 * scale], fill=(220, 185, 155))
            
            # Augen (schauen zum Feuer)
            feuer_richtung = math.atan2(cy - kopf_y, cx - x)
            auge_offset_x = math.cos(feuer_richtung) * 3 * scale
            draw.ellipse([x - 4 * scale + auge_offset_x, kopf_y - 2 * scale, x - 2 * scale + auge_offset_x, kopf_y + 2 * scale], fill=(40, 40, 40))
            draw.ellipse([x + 2 * scale + auge_offset_x, kopf_y - 2 * scale, x + 4 * scale + auge_offset_x, kopf_y + 2 * scale], fill=(40, 40, 40))
            
            # Hinweis-Glow um Spieler
            if hinweis:
                self._render_hinweis_effekt(img, draw, x, y, hinweis)
        else:
            # Toter Spieler - liegend
            draw.ellipse([x - 20 * scale, y + 10 * scale, x + 20 * scale, y + 30 * scale], fill=koerper_farbe)
            # X über den Augen
            draw.line([(x - 8 * scale, y + 15 * scale), (x - 2 * scale, y + 21 * scale)], fill=(100, 50, 50), width=2)
            draw.line([(x - 8 * scale, y + 21 * scale), (x - 2 * scale, y + 15 * scale)], fill=(100, 50, 50), width=2)
            draw.line([(x + 2 * scale, y + 15 * scale), (x + 8 * scale, y + 21 * scale)], fill=(100, 50, 50), width=2)
            draw.line([(x + 2 * scale, y + 21 * scale), (x + 8 * scale, y + 15 * scale)], fill=(100, 50, 50), width=2)
        
        # Name
        name_text = spieler.name[:12]  # Maximal 12 Zeichen
        bbox = draw.textbbox((0, 0), name_text, font=self._font)
        text_width = bbox[2] - bbox[0]
        
        # Hintergrund für Namen
        draw.rectangle([
            x - text_width // 2 - 3, y + 35,
            x + text_width // 2 + 3, y + 52
        ], fill=(0, 0, 0, 180))
        
        draw.text(
            (x - text_width // 2, y + 37),
            name_text,
            fill=(255, 255, 255) if spieler.ist_am_leben else (150, 150, 150),
            font=self._font
        )
    
    def _apply_hinweis_farbe(
        self, 
        basis_farbe: Tuple[int, int, int], 
        hinweis_typ: str, 
        intensitaet: float
    ) -> Tuple[int, int, int]:
        """Wendet Hinweis-Färbung auf die Basis-Farbe an"""
        hinweis_farben = {
            'augen_flackern': (200, 50, 50),
            'schatten': (30, 30, 40),
            'mond_schein': (150, 150, 220),
            'nervoes': (200, 180, 100),
            'gluehen': (150, 100, 200),
            'selbst_verdaechtigung': (220, 100, 50),
        }
        
        hinweis_farbe = hinweis_farben.get(hinweis_typ, basis_farbe)
        
        # Mische Farben basierend auf Intensität
        r = int(basis_farbe[0] * (1 - intensitaet) + hinweis_farbe[0] * intensitaet)
        g = int(basis_farbe[1] * (1 - intensitaet) + hinweis_farbe[1] * intensitaet)
        b = int(basis_farbe[2] * (1 - intensitaet) + hinweis_farbe[2] * intensitaet)
        
        return (min(255, r), min(255, g), min(255, b))
    
    def _render_hinweis_effekt(
        self, 
        img: Image.Image, 
        draw: ImageDraw.Draw, 
        x: float, 
        y: float, 
        hinweis: Tuple[str, float]
    ):
        """Rendert visuelle Hinweis-Effekte um einen Spieler"""
        hinweis_typ, intensitaet = hinweis
        
        if hinweis_typ == 'augen_flackern':
            # Rotes Glühen um Kopf
            kopf_y = y - 40
            for i in range(int(5 * intensitaet), 0, -1):
                alpha = int(50 * intensitaet * (1 - i / 5))
                glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse([
                    x - 15 - i * 3, kopf_y - 15 - i * 3,
                    x + 15 + i * 3, kopf_y + 15 + i * 3
                ], fill=(200, 50, 50, alpha))
                img.paste(Image.alpha_composite(img, glow))
                
        elif hinweis_typ == 'schatten':
            # Dunkler Schatten hinter Spieler
            schatten = Image.new('RGBA', img.size, (0, 0, 0, 0))
            schatten_draw = ImageDraw.Draw(schatten)
            schatten_draw.ellipse([
                x - 30, y - 50,
                x + 40, y + 30
            ], fill=(0, 0, 0, int(100 * intensitaet)))
            img.paste(Image.alpha_composite(img, schatten))
            
        elif hinweis_typ == 'mond_schein':
            # Bläuliches Mondlicht von oben
            beam = Image.new('RGBA', img.size, (0, 0, 0, 0))
            beam_draw = ImageDraw.Draw(beam)
            beam_punkte = [
                (x - 5, 0),
                (x + 5, 0),
                (x + 20, y + 30),
                (x - 20, y + 30),
            ]
            beam_draw.polygon(beam_punkte, fill=(150, 150, 220, int(60 * intensitaet)))
            img.paste(Image.alpha_composite(img, beam))
            
        elif hinweis_typ == 'gluehen':
            # Mystisches Glühen
            for i in range(int(8 * intensitaet), 0, -1):
                alpha = int(40 * intensitaet * (1 - i / 8))
                glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse([
                    x - 20 - i * 4, y - 30 - i * 4,
                    x + 20 + i * 4, y + 20 + i * 4
                ], fill=(150, 100, 200, alpha))
                img.paste(Image.alpha_composite(img, glow))
                
        elif hinweis_typ == 'selbst_verdaechtigung':
            # Orange/rotes warnendes Glühen
            for i in range(int(6 * intensitaet), 0, -1):
                alpha = int(60 * intensitaet * (1 - i / 6))
                glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse([
                    x - 25 - i * 3, y - 35 - i * 3,
                    x + 25 + i * 3, y + 25 + i * 3
                ], fill=(220, 100, 50, alpha))
                img.paste(Image.alpha_composite(img, glow))
    
    def _render_nebel(self, img: Image.Image):
        """Rendert Nebel-Effekt"""
        nebel = Image.new('RGBA', img.size, (0, 0, 0, 0))
        nebel_draw = ImageDraw.Draw(nebel)
        
        for _ in range(20):
            x = random.randint(0, self.width)
            y = random.randint(self.height // 2, self.height)
            w = random.randint(100, 300)
            h = random.randint(30, 80)
            alpha = random.randint(20, 50)
            nebel_draw.ellipse([x - w, y - h, x + w, y + h], fill=(150, 150, 160, alpha))
        
        nebel = nebel.filter(ImageFilter.GaussianBlur(radius=20))
        img.paste(Image.alpha_composite(img, nebel))
    
    def _render_nacht_overlay(self, img: Image.Image):
        """Rendert ein dunkles Nacht-Overlay"""
        overlay = Image.new('RGBA', img.size, (0, 0, 30, 40))
        img.paste(Image.alpha_composite(img, overlay))


# ============================================================================
# HELPER-FUNKTIONEN FÜR FLASK-INTEGRATION
# ============================================================================

_renderer = None

def get_renderer() -> VillageRenderer:
    """Singleton für den Renderer"""
    global _renderer
    if _renderer is None:
        _renderer = VillageRenderer()
    return _renderer


def render_village_for_room(raum_id: int, hinweise: Dict[int, Tuple[str, float]] = None) -> str:
    """
    Rendert das Dorf für einen Raum und gibt Base64-Bild zurück.
    
    Args:
        raum_id: ID des Raums
        hinweise: Optional - Dict von spieler_id zu (hinweis_typ, intensität)
        
    Returns:
        Base64-kodiertes PNG für HTML img src
    """
    from models import Raum, Spieler
    
    raum = Raum.query.get(raum_id)
    if not raum:
        return None
    
    # Hole alle Spieler (KEINE Rollen-Information!)
    spieler_db = Spieler.query.filter_by(raum_id=raum_id, ist_erzaehler=False).all()
    
    spieler_visuals = []
    for i, s in enumerate(spieler_db):
        spieler_visuals.append(SpielerVisual(
            id=s.id,
            name=s.name,
            sitzplatz=s.sitzplatz if s.sitzplatz is not None else i,
            ist_am_leben=s.ist_am_leben,
        ))
    
    # Bestimme Phase
    phase = 'nacht' if 'nacht' in raum.aktuelle_phase.lower() else 'tag'
    if 'daemmer' in raum.aktuelle_phase.lower():
        phase = 'daemmerung'
    
    szene = DorfSzene(
        spieler=spieler_visuals,
        phase=phase,
        runde=raum.runde,
        aktive_hinweise=hinweise or {},
    )
    
    renderer = get_renderer()
    return renderer.render_szene_base64(szene)


def generate_test_village() -> str:
    """Generiert ein Test-Bild für Entwicklung"""
    test_spieler = [
        SpielerVisual(id=1, name="Wolfgang", sitzplatz=0, ist_am_leben=True),
        SpielerVisual(id=2, name="Maria", sitzplatz=1, ist_am_leben=True),
        SpielerVisual(id=3, name="Hans", sitzplatz=2, ist_am_leben=False),
        SpielerVisual(id=4, name="Greta", sitzplatz=3, ist_am_leben=True),
        SpielerVisual(id=5, name="Friedrich", sitzplatz=4, ist_am_leben=True),
        SpielerVisual(id=6, name="Anna", sitzplatz=5, ist_am_leben=True),
        SpielerVisual(id=7, name="Klaus", sitzplatz=6, ist_am_leben=True),
        SpielerVisual(id=8, name="Sophie", sitzplatz=7, ist_am_leben=True),
    ]
    
    szene = DorfSzene(
        spieler=test_spieler,
        phase='nacht',
        runde=2,
        aktive_hinweise={
            1: ('augen_flackern', 0.7),
            4: ('schatten', 0.5),
            6: ('selbst_verdaechtigung', 0.8),
        },
    )
    
    renderer = get_renderer()
    return renderer.render_szene_base64(szene)


if __name__ == '__main__':
    # Test-Rendering
    print("Generiere Test-Bild...")
    base64_img = generate_test_village()
    
    # Speichere als HTML zum Testen
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Village Test</title></head>
    <body style="background: #222; display: flex; justify-content: center; padding: 20px;">
        <img src="{base64_img}" style="border: 2px solid #444; border-radius: 10px;">
    </body>
    </html>
    """
    
    with open('village_test.html', 'w') as f:
        f.write(html)
    
    print("Test-Bild gespeichert als village_test.html")


