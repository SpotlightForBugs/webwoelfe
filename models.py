"""
Datenbankmodelle für das Webwölfe-Spiel
Alle Rollen basierend auf: https://werwolf.fandom.com/de/wiki/Werwolf-Rollen-Sammlung
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import secrets
from logger import logger

# Import phases from centralized modules
from phases import get_phase_list

db = SQLAlchemy()


class Raum(db.Model):
    """Ein Spielraum/Lobby"""

    __tablename__ = "raeume"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    modus = db.Column(
        db.String(20), nullable=False, default="online"
    )  # 'online' oder 'gruppe'
    erstellt_am = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    spieler_anzahl = db.Column(db.Integer, default=8)
    spiel_gestartet = db.Column(db.Boolean, default=False)
    aktuelle_phase = db.Column(db.String(30), default="lobby")
    runde = db.Column(db.Integer, default=0)
    erzaehler_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)
    erzaehler_modus = db.Column(db.String(20), default="selbst")  # selbst, zufall

    # Spielende
    spiel_beendet = db.Column(db.Boolean, default=False)
    gewinner = db.Column(db.String(50), nullable=True)

    # Rollen-Konfiguration (JSON der aktivierten Rollen)
    aktive_rollen = db.Column(db.Text, default="{}")

    # Timer für diskussion_abstimmung Phase
    timer_start = db.Column(
        db.DateTime, nullable=True
    )  # Wann die aktuelle Phase begonnen hat
    timer_duration = db.Column(db.Integer, default=120)  # Dauer der Phase in Sekunden

    # Live-Abstimmungsdaten (JSON: {voter_id: target_id})
    phase_votes = db.Column(db.Text, default="{}")

    spieler = db.relationship(
        "Spieler", backref="raum", lazy=True, foreign_keys="Spieler.raum_id"
    )

    @staticmethod
    def generiere_code():
        """Generiert einen einzigartigen 6-stelligen Raumcode"""
        while True:
            code = "".join(
                secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6)
            )
            if not Raum.query.filter_by(code=code).first():
                logger.debug(f"Generated new room code: {code}")
                return code


class Spieler(db.Model):
    """Ein Spieler im Spiel"""

    __tablename__ = "spieler"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    raum_id = db.Column(
        db.Integer, db.ForeignKey("raeume.id"), nullable=True, index=True
    )
    rolle = db.Column(db.String(30), nullable=True, index=True)
    ist_am_leben = db.Column(db.Boolean, default=True, index=True)
    ist_erzaehler = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="wartend")  # wartend, schläft, aktiv, tot
    beigetreten_am = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Composite indexes for common query patterns in large games
    __table_args__ = (
        db.Index("idx_spieler_raum_leben", "raum_id", "ist_am_leben"),
        db.Index("idx_spieler_raum_rolle", "raum_id", "rolle"),
        db.Index("idx_spieler_raum_erzaehler", "raum_id", "ist_erzaehler"),
    )

    # Sitzplatz-System für Nachbar-Mechanik und 3D-Visualisierung
    sitzplatz = db.Column(db.Integer, nullable=True)  # Position im Kreis (0-n)
    # Nachbarn werden dynamisch berechnet basierend auf Sitzplatz

    # ==========================================================================
    # DYNAMIC STATE STORAGE
    # All role-specific state is stored as JSON in this column.
    # Access via roles.base.get_spieler_state() / set_spieler_state()
    # Each role defines its state fields via Role.state_fields()
    # ==========================================================================
    rolle_zustand = db.Column(db.Text, default="{}")  # JSON: {"rolle.field": value}

    # ==========================================================================
    # HELPER METHODS FOR STATE ACCESS
    # ==========================================================================

    def get_state(self, key: str, default=None):
        """
        Liest einen Zustandswert.

        Args:
            key: Der Schlüssel (z.B. "hexe.heiltrank" oder "global.verliebt_mit_id")
            default: Standardwert wenn nicht gefunden
        """
        import json

        try:
            state = json.loads(self.rolle_zustand or "{}")
            val = state.get(key, default)
            # logger.debug(f"State read: {self.name}.{key} = {val}") # Too verbose
            return val
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error reading state for {self.name}: {e}")
            return default

    def set_state(self, key: str, value):
        """
        Setzt einen Zustandswert.

        Args:
            key: Der Schlüssel
            value: Der Wert
        """
        import json

        logger.debug(f"State update: {self.name}.{key} = {value}")

        try:
            state = json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            state = {}
        state[key] = value
        self.rolle_zustand = json.dumps(state)

    def get_all_state(self) -> dict:
        """Liest alle Zustandswerte."""
        import json

        try:
            return json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def reset_state(self):
        """Setzt den Zustand zurück."""
        self.rolle_zustand = "{}"

    # ==========================================================================
    # WIN / LOSE CONDITION MANAGEMENT
    # ==========================================================================

    def add_win_condition(self, condition_id: str):
        """Fügt eine Gewinnbedingung hinzu."""
        state = self.get_all_state()
        conditions = state.get("win_conditions", [])
        if condition_id not in conditions:
            conditions.append(condition_id)
            self.set_state("win_conditions", conditions)

    def remove_win_condition(self, condition_id: str):
        """Entfernt eine Gewinnbedingung."""
        state = self.get_all_state()
        conditions = state.get("win_conditions", [])
        if condition_id in conditions:
            conditions.remove(condition_id)
            self.set_state("win_conditions", conditions)

    def has_win_condition(self, condition_id: str) -> bool:
        """Prüft ob eine Gewinnbedingung existiert."""
        conditions = self.get_state("win_conditions", [])
        return condition_id in (conditions if conditions else [])

    def add_lose_condition(self, condition_id: str, context: dict | None = None):
        """Fügt eine Niederlagenbedingung hinzu."""
        state = self.get_all_state()
        conditions = state.get("lose_conditions", {})
        conditions[condition_id] = context or {}
        self.set_state("lose_conditions", conditions)

    def remove_lose_condition(self, condition_id: str):
        """Entfernt eine Niederlagenbedingung."""
        state = self.get_all_state()
        conditions = state.get("lose_conditions", {})
        if condition_id in conditions:
            del conditions[condition_id]
            self.set_state("lose_conditions", conditions)

    def get_lose_conditions(self) -> dict:
        """Gibt alle aktiven Niederlagenbedingungen zurück."""
        result = self.get_state("lose_conditions", {})
        return result if isinstance(result, dict) else {}

    @staticmethod
    def generiere_session():
        """Generiert eine einzigartige Session-ID"""
        sid = secrets.token_hex(32)
        return sid

    def hole_nachbar_links(self):
        """Gibt den linken Nachbarn zurück (im Uhrzeigersinn)"""
        if self.sitzplatz is None or not self.raum_id:
            return None
        lebende_spieler = (
            Spieler.query.filter_by(
                raum_id=self.raum_id, ist_am_leben=True, ist_erzaehler=False
            )
            .order_by(Spieler.sitzplatz)
            .all()
        )
        if len(lebende_spieler) < 2:
            return None

        # Finde Position in der Liste der lebenden Spieler
        eigene_position = None
        for i, s in enumerate(lebende_spieler):
            if s.id == self.id:
                eigene_position = i
                break

        if eigene_position is None:
            return None

        # Linker Nachbar (einer weniger, mit Wrap-Around)
        nachbar_pos = (eigene_position - 1) % len(lebende_spieler)
        return lebende_spieler[nachbar_pos]

    def hole_nachbar_rechts(self):
        """Gibt den rechten Nachbarn zurück (gegen Uhrzeigersinn)"""
        if self.sitzplatz is None or not self.raum_id:
            return None
        lebende_spieler = (
            Spieler.query.filter_by(
                raum_id=self.raum_id, ist_am_leben=True, ist_erzaehler=False
            )
            .order_by(Spieler.sitzplatz)
            .all()
        )
        if len(lebende_spieler) < 2:
            return None

        eigene_position = None
        for i, s in enumerate(lebende_spieler):
            if s.id == self.id:
                eigene_position = i
                break

        if eigene_position is None:
            return None

        # Rechter Nachbar (einer mehr, mit Wrap-Around)
        nachbar_pos = (eigene_position + 1) % len(lebende_spieler)
        return lebende_spieler[nachbar_pos]

    def hole_beide_nachbarn(self):
        """Gibt beide Nachbarn als Liste zurück"""
        nachbarn = []
        links = self.hole_nachbar_links()
        rechts = self.hole_nachbar_rechts()
        if links:
            nachbarn.append(links)
        if rechts and (
            not links or rechts.id != links.id
        ):  # Vermeidung bei nur 2 Spielern
            nachbarn.append(rechts)
        return nachbarn


class SpielAktion(db.Model):
    """Aktionen während des Spiels (Abstimmungen, Tötungen, etc.)"""

    __tablename__ = "aktionen"

    id = db.Column(db.Integer, primary_key=True)
    raum_id = db.Column(db.Integer, db.ForeignKey("raeume.id"), nullable=False)
    runde = db.Column(db.Integer, nullable=False)
    phase = db.Column(db.String(30), nullable=False)
    aktion_typ = db.Column(db.String(30), nullable=False)
    von_spieler_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=False)
    ziel_spieler_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)
    zusatz_daten = db.Column(db.Text, nullable=True)  # JSON für komplexe Aktionen
    zeitpunkt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    von_spieler = db.relationship("Spieler", foreign_keys=[von_spieler_id])
    ziel_spieler = db.relationship("Spieler", foreign_keys=[ziel_spieler_id])


class SpielLog(db.Model):
    """Spielverlauf-Protokoll"""

    __tablename__ = "spiellog"

    id = db.Column(db.Integer, primary_key=True)
    raum_id = db.Column(db.Integer, db.ForeignKey("raeume.id"), nullable=False)
    nachricht = db.Column(db.Text, nullable=False)
    zeitpunkt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sichtbar_fuer = db.Column(
        db.String(100), default="alle"
    )  # alle, erzähler, werwolf, spieler_id


class ErzaehlerEvent(db.Model):
    """Tracker für einmalige Erzähler-Events (verhindert Wiederholung)"""

    __tablename__ = "erzaehler_events"

    id = db.Column(db.Integer, primary_key=True)
    raum_id = db.Column(db.Integer, db.ForeignKey("raeume.id"), nullable=False)
    event_typ = db.Column(
        db.String(50), nullable=False
    )  # z.B. 'amor_verliebte', 'wildes_kind_vorbild'
    runde = db.Column(db.Integer, nullable=True)  # In welcher Runde Event passierte
    ziel_spieler_ids = db.Column(db.String(100), nullable=True)  # Komma-getrennte IDs
    gespielt_am = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def event_bereits_gespielt(raum_id, event_typ):
        """Prüft ob ein Event bereits gespielt wurde"""
        return (
            ErzaehlerEvent.query.filter_by(raum_id=raum_id, event_typ=event_typ).first()
            is not None
        )

    @staticmethod
    def registriere_event(raum_id, event_typ, runde=None, ziel_spieler_ids=None):
        """Registriert ein gespieltes Event"""
        logger.info(f"Registering narrator event: {event_typ} in room {raum_id}")
        event = ErzaehlerEvent(  # pyright: ignore[reportCallIssue]
            raum_id=raum_id,
            event_typ=event_typ,
            runde=runde,
            ziel_spieler_ids=(
                ",".join(map(str, ziel_spieler_ids)) if ziel_spieler_ids else None
            ),
        )
        db.session.add(event)
        db.session.commit()
        return event


class SpielerPosition(db.Model):
    """3D-Position eines Spielers im Dorf (für Visualisierung)"""

    __tablename__ = "spieler_positionen"

    id = db.Column(db.Integer, primary_key=True)
    spieler_id = db.Column(
        db.Integer, db.ForeignKey("spieler.id"), nullable=False, unique=True
    )


class SeherinEnthuellung(db.Model):  # TODO: REMOVE ROLE BASED HARDCODING
    """
    Snapshot der Seherin-Enthüllungen.

    Speichert was die Seherin ZUM ZEITPUNKT der Enthüllung gesehen hat.
    Auch wenn sich die Rolle später ändert (z.B. durch Infektion),
    bleibt die ursprüngliche Enthüllung erhalten.
    """

    __tablename__ = "seherin_enthuellung"

    id = db.Column(db.Integer, primary_key=True)
    raum_id = db.Column(
        db.Integer, db.ForeignKey("raeume.id"), nullable=False, index=True
    )
    seherin_id = db.Column(
        db.Integer, db.ForeignKey("spieler.id"), nullable=False, index=True
    )
    ziel_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=False)

    # Snapshot zum Zeitpunkt der Enthüllung
    enthuellung_typ = db.Column(
        db.String(20), nullable=False
    )  # 'gut', 'boese', 'neutral'
    gesehene_rolle = db.Column(
        db.String(50), nullable=True
    )  # Die Rolle die gesehen wurde
    runde = db.Column(db.Integer, nullable=False)  # In welcher Runde enthüllt
    enthuellt_am = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def speichere_enthuellung(
        seherin_id: int,
        ziel_id: int,
        raum_id: int,
        enthuellung_typ: str,
        rolle: str,
        runde: int,
    ):
        """Speichert eine neue Enthüllung als Snapshot"""
        logger.info(
            f"Saving Seherin reveal: Seherin {seherin_id} -> Target {ziel_id} ({rolle})"
        )
        # Prüfe ob bereits enthüllt
        bestehend = SeherinEnthuellung.query.filter_by(
            seherin_id=seherin_id, ziel_id=ziel_id, raum_id=raum_id
        ).first()

        if bestehend:
            # Bereits enthüllt - keine Änderung
            return bestehend

        enthuellung = SeherinEnthuellung(  # pyright: ignore[reportCallIssue]  #TODO: REMOVE ROLE BASED HARDCODING
            raum_id=raum_id,
            seherin_id=seherin_id,
            ziel_id=ziel_id,
            enthuellung_typ=enthuellung_typ,
            gesehene_rolle=rolle,
            runde=runde,
        )
        db.session.add(enthuellung)
        db.session.commit()
        return enthuellung

    @staticmethod
    def hole_enthuellung(seherin_id: int, raum_id: int) -> dict:
        """
        Holt alle Enthüllungen einer Seherin als Dictionary.

        Returns:
            Dict von ziel_id -> {'typ': 'gut'/'boese', 'rolle': 'Werwolf', 'runde': 2}
        """
        enthuellungen = SeherinEnthuellung.query.filter_by(
            seherin_id=seherin_id, raum_id=raum_id
        ).all()

        return {
            e.ziel_id: {
                "typ": e.enthuellung_typ,
                "rolle": e.gesehene_rolle,
                "runde": e.runde,
            }
            for e in enthuellungen
        }

    # Relationships mit expliziten foreign_keys
    seherin = db.relationship(
        "Spieler",
        foreign_keys=[seherin_id],
        backref="enthüllungen_als_seherin",  # TODO: REMOVE ROLE BASED HARDCODING
    )
    ziel = db.relationship(
        "Spieler",
        foreign_keys=[ziel_id],
        backref="enthüllungen_als_ziel",  # TODO: REMOVE ROLE BASED HARDCODING
    )


# ============================================================================
# NARRATOR EVENTS - Dynamic narrator text system
# Core phase events and role-specific events are now in narrator.py
# Role-specific events are collected from each Role's get_erzaehler_events()
# ============================================================================

from narrator import ERZAEHLER_EVENTS, hole_erzaehler_text, get_all_narrator_events


# ============================================================================
# HINWEIS-SYSTEM FÜR ONLINE-MODUS
# Subtile visuelle/akustische Hinweise zur Werwolf-Erkennung
# Prozentbasiert, nicht spezifisch, ausbalanciert
# ============================================================================
# Todo: add sounds and fallback to descriptions via tts if no audio available.
HINWEIS_TYPEN = {
    "augen_flackern": {
        "name": "Augen-Flackern",
        "beschreibung": "Das Avatar-Bild des Spielers flackert kurz rot",
        "dauer_ms": 150,
        "css_class": "hint-eyes-flicker",
        "audio": None,
        "verdaechtigkeit": 0.3,  # Wie verdächtig ist dieser Hinweis (0-1)
    },
    "schatten": {
        "name": "Schatten",
        "beschreibung": "Ein kurzer Schatten huscht über den Spieler",
        "dauer_ms": 300,
        "css_class": "hint-shadow",
        "audio": "shadow_swoosh.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.2,
    },
    "heulen_fern": {
        "name": "Fernes Heulen",
        "beschreibung": "Ein leises, fernes Wolfsheulen ist zu hören",
        "dauer_ms": 2000,
        "css_class": None,
        "audio": "distant_howl.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.4,
    },
    "mond_schein": {
        "name": "Mondschein",
        "beschreibung": "Mondlicht erhellt kurz den Spieler",
        "dauer_ms": 500,
        "css_class": "hint-moonlight",
        "audio": None,
        "verdaechtigkeit": 0.25,
    },
    "nervoes": {
        "name": "Nervöses Zittern",
        "beschreibung": "Die Spielerkarte zittert leicht",
        "dauer_ms": 800,
        "css_class": "hint-nervous",
        "audio": None,
        "verdaechtigkeit": 0.15,
    },
    "blick_abwenden": {
        "name": "Blick abwenden",
        "beschreibung": "Das Avatar dreht sich kurz weg",
        "dauer_ms": 400,
        "css_class": "hint-look-away",
        "audio": None,
        "verdaechtigkeit": 0.2,
    },
    "kratzen": {
        "name": "Kratzen",
        "beschreibung": "Ein Kratzgeräusch ist zu hören",
        "dauer_ms": 1000,
        "css_class": None,
        "audio": "scratch.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.35,
    },
    "herzschlag": {
        "name": "Schneller Herzschlag",
        "beschreibung": "Ein schneller Herzschlag pulsiert",
        "dauer_ms": 1500,
        "css_class": "hint-heartbeat",
        "audio": "heartbeat_fast.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.3,
    },
    "gluehen": {
        "name": "Mystisches Glühen",
        "beschreibung": "Ein mystisches Glühen umgibt den Spieler",
        "dauer_ms": 600,
        "css_class": "hint-glow",
        "audio": None,
        "verdaechtigkeit": 0.1,  # Niedriger, da auch gute Rollen glühen
    },
    "fluestern": {
        "name": "Flüstern",
        "beschreibung": "Unverständliches Flüstern ist zu hören",
        "dauer_ms": 1200,
        "css_class": None,
        "audio": "whisper.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.25,
    },
    "selbst_verdaechtigung": {
        "name": "Selbst-Verdächtigung",
        "beschreibung": "Der Spieler macht sich selbst verdächtig (Selbstmörder)",
        "dauer_ms": 1000,
        "css_class": "hint-sus-self",
        "audio": "suspicious.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.5,  # Spieler-kontrolliert
    },
    "stolpern": {
        "name": "Stolpern",
        "beschreibung": "Der Spieler scheint zu stolpern",
        "dauer_ms": 500,
        "css_class": "hint-stumble",
        "audio": "stumble.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.1,
    },
    "kichern": {
        "name": "Böses Kichern",
        "beschreibung": "Ein leises, böses Kichern",
        "dauer_ms": 800,
        "css_class": None,
        "audio": "evil_chuckle.mp3",  # TODO: Add sound
        "verdaechtigkeit": 0.45,
    },
}

# ============================================================================
# HINWEIS-KONFIGURATION FÜR REMOTE-PLAY
# WICHTIG: Im Remote-Modus können Spieler KEINE Audio von anderen Geräten hören!
# Daher: Hinweise werden als SYNCHRONISIERTE VISUELLE EVENTS an ALLE gesendet
# ============================================================================

HINWEIS_MODUS = {
    "gruppe": {
        # Im Gruppen-Modus: Audio + Visual für den Erzähler
        "audio_erlaubt": True,
        "visual_ziel": "erzaehler",  # Nur Erzähler sieht Hinweise
        "synchronisiert": False,
    },
    "online": {
        # Im Online-Modus: NUR Visual, SYNCHRONISIERT für alle!
        "audio_erlaubt": False,  # Kein Audio im Remote Play!
        "visual_ziel": "alle",  # Alle sehen den Hinweis gleichzeitig
        "synchronisiert": True,  # Gleicher Timestamp für alle
        "hinweis_nachricht": True,  # Zeige Text wie "Ein Schatten huscht über {spieler}"
    },
}

# Hinweis-Konfiguration pro Rollen-Team
HINWEIS_CHANCEN = {
    "werwolf": {  # TODO: REMOVE ROLE BASED HARDCODING
        # Werwölfe haben höhere Chancen, verdächtige Hinweise zu produzieren
        "basis_chance": 0.15,  # 15% Basis-Chance pro Nachtphase
        "hinweise": ["augen_flackern", "schatten", "mond_schein"],  # Nur visuelle!
        "max_pro_nacht": 2,
    },
    "dorf": {
        # Dorfbewohner produzieren selten Hinweise (False Positives)
        "basis_chance": 0.05,  # 5% Basis-Chance
        "hinweise": ["nervoes", "stolpern", "gluehen"],
        "max_pro_nacht": 1,
    },
    "solo": {
        # Solo-Rollen haben variable Hinweise
        "basis_chance": 0.10,
        "hinweise": ["schatten", "blick_abwenden", "mond_schein"],
        "max_pro_nacht": 1,
    },
    "neutral": {
        "basis_chance": 0.08,
        "hinweise": ["gluehen", "mond_schein"],
        "max_pro_nacht": 1,
    },
}

# Hinweise die ALLE Spieler sehen können (für Online-Synchronisation)
SYNCHRONISIERTE_HINWEISE = {
    "augen_flackern": {
        "nachricht": "Die Augen von {spieler} flackern kurz seltsam...",
        "3d_effekt": "eyes_glow_red",  # 3D-Visualisierung
    },
    "schatten": {
        "nachricht": "Ein Schatten huscht über {spieler}...",
        "3d_effekt": "shadow_pass",
    },
    "mond_schein": {
        "nachricht": "Mondlicht fällt auf {spieler}...",
        "3d_effekt": "moonbeam",
    },
    "nervoes": {
        "nachricht": "{spieler} wirkt nervös...",
        "3d_effekt": "character_shake",
    },
    "stolpern": {
        "nachricht": "{spieler} stolpert kurz...",
        "3d_effekt": "character_stumble",
    },
    "gluehen": {
        "nachricht": "Ein mystisches Glühen umgibt {spieler}...",
        "3d_effekt": "aura_glow",
    },
    "blick_abwenden": {
        "nachricht": "{spieler} wendet den Blick ab...",
        "3d_effekt": "look_away",
    },
    "selbst_verdaechtigung": {  # TOOD: DAS IST NICHT AKZEPTABEL WEIL DANN OFFENSICHTLICH IST; DASS DAS EIN SELBSTMÖRDER IST
        "nachricht": "{spieler} verhält sich verdächtig!",
        "3d_effekt": "suspicious_behavior",
    },
}

# Spezielle Rollen-Hinweise (überschreiben Team-Standard)
SPEZIAL_HINWEISE = {
    "Selbstmörder": {  # TODO: REMOVE ROLE BASED HARDCODING
        # Der Selbstmörder kann aktiv Hinweise auf sich ziehen!
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": [
            "selbst_verdaechtigung",
            "nervoes",
            "stolpern",
            "blick_abwenden",
        ],
        "hinweise_pro_tag": 3,  # Kann 3x pro Tag sich verdächtig machen
        "beschreibung": 'Klicke auf "Verdächtig wirken" um subtile Hinweise zu senden.',
    },
    "Gerber": {  # TODO: REMOVE ROLE BASED HARDCODING
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": ["selbst_verdaechtigung", "nervoes"],
        "hinweise_pro_tag": 2,
        "beschreibung": "Du kannst dich verdächtig machen, um gehängt zu werden.",
    },
    "Dorfdepp": {  # TODO: REMOVE ROLE BASED HARDCODING
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": ["stolpern", "nervoes"],
        "hinweise_pro_tag": 2,
        "beschreibung": "Mach dich zum Deppen und wirke verdächtig!",
    },
    "Engel": {  # TODO: REMOVE ROLE BASED HARDCODING
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": ["gluehen", "selbst_verdaechtigung"],
        "hinweise_pro_tag": 2,
        "beschreibung": "Du musst in der ersten Runde sterben! Ziehe Aufmerksamkeit auf dich.",
    },
    "Weißer Wolf": {  # TODO: REMOVE ROLE BASED HARDCODING
        # Besonders unauffällig unter Wölfen
        "basis_chance_override": 0.08,  # Niedrigere Chance als normale Werwölfe
        "hinweise": ["schatten"],
    },
    "Wolfshund": {  # TODO: REMOVE ROLE BASED HARDCODING
        # Je nach Entscheidung verschiedene Hinweise
        "dynamisch": True,
    },
}

# Spielregeln/Varianten für Regelauswahl
SPIEL_REGELN = {  # TODO: MAKE THOSE ACTUALLY WORK AND DO STUFF.
    "standard": {
        "name": "Standard-Regeln",
        "beschreibung": "Die klassischen Werwolf-Regeln.",
        "einstellungen": {
            "nacht_zeit_sekunden": 60,
            "tag_diskussion_minuten": 5,
            "abstimmung_zeit_sekunden": 30,
            "tote_duerfen_reden": False,
            "rolle_bei_tod_zeigen": True,
        },
    },
    "schnell": {
        "name": "Schnellspiel",
        "beschreibung": "Kürzere Zeiten für schnelle Runden.",
        "einstellungen": {
            "nacht_zeit_sekunden": 30,
            "tag_diskussion_minuten": 2,
            "abstimmung_zeit_sekunden": 15,
            "tote_duerfen_reden": False,
            "rolle_bei_tod_zeigen": True,
        },
    },
    "chaos": {
        "name": "Chaos-Modus",
        "beschreibung": "Mehr Zufallselemente und Überraschungen.",
        "einstellungen": {
            "nacht_zeit_sekunden": 45,
            "tag_diskussion_minuten": 3,
            "abstimmung_zeit_sekunden": 20,
            "tote_duerfen_reden": True,  # Geister dürfen flüstern
            "rolle_bei_tod_zeigen": False,  # Rollen bleiben geheim
            "zufalls_ereignisse": True,
        },
    },
    "profi": {
        "name": "Profi-Modus",
        "beschreibung": "Für erfahrene Spieler. Weniger Hinweise, mehr Strategie.",
        "einstellungen": {
            "nacht_zeit_sekunden": 90,
            "tag_diskussion_minuten": 7,
            "abstimmung_zeit_sekunden": 45,
            "tote_duerfen_reden": False,
            "rolle_bei_tod_zeigen": False,
            "hinweise_aktiviert": False,  # Keine visuellen Hinweise
        },
    },
    "party": {
        "name": "Party-Modus",
        "beschreibung": "Lockere Regeln für Partys und große Gruppen.",
        "einstellungen": {
            "nacht_zeit_sekunden": 45,
            "tag_diskussion_minuten": 4,
            "abstimmung_zeit_sekunden": 20,
            "tote_duerfen_reden": True,
            "rolle_bei_tod_zeigen": True,
            "mehrfach_stimmen_erlaubt": True,
        },
    },
}


# ============================================================================
# ROLLEN DEFINITIONEN - Vollstaendige Sammlung
# Basierend auf: https://werwolf.fandom.com/de/wiki/Werwolf-Rollen-Sammlung
# Icons: FontAwesome 6 (https://fontawesome.com/icons)
#
# HINWEIS: Diese Definition ist nur noch fuer Abwaertskompatibilitaet.
# Neue Rollen werden in roles/ als eigene Klassen definiert!
# Siehe roles/README.md fuer Details.


# ============================================================================
# DYNAMISCHES ROLLEN-SYSTEM
# Alle Rollen werden jetzt aus roles/*.py geladen.
# Um eine neue Rolle hinzuzufügen: Einfach eine .py-Datei in roles/ erstellen!
# ============================================================================


def _erstelle_rollen_dict():
    """
    Erstellt das ROLLEN-Dict dynamisch aus dem modularen System (roles/*.py).

    Neue Rollen einfach als *.py-Datei in roles/ hinzufügen - sie werden
    automatisch erkannt und registriert!
    """
    try:
        from roles import get_alle_rollen

        logger.debug("Loading roles from registry...")
        return get_alle_rollen()
    except Exception as e:
        logger.error(f"[ROLLEN] Fehler beim Laden: {e}")
        print(f"[ROLLEN] Fehler beim Laden: {e}")
        return {}


# Das eigentliche ROLLEN-Dict (wird beim Import erstellt)
ROLLEN = _erstelle_rollen_dict()


# Spielphasen in korrekter Reihenfolge (importiert aus phases.py)
PHASEN = get_phase_list()


# Rollen-Konfiguration nach Spielerzahl (Empfehlung)
# For games larger than defined here, use berechne_rollen() from game_logic.py
ROLLEN_EMPFEHLUNG = {
    5: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Dorfbewohner",
        "Dorfbewohner",
    ],  # TODO: REMOVE ROLE BASED HARDCODING
    6: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Dorfbewohner",
        "Dorfbewohner",
    ],  # TODO: REMOVE ROLE BASED HARDCODING
    7: [  # TODO: REMOVE ROLE BASED HARDCODING #TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    8: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    9: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",  # TODO: REMOVE ROLE BASED HARDCODING
        "Jaeger",
        "Amor",
        "Heiler",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    10: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    11: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    12: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Zwei Schwestern",
        "Zwei Schwestern",
        "Dorfbewohner",
    ],
    13: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Weisser Wolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    14: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Weisser Wolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    15: [  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",  # TODO: REMOVE ROLE BASED HARDCODING
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",  # TODO: REMOVE ROLE BASED HARDCODING
        "Medium",
        "Rabe",
        "Dorfbewohner",
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",
    ],
    16: [
        "Werwolf",
        "Werwolf",
        "Werwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",  # TODO: REMOVE ROLE BASED HARDCODING
        "Alter Mann",
        "Medium",
        "Rabe",  # TODO: REMOVE ROLE BASED HARDCODING
        "Prinz",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    17: [
        "Werwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Urwolf",
        "Seherin",  # TODO: REMOVE ROLE BASED HARDCODING
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Prinz",
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
    ],
    18: [
        "Werwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Werwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Urwolf",  # TODO: REMOVE ROLE BASED HARDCODING
        "Seherin",  # TODO: REMOVE ROLE BASED HARDCODING
        "Hexe",  # TODO: REMOVE ROLE BASED HARDCODING
        "Jaeger",  # TODO: REMOVE ROLE BASED HARDCODING
        "Amor",  # TODO: REMOVE ROLE BASED HARDCODING
        "Heiler",  # TODO: REMOVE ROLE BASED HARDCODING
        "Alter Mann",  # TODO: REMOVE ROLE BASED HARDCODING
        "Medium",  # TODO: REMOVE ROLE BASED HARDCODING
        "Rabe",  # TODO: REMOVE ROLE BASED HARDCODING
        "Prinz",  # TODO: REMOVE ROLE BASED HARDCODING
        "Floetenspieler",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
        "Dorfbewohner",  # TODO: REMOVE ROLE BASED HARDCODING
    ],
}


def berechne_balance_statistik(spieler_anzahl: int) -> dict:
    """
    Calculate balance statistics for a given player count.
    Useful for verifying game balance.

    Args:
        spieler_anzahl: Number of players

    Returns:
        Dictionary with balance statistics
    """
    from game_logic import berechne_rollen

    rollen = berechne_rollen(spieler_anzahl)

    # Calculate team sizes
    team_dorf = 0
    team_werwolf = 0
    team_solo = 0
    team_andere = 0  # Vampire, Zombie, etc. #TODO: REMOVE ROLE BASED HARDCODING

    for rolle_name, anzahl in rollen.items():
        if rolle_name == "Erzaehler":
            continue
        rolle_info = ROLLEN.get(rolle_name, {})
        team = rolle_info.get("team", "dorf")

        if team == "dorf":
            team_dorf += anzahl
        elif team == "werwolf":
            team_werwolf += anzahl
        elif team == "solo":
            team_solo += anzahl
        else:
            team_andere += anzahl

    total = team_dorf + team_werwolf + team_solo + team_andere

    return {
        "total_players": spieler_anzahl,
        "team_dorf": team_dorf,
        "team_werwolf": team_werwolf,
        "team_solo": team_solo,
        "team_andere": team_andere,
        "dorf_prozent": round(team_dorf / total * 100, 1) if total > 0 else 0,
        "werwolf_prozent": round(team_werwolf / total * 100, 1)
        if total > 0
        else 0,  # TODO: REMOVE ROLE BASED HARDCODING
        "solo_prozent": round(team_solo / total * 100, 1) if total > 0 else 0,
        "andere_prozent": round(team_andere / total * 100, 1) if total > 0 else 0,
        "rollen": rollen,
        "balance_ratio": f"1:{round(team_dorf / team_werwolf, 1) if team_werwolf > 0 else 0}",
    }


# Teams und ihre Gewinnbedingungen (imported from constants.py - kept here for legacy compatibility)
# Use: from constants import TEAMS instead


# ============================================================================
# HELFER-FUNKTIONEN FUER ROLLEN
# diese Funktionen nutzen das dynamische ROLLEN-Dict
# ============================================================================


def get_rollen_nach_kategorie():
    """
    Gibt alle Rollen gruppiert nach Kategorie zurueck.
    Format: dict[kategorie][rolle_name] = rolle_data

    Diese Funktion wird bei jedem Aufruf neu berechnet,
    um auch zur Laufzeit hinzugefuegte Rollen zu beruecksichtigen.
    """
    kategorien = {}
    rollen_dict = _erstelle_rollen_dict()  # Frisch laden
    for rolle_name, rolle_data in rollen_dict.items():
        kat = rolle_data.get("kategorie", "sonstige")
        if kat not in kategorien:
            kategorien[kat] = {}
        kategorien[kat][rolle_name] = rolle_data

    return kategorien


def get_rollen_nach_kategorie_liste():
    """
    Gibt alle Rollen gruppiert nach Kategorie als Liste zurueck.
    Format: dict[kategorie] = [rolle_data, ...]
    sortiert nach ID innerhalb jeder Kategorie.
    """
    kategorien = {}
    rollen_dict = _erstelle_rollen_dict()  # Frisch laden
    for rolle_name, rolle_data in rollen_dict.items():
        kat = rolle_data.get("kategorie", "sonstige")
        if kat not in kategorien:
            kategorien[kat] = []
        kategorien[kat].append({"name": rolle_name, **rolle_data})

    # Sortiere nach ID innerhalb jeder Kategorie
    for kat in kategorien:
        kategorien[kat].sort(key=lambda x: x.get("id", 999))

    return kategorien


# Kategorienamen für UI (mit schönen deutschen Namen)
KATEGORIE_NAMEN = {
    "grundrollen": "Grundrollen",
    "dorfbewohner": "Dorfbewohner-Varianten",
    "werwolf": "Werwolf-Varianten",
    "seher": "Sehende Rollen",
    "hexe": "Hexen & Zauberer",
    "jaeger": "Jaeger & Kaempfer",
    "heiler": "Heiler & Beschuetzer",
    "spezial": "Spezialrollen",
    "boese": "Boese Wesen",
    "solo": "Einzelkaempfer",
    "sonstige": "Sonstige Rollen",
}


def get_rollen_anzahl():
    """Gibt die Anzahl aller verfügbaren Rollen zurück."""
    return len(_erstelle_rollen_dict())
