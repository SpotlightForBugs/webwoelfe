"""
Webwölfe - Server-Side Village Renderer
Rendert die 3D-Dorfszene komplett auf dem Server.
Clients erhalten nur fertige Bilder - kein Zugang zu Spielzustand!

Verwendet isometrische 2.5D-Darstellung für Performance und Ästhetik.
Mit wunderschöner Grafik für ein mittelalterliches Dorf bei Nacht.
"""

import io
import math
import base64
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import colorsys


# ============================================================================
# KONFIGURATION
# ============================================================================

VILLAGE_WIDTH = 1000
VILLAGE_HEIGHT = 700
BACKGROUND_COLOR = (12, 10, 25)  # Tiefe Nachthimmel

# Isometrische Projektion
ISO_ANGLE = 30  # Grad
ISO_SCALE_Y = 0.5  # Vertikale Kompression

# Spieler-Positionen im Kreis
CIRCLE_RADIUS = 240
CIRCLE_CENTER = (VILLAGE_WIDTH // 2, VILLAGE_HEIGHT // 2 + 60)

# Wunderschöne Farbpalette
FARBEN = {
    # Himmel & Atmosphäre
    "nacht_himmel": [(8, 6, 20), (15, 12, 35), (25, 20, 50)],
    "tag_himmel": [(135, 180, 220), (180, 210, 240), (220, 235, 255)],
    "daemmerung_himmel": [(80, 50, 100), (120, 70, 100), (180, 100, 80)],
    "sterne": [(255, 255, 255), (255, 250, 220), (200, 220, 255)],
    # Feuer & Licht
    "feuer_kern": (255, 255, 200),
    "feuer_innen": (255, 200, 50),
    "feuer_mitte": (255, 130, 30),
    "feuer_aussen": (200, 60, 10),
    "feuer_glut": (180, 40, 10),
    # Boden & Vegetation
    "gras_dunkel": (25, 45, 25),
    "gras_hell": (35, 60, 35),
    "erde": (45, 35, 30),
    "erde_dunkel": (35, 28, 25),
    "steine": [(60, 55, 55), (70, 65, 60), (55, 50, 50)],
    # Mond
    "mond": (255, 252, 230),
    "mond_glow": (255, 255, 220, 80),
    "mond_krater": (220, 215, 200),
    # Sonne
    "sonne": (255, 240, 180),
    "sonne_glow": (255, 220, 100),
    # Charaktere
    "haut_hell": (240, 210, 180),
    "haut_mittel": (220, 185, 155),
    "haut_dunkel": (180, 140, 110),
    "haare_braun": (80, 50, 30),
    "haare_blond": (220, 180, 100),
    "haare_schwarz": (30, 25, 25),
    "haare_grau": (150, 145, 140),
    "haare_rot": (160, 60, 40),
    # Kleidung nach Team/Rolle
    "kleidung_dorf": (80, 100, 140),
    "kleidung_werwolf": (100, 40, 40),
    "kleidung_seherin": (100, 60, 150),
    "kleidung_hexe": (40, 100, 60),
    "kleidung_heiler": (60, 140, 100),
    "kleidung_jaeger": (140, 100, 50),
    "kleidung_amor": (200, 80, 120),
    "kleidung_neutral": (90, 85, 80),
    # Status-Effekte
    "tot": (80, 75, 70),
    "werwolf_aura": (180, 30, 30, 60),
    "dorf_aura": (60, 140, 60, 50),
    "seherin_aura": (140, 80, 200, 60),
    "mystisch": (150, 100, 200),
    # Schatten
    "schatten": (0, 0, 0, 100),
    "schatten_stark": (0, 0, 0, 150),
}

# Rollen-spezifische Farben und Icons
ROLLEN_FARBEN = {
    "werwolf": ((180, 40, 40), "🐺"),
    "seherin": ((120, 80, 180), "👁️"),
    "hexe": ((50, 130, 70), "🧪"),
    "heiler": ((60, 160, 100), "💚"),
    "jaeger": ((160, 110, 40), "🎯"),
    "jäger": ((160, 110, 40), "🎯"),
    "amor": ((220, 90, 130), "💕"),
    "dorfbewohner": ((90, 120, 160), "🏠"),
    "vampir": ((80, 40, 120), "🧛"),
    "zombie": ((70, 80, 70), "🧟"),
    "engel": ((240, 220, 160), "😇"),
    "henker": ((60, 50, 50), "⚔️"),
    "medium": ((100, 80, 180), "🔮"),
    "bürgermeister": ((180, 140, 50), "👑"),
    "buergermeister": ((180, 140, 50), "👑"),
    "prostituierte": ((220, 120, 160), "💋"),
    "leibwächter": ((100, 100, 110), "🛡️"),
    "leibwaechter": ((100, 100, 110), "🛡️"),
    "alter_mann": ((120, 110, 100), "👴"),
    "dorfdepp": ((140, 100, 180), "🤪"),
    "erzähler": ((200, 160, 60), "📖"),
    "erzaehler": ((200, 160, 60), "📖"),
}


@dataclass
class SpielerVisual:
    """Visuelle Repräsentation eines Spielers"""

    id: int
    name: str
    sitzplatz: int
    ist_am_leben: bool
    # Rollen-Info für visuelle Darstellung (optional)
    rolle: Optional[str] = None
    team: Optional[str] = None
    # Sichtbar für diesen Spieler?
    sichtbar_als_werwolf: bool = False  # Für andere Werwölfe
    sichtbar_als_dorf: bool = False  # Von Seherin als Dorf enthüllt
    sichtbar_als_boese: bool = False  # Von Seherin als böse enthüllt
    ist_verliebt: bool = False  # Von Amor verkuppelt
    ist_geschuetzt: bool = False  # Vom Heiler geschützt
    # Hinweise
    aktiver_hinweis: Optional[str] = None
    hinweis_intensitaet: float = 0.0
    # Charakter-Aussehen (zufällig generiert pro Spieler)
    haar_farbe: Optional[str] = None
    haut_farbe: Optional[str] = None
    geschlecht: Optional[str] = None


@dataclass
class DorfSzene:
    """Komplette Dorfszene für Rendering"""

    spieler: List[SpielerVisual]
    phase: str  # 'nacht', 'tag', 'daemmerung'
    runde: int
    aktive_hinweise: Dict[
        int, Tuple[str, float]
    ]  # spieler_id -> (hinweis_typ, intensität)
    wetter: str = "klar"  # 'klar', 'nebel', 'sturm'
    # Der Spieler, der diese Szene sieht (für Werwolf-Sicht etc.)
    betrachter_id: Optional[int] = None
    betrachter_rolle: Optional[str] = None
    betrachter_team: Optional[str] = None


class VillageRenderer:
    """
    Server-Side Village Renderer

    Rendert das Dorf mit wunderschöner Grafik.
    Jede Rolle bekommt einen einzigartigen Charakter.
    Der Client erhält NUR das fertige Bild.
    """

    def __init__(self):
        self.width = VILLAGE_WIDTH
        self.height = VILLAGE_HEIGHT

        # Cache für generierte Charakter-Eigenschaften
        self._charakter_cache = {}

        # Font für Namen
        try:
            self._font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14
            )
            self._font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11
            )
            self._font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
            )
        except:
            try:
                self._font = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", 14
                )
                self._font_small = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", 11
                )
                self._font_large = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", 16
                )
            except:
                self._font = ImageFont.load_default()
                self._font_small = self._font
                self._font_large = self._font

    def _get_charakter_eigenschaften(self, spieler_id: int) -> Dict:
        """Generiert konsistente Charakter-Eigenschaften basierend auf Spieler-ID"""
        if spieler_id not in self._charakter_cache:
            random.seed(spieler_id * 12345)
            self._charakter_cache[spieler_id] = {
                "haar_farbe": random.choice(
                    ["braun", "blond", "schwarz", "grau", "rot"]
                ),
                "haut_ton": random.choice(["hell", "mittel", "dunkel"]),
                "geschlecht": random.choice(["m", "w"]),
                "haar_stil": random.randint(0, 3),
                "koerper_typ": random.choice(["normal", "breit", "schlank"]),
            }
            random.seed()  # Reset random
        return self._charakter_cache[spieler_id]

    def render_szene(self, szene: DorfSzene) -> bytes:
        """
        Rendert eine komplette Dorfszene und gibt PNG-Bytes zurück.
        """
        # Erstelle Bild mit RGBA für Transparenz-Effekte
        img = Image.new("RGBA", (self.width, self.height), BACKGROUND_COLOR + (255,))
        draw = ImageDraw.Draw(img)

        # 1. Himmel rendern (mit Sternen bei Nacht)
        self._render_himmel(img, draw, szene.phase)

        # 2. Hügel und Landschaft im Hintergrund
        self._render_landschaft(img, draw, szene.phase)

        # 3. Mond/Sonne rendern
        if szene.phase == "nacht":
            self._render_mond(img, draw)
        elif szene.phase == "tag":
            self._render_sonne(img, draw)
        else:
            self._render_daemmerung_licht(img, draw)

        # 4. Bäume im Hintergrund
        self._render_baeume(img, draw, szene.phase)

        # 5. Boden/Dorfplatz rendern
        self._render_boden(img, draw, szene.phase)

        # 6. Kleine Häuser im Hintergrund
        self._render_haeuser(img, draw, szene.phase)

        # 7. Lagerfeuer rendern
        self._render_lagerfeuer(img, draw, szene.phase)

        # 8. Spieler rendern (von hinten nach vorne)
        spieler_sortiert = self._sortiere_spieler_fuer_rendering(szene.spieler)
        total_spieler = max(len(szene.spieler), 8)
        for spieler in spieler_sortiert:
            hinweis = szene.aktive_hinweise.get(spieler.id)
            self._render_spieler_charakter(
                img, draw, spieler, szene, hinweis, total_spieler
            )

        # 9. Atmosphären-Effekte
        if szene.wetter == "nebel":
            self._render_nebel(img)

        # 10. Finales Overlay
        if szene.phase == "nacht":
            self._render_nacht_overlay(img)

        # In PNG konvertieren
        buffer = io.BytesIO()
        # Convert to RGB for final output (remove alpha)
        final_img = Image.new("RGB", img.size, (0, 0, 0))
        final_img.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        final_img.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    def render_szene_base64(self, szene: DorfSzene) -> str:
        """Rendert Szene und gibt Base64-String für HTML img src zurück"""
        png_bytes = self.render_szene(szene)
        b64 = base64.b64encode(png_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    def _render_himmel(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert wunderschönen Himmel mit Gradient und Details"""
        horizon_y = int(self.height * 0.55)

        if phase == "nacht":
            # Wunderschöner Nachthimmel mit Gradient
            for y in range(horizon_y):
                ratio = y / horizon_y
                # Von tiefem Schwarz-Blau zu leichterem Dunkelblau
                r = int(8 + ratio * 15)
                g = int(6 + ratio * 12)
                b = int(20 + ratio * 30)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))

            # Milchstraße (diagonaler Streifen mit schwachem Glow)
            milky = Image.new("RGBA", img.size, (0, 0, 0, 0))
            milky_draw = ImageDraw.Draw(milky)
            for _ in range(300):
                x = random.randint(0, self.width)
                y = random.randint(0, horizon_y)
                # Dichter in diagonalem Band
                if abs(y - (x * 0.4)) < 80:
                    alpha = random.randint(20, 60)
                    milky_draw.ellipse(
                        [x - 1, y - 1, x + 1, y + 1], fill=(200, 200, 255, alpha)
                    )
            img.paste(Image.alpha_composite(img, milky))

            # Sterne - verschiedene Größen und Helligkeit
            for _ in range(150):
                x = random.randint(0, self.width)
                y = random.randint(0, horizon_y - 20)
                star_type = random.random()

                if star_type < 0.6:  # Kleine Sterne
                    brightness = random.randint(150, 255)
                    draw.point((x, y), fill=(brightness, brightness, brightness))
                elif star_type < 0.9:  # Mittlere Sterne
                    brightness = random.randint(180, 255)
                    color = random.choice(FARBEN["sterne"])
                    draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=color)
                else:  # Große funkelnde Sterne
                    brightness = random.randint(220, 255)
                    # Stern mit Strahlen
                    draw.line(
                        [(x - 3, y), (x + 3, y)],
                        fill=(brightness, brightness, brightness, 180),
                    )
                    draw.line(
                        [(x, y - 3), (x, y + 3)],
                        fill=(brightness, brightness, brightness, 180),
                    )
                    draw.ellipse([x - 1, y - 1, x + 2, y + 2], fill=(255, 255, 250))

        elif phase == "tag":
            # Schöner blauer Tageshimmel
            for y in range(horizon_y):
                ratio = y / horizon_y
                r = int(135 + ratio * 85)
                g = int(180 + ratio * 55)
                b = int(235 + ratio * 20)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))

            # Leichte Wolken
            for _ in range(5):
                cx = random.randint(50, self.width - 50)
                cy = random.randint(30, horizon_y // 2)
                for _ in range(random.randint(3, 6)):
                    ox = random.randint(-40, 40)
                    oy = random.randint(-15, 15)
                    w = random.randint(30, 60)
                    h = random.randint(15, 30)
                    draw.ellipse(
                        [cx + ox - w, cy + oy - h, cx + ox + w, cy + oy + h],
                        fill=(255, 255, 255, 30),
                    )
        else:
            # Dämmerung - Orange/Lila Gradient
            for y in range(horizon_y):
                ratio = y / horizon_y
                if ratio < 0.5:
                    # Oberer Teil: Dunkelblau zu Lila
                    r = int(40 + ratio * 100)
                    g = int(30 + ratio * 50)
                    b = int(80 + ratio * 40)
                else:
                    # Unterer Teil: Lila zu Orange
                    sub_ratio = (ratio - 0.5) * 2
                    r = int(90 + sub_ratio * 120)
                    g = int(55 + sub_ratio * 60)
                    b = int(100 - sub_ratio * 40)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))

    def _render_mond(self, img: Image.Image, draw: ImageDraw.Draw):
        """Rendert einen wunderschönen detaillierten Mond"""
        mond_x, mond_y = self.width - 140, 90
        mond_radius = 50

        # Äußerer Mondschein-Halo (mehrere Schichten)
        for i in range(30, 0, -1):
            alpha = int(40 * (1 - i / 30))
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_color = (255, 255, 220, alpha)
            r = mond_radius + i * 4
            glow_draw.ellipse(
                [mond_x - r, mond_y - r, mond_x + r, mond_y + r],
                fill=glow_color,
            )
            img.paste(Image.alpha_composite(img, glow))

        # Mond-Körper mit Gradient
        for i in range(mond_radius, 0, -1):
            ratio = i / mond_radius
            r = int(255 - (1 - ratio) * 15)
            g = int(252 - (1 - ratio) * 20)
            b = int(230 - (1 - ratio) * 30)
            draw.ellipse(
                [mond_x - i, mond_y - i, mond_x + i, mond_y + i],
                fill=(r, g, b),
            )

        # Mondkrater (realistischer)
        krater_daten = [
            (mond_x - 15, mond_y - 10, 12, 0.15),
            (mond_x + 20, mond_y + 15, 10, 0.12),
            (mond_x - 5, mond_y + 20, 8, 0.10),
            (mond_x + 10, mond_y - 15, 6, 0.08),
            (mond_x - 25, mond_y + 5, 5, 0.08),
        ]
        for kx, ky, size, darkness in krater_daten:
            # Krater-Schatten
            shade = int(255 * (1 - darkness))
            draw.ellipse(
                [kx - size, ky - size, kx + size, ky + size],
                fill=(shade, shade - 5, shade - 15),
            )
            # Krater-Highlight am Rand
            draw.arc(
                [kx - size + 1, ky - size + 1, kx + size - 1, ky + size - 1],
                200,
                340,
                fill=(255, 252, 240),
                width=1,
            )

    def _render_sonne(self, img: Image.Image, draw: ImageDraw.Draw):
        """Rendert eine strahlende Sonne"""
        sonne_x, sonne_y = 120, 100
        sonne_radius = 45

        # Sonnenschein-Glow
        for i in range(25, 0, -1):
            alpha = int(60 * (1 - i / 25))
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse(
                [
                    sonne_x - sonne_radius - i * 5,
                    sonne_y - sonne_radius - i * 5,
                    sonne_x + sonne_radius + i * 5,
                    sonne_y + sonne_radius + i * 5,
                ],
                fill=(255, 220, 100, alpha),
            )
            img.paste(Image.alpha_composite(img, glow))

        # Sonnenstrahlen (dynamisch)
        for i in range(16):
            winkel = i * 22.5 * math.pi / 180
            # Alternierende Strahlenlängen
            laenge = sonne_radius + (40 if i % 2 == 0 else 25)
            start_r = sonne_radius + 5
            start_x = sonne_x + math.cos(winkel) * start_r
            start_y = sonne_y + math.sin(winkel) * start_r
            end_x = sonne_x + math.cos(winkel) * laenge
            end_y = sonne_y + math.sin(winkel) * laenge
            draw.line(
                [(start_x, start_y), (end_x, end_y)],
                fill=(255, 230, 120),
                width=3 if i % 2 == 0 else 2,
            )

        # Sonne selbst mit Gradient
        for i in range(sonne_radius, 0, -1):
            ratio = i / sonne_radius
            r = 255
            g = int(240 - (1 - ratio) * 30)
            b = int(180 - (1 - ratio) * 80)
            draw.ellipse(
                [sonne_x - i, sonne_y - i, sonne_x + i, sonne_y + i],
                fill=(r, g, b),
            )

    def _render_daemmerung_licht(self, img: Image.Image, draw: ImageDraw.Draw):
        """Rendert Dämmerungslicht am Horizont"""
        horizon_y = int(self.height * 0.55)

        # Glühender Horizont
        for i in range(40, 0, -1):
            alpha = int(40 * (1 - i / 40))
            y = horizon_y - 20
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse(
                [
                    self.width // 2 - 200 - i * 5,
                    y - i * 2,
                    self.width // 2 + 200 + i * 5,
                    y + i * 3,
                ],
                fill=(255, 150, 80, alpha),
            )
            img.paste(Image.alpha_composite(img, glow))

    def _render_landschaft(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert sanfte Hügel im Hintergrund"""
        horizon_y = int(self.height * 0.55)

        # Farben basierend auf Phase
        if phase == "nacht":
            huegel_farben = [(25, 30, 35), (20, 25, 30), (15, 20, 25)]
        elif phase == "tag":
            huegel_farben = [(80, 120, 80), (60, 100, 60), (45, 85, 50)]
        else:
            huegel_farben = [(60, 50, 55), (50, 40, 45), (40, 35, 40)]

        # Mehrere Hügelschichten
        for layer, farbe in enumerate(huegel_farben):
            offset = layer * 25
            punkte = [(0, horizon_y + offset)]

            # Sanfte Kurve für Hügel
            for x in range(0, self.width + 50, 50):
                h = math.sin(x * 0.008 + layer * 2) * 30 + math.sin(x * 0.015) * 15
                punkte.append((x, horizon_y + offset - 40 - h))

            punkte.append((self.width, horizon_y + offset))
            punkte.append((self.width, self.height))
            punkte.append((0, self.height))

            draw.polygon(punkte, fill=farbe)

    def _render_baeume(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert Silhouetten von Bäumen"""
        horizon_y = int(self.height * 0.55)

        if phase == "nacht":
            baum_farbe = (15, 18, 22)
        elif phase == "tag":
            baum_farbe = (35, 55, 35)
        else:
            baum_farbe = (30, 25, 30)

        # Bäume links und rechts
        baum_positionen = [
            (30, horizon_y + 30, 50, 80),
            (80, horizon_y + 20, 40, 70),
            (self.width - 50, horizon_y + 25, 45, 75),
            (self.width - 100, horizon_y + 35, 35, 60),
        ]

        for x, y, breite, hoehe in baum_positionen:
            # Baumkrone (Dreieck)
            punkte = [
                (x, y - hoehe),
                (x - breite // 2, y),
                (x + breite // 2, y),
            ]
            draw.polygon(punkte, fill=baum_farbe)
            # Stamm
            draw.rectangle(
                [x - 5, y, x + 5, y + 20],
                fill=(40, 30, 25) if phase != "nacht" else (20, 18, 18),
            )

    def _render_haeuser(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert wunderschöne mittelalterliche Häuser im Hintergrund"""
        horizon_y = int(self.height * 0.55)

        if phase == "nacht":
            wand_farbe = (50, 45, 40)
            wand_akzent = (60, 55, 50)
            dach_farbe = (65, 40, 35)
            dach_dunkel = (50, 30, 25)
            fenster_farbe = (255, 200, 100)  # Warmes Licht
            schornstein_farbe = (60, 50, 45)
        elif phase == "tag":
            wand_farbe = (200, 180, 150)
            wand_akzent = (180, 160, 130)
            dach_farbe = (140, 70, 55)
            dach_dunkel = (120, 55, 45)
            fenster_farbe = (140, 160, 180)
            schornstein_farbe = (100, 90, 85)
        else:
            wand_farbe = (120, 100, 85)
            wand_akzent = (100, 85, 75)
            dach_farbe = (100, 55, 45)
            dach_dunkel = (80, 45, 35)
            fenster_farbe = (255, 190, 100)
            schornstein_farbe = (80, 70, 65)

        # Mehr Häuser, größer und verteilt
        haus_positionen = [
            # (x, y, breite, hoehe, hat_schornstein, num_fenster)
            (120, horizon_y + 50, 70, 55, True, 2),
            (230, horizon_y + 70, 55, 45, False, 1),
            (self.width - 120, horizon_y + 50, 65, 50, True, 2),
            (self.width - 230, horizon_y + 65, 50, 42, False, 1),
            (self.width // 2 - 180, horizon_y + 40, 60, 48, True, 1),
            (self.width // 2 + 180, horizon_y + 45, 55, 45, False, 1),
        ]

        for x, y, breite, hoehe, hat_schornstein, num_fenster in haus_positionen:
            # Schatten
            schatten = Image.new("RGBA", img.size, (0, 0, 0, 0))
            schatten_draw = ImageDraw.Draw(schatten)
            schatten_draw.ellipse(
                [x - breite // 2 - 5, y + 2, x + breite // 2 + 5, y + 15],
                fill=(0, 0, 0, 40),
            )
            img.paste(Image.alpha_composite(img, schatten))

            # Wand mit Fachwerk-Effekt
            draw.rectangle(
                [x - breite // 2, y - hoehe, x + breite // 2, y], fill=wand_farbe
            )

            # Fachwerk-Balken
            balken_farbe = (50, 35, 30) if phase != "tag" else (80, 55, 45)
            # Horizontaler Balken
            draw.rectangle(
                [
                    x - breite // 2,
                    y - hoehe // 2 - 2,
                    x + breite // 2,
                    y - hoehe // 2 + 2,
                ],
                fill=balken_farbe,
            )
            # Vertikale Balken
            draw.rectangle(
                [x - breite // 2, y - hoehe, x - breite // 2 + 4, y], fill=balken_farbe
            )
            draw.rectangle(
                [x + breite // 2 - 4, y - hoehe, x + breite // 2, y], fill=balken_farbe
            )
            # Diagonale Kreuz-Balken (vereinfacht als Linien)
            draw.line(
                [(x - breite // 2, y - hoehe), (x, y - hoehe // 2)],
                fill=balken_farbe,
                width=2,
            )
            draw.line(
                [(x + breite // 2, y - hoehe), (x, y - hoehe // 2)],
                fill=balken_farbe,
                width=2,
            )

            # Dach mit Schichten-Effekt
            dach_hoehe = 30 + hoehe // 4
            dach_punkte = [
                (x - breite // 2 - 12, y - hoehe),
                (x, y - hoehe - dach_hoehe),
                (x + breite // 2 + 12, y - hoehe),
            ]
            draw.polygon(dach_punkte, fill=dach_farbe)
            # Dach-Schattenseite
            dach_schatten = [
                (x, y - hoehe - dach_hoehe),
                (x + breite // 2 + 12, y - hoehe),
                (x + breite // 2 + 8, y - hoehe),
                (x, y - hoehe - dach_hoehe + 5),
            ]
            draw.polygon(dach_schatten, fill=dach_dunkel)

            # Schornstein
            if hat_schornstein:
                sx = x + breite // 4
                draw.rectangle(
                    [sx - 6, y - hoehe - dach_hoehe + 8, sx + 6, y - hoehe - 5],
                    fill=schornstein_farbe,
                )
                # Rauch bei Nacht
                if phase == "nacht":
                    rauch = Image.new("RGBA", img.size, (0, 0, 0, 0))
                    rauch_draw = ImageDraw.Draw(rauch)
                    for i in range(3):
                        ry = y - hoehe - dach_hoehe - 5 - i * 12
                        rx = sx + i * 3
                        rauch_draw.ellipse(
                            [rx - 5 - i * 2, ry - 4, rx + 5 + i * 2, ry + 4],
                            fill=(180, 180, 180, 40 - i * 10),
                        )
                    img.paste(Image.alpha_composite(img, rauch))

            # Fenster mit warmem Licht
            fenster_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            fenster_draw = ImageDraw.Draw(fenster_layer)

            if num_fenster >= 1:
                # Erstes Fenster
                fx = x - breite // 4 if num_fenster > 1 else x
                fenster_draw.rectangle(
                    [fx - 8, y - hoehe + 12, fx + 8, y - hoehe + 28],
                    fill=fenster_farbe + (220,),
                )
                # Fensterkreuz
                draw.line(
                    [(fx, y - hoehe + 12), (fx, y - hoehe + 28)],
                    fill=balken_farbe,
                    width=1,
                )
                draw.line(
                    [(fx - 8, y - hoehe + 20), (fx + 8, y - hoehe + 20)],
                    fill=balken_farbe,
                    width=1,
                )

                # Lichtschein bei Nacht
                if phase == "nacht":
                    for glow in range(3, 0, -1):
                        alpha = 20 * (4 - glow)
                        fenster_draw.ellipse(
                            [
                                fx - 12 - glow * 3,
                                y - hoehe + 10 - glow * 2,
                                fx + 12 + glow * 3,
                                y - hoehe + 30 + glow * 2,
                            ],
                            fill=(255, 200, 100, alpha),
                        )

            if num_fenster >= 2:
                # Zweites Fenster
                fx = x + breite // 4
                fenster_draw.rectangle(
                    [fx - 8, y - hoehe + 12, fx + 8, y - hoehe + 28],
                    fill=fenster_farbe + (220,),
                )
                draw.line(
                    [(fx, y - hoehe + 12), (fx, y - hoehe + 28)],
                    fill=balken_farbe,
                    width=1,
                )
                draw.line(
                    [(fx - 8, y - hoehe + 20), (fx + 8, y - hoehe + 20)],
                    fill=balken_farbe,
                    width=1,
                )

                if phase == "nacht":
                    for glow in range(3, 0, -1):
                        alpha = 20 * (4 - glow)
                        fenster_draw.ellipse(
                            [
                                fx - 12 - glow * 3,
                                y - hoehe + 10 - glow * 2,
                                fx + 12 + glow * 3,
                                y - hoehe + 30 + glow * 2,
                            ],
                            fill=(255, 200, 100, alpha),
                        )

            img.paste(Image.alpha_composite(img, fenster_layer))

            # Tür
            tuer_farbe = (70, 50, 40) if phase != "tag" else (100, 70, 55)
            draw.rectangle([x - 7, y - 22, x + 7, y], fill=tuer_farbe)
            # Türknauf
            draw.ellipse([x + 3, y - 13, x + 6, y - 10], fill=(180, 150, 80))

    def _render_boden(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert den schönen Dorfplatz"""
        cx, cy = CIRCLE_CENTER

        # Äußerer Grasbereich mit Textur
        if phase == "nacht":
            gras_farbe = FARBEN["gras_dunkel"]
            erde_farbe = FARBEN["erde_dunkel"]
        else:
            gras_farbe = FARBEN["gras_hell"]
            erde_farbe = FARBEN["erde"]

        # Gras-Ellipse
        draw.ellipse(
            [
                cx - CIRCLE_RADIUS - 100,
                cy - (CIRCLE_RADIUS + 100) * ISO_SCALE_Y,
                cx + CIRCLE_RADIUS + 100,
                cy + (CIRCLE_RADIUS + 100) * ISO_SCALE_Y,
            ],
            fill=gras_farbe,
        )

        # Erdpfad / Dorfplatz
        draw.ellipse(
            [
                cx - CIRCLE_RADIUS - 30,
                cy - (CIRCLE_RADIUS + 30) * ISO_SCALE_Y,
                cx + CIRCLE_RADIUS + 30,
                cy + (CIRCLE_RADIUS + 30) * ISO_SCALE_Y,
            ],
            fill=erde_farbe,
        )

        # Steinkreis um das Feuer (schöner)
        for i in range(20):
            winkel = i * 18 * math.pi / 180
            x = cx + math.cos(winkel) * 60
            y = cy + math.sin(winkel) * 60 * ISO_SCALE_Y
            stein_farbe = random.choice(FARBEN["steine"])
            stein_w = random.randint(8, 14)
            stein_h = int(stein_w * 0.6)
            draw.ellipse(
                [x - stein_w, y - stein_h, x + stein_w, y + stein_h],
                fill=stein_farbe,
            )
            # Highlight auf Steinen
            draw.arc(
                [x - stein_w + 2, y - stein_h + 2, x + stein_w - 2, y + stein_h - 2],
                200,
                340,
                fill=(stein_farbe[0] + 20, stein_farbe[1] + 20, stein_farbe[2] + 20),
            )

    def _render_lagerfeuer(self, img: Image.Image, draw: ImageDraw.Draw, phase: str):
        """Rendert ein wunderschönes, realistisches Lagerfeuer"""
        cx, cy = CIRCLE_CENTER

        # Holzscheite (realistischer)
        holz_farbe = (70, 45, 25)
        holz_dunkel = (50, 30, 18)
        for i in range(6):
            winkel = i * 60 * math.pi / 180 + 0.2
            x1 = cx + math.cos(winkel) * 12
            y1 = cy + math.sin(winkel) * 12 * ISO_SCALE_Y - 3
            x2 = cx + math.cos(winkel + 0.4) * 30
            y2 = cy + math.sin(winkel + 0.4) * 30 * ISO_SCALE_Y - 3
            draw.line([(x1, y1), (x2, y2)], fill=holz_farbe, width=8)
            draw.line([(x1 + 2, y1 + 1), (x2 + 2, y2 + 1)], fill=holz_dunkel, width=4)

        # Glühende Kohlen/Asche am Boden
        glut = Image.new("RGBA", img.size, (0, 0, 0, 0))
        glut_draw = ImageDraw.Draw(glut)
        for _ in range(20):
            gx = cx + random.randint(-25, 25)
            gy = cy + random.randint(-8, 8)
            gr = random.randint(2, 5)
            glut_draw.ellipse(
                [gx - gr, gy - gr, gx + gr, gy + gr],
                fill=(200, 80, 20, random.randint(100, 200)),
            )
        img.paste(Image.alpha_composite(img, glut))

        # Feuer (nur nachts und in Dämmerung sichtbar intensiv)
        if phase != "tag":
            # Feuerschein auf Boden
            for i in range(15, 0, -1):
                alpha = int(50 * (1 - i / 15))
                glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse(
                    [
                        cx - 50 - i * 5,
                        cy - 25 - i * 2,
                        cx + 50 + i * 5,
                        cy + 25 + i * 2,
                    ],
                    fill=(255, 150, 50, alpha),
                )
                img.paste(Image.alpha_composite(img, glow))

            # Mehrschichtige Flammen für Realismus
            # Äußere Flamme (rot-orange)
            flammen_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            flammen_draw = ImageDraw.Draw(flammen_layer)

            # Basis-Flammenform
            for f in range(3):
                fx_offset = random.randint(-8, 8)
                fy_offset = random.randint(-5, 5)
                f_hoehe = 55 + random.randint(-5, 10)

                flammen_punkte = [
                    (cx - 25 + fx_offset, cy + 5),
                    (cx - 15 + fx_offset, cy - f_hoehe * 0.3 + fy_offset),
                    (cx - 8 + fx_offset, cy - f_hoehe * 0.6 + fy_offset),
                    (cx + fx_offset, cy - f_hoehe + fy_offset),
                    (cx + 8 + fx_offset, cy - f_hoehe * 0.6 + fy_offset),
                    (cx + 15 + fx_offset, cy - f_hoehe * 0.3 + fy_offset),
                    (cx + 25 + fx_offset, cy + 5),
                ]
                flammen_draw.polygon(
                    flammen_punkte, fill=FARBEN["feuer_aussen"] + (200,)
                )

            img.paste(Image.alpha_composite(img, flammen_layer))

            # Mittlere Flamme (orange)
            inner_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            inner_draw = ImageDraw.Draw(inner_layer)
            innere_punkte = [
                (cx - 15, cy),
                (cx - 8, cy - 30),
                (cx, cy - 45),
                (cx + 8, cy - 30),
                (cx + 15, cy),
            ]
            inner_draw.polygon(innere_punkte, fill=FARBEN["feuer_mitte"] + (220,))
            img.paste(Image.alpha_composite(img, inner_layer))

            # Kern (gelb-weiß)
            kern_punkte = [
                (cx - 8, cy - 5),
                (cx - 4, cy - 20),
                (cx, cy - 30),
                (cx + 4, cy - 20),
                (cx + 8, cy - 5),
            ]
            draw.polygon(kern_punkte, fill=FARBEN["feuer_innen"])

            # Heißer Kern
            draw.ellipse([cx - 4, cy - 18, cx + 4, cy - 8], fill=FARBEN["feuer_kern"])

            # Funken
            funken = Image.new("RGBA", img.size, (0, 0, 0, 0))
            funken_draw = ImageDraw.Draw(funken)
            for _ in range(15):
                fx = cx + random.randint(-30, 30)
                fy = cy - random.randint(20, 80)
                funken_draw.ellipse(
                    [fx - 1, fy - 1, fx + 1, fy + 1],
                    fill=(255, random.randint(150, 255), 50, random.randint(150, 255)),
                )
            img.paste(Image.alpha_composite(img, funken))
        else:
            # Tagsüber: Rauchende Asche
            for i in range(5):
                rx = cx + random.randint(-10, 10)
                ry = cy - 20 - i * 15
                draw.ellipse([rx - 8, ry - 5, rx + 8, ry + 5], fill=(150, 150, 150, 50))

    def _sortiere_spieler_fuer_rendering(
        self, spieler: List[SpielerVisual]
    ) -> List[SpielerVisual]:
        """Sortiert Spieler von hinten nach vorne für korrekte Überlappung"""

        def y_position(s: SpielerVisual) -> float:
            anzahl = max(len(spieler), 8)
            winkel = (s.sitzplatz / anzahl) * 2 * math.pi - math.pi / 2
            return math.sin(winkel)

        return sorted(spieler, key=y_position)

    def _get_rollen_farbe(
        self, rolle: Optional[str], team: Optional[str]
    ) -> Tuple[int, int, int]:
        """Gibt die passende Farbe für eine Rolle zurück"""
        if rolle:
            rolle_lower = rolle.lower()
            if rolle_lower in ROLLEN_FARBEN:
                return ROLLEN_FARBEN[rolle_lower][0]

        # Fallback auf Team-Farben
        if team:
            team_lower = team.lower()
            if team_lower == "werwolf":
                return FARBEN["kleidung_werwolf"]
            elif team_lower == "dorf":
                return FARBEN["kleidung_dorf"]

        return FARBEN["kleidung_neutral"]

    def _render_spieler_charakter(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        spieler: SpielerVisual,
        szene: DorfSzene,
        hinweis: Optional[Tuple[str, float]] = None,
        total_spieler: int = 8,
    ):
        """Rendert einen wunderschönen, einzigartigen Charakter für jeden Spieler"""
        anzahl = max(total_spieler, 8)
        winkel = (spieler.sitzplatz / anzahl) * 2 * math.pi - math.pi / 2

        cx, cy = CIRCLE_CENTER
        tiefenfaktor = 0.65 + 0.35 * ((math.sin(winkel) + 1) / 2)
        radius = CIRCLE_RADIUS * (0.8 + 0.2 * tiefenfaktor)
        x = cx + math.cos(winkel) * radius
        y = cy + math.sin(winkel) * radius * ISO_SCALE_Y

        scale = 0.6 + 0.5 * tiefenfaktor

        # Hole konsistente Charakter-Eigenschaften
        char_props = self._get_charakter_eigenschaften(spieler.id)

        # Bestimme Kleidungsfarbe basierend auf Rolle/Team
        if spieler.ist_am_leben:
            kleidung_farbe = self._get_rollen_farbe(spieler.rolle, spieler.team)
        else:
            kleidung_farbe = FARBEN["tot"]

        # Schatten
        if spieler.ist_am_leben:
            schatten = Image.new("RGBA", img.size, (0, 0, 0, 0))
            schatten_draw = ImageDraw.Draw(schatten)
            schatten_draw.ellipse(
                [x - 20 * scale, y + 30 * scale, x + 20 * scale, y + 40 * scale],
                fill=(0, 0, 0, 60),
            )
            img.paste(Image.alpha_composite(img, schatten))

        # === AURA-EFFEKTE basierend auf Sichtbarkeit ===

        # Werwolf-Sicht: Andere Werwölfe sehen sich
        if spieler.sichtbar_als_werwolf:
            self._render_aura(
                img, x, y - 20 * scale, (180, 30, 30, 80), scale, "werwolf"
            )

        # Seherin-Enthüllung
        if spieler.sichtbar_als_boese:
            self._render_aura(img, x, y - 20 * scale, (200, 40, 40, 70), scale, "boese")
        elif spieler.sichtbar_als_dorf:
            self._render_aura(img, x, y - 20 * scale, (60, 180, 60, 60), scale, "gut")

        # Verliebt-Effekt
        if spieler.ist_verliebt:
            self._render_herz_effekt(img, x, y - 55 * scale)

        # Geschützt-Effekt
        if spieler.ist_geschuetzt:
            self._render_schild_effekt(img, draw, x, y - 20 * scale, scale)

        if spieler.ist_am_leben:
            # === LEBENDER SPIELER - Detaillierter Charakter ===

            # Körper/Robe
            self._render_koerper(draw, x, y, scale, kleidung_farbe, char_props)

            # Kopf und Gesicht
            self._render_kopf(draw, x, y, scale, char_props, cx, cy, szene.phase)

            # Haare
            self._render_haare(draw, x, y, scale, char_props)

            # Rollen-spezifische Accessoires
            if spieler.rolle:
                self._render_accessoire(img, draw, x, y, scale, spieler.rolle)

            # Hinweis-Effekte
            if hinweis:
                self._render_hinweis_effekt(img, draw, x, y, hinweis, scale)
        else:
            # === TOTER SPIELER ===
            self._render_toter_spieler(img, draw, x, y, scale, char_props)

        # Name mit schönem Badge
        self._render_spieler_name(draw, x, y, spieler, scale)

    def _render_aura(
        self,
        img: Image.Image,
        x: float,
        y: float,
        farbe: Tuple[int, int, int, int],
        scale: float,
        typ: str,
    ):
        """Rendert eine Aura um einen Spieler"""
        aura = Image.new("RGBA", img.size, (0, 0, 0, 0))
        aura_draw = ImageDraw.Draw(aura)

        for i in range(8, 0, -1):
            alpha = int(farbe[3] * (1 - i / 8))
            aura_draw.ellipse(
                [
                    x - (25 + i * 4) * scale,
                    y - (35 + i * 4) * scale,
                    x + (25 + i * 4) * scale,
                    y + (30 + i * 4) * scale,
                ],
                fill=(farbe[0], farbe[1], farbe[2], alpha),
            )
        img.paste(Image.alpha_composite(img, aura))

    def _render_herz_effekt(self, img: Image.Image, x: float, y: float):
        """Rendert schwebende Herzen für verliebte Spieler"""
        herz = Image.new("RGBA", img.size, (0, 0, 0, 0))
        herz_draw = ImageDraw.Draw(herz)

        # Zwei kleine Herzen
        for offset in [-12, 12]:
            hx, hy = x + offset, y - 10
            # Herz-Form (vereinfacht als zwei Kreise + Dreieck)
            herz_draw.ellipse(
                [hx - 6, hy - 4, hx - 1, hy + 2], fill=(255, 100, 120, 200)
            )
            herz_draw.ellipse(
                [hx + 1, hy - 4, hx + 6, hy + 2], fill=(255, 100, 120, 200)
            )
            herz_draw.polygon(
                [(hx - 6, hy), (hx + 6, hy), (hx, hy + 8)], fill=(255, 100, 120, 200)
            )

        img.paste(Image.alpha_composite(img, herz))

    def _render_schild_effekt(
        self, img: Image.Image, draw: ImageDraw.Draw, x: float, y: float, scale: float
    ):
        """Rendert einen Schutzschild-Effekt"""
        schild = Image.new("RGBA", img.size, (0, 0, 0, 0))
        schild_draw = ImageDraw.Draw(schild)

        # Goldener Schild-Glow
        for i in range(5, 0, -1):
            alpha = int(40 * (1 - i / 5))
            schild_draw.ellipse(
                [
                    x - (28 + i * 2) * scale,
                    y - (40 + i * 2) * scale,
                    x + (28 + i * 2) * scale,
                    y + (35 + i * 2) * scale,
                ],
                outline=(255, 215, 0, alpha),
                width=2,
            )
        img.paste(Image.alpha_composite(img, schild))

    def _render_koerper(
        self,
        draw: ImageDraw.Draw,
        x: float,
        y: float,
        scale: float,
        farbe: Tuple[int, int, int],
        char_props: Dict,
    ):
        """Rendert den Körper/Robe eines Charakters"""
        # Robe mit Faltenwurf
        robe_punkte = [
            (x - 14 * scale, y + 30 * scale),  # Unten links
            (x - 18 * scale, y + 5 * scale),  # Hüfte links
            (x - 16 * scale, y - 15 * scale),  # Taille links
            (x - 10 * scale, y - 28 * scale),  # Schulter links
            (x, y - 32 * scale),  # Kragen
            (x + 10 * scale, y - 28 * scale),  # Schulter rechts
            (x + 16 * scale, y - 15 * scale),  # Taille rechts
            (x + 18 * scale, y + 5 * scale),  # Hüfte rechts
            (x + 14 * scale, y + 30 * scale),  # Unten rechts
        ]

        # Robe mit Gradient-Effekt (dunklerer Rand)
        draw.polygon(robe_punkte, fill=farbe)

        # Falten/Details
        dunklere_farbe = (
            max(0, farbe[0] - 30),
            max(0, farbe[1] - 30),
            max(0, farbe[2] - 30),
        )
        hellere_farbe = (
            min(255, farbe[0] + 30),
            min(255, farbe[1] + 30),
            min(255, farbe[2] + 30),
        )

        # Mittlere Falte
        draw.line(
            [(x, y - 10 * scale), (x, y + 25 * scale)], fill=dunklere_farbe, width=1
        )

        # Highlight links
        draw.line(
            [(x - 8 * scale, y - 20 * scale), (x - 10 * scale, y + 10 * scale)],
            fill=hellere_farbe,
            width=1,
        )

        # Gürtel
        draw.rectangle(
            [x - 12 * scale, y - 8 * scale, x + 12 * scale, y - 3 * scale],
            fill=(60, 45, 35),
        )
        # Gürtelschnalle
        draw.ellipse(
            [x - 3 * scale, y - 7 * scale, x + 3 * scale, y - 4 * scale],
            fill=(180, 150, 80),
        )

    def _render_kopf(
        self,
        draw: ImageDraw.Draw,
        x: float,
        y: float,
        scale: float,
        char_props: Dict,
        feuer_x: float,
        feuer_y: float,
        phase: str,
    ):
        """Rendert Kopf und Gesicht"""
        kopf_y = y - 45 * scale

        # Hautfarbe
        haut_key = f"haut_{char_props['haut_ton']}"
        haut_farbe = FARBEN.get(haut_key, FARBEN["haut_mittel"])

        # Kopf (Oval)
        draw.ellipse(
            [x - 11 * scale, kopf_y - 12 * scale, x + 11 * scale, kopf_y + 12 * scale],
            fill=haut_farbe,
        )

        # Ohren
        draw.ellipse(
            [x - 14 * scale, kopf_y - 3 * scale, x - 10 * scale, kopf_y + 5 * scale],
            fill=haut_farbe,
        )
        draw.ellipse(
            [x + 10 * scale, kopf_y - 3 * scale, x + 14 * scale, kopf_y + 5 * scale],
            fill=haut_farbe,
        )

        # Augen (schauen zum Feuer)
        feuer_richtung = math.atan2(feuer_y - kopf_y, feuer_x - x)
        auge_offset_x = math.cos(feuer_richtung) * 2 * scale

        # Augenweiß
        draw.ellipse(
            [x - 6 * scale, kopf_y - 3 * scale, x - 1 * scale, kopf_y + 2 * scale],
            fill=(255, 255, 255),
        )
        draw.ellipse(
            [x + 1 * scale, kopf_y - 3 * scale, x + 6 * scale, kopf_y + 2 * scale],
            fill=(255, 255, 255),
        )

        # Pupillen
        pupillen_farbe = (40, 35, 30)
        draw.ellipse(
            [
                x - 5 * scale + auge_offset_x,
                kopf_y - 2 * scale,
                x - 2 * scale + auge_offset_x,
                kopf_y + 1 * scale,
            ],
            fill=pupillen_farbe,
        )
        draw.ellipse(
            [
                x + 2 * scale + auge_offset_x,
                kopf_y - 2 * scale,
                x + 5 * scale + auge_offset_x,
                kopf_y + 1 * scale,
            ],
            fill=pupillen_farbe,
        )

        # Mund (leichtes Lächeln)
        draw.arc(
            [x - 4 * scale, kopf_y + 4 * scale, x + 4 * scale, kopf_y + 9 * scale],
            0,
            180,
            fill=(150, 80, 80),
            width=1,
        )

        # Nase
        draw.line(
            [(x, kopf_y), (x, kopf_y + 4 * scale)],
            fill=(haut_farbe[0] - 20, haut_farbe[1] - 20, haut_farbe[2] - 20),
            width=1,
        )

        # Wangen-Rouge bei Feuerschein (Nacht)
        if phase == "nacht":
            wangen = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            wangen_draw = ImageDraw.Draw(wangen)
            wangen_draw.ellipse(
                [x - 9 * scale, kopf_y + 1 * scale, x - 4 * scale, kopf_y + 5 * scale],
                fill=(255, 180, 150, 60),
            )
            wangen_draw.ellipse(
                [x + 4 * scale, kopf_y + 1 * scale, x + 9 * scale, kopf_y + 5 * scale],
                fill=(255, 180, 150, 60),
            )

    def _render_haare(
        self, draw: ImageDraw.Draw, x: float, y: float, scale: float, char_props: Dict
    ):
        """Rendert Haare basierend auf Charakter-Eigenschaften"""
        kopf_y = y - 45 * scale
        haar_key = f"haare_{char_props['haar_farbe']}"
        haar_farbe = FARBEN.get(haar_key, FARBEN["haare_braun"])
        haar_dunkel = (
            max(0, haar_farbe[0] - 20),
            max(0, haar_farbe[1] - 20),
            max(0, haar_farbe[2] - 20),
        )

        stil = char_props["haar_stil"]
        geschlecht = char_props["geschlecht"]

        if geschlecht == "w":
            # Lange Haare für weibliche Charaktere
            if stil == 0:
                # Glattes langes Haar
                draw.ellipse(
                    [
                        x - 14 * scale,
                        kopf_y - 14 * scale,
                        x + 14 * scale,
                        kopf_y + 8 * scale,
                    ],
                    fill=haar_farbe,
                )
                # Strähnen
                draw.polygon(
                    [
                        (x - 13 * scale, kopf_y + 5 * scale),
                        (x - 16 * scale, y - 20 * scale),
                        (x - 10 * scale, y - 20 * scale),
                    ],
                    fill=haar_farbe,
                )
                draw.polygon(
                    [
                        (x + 13 * scale, kopf_y + 5 * scale),
                        (x + 16 * scale, y - 20 * scale),
                        (x + 10 * scale, y - 20 * scale),
                    ],
                    fill=haar_farbe,
                )
            elif stil == 1:
                # Welliges Haar
                draw.ellipse(
                    [
                        x - 15 * scale,
                        kopf_y - 15 * scale,
                        x + 15 * scale,
                        kopf_y + 5 * scale,
                    ],
                    fill=haar_farbe,
                )
                for i in range(-2, 3):
                    draw.ellipse(
                        [
                            x + (i * 6 - 5) * scale,
                            kopf_y + 3 * scale,
                            x + (i * 6 + 5) * scale,
                            y - 18 * scale,
                        ],
                        fill=haar_farbe,
                    )
            else:
                # Hochgesteckt
                draw.ellipse(
                    [
                        x - 12 * scale,
                        kopf_y - 18 * scale,
                        x + 12 * scale,
                        kopf_y + 2 * scale,
                    ],
                    fill=haar_farbe,
                )
                draw.ellipse(
                    [
                        x - 8 * scale,
                        kopf_y - 22 * scale,
                        x + 8 * scale,
                        kopf_y - 10 * scale,
                    ],
                    fill=haar_dunkel,
                )
        else:
            # Kurze Haare für männliche Charaktere
            if stil == 0:
                # Kurz und ordentlich
                draw.ellipse(
                    [
                        x - 12 * scale,
                        kopf_y - 14 * scale,
                        x + 12 * scale,
                        kopf_y + 2 * scale,
                    ],
                    fill=haar_farbe,
                )
            elif stil == 1:
                # Lockig
                for i in range(-2, 3):
                    ox = i * 5 * scale
                    draw.ellipse(
                        [
                            x + ox - 5 * scale,
                            kopf_y - 15 * scale,
                            x + ox + 5 * scale,
                            kopf_y - 5 * scale,
                        ],
                        fill=haar_farbe,
                    )
            else:
                # Seitenscheitel
                draw.polygon(
                    [
                        (x - 12 * scale, kopf_y - 8 * scale),
                        (x - 5 * scale, kopf_y - 15 * scale),
                        (x + 12 * scale, kopf_y - 12 * scale),
                        (x + 12 * scale, kopf_y + 2 * scale),
                        (x - 12 * scale, kopf_y + 2 * scale),
                    ],
                    fill=haar_farbe,
                )

    def _render_accessoire(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        x: float,
        y: float,
        scale: float,
        rolle: str,
    ):
        """Rendert rollen-spezifische Accessoires"""
        rolle_lower = rolle.lower()
        kopf_y = y - 45 * scale

        if rolle_lower in ["seherin", "aurenseherin", "seherlehrling"]:
            # Mystisches drittes Auge / Stirnband
            draw.ellipse(
                [
                    x - 4 * scale,
                    kopf_y - 15 * scale,
                    x + 4 * scale,
                    kopf_y - 10 * scale,
                ],
                fill=(180, 100, 255),
            )
            draw.ellipse(
                [
                    x - 2 * scale,
                    kopf_y - 14 * scale,
                    x + 2 * scale,
                    kopf_y - 11 * scale,
                ],
                fill=(255, 255, 255),
            )

        elif rolle_lower in ["hexe", "giftmischerin", "kräuterweib", "kraeuterweib"]:
            # Spitzer Hut
            hut_punkte = [
                (x - 15 * scale, kopf_y - 12 * scale),
                (x, kopf_y - 35 * scale),
                (x + 15 * scale, kopf_y - 12 * scale),
            ]
            draw.polygon(hut_punkte, fill=(40, 35, 50))
            # Hutband
            draw.line(
                [
                    (x - 14 * scale, kopf_y - 13 * scale),
                    (x + 14 * scale, kopf_y - 13 * scale),
                ],
                fill=(100, 60, 120),
                width=int(3 * scale),
            )

        elif rolle_lower in ["werwolf", "urwolf", "weisser_wolf", "wolfsjunge"]:
            # Wolfsohren-Andeutung
            draw.polygon(
                [
                    (x - 10 * scale, kopf_y - 10 * scale),
                    (x - 6 * scale, kopf_y - 20 * scale),
                    (x - 2 * scale, kopf_y - 10 * scale),
                ],
                fill=(80, 60, 50),
            )
            draw.polygon(
                [
                    (x + 2 * scale, kopf_y - 10 * scale),
                    (x + 6 * scale, kopf_y - 20 * scale),
                    (x + 10 * scale, kopf_y - 10 * scale),
                ],
                fill=(80, 60, 50),
            )

        elif rolle_lower in ["heiler", "leibwächter", "leibwaechter", "ergebene_magd"]:
            # Heiligen-Schein / Kreuz
            draw.line(
                [(x, y - 30 * scale), (x, y - 38 * scale)],
                fill=(100, 180, 100),
                width=2,
            )
            draw.line(
                [(x - 4 * scale, y - 34 * scale), (x + 4 * scale, y - 34 * scale)],
                fill=(100, 180, 100),
                width=2,
            )

        elif rolle_lower in ["jaeger", "jäger", "buddler", "inquisitor"]:
            # Armbrust/Waffe am Rücken
            draw.line(
                [(x - 8 * scale, y - 35 * scale), (x + 15 * scale, y + 5 * scale)],
                fill=(100, 70, 40),
                width=3,
            )

        elif rolle_lower in ["amor", "hure", "prostituierte"]:
            # Herz-Symbol
            acc = Image.new("RGBA", img.size, (0, 0, 0, 0))
            acc_draw = ImageDraw.Draw(acc)
            hx, hy = x, kopf_y - 18 * scale
            acc_draw.ellipse([hx - 5, hy - 3, hx, hy + 2], fill=(255, 100, 120, 220))
            acc_draw.ellipse([hx, hy - 3, hx + 5, hy + 2], fill=(255, 100, 120, 220))
            acc_draw.polygon(
                [(hx - 5, hy), (hx + 5, hy), (hx, hy + 6)], fill=(255, 100, 120, 220)
            )
            img.paste(Image.alpha_composite(img, acc))

        elif rolle_lower in ["bürgermeister", "buergermeister", "könig", "koenig"]:
            # Krone
            krone_punkte = [
                (x - 10 * scale, kopf_y - 12 * scale),
                (x - 10 * scale, kopf_y - 18 * scale),
                (x - 5 * scale, kopf_y - 15 * scale),
                (x, kopf_y - 22 * scale),
                (x + 5 * scale, kopf_y - 15 * scale),
                (x + 10 * scale, kopf_y - 18 * scale),
                (x + 10 * scale, kopf_y - 12 * scale),
            ]
            draw.polygon(krone_punkte, fill=(220, 180, 50))
            # Juwelen
            draw.ellipse(
                [
                    x - 2 * scale,
                    kopf_y - 16 * scale,
                    x + 2 * scale,
                    kopf_y - 13 * scale,
                ],
                fill=(200, 50, 50),
            )

    def _render_toter_spieler(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        x: float,
        y: float,
        scale: float,
        char_props: Dict,
    ):
        """Rendert einen toten Spieler (liegend mit Grabstein)"""
        # Liegende Silhouette
        draw.ellipse(
            [x - 25 * scale, y + 15 * scale, x + 25 * scale, y + 35 * scale],
            fill=FARBEN["tot"],
        )

        # Kleiner Grabstein
        stein_farbe = (70, 65, 65)
        draw.rectangle(
            [x - 8 * scale, y - 5 * scale, x + 8 * scale, y + 15 * scale],
            fill=stein_farbe,
        )
        # Abgerundete Spitze
        draw.ellipse(
            [x - 8 * scale, y - 15 * scale, x + 8 * scale, y + 5 * scale],
            fill=stein_farbe,
        )

        # RIP-Text oder Kreuz
        draw.line([(x, y - 8 * scale), (x, y + 2 * scale)], fill=(90, 85, 85), width=2)
        draw.line(
            [(x - 4 * scale, y - 4 * scale), (x + 4 * scale, y - 4 * scale)],
            fill=(90, 85, 85),
            width=2,
        )

    def _render_spieler_name(
        self,
        draw: ImageDraw.Draw,
        x: float,
        y: float,
        spieler: SpielerVisual,
        scale: float,
    ):
        """Rendert den Spielernamen mit schönem Badge"""
        name_text = spieler.name[:14]  # Maximal 14 Zeichen
        bbox = draw.textbbox((0, 0), name_text, font=self._font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        badge_x = x - text_width // 2 - 8
        badge_y = y + 42 * scale
        badge_width = text_width + 16
        badge_height = text_height + 10

        # Badge-Hintergrund mit Gradient-Effekt
        badge_farbe = (30, 25, 25, 220) if spieler.ist_am_leben else (50, 45, 45, 180)

        # Rolle-basierte Badge-Akzentfarbe
        if spieler.rolle and spieler.ist_am_leben:
            rolle_lower = spieler.rolle.lower()
            if rolle_lower in ROLLEN_FARBEN:
                akzent = ROLLEN_FARBEN[rolle_lower][0]
            else:
                akzent = (100, 100, 100)
        else:
            akzent = (100, 100, 100)

        # Zeichne abgerundetes Badge
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
            radius=8,
            fill=badge_farbe[:3],
        )

        # Akzent-Linie oben
        draw.line(
            [(badge_x + 4, badge_y + 2), (badge_x + badge_width - 4, badge_y + 2)],
            fill=akzent,
            width=2,
        )

        # Name
        text_color = (255, 255, 255) if spieler.ist_am_leben else (150, 145, 145)
        draw.text(
            (badge_x + 8, badge_y + 4),
            name_text,
            fill=text_color,
            font=self._font,
        )

    def _render_hinweis_effekt(
        self,
        img: Image.Image,
        draw: ImageDraw.Draw,
        x: float,
        y: float,
        hinweis: Tuple[str, float],
        scale: float = 1.0,
    ):
        """Rendert visuelle Hinweis-Effekte um einen Spieler"""
        hinweis_typ, intensitaet = hinweis
        kopf_y = y - 45 * scale

        if hinweis_typ == "augen_flackern":
            # Rotes Glühen um Kopf (Werwolf-Verdacht)
            for i in range(int(6 * intensitaet), 0, -1):
                alpha = int(60 * intensitaet * (1 - i / 6))
                glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse(
                    [
                        x - (15 + i * 4) * scale,
                        kopf_y - (15 + i * 4) * scale,
                        x + (15 + i * 4) * scale,
                        kopf_y + (15 + i * 4) * scale,
                    ],
                    fill=(220, 50, 50, alpha),
                )
                img.paste(Image.alpha_composite(img, glow))

        elif hinweis_typ == "schatten":
            # Dunkler Schatten hinter Spieler
            schatten = Image.new("RGBA", img.size, (0, 0, 0, 0))
            schatten_draw = ImageDraw.Draw(schatten)
            schatten_draw.ellipse(
                [x - 35 * scale, y - 55 * scale, x + 45 * scale, y + 35 * scale],
                fill=(0, 0, 0, int(120 * intensitaet)),
            )
            img.paste(Image.alpha_composite(img, schatten))

        elif hinweis_typ == "mond_schein":
            # Bläuliches Mondlicht von oben
            beam = Image.new("RGBA", img.size, (0, 0, 0, 0))
            beam_draw = ImageDraw.Draw(beam)
            beam_punkte = [
                (x - 8 * scale, 0),
                (x + 8 * scale, 0),
                (x + 25 * scale, y + 35 * scale),
                (x - 25 * scale, y + 35 * scale),
            ]
            beam_draw.polygon(beam_punkte, fill=(150, 150, 220, int(50 * intensitaet)))
            img.paste(Image.alpha_composite(img, beam))

        elif hinweis_typ == "gluehen":
            # Mystisches lila Glühen
            for i in range(int(8 * intensitaet), 0, -1):
                alpha = int(45 * intensitaet * (1 - i / 8))
                glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse(
                    [
                        x - (22 + i * 5) * scale,
                        y - (35 + i * 5) * scale,
                        x + (22 + i * 5) * scale,
                        y + (25 + i * 5) * scale,
                    ],
                    fill=(150, 80, 220, alpha),
                )
                img.paste(Image.alpha_composite(img, glow))

        elif hinweis_typ == "selbst_verdaechtigung":
            # Orange/rotes warnendes Glühen
            for i in range(int(6 * intensitaet), 0, -1):
                alpha = int(70 * intensitaet * (1 - i / 6))
                glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse(
                    [
                        x - (28 + i * 4) * scale,
                        y - (40 + i * 4) * scale,
                        x + (28 + i * 4) * scale,
                        y + (30 + i * 4) * scale,
                    ],
                    fill=(240, 120, 50, alpha),
                )
                img.paste(Image.alpha_composite(img, glow))

        elif hinweis_typ == "unschuldig":
            # Grünes sanftes Leuchten
            for i in range(int(5 * intensitaet), 0, -1):
                alpha = int(40 * intensitaet * (1 - i / 5))
                glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse(
                    [
                        x - (20 + i * 4) * scale,
                        y - (35 + i * 4) * scale,
                        x + (20 + i * 4) * scale,
                        y + (25 + i * 4) * scale,
                    ],
                    fill=(80, 200, 80, alpha),
                )
                img.paste(Image.alpha_composite(img, glow))

    def _render_nebel(self, img: Image.Image):
        """Rendert Nebel-Effekt"""
        nebel = Image.new("RGBA", img.size, (0, 0, 0, 0))
        nebel_draw = ImageDraw.Draw(nebel)

        for _ in range(20):
            x = random.randint(0, self.width)
            y = random.randint(self.height // 2, self.height)
            w = random.randint(100, 300)
            h = random.randint(30, 80)
            alpha = random.randint(20, 50)
            nebel_draw.ellipse(
                [x - w, y - h, x + w, y + h], fill=(150, 150, 160, alpha)
            )

        nebel = nebel.filter(ImageFilter.GaussianBlur(radius=20))
        img.paste(Image.alpha_composite(img, nebel))

    def _render_nacht_overlay(self, img: Image.Image):
        """Rendert ein dunkles Nacht-Overlay"""
        overlay = Image.new("RGBA", img.size, (0, 0, 30, 40))
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


def render_village_for_room(
    raum_id: int,
    hinweise: Dict[int, Tuple[str, float]] = None,
    betrachter_id: int = None,
) -> str:
    """
    Rendert das Dorf für einen Raum und gibt Base64-Bild zurück.

    Berücksichtigt Sichtbarkeit:
    - Werwölfe sehen andere Werwölfe
    - Seherin sieht ihre Enthüllungen
    - Amor sieht verliebte Spieler

    Args:
        raum_id: ID des Raums
        hinweise: Optional - Dict von spieler_id zu (hinweis_typ, intensität)
        betrachter_id: Optional - ID des Spielers, der die Szene betrachtet

    Returns:
        Base64-kodiertes PNG für HTML img src
    """
    from models import Raum, Spieler
    from roles.enums import Team

    raum = Raum.query.get(raum_id)
    if not raum:
        return None

    # Hole alle Spieler
    spieler_db = Spieler.query.filter_by(raum_id=raum_id, ist_erzaehler=False).all()

    # Finde den Betrachter
    betrachter = None
    betrachter_rolle = None
    betrachter_team = None
    betrachter_ist_werwolf = False
    betrachter_enthuellung = {}
    betrachter_verliebt_mit = set()

    if betrachter_id:
        betrachter = Spieler.query.get(betrachter_id)
        if betrachter and betrachter.rolle_objekt:
            betrachter_rolle = betrachter.rolle
            try:
                betrachter_team = (
                    betrachter.rolle_objekt.team.value
                    if betrachter.rolle_objekt.team
                    else None
                )
            except:
                betrachter_team = None
            betrachter_ist_werwolf = (
                betrachter_team == Team.WERWOLF.value if betrachter_team else False
            )

            # Hole Enthüllungen der Seherin
            if hasattr(betrachter.rolle_objekt, "enthuellung"):
                betrachter_enthuellung = betrachter.rolle_objekt.enthuellung or {}

            # Hole verliebte Partner (Amor)
            if hasattr(betrachter, "verliebt_mit"):
                betrachter_verliebt_mit = set(betrachter.verliebt_mit or [])

    # Sammle alle Werwolf-IDs für Werwolf-Sicht
    werwolf_ids = set()
    for s in spieler_db:
        if s.rolle_objekt:
            try:
                if s.rolle_objekt.team == Team.WERWOLF:
                    werwolf_ids.add(s.id)
            except:
                pass

    spieler_visuals = []
    for i, s in enumerate(spieler_db):
        # Grundlegende Informationen
        visual = SpielerVisual(
            id=s.id,
            name=s.name,
            sitzplatz=s.sitzplatz if s.sitzplatz is not None else i,
            ist_am_leben=s.ist_am_leben,
        )

        # Sichtbarkeit für Betrachter
        if betrachter_id:
            # Werwölfe sehen andere Werwölfe
            if betrachter_ist_werwolf and s.id in werwolf_ids and s.id != betrachter_id:
                visual.sichtbar_als_werwolf = True
                visual.rolle = "Werwolf"
                visual.team = "werwolf"

            # Seherin sieht ihre Enthüllungen
            if s.id in betrachter_enthuellung:
                enth = betrachter_enthuellung[s.id]
                if enth == "boese" or enth == "werwolf":
                    visual.sichtbar_als_boese = True
                else:
                    visual.sichtbar_als_dorf = True

            # Verliebte sehen sich
            if s.id in betrachter_verliebt_mit:
                visual.ist_verliebt = True

        spieler_visuals.append(visual)

    # Bestimme Phase
    phase = "nacht" if "nacht" in raum.aktuelle_phase.lower() else "tag"
    if "daemmer" in raum.aktuelle_phase.lower():
        phase = "daemmerung"

    szene = DorfSzene(
        spieler=spieler_visuals,
        phase=phase,
        runde=raum.runde,
        aktive_hinweise=hinweise or {},
        betrachter_id=betrachter_id,
        betrachter_rolle=betrachter_rolle,
        betrachter_team=betrachter_team,
    )

    renderer = get_renderer()
    return renderer.render_szene_base64(szene)


def generate_test_village() -> str:
    """Generiert ein Test-Bild für Entwicklung mit allen Features"""
    test_spieler = [
        SpielerVisual(
            id=1,
            name="Wolfgang",
            sitzplatz=0,
            ist_am_leben=True,
            rolle="Werwolf",
            team="werwolf",
            sichtbar_als_werwolf=True,
        ),
        SpielerVisual(
            id=2,
            name="Maria",
            sitzplatz=1,
            ist_am_leben=True,
            rolle="Seherin",
            team="dorf",
            sichtbar_als_dorf=True,
        ),
        SpielerVisual(
            id=3,
            name="Hans",
            sitzplatz=2,
            ist_am_leben=False,
            rolle="Dorfbewohner",
            team="dorf",
        ),
        SpielerVisual(
            id=4,
            name="Greta",
            sitzplatz=3,
            ist_am_leben=True,
            rolle="Hexe",
            team="dorf",
            sichtbar_als_boese=True,  # Falsche Seherin-Enthüllung
        ),
        SpielerVisual(
            id=5,
            name="Friedrich",
            sitzplatz=4,
            ist_am_leben=True,
            rolle="Jäger",
            team="dorf",
            ist_verliebt=True,
        ),
        SpielerVisual(
            id=6,
            name="Anna",
            sitzplatz=5,
            ist_am_leben=True,
            rolle="Amor",
            team="dorf",
            ist_verliebt=True,
        ),
        SpielerVisual(
            id=7,
            name="Klaus",
            sitzplatz=6,
            ist_am_leben=True,
            rolle="Werwolf",
            team="werwolf",
            sichtbar_als_werwolf=True,
        ),
        SpielerVisual(
            id=8,
            name="Sophie",
            sitzplatz=7,
            ist_am_leben=True,
            rolle="Heiler",
            team="dorf",
            ist_geschuetzt=True,
        ),
    ]

    szene = DorfSzene(
        spieler=test_spieler,
        phase="nacht",
        runde=2,
        aktive_hinweise={
            1: ("augen_flackern", 0.7),
            4: ("schatten", 0.5),
            6: ("selbst_verdaechtigung", 0.8),
        },
        betrachter_id=1,  # Aus Werwolf-Perspektive
        betrachter_rolle="Werwolf",
        betrachter_team="werwolf",
    )

    renderer = get_renderer()
    return renderer.render_szene_base64(szene)


if __name__ == "__main__":
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

    with open("village_test.html", "w") as f:
        f.write(html)

    print("Test-Bild gespeichert als village_test.html")
