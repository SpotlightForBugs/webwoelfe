"""
Webwoelfe - Das Online Werwolf-Spiel
Ein Echtzeit-Multiplayer Werwolf-Spiel mit WebSocket-Unterstützung.
"""

# Gevent monkey-patching MUSS vor allen anderen Imports erfolgen!
# (Gevent ist der moderne Ersatz für das deprecated eventlet)
from gevent import monkey
import gevent
import inspect
from functools import wraps
from flask_minify import Minify

monkey.patch_all()

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_migrate import Migrate
from models import (
    db,
    Raum,
    Spieler,
    SpielAktion,
    SpielLog,
    ROLLEN,
    PHASEN,
    ERZAEHLER_EVENTS,
    get_rollen_nach_kategorie,
    get_rollen_nach_kategorie_liste,
    get_rollen_anzahl,
)
from constants import TEAMS, SPIEL_REGELN, ROLLEN_EMPFEHLUNG
from roles import get_rollen_nach_erweiterung, ERWEITERUNG_INFO, KATEGORIE_INFO
from logger import logger
import game_logic
import secrets
import os
import random
from datetime import datetime, timezone

# App Konfiguration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


# Database configuration: prefer env-provided URI (e.g., Postgres in Docker)
def _resolve_database_uri() -> str:
    # Common env var names
    uri = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if uri:
        # Normalize deprecated postgres:// scheme to postgresql:// for SQLAlchemy
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    # Default to local SQLite when no env var is set
    return "sqlite:///webwoelfe.db"


app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
Minify(app=app, html=True, js=True, cssless=True)


# =============================================================================
# TEMPLATE HELPERS - For CSS inlining
# =============================================================================


@app.context_processor
def inject_css_reader():
    """Inject a function to read CSS files for inlining."""

    def read_css(filename):
        """Read a CSS file from static folder for inlining."""
        try:
            if app.static_folder is None:
                raise ValueError("Static folder is not configured")
            css_path = os.path.join(app.static_folder, filename)
            with open(css_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not read CSS file {filename}: {e}")
            return f"/* Error loading {filename} */"  # Make this also a console.log error in the browser

    return dict(read_css=read_css)


@app.context_processor
def inject_cache_buster():
    """Inject a function to add cache busting query parameters to static files."""

    def versioned_url(endpoint, **values):
        """
        Generate a URL with a cache-busting query parameter based on file modification time.
        Usage in templates: {{ versioned_url('static', filename='js/dist/hints.js') }}
        """
        if endpoint == "static" and "filename" in values:
            filename = values["filename"]
            try:
                if app.static_folder is None:
                    raise ValueError("Static folder is not configured")
                filepath = os.path.join(app.static_folder, filename)
                if os.path.exists(filepath):
                    # Get file modification time as cache buster
                    mtime = int(os.path.getmtime(filepath))
                    values["v"] = mtime
            except Exception as e:
                logger.warning(f"Could not get mtime for {filename}: {e}")
                # Fallback to timestamp if file doesn't exist or error
                values["v"] = int(datetime.now(timezone.utc).timestamp())

        return url_for(endpoint, **values)

    return dict(versioned_url=versioned_url)


# Automatic phases that advance immediately after audio (no player interaction needed)
# These are pure transition/info phases
AUTOMATISCHE_PHASEN = {
    "rollen_verteilt",  # Info-Phase nach Spielstart
    "nacht_start",  # Übergang Tag -> Nacht
    "nacht_ende",  # Übergang Nacht -> Tag
    "tag_start",  # Übergang Nacht -> Tag
    "tag_ende",  # Übergang am Tagesende
}

# Spielname als Konstante
SPIEL_NAME = "Webwölfe"

# Phasen-Konfiguration
# Wartezeit zwischen automatischen Phasenwechseln (in Sekunden)
# Mindestens 30 Sekunden um Audio-Erzählung vollständig abzuspielen
PHASE_WECHSEL_DELAY = int(os.environ.get("PHASE_DELAY", "45"))

# Minimum delay before accepting audio_fertig (in seconds)
# This prevents duplicate events from the same client but allows quick phase transitions
AUDIO_FERTIG_MIN_DELAY = float(os.environ.get("AUDIO_MIN_DELAY", "1.0"))

# Track audio completion per player in each phase with specific audio file
# Key: (room_code, phase_name, audio_filename), Value: set of player_ids who confirmed audio_fertig
# This ensures we track completion of the SPECIFIC audio file, not just any audio in that phase
_audio_fertig_players: dict[tuple[str, str, str], set[int]] = {}

# Minimum percentage of players that must confirm audio before auto-advance (80%)
AUDIO_CONFIRMATION_THRESHOLD = float(os.environ.get("AUDIO_THRESHOLD", "0.8"))


# ============================================================================

# ============================================================================
# LOGGING SYSTEM
# ============================================================================


def log_ts(msg: str):
    """Log mit Timestamp für Debugging"""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_entry = f"[{ts}] {msg}"
    print(log_entry)


def _apply_action_effects(ergebnis, spieler, targets, raum, kontext):
    """
    Apply effects from an AktionsErgebnis to the game state.

    This centralizes effect handling that was previously hardcoded for each role.
    Effects are defined dynamically by each role's execute_action method.
    """
    if not ergebnis:
        return

    effekte = ergebnis.effekte or {}

    # 1. Generic State Updates for other players
    if ergebnis.multi_target_updates:
        for t_id, updates in ergebnis.multi_target_updates.items():
            t_spieler = db.session.get(Spieler, int(t_id))
            if t_spieler:
                for key, value in updates.items():
                    t_spieler.set_state(key, value)

    # 2. Generic Logging
    if ergebnis.additional_logs:
        for log_def in ergebnis.additional_logs:
            game_logic.log_eintrag(
                raum.id,
                log_def["text"],
                sichtbar_fuer=str(log_def.get("sichtbar_fuer", "alle")),
            )

    # Handle kill effects
    if "toeten" in effekte:
        ziel_id = effekte["toeten"]
        todesursache = effekte.get("todesursache", "unbekannt")
        ziel = db.session.get(Spieler, ziel_id)
        if ziel:
            game_logic.toete_spieler(ziel, todesursache)
            socketio.emit(
                "spieler_gestorben",
                {
                    "spieler_id": ziel.id,
                    "spieler_name": ziel.name,
                    "todesart": todesursache,
                    "rolle": ziel.rolle,
                },
                room=raum.code,  # pyright: ignore[reportCallIssue]
            )

    # Handle phase trigger effects
    if "trigger_phase" in effekte:
        phase_name = effekte["trigger_phase"]
        log_ts(f"[Effekt] Triggering special phase: {phase_name}")
        raum.aktuelle_phase = phase_name

    # Handle state updates from the result
    if ergebnis.state_updates:
        for key, value in ergebnis.state_updates.items():
            spieler.set_state(key, value)

    # Handle private info notifications
    if ergebnis.private_infos:
        for player_id, info in ergebnis.private_infos.items():
            if "overlay" in info:
                socketio.emit(
                    "zeige_overlay",
                    info["overlay"],
                    room=f"player_{player_id}",  # pyright: ignore[reportCallIssue]
                )
            if "nachricht" in info:
                socketio.emit(
                    "private_nachricht",
                    {
                        "nachricht": info["nachricht"],
                        "typ": info.get("alert_type", "info"),
                    },
                    room=f"player_{player_id}",  # pyright: ignore[reportCallIssue]
                )


# Initialisierung
db.init_app(app)
Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")


# ============================================================================
# TEMPLATE FILTER - Jinja2 Filter
# ============================================================================


@app.template_filter("css_class")
def css_class_filter(value):
    """
    Konvertiert einen String zu einem CSS-klassen-kompatiblen Format.
    z.B. "Hexe" -> "hexe", "Alter Mann" -> "alter-mann"
    """
    if not value:
        return "unbekannt"
    # Kleinbuchstaben, Leerzeichen durch Bindestriche ersetzen, Sonderzeichen entfernen
    import re

    result = str(value).lower()
    result = result.replace(" ", "-")
    result = (
        result.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    result = re.sub(r"[^a-z0-9\-]", "", result)
    return result


def get_rollen_styles():
    """
    Generiert ein Dictionary mit Rollen-Styles für das Template.
    Verwendet die RoleRegistry, um dynamische Styles zu erstellen.
    """
    from roles import RoleRegistry

    styles = {}
    for role in RoleRegistry.get_all():
        info = role.info
        css_class = info.computed_css_class

        # Defaults if not set
        grad_from = info.avatar_gradient_from or info.farbe or "#4a5568"
        grad_to = info.avatar_gradient_to or grad_from
        border = info.avatar_border_color or info.farbe or "#5a6678"

        styles[css_class] = {
            "name": info.name,
            "team": info.team.value if info.team else "",
            "avatar_gradient_from": grad_from,
            "avatar_gradient_to": grad_to,
            "avatar_border_color": border,
            "badge_emoji": info.badge_emoji or "",
        }

    return styles


# Datenbank-Migrationen werden per Alembic/Flask-Migrate verwaltet.
# Für lokale Entwicklung optional automatische Schemaerstellung aktivieren:
if os.environ.get("AUTO_DB_CREATE_ALL", "0") == "1":
    with app.app_context():
        db.create_all()


# ============================================================================
# KONTEXT-PROZESSOR - Globale Template-Variablen
# ============================================================================


@app.context_processor
def inject_globals():
    """Stellt globale Variablen fuer alle Templates bereit"""
    return {
        "debug": app.debug,
        "spiel_name": SPIEL_NAME,
        "alle_rollen": ROLLEN,
        "alle_teams": TEAMS,
        "rollen_nach_kategorie": get_rollen_nach_kategorie(),
        "rollen_nach_erweiterung": get_rollen_nach_erweiterung(),
        "erweiterung_info": ERWEITERUNG_INFO,
        "kategorie_info": KATEGORIE_INFO,
    }


# ============================================================================
# AUDIO-HELPER - Text-to-Speech Funktionen
# ============================================================================


def generiere_erzaehler_audio(text: str, stil: str = "normal") -> str | None:
    """
    Generiert Audio für Erzähler-Text mittels Edge-TTS.

    Args:
        text: Der zu sprechende Text
        stil: Der Sprechstil (normal, dramatisch, etc.)

    Returns:
        URL-Pfad zur Audio-Datei oder None bei Fehler
    """
    try:
        from audio import (
            text_zu_audio_sync,
            text_zu_audio_elevenlabs_sync,
            elevenlabs_aktiv,
        )

        audio_path = None

        # Try ElevenLabs first if enabled
        if elevenlabs_aktiv():
            try:
                audio_path = text_zu_audio_elevenlabs_sync(text, stil=stil)
                if audio_path:
                    log_ts(f"[Audio] Generated with ElevenLabs")
            except Exception as e:
                log_ts(f"[Audio] ElevenLabs failed: {e}, falling back to Edge-TTS")

        # Fallback to Edge-TTS if ElevenLabs failed or not enabled
        if not audio_path:
            try:
                audio_path = text_zu_audio_sync(text, stil=stil)
                if audio_path:
                    log_ts(f"[Audio] Generated with Edge-TTS")
            except Exception as e:
                log_ts(f"[Audio] Edge-TTS failed: {e}")

        if audio_path:
            # Konvertiere relativen Pfad zu URL-Pfad
            url_path = "/" + audio_path.replace("\\", "/")
            log_ts(f"[Audio] Final path: {url_path}")
            return url_path

        log_ts(f"[Audio] ERROR: Could not generate audio for text: {text[:50]}...")
        return None
    except Exception as e:
        print(f"Fehler bei Audio-Generierung: {e}")
        import traceback

        traceback.print_exc()
        return None


# ============================================================================
# HTTP ROUTEN
# ============================================================================


@app.route("/")
def index():
    """Startseite mit Spielmodus-Auswahl"""
    return render_template("index.html")


@app.route("/rollen")
def rollen_uebersicht():
    """Uebersicht aller Rollen"""
    kategorien = get_rollen_nach_kategorie_liste()
    return render_template(
        "rollen.html", kategorien=kategorien, rollen_anzahl=get_rollen_anzahl()
    )


@app.route("/raum/erstellen", methods=["POST"])
def raum_erstellen():
    """Erstellt einen neuen Spielraum"""
    modus = request.form.get("modus", "online")
    name = request.form.get("raum_name", "Webwölfe Runde")
    spieler_name = request.form.get("spieler_name", "Spielleiter")
    erzaehler_modus = request.form.get("erzaehler_modus", "selbst")
    ist_erzaehler = erzaehler_modus == "selbst"

    # Raum erstellen
    # Spieleranzahl wird jetzt dynamisch aus der Lobby berechnet – keine manuelle Eingabe nötig
    raum = Raum(  # pyright: ignore[reportCallIssue]
        code=Raum.generiere_code(),
        name=name,
        modus=modus,
        spieler_anzahl=0,
        erzaehler_modus=erzaehler_modus,
    )
    db.session.add(raum)
    db.session.flush()

    # Ersteller als ersten Spieler hinzufuegen
    session_id = Spieler.generiere_session()
    spieler = Spieler(  # pyright: ignore[reportCallIssue]
        name=spieler_name[:30],
        session_id=session_id,
        raum_id=raum.id,
        ist_erzaehler=ist_erzaehler,
    )
    db.session.add(spieler)

    if ist_erzaehler:
        raum.erzaehler_id = spieler.id

    db.session.commit()

    # Session setzen
    session["spieler_session"] = session_id
    session["raum_code"] = raum.code

    return redirect(url_for("lobby", code=raum.code))


@app.route("/raum/beitreten", methods=["POST"])
def raum_beitreten():
    """Tritt einem existierenden Raum bei"""
    code = request.form.get("code", "").upper().strip()
    spieler_name = request.form.get("spieler_name", "Spieler")

    raum = Raum.query.filter_by(code=code).first()

    if not raum:
        return render_template("index.html", fehler="Raum nicht gefunden!")

    if raum.spiel_gestartet:
        return render_template("index.html", fehler="Das Spiel hat bereits begonnen!")

    # Pruefen ob Name bereits vergeben
    existiert = Spieler.query.filter_by(raum_id=raum.id, name=spieler_name[:30]).first()
    if existiert:
        return render_template("index.html", fehler="Dieser Name ist bereits vergeben!")

    # Spieler erstellen
    session_id = Spieler.generiere_session()
    spieler = Spieler(name=spieler_name[:30], session_id=session_id, raum_id=raum.id)  # type: ignore[call-arg]
    db.session.add(spieler)
    db.session.commit()

    session["spieler_session"] = session_id
    session["raum_code"] = raum.code

    return redirect(url_for("lobby", code=raum.code))


@app.route("/lobby/<code>")
def lobby(code):
    """Lobby-Ansicht eines Raums"""
    raum = Raum.query.filter_by(code=code).first_or_404()
    spieler = hole_aktuellen_spieler()

    if not spieler or spieler.raum_id != raum.id:
        return redirect(url_for("index"))

    if raum.spiel_gestartet:
        return redirect(url_for("spiel", code=code))

    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()
    erzaehler = next((s for s in alle_spieler if s.ist_erzaehler), None)
    spieler_ohne_erzaehler = [s for s in alle_spieler if not s.ist_erzaehler]
    aktuelle_spielerzahl = len(spieler_ohne_erzaehler)
    ziel_spielerzahl = max(5, aktuelle_spielerzahl)
    raum.spieler_anzahl = ziel_spielerzahl
    db.session.commit()

    fehlende_spieler = max(0, 5 - aktuelle_spielerzahl)
    rollen_vorschau_total = max(5, aktuelle_spielerzahl) + (1 if erzaehler else 0)
    rollen_vorschau = game_logic.berechne_rollen(
        rollen_vorschau_total, mit_erzaehler=bool(erzaehler)
    )

    return render_template(
        "lobby.html",
        raum=raum,
        spieler=spieler,
        alle_spieler=alle_spieler,
        erzaehler=erzaehler,
        rollen=ROLLEN,
        rollen_vorschau=rollen_vorschau,
        rollen_vorschau_total=rollen_vorschau_total,
        rollen_vorschau_hat_erzaehler=bool(erzaehler),
        fehlende_spieler=fehlende_spieler,
        ist_spiel_bereit=fehlende_spieler == 0,
    )


@app.route("/spiel/<code>")
def spiel(code):
    """Hauptspielansicht"""
    raum = Raum.query.filter_by(code=code).first_or_404()
    spieler = hole_aktuellen_spieler()

    if not spieler or spieler.raum_id != raum.id:
        return redirect(url_for("index"))

    if not raum.spiel_gestartet:
        return redirect(url_for("lobby", code=code))

    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).order_by(Spieler.name).all()
    lebende = [s for s in alle_spieler if s.ist_am_leben]

    # Rolle-Info holen - SICHER: Nur eigene Rolle wird mitgegeben
    rolle_info = ROLLEN.get(spieler.rolle, {})

    # Debug logging für Rolle
    if spieler.rolle:
        log_ts(
            f"[Spiel] Spieler {spieler.name} hat Rolle: {spieler.rolle}, Team: {rolle_info.get('team', 'NICHT GEFUNDEN')}"
        )

    # Logs fuer Spieler - SICHER: Nur fuer den Spieler sichtbare Logs
    if spieler.ist_erzaehler:
        logs = (
            SpielLog.query.filter_by(raum_id=raum.id)
            .order_by(SpielLog.zeitpunkt.desc())
            .limit(50)
            .all()
        )
    else:
        # Uses SichtbarkeitFuerWoelfe.ALLE enum value for visibility check
        from roles.enums import SichtbarkeitFuerWoelfe

        logs = (
            SpielLog.query.filter(
                SpielLog.raum_id == raum.id,
                db.or_(
                    SpielLog.sichtbar_fuer == SichtbarkeitFuerWoelfe.ALLE.value,
                    SpielLog.sichtbar_fuer == str(spieler.id),
                    SpielLog.sichtbar_fuer == spieler.rolle,
                ),
            )
            .order_by(SpielLog.zeitpunkt.desc())
            .limit(20)
            .all()
        )

    # Seherin-Enthüllungen als SNAPSHOT holen (ändern sich nicht bei Rollenänderung)
    seherin_enthuellung = {}
    try:
        from models import SeherinEnthuellung
        from roles import RoleRegistry
        from roles.enums import AktionsTyp

        role_obj = RoleRegistry.get(spieler.rolle)
        # Check if role has SEHEN action type (Seherin mechanism)
        if role_obj and role_obj.aktions_typ == AktionsTyp.SEHEN:
            seherin_enthuellung = SeherinEnthuellung.hole_enthuellung(
                spieler.id, raum.id
            )
    except Exception:
        log_ts(
            "[Spiel] Seherin-Enthüllungen konnten nicht geladen werden. Tabelle existiert vielleicht noch nicht."
        )
        pass  # Tabelle existiert vielleicht noch nicht

    # SICHER: Spieler-Daten werden OHNE Rollen (ausser eigene) gesendet
    sichere_spieler = []
    for s in alle_spieler:
        spieler_data = {
            "id": s.id,
            "name": s.name,
            "ist_am_leben": s.ist_am_leben,
            "ist_erzaehler": s.ist_erzaehler,
        }
        # Rolle nur fuer sich selbst oder tote Spieler (nach Tod enthüllt)
        if s.id == spieler.id:
            spieler_data["rolle"] = s.rolle
        elif not s.ist_am_leben:
            spieler_data["rolle"] = s.rolle
        # Werewolves see each other (uses dynamic role registry for team check)
        elif game_logic.ist_werwolf_rolle(
            spieler.rolle
        ) and game_logic.ist_werwolf_rolle(s.rolle):
            spieler_data["ist_werwolf"] = True  # Mark as werewolf for frontend

        # =========================================================================
        # DYNAMIC VISIBILITY - Replaces hardcoded Amor/lover checks
        # =========================================================================
        # Get all GlobalStateDefinitions from registered roles
        from roles.base import get_player_visual_effects
        from roles import RoleRegistry

        global_state_defs = RoleRegistry.get_all_global_state_definitions_objects()

        # Get visual effects for this player, filtered by viewer visibility
        player_effects = get_player_visual_effects(
            s, global_state_defs, viewer_id=spieler.id, viewer_rolle=spieler.rolle
        )

        # Apply effects to player data
        for effect in player_effects:
            # Mark player with the effect's CSS class
            if effect.get("css_class"):
                spieler_data.setdefault("effect_classes", []).append(
                    effect["css_class"]
                )

            # Mark visual effect type (e.g., "heart" for lovers)
            if effect.get("visual_effect"):
                spieler_data.setdefault("visual_effects", []).append(
                    effect["visual_effect"]
                )
                # Special handling for known effect types
                if effect["visual_effect"] == "heart":
                    spieler_data["ist_verliebt"] = True

            # If this effect reveals the target's role, include it
            if effect.get("reveals_role") and effect.get("revealed_role"):
                spieler_data["rolle"] = effect["revealed_role"]
                spieler_data["ist_partner"] = True  # Mark as partner for UI styling

            # Add icon if present
            if effect.get("icon"):
                spieler_data.setdefault("effect_icons", []).append(effect["icon"])

        sichere_spieler.append(spieler_data)

    # Erzähler-Text für Gruppen-Modus
    erzaehler_text = None
    if spieler.ist_erzaehler and raum.modus == "gruppe":
        phase_key = raum.aktuelle_phase
        if phase_key in ERZAEHLER_EVENTS:
            erzaehler_text = ERZAEHLER_EVENTS[phase_key]

    enthuellung = {
        ziel_id: data["typ"] for ziel_id, data in seherin_enthuellung.items()
    }

    return render_template(
        "spiel.html",
        raum=raum,
        spieler=spieler,
        sichere_spieler=sichere_spieler,
        alle_spieler=alle_spieler,
        lebende=lebende,
        rolle_info=rolle_info,
        logs=logs,
        phasen=PHASEN,
        erzaehler_text=erzaehler_text,
        enthuellung=enthuellung,  # Seherin-Snapshot
        rollen_styles=get_rollen_styles(),  # Dynamische Rollen-Styles
    )


# ============================================================================
# ROLE API - Dynamic UI and Phase Generation
# ============================================================================


@app.route("/api/role/<role_name>/ui", methods=["GET"])
def get_role_ui(role_name):
    """Get UI definition for a specific role."""
    from roles import RoleRegistry, SpielKontext
    from roles.enums import Phase

    rolle = RoleRegistry.get(role_name)
    if not rolle:
        return jsonify({"success": False, "error": "Role not found"}), 404

    ui = rolle.get_ui_definition()
    ui_dict = ui.to_dict()

    # DYNAMIC INJECTION: If player is active in this phase, add phase start info
    spieler = hole_aktuellen_spieler()
    if spieler and spieler.raum_id:
        raum = db.session.get(Raum, spieler.raum_id)
        if raum and raum.aktuelle_phase == rolle.get_phase_name():
            # Build context to get dynamic info
            werwolf_opfer_id = None

            # Use role property to decide if we need the victim info (dynamic)
            if rolle.requires_victim_info:
                ww_result = game_logic.werwolf_abstimmung(raum)
                if ww_result and "opfer_id" in ww_result:
                    werwolf_opfer_id = ww_result["opfer_id"]

            kontext = SpielKontext(
                raum_id=raum.id,
                runde=raum.runde,
                phase=(
                    Phase(raum.aktuelle_phase)
                    if raum.aktuelle_phase in [p.value for p in Phase]
                    else raum.aktuelle_phase
                ),
                aktiver_spieler_id=spieler.id,
                lebende_spieler=[s.id for s in game_logic.hole_lebende_spieler(raum)],
                tote_spieler=[
                    s.id
                    for s in Spieler.query.filter_by(
                        raum_id=raum.id, ist_am_leben=False
                    ).all()
                ],
                werwolf_opfer_id=werwolf_opfer_id,
            )

            # Get dynamic info
            start_info = rolle.get_phase_start_info(spieler, kontext)

            # Inject victim info into instructions if present (uses role's requires_victim_info property)
            if start_info and "werwolf_opfer_id" in start_info:
                opfer = db.session.get(Spieler, start_info["werwolf_opfer_id"])
                if opfer:
                    # Append victim info to instructions
                    ui_dict["instructions"] += (
                        f" <br><strong>Das Werwolf-Opfer ist: {opfer.name}</strong>"
                    )

    return jsonify(
        {
            "success": True,
            "ui": ui_dict,
            "phase_name": rolle.get_phase_name(),
        }
    )


@app.route("/api/roles", methods=["GET"])
def get_all_roles_api():
    """
    Get all roles with complete metadata for UI generation.

    Query Parameters:
    - extension_pack: Filter by extension (base, neumond, gemeinde, charaktere, sonderedition)
    - kategorie: Filter by category
    - team: Filter by team (dorf, werwolf, solo)

    Returns comprehensive role data including:
    - name, id, team, category
    - icon (FontAwesome), color (hex)
    - extension_pack for filtering
    - description, phase_name
    - UI definition (buttons, prompts)
    """
    from roles import RoleRegistry

    # Get query parameters
    extension_filter = request.args.get("extension_pack")
    kategorie_filter = request.args.get("kategorie")
    team_filter = request.args.get("team")

    # Get all roles
    all_roles = RoleRegistry.get_all()

    # Apply filters
    filtered_roles = all_roles
    if extension_filter:
        filtered_roles = [
            r for r in filtered_roles if r.info.extension_pack == extension_filter
        ]
    if kategorie_filter:
        from roles.enums import Kategorie

        filtered_roles = [
            r for r in filtered_roles if r.info.kategorie.value == kategorie_filter
        ]
    if team_filter:
        from roles.enums import Team

        filtered_roles = [r for r in filtered_roles if r.info.team.value == team_filter]

    # Convert to dict format
    roles_data = [role.to_dict() for role in filtered_roles]

    # Group by extension pack for frontend convenience
    grouped_by_extension = {}
    for role in filtered_roles:
        try:
            ext_pack = role.info.extension_pack
            if ext_pack not in grouped_by_extension:
                grouped_by_extension[ext_pack] = []
            grouped_by_extension[ext_pack].append(role.to_dict())
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der Rolle {role}: {e}")
            continue

    return jsonify(
        {
            "success": True,
            "roles": roles_data,
            "grouped_by_extension": grouped_by_extension,
            "total_count": len(roles_data),
        }
    )


@app.route("/api/role/<role_name>/info", methods=["GET"])
def get_role_info_api(role_name):
    """Get complete information about a role."""
    from roles import RoleRegistry

    rolle = RoleRegistry.get(role_name)
    if not rolle:
        return jsonify({"success": False, "error": "Role not found"}), 404

    return jsonify(
        {
            "success": True,
            "role": rolle.to_dict(),
        }
    )


@app.route("/api/game/<code>/phases", methods=["GET"])
def get_game_phases(code):
    """Get dynamic phase list and phase-role mapping for a specific game."""
    from phase_generator import (
        generate_phases_for_game,
        get_phase_display_info,
        build_phase_role_mapping,
    )

    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Room not found"}), 404

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"success": False, "error": "Not authorized"}), 403

    # Don't generate phases if game hasn't started yet (roles not distributed)
    if not raum.spiel_gestartet or not any(s.rolle for s in raum.spieler):
        return jsonify(
            {"success": True, "phases": [], "phase_info": [], "phase_mapping": {}}
        )

    phases = generate_phases_for_game(raum)
    phase_info = [get_phase_display_info(p) for p in phases]
    phase_mapping = build_phase_role_mapping(raum)

    return jsonify(
        {
            "success": True,
            "phases": phases,
            "phase_info": phase_info,
            "phase_mapping": phase_mapping,  # NEW: Which role acts in which phase
            "current_phase": raum.aktuelle_phase,
            "current_round": raum.runde,
        }
    )


@app.route("/api/phase/<phase_name>/info", methods=["GET"])
def get_phase_info(phase_name):
    """Get display information for a phase."""
    from phase_generator import get_phase_display_info

    info = get_phase_display_info(phase_name)
    return jsonify(
        {
            "success": True,
            "phase": phase_name,
            "info": info,
        }
    )


@app.route("/api/game/<code>/phase-info", methods=["GET"])
def get_game_phase_info(code):
    """
    Get dynamic phase type information for a game.

    This replaces hardcoded phase lists in the frontend.
    Returns:
        - phase: Current phase name
        - phase_type: "day", "night", or "transition"
        - is_night: Boolean for day/night cycle
        - active_role: Role that is currently acting (if applicable)
        - victim_info: Victim information for roles like Hexe (if applicable)
    """
    from roles import RoleRegistry

    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"success": False, "error": "Nicht autorisiert"}), 403

    phase = raum.aktuelle_phase

    # Determine phase type dynamically
    # Day phases are explicit; night phases are derived from role phases
    known_day_phases = [
        "tag_start",
        "diskussion",
        "abstimmung",
        "hinrichtung",
        "tag_ende",
        "spiel_ende",
        "lobby",
        "rollen_verteilt",
        "diskussion_abstimmung",
        "abstimmung_ergebnis",
    ]

    if phase in known_day_phases:
        phase_type = "day"
        is_night = False
    elif phase.startswith("nacht") or phase == "nacht_start" or phase == "nacht_ende":
        phase_type = "night"
        is_night = True
    elif phase.endswith("_phase"):
        # Role phase - check if it's a night role
        role = RoleRegistry.get_role_for_phase(phase)
        if role:
            # If role has night activity, it's a night phase
            is_active = (
                role.is_active_on_first_night() or role.is_active_on_every_night()
            )
            phase_type = "night" if is_active else "transition"
            is_night = is_active
        else:
            phase_type = "night"  # Default to night for unknown _phase endings
            is_night = True
    else:
        phase_type = "transition"
        is_night = False

    # Get active role for this phase
    active_role = None
    role = RoleRegistry.get_role_for_phase(phase)
    if role:
        active_role = role.info.name

    # Get victim info if applicable (for Hexe, etc.)
    victim_info = None
    if spieler.rolle and active_role:
        viewer_role = RoleRegistry.get(spieler.rolle)
        if viewer_role:
            try:
                # Use from_raum safely
                if hasattr(game_logic.SpielKontext, "from_raum"):
                    kontext = game_logic.SpielKontext.from_raum(raum)
                else:
                    # Fallback manual construction (should not be needed with fix, but safe)
                    from roles.enums import Phase

                    kontext = game_logic.SpielKontext(
                        raum_id=raum.id,
                        runde=raum.runde,
                        phase=(
                            Phase(raum.aktuelle_phase)
                            if raum.aktuelle_phase in [p.value for p in Phase]
                            else raum.aktuelle_phase
                        ),  # type: ignore
                        aktiver_spieler_id=spieler.id,
                        lebende_spieler=[
                            s.id for s in game_logic.hole_lebende_spieler(raum)
                        ],
                        tote_spieler=[
                            s.id
                            for s in Spieler.query.filter_by(
                                raum_id=raum.id, ist_am_leben=False
                            ).all()
                        ],
                    )

                start_info = viewer_role.get_phase_start_info(spieler, kontext)
                if start_info and "werwolf_opfer_id" in start_info:
                    opfer = db.session.get(Spieler, start_info["werwolf_opfer_id"])
                    if opfer:
                        victim_info = {
                            "id": opfer.id,
                            "name": opfer.name,
                        }
            except Exception as e:
                log_ts(f"[Phase Info] Error getting start info: {e}")
                # Don't crash the whole endpoint just because victim info failed
                pass

    return jsonify(
        {
            "success": True,
            "phase": phase,
            "phase_type": phase_type,
            "is_night": is_night,
            "active_role": active_role,
            "victim_info": victim_info,
            "runde": raum.runde,
        }
    )


# ============================================================================
# SITZORDNUNG API - Drag & Drop Sitzplatzwahl
# ============================================================================


@app.route("/api/sitzordnung/<code>", methods=["GET"])
def get_sitzordnung(code):
    """Gibt die aktuelle Sitzordnung zurück"""
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"success": False, "error": "Nicht autorisiert"}), 403

    alle_spieler = (
        Spieler.query.filter_by(raum_id=raum.id, ist_erzaehler=False)
        .order_by(Spieler.sitzplatz, Spieler.id)
        .all()
    )

    return jsonify(
        {
            "success": True,
            "sitzordnung": [
                {
                    "id": s.id,
                    "name": s.name,
                    "sitzplatz": s.sitzplatz if s.sitzplatz is not None else i,
                }
                for i, s in enumerate(alle_spieler)
            ],
        }
    )


@app.route("/api/rollen_vorschau/<code>", methods=["GET"])
def get_rollen_vorschau(code):
    """Gibt die aktuelle Rollenvorschau basierend auf Spieleranzahl zurück"""
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()
    erzaehler = next((s for s in alle_spieler if s.ist_erzaehler), None)
    spieler_ohne_erzaehler = [s for s in alle_spieler if not s.ist_erzaehler]
    aktuelle_spielerzahl = len(spieler_ohne_erzaehler)

    rollen_vorschau_total = max(5, aktuelle_spielerzahl) + (1 if erzaehler else 0)
    rollen_vorschau = game_logic.berechne_rollen(
        rollen_vorschau_total, mit_erzaehler=bool(erzaehler)
    )

    # Rollen mit Farben für Frontend
    rollen_mit_farben = []
    for rollen_name, anzahl in rollen_vorschau.items():
        rolle_info = ROLLEN.get(rollen_name, {})
        rollen_mit_farben.append(
            {
                "name": rollen_name,
                "anzahl": anzahl,
                "farbe": rolle_info.get("farbe", "var(--text-secondary)"),
            }
        )

    return jsonify(
        {
            "success": True,
            "total": rollen_vorschau_total,
            "hat_erzaehler": bool(erzaehler),
            "rollen": rollen_mit_farben,
        }
    )


@app.route("/api/sitzordnung/<code>", methods=["POST"])
def set_sitzordnung(code):
    """Aktualisiert die Sitzordnung"""
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    if raum.spiel_gestartet:
        # Silently ignore seating order updates after game start (race condition)
        return jsonify({"success": True, "ignored": True}), 200

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"success": False, "error": "Nicht autorisiert"}), 403

    data = request.get_json()
    ordnung = data.get("ordnung", [])  # Liste von {id, sitzplatz}

    for eintrag in ordnung:
        s = db.session.get(Spieler, eintrag.get("id"))
        if s and s.raum_id == raum.id:
            s.sitzplatz = eintrag.get("sitzplatz")

    db.session.commit()

    # Broadcastet die neue Sitzordnung an alle Spieler
    socketio.emit("sitzordnung_aktualisiert", {"ordnung": ordnung}, room=raum.code)  # pyright: ignore[reportCallIssue]

    return jsonify({"success": True})


@app.route("/api/phase_role_mapping", methods=["GET"])
def get_phase_role_mapping():
    """
    Gibt ein Mapping von Phasen zu Rollen zurück.
    Ermöglicht Frontend die dynamische Bestimmung ob ein Spieler in einer Phase aktiv ist.
    """
    from roles import RoleRegistry
    from phases import get_phase_list

    mapping = {}

    # Mapping für Nacht-Phasen
    for role in RoleRegistry.get_all():
        # Check if role is active at night using the Role methods, not RollenInfo
        is_nacht_aktiv = (
            role.is_active_on_first_night() or role.is_active_on_every_night()
        )
        if is_nacht_aktiv:
            phase_name = role.get_phase_name()
            mapping[phase_name] = {
                "role_name": role.info.name,
                "team": role.info.team.value,
                "kategorie": role.info.kategorie.value,
            }

    # Zusätzlich: Alle Phasen zurückgeben
    all_phases = get_phase_list()

    return jsonify(
        {
            "success": True,
            "mapping": mapping,
            "all_phases": all_phases,
        }
    )


@app.route("/api/role_info/<role_name>", methods=["GET"])
def get_role_info(role_name):
    """
    Gibt detaillierte Informationen über eine Rolle zurück.
    """
    from roles import RoleRegistry

    role = RoleRegistry.get(role_name)
    if not role:
        return jsonify({"success": False, "error": "Rolle nicht gefunden"}), 404

    return jsonify(
        {
            "success": True,
            "role": role.to_dict(),
        }
    )


@app.route("/api/raum/<code>/status", methods=["GET"])
def get_raum_status(code):
    """Get the current status of a room (is game started, etc.)"""
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    return jsonify(
        {
            "success": True,
            "spiel_gestartet": raum.spiel_gestartet,
            "code": raum.code,
            "aktuelle_phase": raum.aktuelle_phase,
            "runde": raum.runde,
        }
    )


@app.route("/api/raum/<code>/erzaehler/random", methods=["POST"])
def waehle_zufaelligen_erzaehler(code):
    """Wählt einen zufälligen Erzähler aus allen Spielern des Raums."""
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    if raum.spiel_gestartet:
        return jsonify({"success": False, "error": "Spiel bereits gestartet"}), 400

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"success": False, "error": "Nicht autorisiert"}), 403

    if raum.erzaehler_modus != "zufall":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Zufälliger Erzähler ist für diesen Raum nicht aktiviert",
                }
            ),
            400,
        )

    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()
    kandidaten = [s for s in alle_spieler if not s.ist_erzaehler]

    if not kandidaten:
        return jsonify({"success": False, "error": "Keine Kandidaten gefunden"}), 400

    # Entferne bisherigen Erzähler (falls vorhanden)
    for kandidat in alle_spieler:
        if kandidat.ist_erzaehler:
            kandidat.ist_erzaehler = False

    erzaehler = random.choice(kandidaten)
    erzaehler.ist_erzaehler = True
    raum.erzaehler_id = erzaehler.id
    db.session.commit()

    socketio.emit(
        "erzaehler_gewaehlt",
        {"spieler_id": erzaehler.id, "name": erzaehler.name},
        room=raum.code,  # pyright: ignore[reportCallIssue] # pyright: ignore[reportCallIssue]
    )

    return jsonify(
        {"success": True, "erzaehler": {"id": erzaehler.id, "name": erzaehler.name}}
    )


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

from typing import Optional


def hole_aktuellen_spieler() -> Optional[Spieler]:
    """Holt den aktuellen Spieler basierend auf der Session"""
    session_id = session.get("spieler_session")
    if not session_id:
        return None
    return Spieler.query.filter_by(session_id=session_id).first()


# ============================================================================
# CONFIGURATION APIs - Server-side logic for frontend
# ============================================================================


@app.route("/api/config/extension-order", methods=["GET"])
def get_extension_order():
    """
    Get the correct order for extension packs.
    Moved from frontend to ensure consistency.
    """
    return jsonify(
        {
            "success": True,
            "extension_order": [
                "base",
                "neumond",
                "gemeinde",
                "charaktere",
                "sonderedition",
            ],
            "extension_info": {
                "base": {"name": "Basis", "icon": "fa-home", "required": True},
                "neumond": {"name": "Neumond", "icon": "fa-moon"},
                "gemeinde": {"name": "Gemeinde", "icon": "fa-users"},
                "charaktere": {"name": "Charaktere", "icon": "fa-user-friends"},
                "sonderedition": {"name": "Sonderedition", "icon": "fa-star"},
            },
        }
    )


@app.route("/api/roles/preview", methods=["GET"])
def get_random_role_preview():
    """
    Get random role previews for extension packs.
    Replaces frontend logic that just took first 4 roles.

    Query Parameters:
    - extension_pack: Filter by extension pack
    - count: Number of roles to return (default: 4)
    """
    import random
    from roles import RoleRegistry

    extension_pack = request.args.get("extension_pack")
    count = int(request.args.get("count", 4))

    # Get roles for the extension pack
    all_roles = RoleRegistry.get_all()
    if extension_pack:
        filtered_roles = [
            r for r in all_roles if r.info.extension_pack == extension_pack
        ]
    else:
        filtered_roles = all_roles

    # Randomly select roles
    preview_count = min(count, len(filtered_roles))
    selected_roles = (
        random.sample(filtered_roles, preview_count) if filtered_roles else []
    )

    return jsonify(
        {
            "success": True,
            "roles": [{"name": r.info.name, "id": r.info.id} for r in selected_roles],
            "total_in_pack": len(filtered_roles),
            "has_more": len(filtered_roles) > count,
        }
    )


@app.route("/api/phase/is-day", methods=["GET"])
def check_if_phase_is_day():
    """
    Server-authoritative phase type determination.
    Replaces client-side hardcoded phase list.

    Query Parameters:
    - phase: Phase name to check
    """
    phase = request.args.get("phase", "")

    # Definitive day phases
    day_phases = {
        "tag_start",
        "diskussion",
        "abstimmung",
        "hinrichtung",
        "tag_ende",
        "spiel_ende",
        "lobby",
        "rollen_verteilt",
    }

    # Check explicit day phases
    is_day = phase in day_phases

    # Check patterns for day/night classification
    if not is_day:
        is_day = (
            "tag" in phase.lower()
            or "abstimmung" in phase.lower()
            or "diskussion" in phase.lower()
        )

    # Night mode is everything else that has phase indicators
    is_night = not is_day and (
        "nacht" in phase.lower() or "phase" in phase.lower() or phase.endswith("_phase")
    )

    return jsonify(
        {
            "success": True,
            "phase": phase,
            "is_day": is_day,
            "is_night": is_night,
            "phase_type": "day" if is_day else ("night" if is_night else "neutral"),
        }
    )


# ============================================================================
# SERVER-SIDE VILLAGE RENDERING - Komplett serverseitig!
# Clients erhalten NUR fertige Bilder, KEINEN Zugriff auf Spielzustand!
# ============================================================================

# Hinweis-Cache pro Raum (temporär, wird nach Anzeige gelöscht)
_aktive_hinweise = {}  # raum_id -> {spieler_id: (hinweis_typ, intensitaet)}


@app.route("/api/village/<code>")
def api_village(code):
    """
    Gibt Dorf-Daten für 3D-Rendering zurück.

    SICHERHEIT:
    - Keine Rollen-Information
    - Nur öffentliche Daten (Namen, lebendig/tot, Sitzplatz)
    - Hinweise werden vom Server kontrolliert
    """
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"error": "Raum nicht gefunden"}), 404

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"error": "Nicht autorisiert"}), 403

    # Hole Spieler-Daten für 3D-Dorf
    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()
    players = []
    for s in alle_spieler:
        players.append(
            {
                "id": s.id,
                "name": s.name,
                "ist_am_leben": s.ist_am_leben,
                "ist_erzaehler": s.ist_erzaehler,
                "sitzplatz": s.sitzplatz,
            }
        )

    return jsonify(
        {
            "players": players,
            "phase": raum.aktuelle_phase,
            "runde": raum.runde,
        }
    )


# ============================================================================
# WEBSOCKET EVENTS - SICHER: Keine sensiblen Daten werden gebroadcastet
# ============================================================================


def sende_rollen_vorschau_update(raum):
    """Berechnet und sendet die Rollenvorschau an alle Clients im Raum"""
    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()
    erzaehler = next((s for s in alle_spieler if s.ist_erzaehler), None)
    spieler_ohne_erzaehler = [s for s in alle_spieler if not s.ist_erzaehler]
    aktuelle_spielerzahl = len(spieler_ohne_erzaehler)

    rollen_vorschau_total = max(5, aktuelle_spielerzahl) + (1 if erzaehler else 0)
    rollen_vorschau = game_logic.berechne_rollen(
        rollen_vorschau_total, mit_erzaehler=bool(erzaehler)
    )

    # Rollen mit Farben für Frontend
    rollen_mit_farben = []
    for rollen_name, anzahl in rollen_vorschau.items():
        rolle_info = ROLLEN.get(rollen_name, {})
        rollen_mit_farben.append(
            {
                "name": rollen_name,
                "anzahl": anzahl,
                "farbe": rolle_info.get("farbe", "var(--text-secondary)"),
            }
        )

    emit(
        "rollen_vorschau_update",
        {
            "rollen": rollen_mit_farben,
            "total": rollen_vorschau_total,
            "hat_erzaehler": bool(erzaehler),
        },
        room=raum.code,  # pyright: ignore[reportCallIssue]
    )


@socketio.on("connect")
def handle_connect():
    """Spieler verbindet sich"""
    spieler = hole_aktuellen_spieler()
    if spieler and spieler.raum_id:
        raum = db.session.get(Raum, spieler.raum_id)
        if raum:
            join_room(raum.code)
            # Private room for individual updates
            join_room(f"player_{spieler.id}")
            logger.info(
                f"[SocketIO] Player {spieler.name} (ID: {spieler.id}) connected and joined room {raum.code} and player_{spieler.id}"
            )
            # SICHER: Nur Name und ID werden geteilt, keine Rolle
            emit(
                "spieler_verbunden",
                {
                    "spieler": {
                        "id": spieler.id,
                        "name": spieler.name,
                        "ist_erzaehler": spieler.ist_erzaehler,
                    },
                    "spieler_id": spieler.id,
                    "spieler_name": spieler.name,
                },
                room=raum.code,  # pyright: ignore[reportCallIssue]
            )
            # Sende aktualisierte Rollenvorschau an alle
            sende_rollen_vorschau_update(raum)
        else:
            logger.warning(
                f"[SocketIO] Player connected but raum with ID {spieler.raum_id} not found"
            )
    else:
        logger.warning(f"[SocketIO] Connection attempt without valid player session")


@socketio.on("disconnect")
def handle_disconnect():
    """Spieler trennt Verbindung"""
    spieler = hole_aktuellen_spieler()
    if spieler and spieler.raum_id:
        raum = db.session.get(Raum, spieler.raum_id)
        if raum:
            leave_room(raum.code)
            emit(
                "spieler_getrennt",
                {"spieler_id": spieler.id, "spieler_name": spieler.name},
                room=raum.code,  # pyright: ignore[reportCallIssue]
            )
            # Sende aktualisierte Rollenvorschau an alle
            sende_rollen_vorschau_update(raum)


@socketio.on("raum_beitreten")
def handle_raum_beitreten(data):
    """Spieler tritt Raum-Channel bei"""
    code = data.get("code")
    if code:
        join_room(code)
        raum = Raum.query.filter_by(code=code).first()
        if raum:
            alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()
            # SICHER: Keine Rollen werden geteilt
            emit(
                "spieler_liste",
                {
                    "spieler": [
                        {"id": s.id, "name": s.name, "ist_erzaehler": s.ist_erzaehler}
                        for s in alle_spieler
                    ]
                },
                room=code,  # pyright: ignore[reportCallIssue]
            )

            # Online-Modus: Sende Erzählung für aktuelle Phase wenn Spiel läuft
            if (
                raum.modus == "online"
                and raum.spiel_gestartet
                and raum.aktuelle_phase in ERZAEHLER_EVENTS
            ):
                erzaehler_info = ERZAEHLER_EVENTS[raum.aktuelle_phase]
                erzaehlung_text = erzaehler_info.get("text", "")
                audio_path = None
                if erzaehlung_text:
                    audio_path = generiere_erzaehler_audio(
                        erzaehlung_text, stil="normal"
                    )
                emit("erzaehlung", {"text": erzaehlung_text, "audio": audio_path})


@socketio.on("spiel_starten")
def handle_spiel_starten(data):
    """Startet das Spiel (nur Erzaehler/Ersteller)"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        emit("fehler", {"nachricht": "Raum nicht gefunden"})
        return

    # Pruefen ob genug Spieler
    anzahl = Spieler.query.filter_by(raum_id=raum.id).count()
    if anzahl < 5:
        emit(
            "fehler",
            {"nachricht": f"Mindestens 5 Spieler benoetigt (aktuell: {anzahl})"},
        )
        return

    if game_logic.starte_spiel(raum):
        # SICHER: Jeder Spieler bekommt NUR seine eigene Rolle
        alle_spieler = Spieler.query.filter_by(raum_id=raum.id).all()

        # Spiel gestartet - alle werden zur Spielseite weitergeleitet
        logger.info(
            f"[Spiel] Emitting spiel_gestartet to room {raum.code} with {len(alle_spieler)} players"
        )
        emit(
            "spiel_gestartet",
            {"phase": raum.aktuelle_phase, "runde": raum.runde},
            room=raum.code,  # pyright: ignore[reportCallIssue]
        )

        # Online-Modus: Automatisch die erste Phase (rollen_verteilt) anzeigen und weiterschalten
        if raum.modus == "online":
            # Sende initiale Erzählung für rollen_verteilt
            if raum.aktuelle_phase in ERZAEHLER_EVENTS:
                erzaehler_info = ERZAEHLER_EVENTS[raum.aktuelle_phase]
                erzaehler_text = erzaehler_info.get("text", "")
                audio_path = None
                if erzaehler_text:
                    audio_path = generiere_erzaehler_audio(
                        erzaehler_text, stil="normal"
                    )
                socketio.emit(
                    "erzaehlung",
                    {"text": erzaehler_text, "audio": audio_path},
                    room=raum.code,  # pyright: ignore[reportCallIssue]
                )

            # Starte Fallback-Timer für automatische Phasen-Progression
            # (gleiche Logik wie in _wechsel_phase_intern für AUTOMATISCHE_PHASEN)
            # WICHTIG: Muss gevent verwenden, da threading mit monkey-patching nicht kooperativ yieldet!
            raum_code = raum.code
            phase_bei_start = raum.aktuelle_phase

            def auto_advance_initial():
                # Warte auf Fallback-Timeout (falls Audio nicht abgespielt wird)
                gevent.sleep(PHASE_WECHSEL_DELAY)
                with app.app_context():
                    raum_aktuell = Raum.query.filter_by(code=raum_code).first()
                    if raum_aktuell and raum_aktuell.aktuelle_phase == phase_bei_start:
                        # Phase wurde noch nicht gewechselt (Audio-Event kam nicht an)
                        # FEHLER: Fallback sollte nie notwendig sein!
                        logger.error(
                            f"[Phase] FALLBACK-TIMEOUT für {phase_bei_start} - Dies ist ein Fehler! Audio-Event kam nicht an."
                        )
                        _wechsel_phase_intern(raum_aktuell)

            gevent.spawn(auto_advance_initial)
    else:
        emit("fehler", {"nachricht": "Spiel konnte nicht gestartet werden"})


@socketio.on("phase_weiter")
def handle_phase_weiter():
    """Wechselt zur naechsten Phase (Erzaehler)"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        return

    # Im Online-Modus darf der Admin/Creator die Phase weiterschalten (automatisch vom Client getriggert).
    # Im Gruppen-Modus darf nur der Erzähler manuell weiterschalten.
    is_admin = raum.erzaehler_id == spieler.id
    if raum.modus != "online" and not spieler.ist_erzaehler:
        emit("fehler", {"nachricht": "Nur der Erzaehler kann die Phase wechseln"})
        return
    if raum.modus == "online" and not is_admin:
        emit("fehler", {"nachricht": "Nur der Spielleiter kann die Phase wechseln"})
        return

    _wechsel_phase_intern(raum)


def pruefe_phase_abschluss(raum):
    """
    Prüft ob alle erforderlichen Aktionen in der aktuellen Phase abgeschlossen sind.
    Wenn ja, wechselt automatisch zur nächsten Phase.
    """
    from roles import RoleRegistry

    phase = raum.aktuelle_phase
    log_ts(f"[PhaseCheck] Prüfe Abschluss für Phase {phase} (Runde {raum.runde})")

    # Use RoleRegistry for dynamic phase-to-role mapping instead of hardcoded dict
    rolle_obj = RoleRegistry.get_role_for_phase(phase)
    rolle = rolle_obj.info.name if rolle_obj else None

    log_ts(f"[PhaseCheck] Phase {phase} zugeordnet zu Rolle: {rolle}")

    # Special handling for werwolf_phase - all wolves must vote
    if phase == "werwolf_phase":
        # Alle lebenden Werwölfe müssen gewählt haben
        alle_fertig = game_logic.alle_haben_gewaehlt(raum, phase, rolle=None)
        # Hole nur Werwölfe
        woelfe = [
            s
            for s in game_logic.hole_lebende_spieler(raum)
            if game_logic.ist_werwolf_rolle(s.rolle)
        ]
        alle_fertig = all(
            game_logic.hat_spieler_gewaehlt(w, raum, phase) for w in woelfe
        )
    elif rolle:
        alle_fertig = game_logic.alle_haben_gewaehlt(raum, phase, rolle)

        # DEBUG: Wenn nicht fertig, logge warum
        if not alle_fertig:
            lebende = game_logic.hole_lebende_spieler(raum)
            relevant = [s for s in lebende if s.rolle == rolle]
            log_ts(
                f"[PhaseCheck] Relevante Spieler für {rolle}: {[s.name for s in relevant]}"
            )
            missing = [
                s.name
                for s in relevant
                if not game_logic.hat_spieler_gewaehlt(s, raum, phase)
            ]
            log_ts(f"[PhaseCheck] Fehlende Aktionen von: {missing}")

            # Defensive Fix: If relevant list is empty but role is assigned, force True?
            # game_logic.alle_haben_gewaehlt returns True if list is empty.
    else:
        # Phase ohne zugeordnete Rolle? (z.B. Tag-Phasen, Spezial)
        log_ts(f"[PhaseCheck] Keine Rolle für Phase {phase} gefunden. Ignoriere.")
        return

    if alle_fertig:
        log_ts(f"[Phase] Alle Aktionen in {phase} abgeschlossen, wechsle Phase")
        _wechsel_phase_intern(raum)
    else:
        log_ts(f"[PhaseCheck] Phase {phase} noch NICHT abgeschlossen.")


def _wechsel_phase_intern(raum):
    """
    Interne Funktion für Phasenwechsel.
    Wird rekursiv aufgerufen für automatische Phasen.
    """
    alte_phase = raum.aktuelle_phase

    # Clear audio tracking for the old phase (all audio files in that phase)
    keys_to_delete = [
        k
        for k in _audio_fertig_players.keys()
        if k[0] == raum.code and k[1] == alte_phase
    ]
    for key in keys_to_delete:
        del _audio_fertig_players[key]
    if keys_to_delete:
        log_ts(
            f"[Phase] Cleared {len(keys_to_delete)} audio tracking entries for completed phase {alte_phase}"
        )

    neue_phase = game_logic.naechste_phase(raum)

    # Phase-spezifische Aktionen
    handle_phase_wechsel(raum, alte_phase, neue_phase)

    # Erzähler-Text für Gruppen-Modus
    erzaehler_text = None
    if raum.modus == "gruppe" and neue_phase in ERZAEHLER_EVENTS:
        erzaehler_text = ERZAEHLER_EVENTS[neue_phase]

    # Online-Modus: Automatische Erzählung mit Audio senden
    if raum.modus == "online" and neue_phase in ERZAEHLER_EVENTS:
        erzaehler_info = ERZAEHLER_EVENTS[neue_phase]
        erzaehlung_text = erzaehler_info.get("text", "")

        # Generiere Audio für die Erzählung
        audio_path = None
        if erzaehlung_text:
            # Bestimme Stil basierend auf Phase
            stil = "normal"
            if "werwolf" in neue_phase.lower():
                stil = "dramatisch"
            elif (
                "tot" in erzaehlung_text.lower() or "stirbt" in erzaehlung_text.lower()
            ):
                stil = "dramatisch"

            audio_path = generiere_erzaehler_audio(erzaehlung_text, stil=stil)

        socketio.emit(
            "erzaehlung",
            {"text": erzaehlung_text, "audio": audio_path},
            room=raum.code,  # pyright: ignore[reportCallIssue]
        )

    # Build phase data for emission
    phase_data = {
        "phase": neue_phase,
        "runde": raum.runde,
        "alte_phase": alte_phase,
        "erzaehler_text": erzaehler_text,
    }

    # Add role-specific phase data (phase names use role's get_phase_name() method)
    # Special case: Hexe phase needs werewolf victim info
    if neue_phase == "hexe_phase":
        # Include werewolf victim for Hexe
        ww_result = game_logic.werwolf_abstimmung(raum)
        if ww_result and "opfer_id" in ww_result:
            opfer = db.session.get(Spieler, ww_result["opfer_id"])
            if opfer:
                phase_data["werwolf_opfer_id"] = opfer.id
                phase_data["werwolf_opfer_name"] = opfer.name
                log_ts(f"[Hexe] Opfer-Info mitgesendet: {opfer.name} (ID: {opfer.id})")

    socketio.emit("phase_geaendert", phase_data, room=raum.code)  # pyright: ignore[reportCallIssue]

    # Zufällige Hinweise generieren
    try:
        generiere_zufalls_hinweis(raum.id)
    except Exception as e:
        log_ts(f"Fehler bei Hinweis-Generierung: {e}")

    # Check if this is an automatic transition phase (uses module-level AUTOMATISCHE_PHASEN)
    ist_automatische_phase = neue_phase in AUTOMATISCHE_PHASEN

    if raum.modus == "online" and ist_automatische_phase:
        # Markiere Raum als "wartet auf Audio"
        # Der Client sendet 'audio_fertig' wenn Audio abgespielt wurde
        # Fallback: Nach PHASE_WECHSEL_DELAY Sekunden automatisch weiter
        raum_code = raum.code
        phase_bei_start = neue_phase

        import gevent

        def auto_advance_fallback():
            # Warte auf Fallback-Timeout (falls Audio nicht abgespielt wird)
            gevent.sleep(PHASE_WECHSEL_DELAY)
            with app.app_context():
                raum_aktuell = Raum.query.filter_by(code=raum_code).first()
                if raum_aktuell and raum_aktuell.aktuelle_phase == phase_bei_start:
                    # Phase wurde noch nicht gewechselt (Audio-Event kam nicht an)
                    # FEHLER: Fallback sollte nie notwendig sein!
                    logger.error(
                        f"[Phase] FALLBACK-TIMEOUT für {phase_bei_start} - Dies ist ein Fehler! Audio-Event kam nicht an."
                    )
                    _wechsel_phase_intern(raum_aktuell)

        gevent.spawn(auto_advance_fallback)


# Socket-Handler für Audio-Fertig-Event
@socketio.on("audio_fertig")
def handle_audio_fertig(data):
    """Client meldet dass Audio VOLLSTÄNDIG abgespielt wurde - Phase kann wechseln wenn ALLE Spieler bereit sind"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.modus != "online":
        return

    gemeldete_phase = data.get("phase", "")
    audio_file = data.get("audio_file", "")

    # Require audio filename to ensure we're tracking the specific audio
    if not audio_file:
        log_ts(f"[Audio] ERROR: audio_fertig from {spieler.name} missing audio_file!")
        return

    # Prüfe ob wir noch in der gleichen Phase sind
    if raum.aktuelle_phase != gemeldete_phase:
        log_ts(
            f"[Audio] Ignoring audio_fertig for old phase {gemeldete_phase} (current: {raum.aktuelle_phase})"
        )
        return

    # Track which players have confirmed THIS SPECIFIC audio file completion
    tracking_key = (raum.code, gemeldete_phase, audio_file)
    if tracking_key not in _audio_fertig_players:
        _audio_fertig_players[tracking_key] = set()

    # Add this player to confirmed set
    _audio_fertig_players[tracking_key].add(spieler.id)
    confirmed_players = _audio_fertig_players[tracking_key]

    # Get all alive players who should see this phase
    alle_spieler = Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).all()
    total_players = len(alle_spieler)
    confirmed_count = len(confirmed_players)

    log_ts(
        f"[Audio] Player {spieler.name} confirmed audio for {gemeldete_phase} ({confirmed_count}/{total_players})"
    )

    # Calculate if we've reached threshold
    threshold_met = confirmed_count >= max(
        1, int(total_players * AUDIO_CONFIRMATION_THRESHOLD)
    )

    if not threshold_met:
        log_ts(
            f"[Audio] Waiting for more players to confirm ({confirmed_count}/{total_players}, need {int(total_players * AUDIO_CONFIRMATION_THRESHOLD)})"
        )
        return

    # Clear tracking for this phase
    if tracking_key in _audio_fertig_players:
        del _audio_fertig_players[tracking_key]

    log_ts(f"[Audio] Threshold met for {gemeldete_phase}, advancing phase")

    # Check if this is an automatic phase or needs action
    if gemeldete_phase in AUTOMATISCHE_PHASEN:
        log_ts(f"[Audio] Automatic phase {gemeldete_phase}, advancing immediately")
        _wechsel_phase_intern(raum)
    else:
        # Interactive phase - check if all actions are complete
        from roles import RoleRegistry

        rolle = RoleRegistry.get_role_for_phase(gemeldete_phase)
        should_advance = False

        if rolle:
            # Check all players with this role (handles shared phases like werwolf_phase)
            alle_mit_rolle = [s for s in alle_spieler if s.rolle == rolle.info.name]
            if alle_mit_rolle:
                alle_fertig = all(
                    game_logic.hat_spieler_gewaehlt(s, raum, gemeldete_phase)
                    for s in alle_mit_rolle
                )
                if alle_fertig:
                    log_ts(
                        f"[Audio] All actions complete for {gemeldete_phase}, advancing"
                    )
                    should_advance = True
                else:
                    log_ts(f"[Audio] Actions pending for {gemeldete_phase}, waiting")

        if should_advance:
            _wechsel_phase_intern(raum)


@socketio.on("aktion_ausfuehren")
def handle_aktion(data):
    """Fuehrt eine Spielaktion aus"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        return

    aktion_typ = data.get("aktion")
    ziel_id = data.get("ziel_id")

    # Validate player can act - dead players can only act if their role allows it (e.g., Jäger)
    if not spieler.ist_am_leben:
        from roles import RoleRegistry

        rolle_obj = RoleRegistry.get(spieler.rolle)
        # Check if role has on_eigener_tod that enables post-death action
        can_act_when_dead = rolle_obj and hasattr(rolle_obj, "on_eigener_tod")
        if not can_act_when_dead:
            emit("fehler", {"nachricht": "Du bist tot und kannst nicht handeln"})
            return

    # Aktion basierend auf Phase und Rolle verarbeiten
    ergebnis = verarbeite_aktion(spieler, raum, aktion_typ, ziel_id)

    if ergebnis and ergebnis.get("erfolg"):
        from roles.enums import AktionsTyp
        from roles import RoleRegistry

        # Map action types to 3D effect types dynamically
        AKTION_TYP_EFFEKT = {
            AktionsTyp.HEILEN.value: "heal",
            AktionsTyp.SCHUETZEN.value: "protect",
            AktionsTyp.VERGIFTEN.value: "poison",
            AktionsTyp.TOETEN.value: "attack",
            AktionsTyp.VERLIEBEN.value: "love",
            AktionsTyp.SEHEN.value: "reveal",
            AktionsTyp.INFIZIEREN.value: "infect",
            AktionsTyp.MARKIEREN.value: "mark",
            AktionsTyp.BLOCKIEREN.value: "block",
        }

        # Build effect_data with result message
        effect_data = {
            "aktion": aktion_typ,
            "nachricht": ergebnis.get("nachricht", "Aktion ausgeführt"),
            "ziel_id": ergebnis.get("ziel_id"),
            "ziel_name": ergebnis.get("ziel_name"),
        }

        # Determine effect from role's action type
        rolle_obj = RoleRegistry.get(spieler.rolle)
        effekt = None
        if rolle_obj:
            aktions_typ_enum = rolle_obj.aktions_typ
            if hasattr(aktions_typ_enum, "value"):
                effekt = AKTION_TYP_EFFEKT.get(aktions_typ_enum.value)

        if effekt:
            effect_data["effekt"] = effekt

        # Include any extra effects data from role action
        if ergebnis.get("effekte"):
            effect_data["effekte"] = ergebnis["effekte"]

        # Use socketio.emit to player's personal room to ensure delivery
        # Player joins room "player_{id}" on connect (see handle_connect)
        socketio.emit("aktion_bestaetigt", effect_data, room=f"player_{spieler.id}")  # pyright: ignore[reportCallIssue]
        log_ts(
            f"[Aktion] Sent aktion_bestaetigt to player_{spieler.id}: {effect_data.get('nachricht')}"
        )

        # Pruefen ob alle fertig sind
        pruefe_phase_abschluss(raum)
    else:
        nachricht = (
            ergebnis.get("nachricht", "Aktion konnte nicht ausgeführt werden")
            if ergebnis
            else "Aktion konnte nicht ausgeführt werden"
        )
        emit("fehler", {"nachricht": nachricht})


@socketio.on("chat_nachricht")
def handle_chat(data):
    """Verarbeitet Chat-Nachrichten"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        return

    nachricht = data.get("nachricht", "")[:500]

    # SICHER: Keine sensiblen Daten im Chat
    if not spieler.ist_am_leben:
        # Tote chatten nur mit Toten
        emit(
            "chat_tot",
            {"von": spieler.name, "nachricht": nachricht, "spieler_id": spieler.id},
            room=raum.code,  # pyright: ignore[reportCallIssue]
        )
    else:
        emit(
            "chat",
            {
                "von": spieler.name,
                "nachricht": nachricht,
                "ist_tot": False,
                "spieler_id": spieler.id,
            },
            room=raum.code,  # pyright: ignore[reportCallIssue]
        )


@socketio.on("navigiere_zur_lobby")
def handle_navigiere_lobby():
    """Sendet Navigation zur Startseite"""
    emit("gehe_zu_startseite")


@socketio.on("navigiere")
def handle_navigiere(data):
    """Sendet Navigation zu angegebenem Ziel"""
    ziel = data.get("ziel", "/")
    emit("navigiere", {"ziel": ziel})


# ============================================================================
# HINWEIS-SYSTEM - Server-kontrollierte synchronisierte Hinweise
# ============================================================================


@socketio.on("hinweis_senden")
def handle_hinweis_senden(data):
    """
    Verarbeitet Hinweis-Anfragen (z.B. Selbstmörder macht sich verdächtig)

    Der Server:
    1. Validiert, dass der Spieler den Hinweis senden darf
    2. Broadcastet den Hinweis an ALLE Spieler im Raum gleichzeitig
    3. Speichert den Hinweis für das Village-Rendering
    """
    from models import SPEZIAL_HINWEISE
    import random

    spieler = hole_aktuellen_spieler()
    if not spieler or not spieler.raum_id:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or not raum.spiel_gestartet:
        return

    hinweis_typ = data.get("hintTyp")
    selbst_ausgeloest = data.get("selbst_ausgeloest", False)

    # Validierung: Darf dieser Spieler Hinweise senden?
    if selbst_ausgeloest:
        # Nur bestimmte Rollen dürfen sich selbst verdächtig machen
        spezial = SPEZIAL_HINWEISE.get(spieler.rolle)
        if not spezial or not spezial.get("kann_hinweis_senden"):
            emit("fehler", {"nachricht": "Du kannst keine Hinweise senden!"})
            return

        # Prüfe verfügbare Hinweise
        if hinweis_typ not in spezial.get("verfuegbare_hinweise", []):
            hinweis_typ = random.choice(spezial["verfuegbare_hinweise"])

    # Speichere Hinweis für Village-Rendering
    if raum.id not in _aktive_hinweise:
        _aktive_hinweise[raum.id] = {}

    # Intensität: selbst-ausgelöst = stark, automatisch = variabel
    intensitaet = 0.8 if selbst_ausgeloest else random.uniform(0.4, 0.7)
    _aktive_hinweise[raum.id][spieler.id] = (hinweis_typ, intensitaet)

    # Broadcaste Hinweis an ALLE Spieler im Raum (synchronisiert!)
    socketio.emit(
        "hinweis_zeigen",
        {
            "spielerId": spieler.id,
            "spielerName": spieler.name,
            "hintTyp": hinweis_typ,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        room=raum.code,  # pyright: ignore[reportCallIssue]
    )

    # Log für Erzähler
    log = SpielLog(  # pyright: ignore[reportCallIssue]
        raum_id=raum.id,
        nachricht=f"[HINWEIS] {spieler.name} zeigte: {hinweis_typ}",
        sichtbar_fuer="erzaehler",
    )
    db.session.add(log)
    db.session.commit()

    # Lösche Hinweis nach 5 Sekunden aus dem Cache
    def clear_hint():
        import time

        time.sleep(5)
        if raum.id in _aktive_hinweise and spieler.id in _aktive_hinweise[raum.id]:
            del _aktive_hinweise[raum.id][spieler.id]

    # In Background ausführen (eventlet-kompatibel)
    socketio.start_background_task(clear_hint)


def generiere_zufalls_hinweis(raum_id: int):
    """
    Generiert zufällige Hinweise basierend auf Rollen-Teams.
    Wird vom Server aufgerufen, z.B. bei Phasenwechsel.

    WICHTIG: Diese Hinweise werden vom SERVER gewürfelt und
    an ALLE Spieler gleichzeitig gesendet!
    """
    from models import HINWEIS_CHANCEN
    import random

    raum = db.session.get(Raum, raum_id)
    if not raum:
        return

    spieler_liste = Spieler.query.filter_by(
        raum_id=raum_id, ist_am_leben=True, ist_erzaehler=False
    ).all()

    for spieler in spieler_liste:
        rolle_info = ROLLEN.get(spieler.rolle, {})
        team = rolle_info.get("team", "dorf")

        config = HINWEIS_CHANCEN.get(team, HINWEIS_CHANCEN["dorf"])

        # Würfle ob Hinweis generiert wird
        if random.random() > config["basis_chance"]:
            continue

        # Wähle zufälligen Hinweis
        hinweis_typ = random.choice(config["hinweise"])
        intensitaet = random.uniform(0.3, 0.6)

        # Speichere für Rendering
        if raum_id not in _aktive_hinweise:
            _aktive_hinweise[raum_id] = {}
        _aktive_hinweise[raum_id][spieler.id] = (hinweis_typ, intensitaet)

        # Broadcaste an alle
        socketio.emit(
            "hinweis_zeigen",
            {
                "spielerId": spieler.id,
                "spielerName": spieler.name,
                "hintTyp": hinweis_typ,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            room=raum.code,  # pyright: ignore[reportCallIssue]
        )


# ============================================================================
# SPIELLOGIK HELFER
# ============================================================================


def verarbeite_aktion(spieler, raum, aktion_typ, ziel_id):
    """
    Verarbeitet eine Spielaktion.

    Refactored to use Role classes for validation and execution where possible.
    Some actions still require special handling (tag_wahl, jaeger_schuss).

    Returns:
        dict with 'erfolg' (bool), 'nachricht' (str), and optional extra data
        or None on error
    """
    log_ts(
        f"[Aktion] {aktion_typ} von {spieler.name} (Rolle: {spieler.rolle}) für Ziel-ID: {ziel_id}"
    )

    # Special case: Day voting (not role-specific)
    if aktion_typ == "tag_wahl":
        if raum.aktuelle_phase != "tag_abstimmung":
            return {"erfolg": False, "nachricht": "Nicht in Abstimmungsphase"}
        if game_logic.hat_spieler_gewaehlt(spieler, raum, raum.aktuelle_phase):
            return {"erfolg": False, "nachricht": "Du hast bereits gewählt"}
        game_logic.registriere_aktion(
            raum.id, raum.runde, raum.aktuelle_phase, "tag_wahl", spieler.id, ziel_id
        )
        game_logic.speichere_abstimmungs_vote(raum, spieler.id, ziel_id)

        # Broadcast: Zeige allen Spielern, wer für wen gestimmt hat
        ziel = db.session.get(Spieler, ziel_id)
        if ziel:
            socketio.emit(
                "stimme_abgegeben",
                {
                    "waehler_id": spieler.id,
                    "waehler_name": spieler.name,
                    "ziel_id": ziel.id,
                    "ziel_name": ziel.name,
                },
                room=raum.code,  # pyright: ignore[reportCallIssue]
            )
            stats = game_logic.berechne_abstimmungs_statistik(raum)
            socketio.emit(
                "abstimmung_status",
                {
                    "gesamt_spieler": stats["gesamt_spieler"],
                    "gesamt_votes": stats["gesamt_votes"],
                    "noch_zu_waehlen": stats["noch_zu_waehlen"],
                    "ziel_stimmen": stats["ziel_stimmen"],
                    "fuehrender_id": stats["fuehrender_id"],
                    "fuehrende_stimmen": stats["fuehrende_stimmen"],
                },
                room=raum.code,  # pyright: ignore[reportCallIssue]
            )
        return {"erfolg": True, "nachricht": "Stimme abgegeben"}

    # ==========================================================================
    # DYNAMIC ACTION HANDLER - Replaces all hardcoded role-specific handlers
    # Actions like jaeger_schuss, amor_verlieben are now handled by role classes
    # ==========================================================================

    from roles import RoleRegistry
    from roles.base import SpielKontext
    from roles.enums import Phase, AktionsTyp

    # Get the player's role class
    rolle_obj = RoleRegistry.get(spieler.rolle)
    if not rolle_obj:
        log_ts(f"[Aktion] FEHLER: Rolle {spieler.rolle} nicht gefunden")
        return False

    # Build SpielKontext
    lebende = [
        s.id
        for s in Spieler.query.filter_by(
            raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
        ).all()
    ]
    tote = [
        s.id
        for s in Spieler.query.filter_by(
            raum_id=raum.id, ist_am_leben=False, ist_erzaehler=False
        ).all()
    ]

    # Get existing actions this round for "already voted" checks
    existing_actions = SpielAktion.query.filter_by(
        raum_id=raum.id,
        runde=raum.runde,
        phase=raum.aktuelle_phase,
    ).all()

    aktionen_liste = [
        {
            "von_spieler_id": a.von_spieler_id,
            "ziel_spieler_id": a.ziel_spieler_id,
            "aktion_typ": a.aktion_typ,
        }
        for a in existing_actions
    ]

    # Calculate execution context variables
    werwolf_opfer_id = None

    # Check if the role requires werewolf victim info (e.g. Hexe, Heiler if modified)
    if rolle_obj.requires_victim_info:
        ww_result = game_logic.werwolf_abstimmung(raum)
        if ww_result and "opfer_id" in ww_result:
            werwolf_opfer_id = ww_result["opfer_id"]

    kontext = SpielKontext(
        raum_id=raum.id,
        runde=raum.runde,
        phase=(
            Phase(raum.aktuelle_phase)
            if raum.aktuelle_phase in [p.value for p in Phase]
            else raum.aktuelle_phase
        ),
        aktiver_spieler_id=spieler.id,
        lebende_spieler=lebende,
        tote_spieler=tote,
        aktionen_diese_runde=aktionen_liste,
        werwolf_opfer_id=werwolf_opfer_id,
    )

    # Build target list (handle both single and multi-target)
    if isinstance(ziel_id, list):
        targets = [db.session.get(Spieler, tid) for tid in ziel_id if tid]
        targets = [t for t in targets if t]  # Filter None
    elif ziel_id:
        target = db.session.get(Spieler, ziel_id)
        targets = [target] if target else []
    else:
        targets = []

    # Try role's execute_action method first (handles special cases like multi-target)
    log_ts(f"[Aktion] Trying execute_action for {spieler.rolle}: {aktion_typ}")
    try:
        ergebnis = rolle_obj.execute_action(aktion_typ, spieler, targets, kontext)
        if ergebnis and ergebnis.erfolg:
            log_ts(f"[Aktion] execute_action SUCCESS: {ergebnis.nachricht}")

            # Register the action
            first_target_id = targets[0].id if targets else None
            game_logic.registriere_aktion(
                raum.id,
                raum.runde,
                raum.aktuelle_phase,
                aktion_typ,
                spieler.id,
                first_target_id,
            )

            # Apply effects from the role action
            _apply_action_effects(ergebnis, spieler, targets, raum, kontext)

            db.session.commit()
            return {
                "erfolg": True,
                "nachricht": ergebnis.nachricht,
                "ziel_id": first_target_id,
                "ziel_name": targets[0].name if targets else None,
            }
        elif ergebnis and not ergebnis.erfolg:
            log_ts(f"[Aktion] execute_action FAILED: {ergebnis.nachricht}")
            # Don't fall through - this was a valid action type that just failed validation
            return {"erfolg": False, "nachricht": ergebnis.nachricht}
    except Exception as e:
        log_ts(f"[Aktion] execute_action error: {e}")
        # Fall through to legacy handler

    # Check if the current phase matches the role's phase (for night actions)
    rolle_phase = rolle_obj.get_phase_name()
    if raum.aktuelle_phase != rolle_phase:
        # Not the right phase for this role's normal action
        log_ts(
            f"[Aktion] Phase mismatch: expected={rolle_phase}, current={raum.aktuelle_phase}"
        )
        # Still allow special actions that aren't phase-dependent
        pass

    # Legacy fallback: use on_nacht_aktion for single-target actions
    ziel = targets[0] if len(targets) == 1 else None

    log_ts(
        f"[Aktion] Fallback to on_nacht_aktion: {spieler.rolle} -> {ziel.name if ziel else 'None'}"
    )

    # Pass 'aktion' only if accepted by the method signature
    sig = inspect.signature(rolle_obj.on_nacht_aktion)
    call_kwargs = {}
    if "aktion" in sig.parameters:
        call_kwargs["aktion"] = aktion_typ

    ergebnis = rolle_obj.on_nacht_aktion(spieler, ziel, kontext, **call_kwargs)

    if ergebnis and ergebnis.erfolg:
        # Register the action
        rolle_phase = rolle_obj.get_phase_name()
        first_target_id = targets[0].id if targets else None
        game_logic.registriere_aktion(
            raum.id, raum.runde, rolle_phase, aktion_typ, spieler.id, first_target_id
        )

        # Apply effects using centralized handler
        _apply_action_effects(ergebnis, spieler, targets, raum, kontext)

        # Send role-specific results
        # DYNAMIC: Check if action was a SEHEN action (Seherin style)
        if aktion_typ == AktionsTyp.SEHEN.value and ergebnis.effekte:
            # Seer gets a special result event (uses EventName enum)
            from roles.enums import EventName

            socketio.emit(  # type: ignore[call-arg]
                EventName.SEHERIN_ERGEBNIS.value,
                {
                    "ziel_name": ziel.name if ziel else "Unbekannt",
                    "ist_werwolf": ergebnis.effekte.get("ist_werwolf", False),
                    "rolle": ergebnis.effekte.get("rolle", "Unbekannt"),
                },
                room=request.sid,  # type: ignore[attr-defined]
            )
        elif ergebnis.nachricht:
            # Generic result message
            emit(
                "aktion_ergebnis",
                {
                    "nachricht": ergebnis.nachricht,
                    "effekte": ergebnis.effekte,
                },
            )

        db.session.commit()
        return {
            "erfolg": True,
            "nachricht": ergebnis.nachricht,
            "ziel_id": first_target_id,
            "ziel_name": targets[0].name if targets else None,
            "effekte": ergebnis.effekte,
        }

    return {"erfolg": False, "nachricht": "Aktion fehlgeschlagen"}


def handle_phase_wechsel(raum, alte_phase, neue_phase):
    """Behandelt Phasenwechsel-Logik"""
    log_ts(f"[Phase] Wechsel: {alte_phase} -> {neue_phase}")

    # Heiler-Schutz zurücksetzen am Nachtende
    # Phase name comes from Heiler role's get_phase_name() method
    if alte_phase == "heiler_phase":
        pass  # Schutz bleibt bis Nacht-Ende

    # Werwolf-Opfer ermitteln und an relevante Rollen senden
    # Phase name comes from Werwolf role's get_phase_name() method
    if alte_phase == "werwolf_phase":
        # Werwolf-Opfer ermitteln
        ergebnis = game_logic.werwolf_abstimmung(raum)
        if ergebnis and "opfer_id" in ergebnis:
            # Find all players whose roles require victim info (dynamic via RoleRegistry)
            from roles import RoleRegistry

            lebende_spieler = Spieler.query.filter_by(
                raum_id=raum.id,
                ist_am_leben=True,
            ).all()

            # Dynamically find players with roles that need victim info
            betroffene_spieler = []
            for spieler in lebende_spieler:
                rolle = RoleRegistry.get(spieler.rolle)
                if (
                    rolle
                    and hasattr(rolle, "requires_victim_info")
                    and rolle.requires_victim_info
                ):
                    betroffene_spieler.append(spieler)

            opfer = db.session.get(Spieler, ergebnis["opfer_id"])
            if opfer and betroffene_spieler:
                for spieler in betroffene_spieler:
                    # Benutze 'role_phase_info' Event, das vom Frontend unterstützt wird
                    socketio.emit(
                        "role_phase_info",
                        {
                            "recipient_id": spieler.id,
                            "payload": {
                                "nachricht": f"Die Werwölfe haben {opfer.name} als Opfer gewählt.",
                                "opfer_id": opfer.id,
                                "opfer_name": opfer.name,
                                "alert_type": "info",
                            },
                        },
                        room=raum.code,  # pyright: ignore[reportCallIssue]
                    )

    # WICHTIG: Nacht-Tode bei nacht_ende verarbeiten!
    # Dies stellt sicher dass Tode immer verarbeitet werden, auch wenn
    # hexe_phase übersprungen wird (weil keine Hexe existiert)
    elif neue_phase == "nacht_ende":
        log_ts(f"[Nacht] Verarbeite Nacht-Ende für Runde {raum.runde}")

        # Query for werewolf actions (phase name from Werwolf.get_phase_name())
        werwolf_opfer = SpielAktion.query.filter(
            SpielAktion.raum_id == raum.id,
            SpielAktion.runde == raum.runde,
            SpielAktion.phase == "werwolf_phase",
            SpielAktion.aktion_typ.in_(["werwolf_wahl", "toeten"]),
        ).first()

        log_ts(f"[Nacht] Werwolf-Opfer-Aktion gefunden: {werwolf_opfer is not None}")
        if werwolf_opfer:
            log_ts(f"[Nacht] Werwolf-Ziel-ID: {werwolf_opfer.ziel_spieler_id}")

        # Query for healing actions (phase name from Hexe.get_phase_name())
        geheilt = SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            phase="hexe_phase",
            aktion_typ="heilen",
        ).first()

        # Query for poisoning actions (phase name from Hexe.get_phase_name())
        vergiftet = SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            phase="hexe_phase",  # Dynamic: from Hexe role
            aktion_typ="vergiften",  # AktionsTyp enum value
        ).first()

        tote = []

        # Werwolf-Opfer (wenn nicht geheilt oder geschützt)
        if werwolf_opfer and werwolf_opfer.ziel_spieler_id:
            opfer = db.session.get(Spieler, werwolf_opfer.ziel_spieler_id)
            if opfer:
                log_ts(
                    f"[Nacht] Werwolf-Opfer: {opfer.name}, am_leben={opfer.ist_am_leben}"
                )
            if opfer and opfer.ist_am_leben:
                # Prüfen ob geheilt
                if geheilt and geheilt.ziel_spieler_id == opfer.id:
                    log_ts(f"[Nacht] {opfer.name} wurde von Hexe geheilt!")
                # Prüfen ob vom Heiler geschützt
                elif opfer.get_state("global.ist_beschuetzt", False):
                    log_ts(f"[Nacht] {opfer.name} wurde vom Heiler geschützt!")
                else:
                    log_ts(f"[Nacht] {opfer.name} STIRBT durch Werwolf!")
                    # "werwolf" is death cause, not role check
                    game_logic.toete_spieler(opfer, "werwolf")
                    tote.append(
                        {
                            "name": opfer.name,
                            "rolle": opfer.rolle,
                            "todesart": "werwolf",  # Death cause identifier
                        }
                    )

        # Hexen-Gift-Opfer
        if vergiftet and vergiftet.ziel_spieler_id:
            opfer = db.session.get(Spieler, vergiftet.ziel_spieler_id)
            if opfer and opfer.ist_am_leben:
                log_ts(f"[Nacht] {opfer.name} STIRBT durch Hexen-Gift!")
                # "hexe" is death cause, not role check
                game_logic.toete_spieler(opfer, "hexe")
                tote.append(
                    {
                        "name": opfer.name,
                        "rolle": opfer.rolle,
                        "todesart": "hexe",  # Death cause identifier
                    }
                )

        # Heiler-Schutz zuruecksetzen
        for s in Spieler.query.filter_by(raum_id=raum.id).all():
            s.set_state("global.ist_beschuetzt", False)
        db.session.commit()

        log_ts(f"[Nacht] Tote in dieser Nacht: {len(tote)}")
        if tote:
            socketio.emit("nacht_ergebnis", {"tote": tote}, room=raum.code)  # pyright: ignore[reportCallIssue]
        else:
            socketio.emit(
                "nacht_ergebnis",
                {"tote": [], "nachricht": "Niemand ist in der Nacht gestorben."},
                room=raum.code,  # pyright: ignore[reportCallIssue]
            )

        # Spielende pruefen
        ende = game_logic.pruefe_spielende(raum)
        if ende:
            log_ts(f"[Spiel] ENDE! Gewinner: {ende.get('gewinner', 'unbekannt')}")
            raum.aktuelle_phase = "spiel_ende"
            db.session.commit()
            socketio.emit("spiel_ende", ende, room=raum.code)  # pyright: ignore[reportCallIssue]

    elif alte_phase == "hinrichtung":
        # Hinrichtung abgeschlossen - prüfe Spielende
        ende = game_logic.pruefe_spielende(raum)
        if ende:
            raum.aktuelle_phase = "spiel_ende"
            db.session.commit()
            socketio.emit("spiel_ende", ende, room=raum.code)  # pyright: ignore[reportCallIssue]

    # Initialisierung für Tag-Abstimmung (Timer setzen)
    if neue_phase == "tag_abstimmung":
        game_logic.starte_tag_abstimmung(raum)


# ============================================================================
# TAG-ABSTIMMUNG PHASE - Timer & Voting Display
# ============================================================================


@socketio.on("timer_tick")
def handle_timer_tick():
    """Sendet Timer-Updates an alle Spieler in einem Raum"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.aktuelle_phase != "tag_abstimmung":
        return

    verbleibend = game_logic.get_verbleibende_zeit(raum)
    abgelaufen = game_logic.timer_abgelaufen(raum)

    emit(
        "timer_update",
        {
            "sekunden_verbleibend": verbleibend,
            "timer_abgelaufen": abgelaufen,
        },
        room=raum.code,  # pyright: ignore[reportCallIssue]
    )

    # Wenn Timer abgelaufen und Phase noch nicht gewechselt, wechsle jetzt
    if abgelaufen and raum.aktuelle_phase == "tag_abstimmung":
        # Werte Abstimmung aus
        ergebnis = game_logic.werte_abstimmung_aus(raum)
        if ergebnis:
            socketio.emit("abstimmung_ergebnis", ergebnis, room=raum.code)  # pyright: ignore[reportCallIssue]

            # Wenn Opfer: töte es
            if not ergebnis.get("kein_opfer"):
                opfer = db.session.get(Spieler, ergebnis["opfer_id"])
                if opfer:
                    tod_ergebnis = game_logic.toete_spieler(opfer, "hinrichtung")
                    socketio.emit(
                        "spieler_gestorben",
                        {
                            "spieler_id": opfer.id,
                            "spieler_name": opfer.name,
                            "rolle": opfer.rolle,
                            "todesart": "hinrichtung",
                        },
                        room=raum.code,  # pyright: ignore[reportCallIssue]
                    )

        # Wechsle zur nächsten Phase
        _wechsel_phase_intern(raum)


@socketio.on("spieler_abstimmen")
def handle_spieler_abstimmen(data):
    """Registriert die Abstimmung eines Spielers"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.aktuelle_phase != "tag_abstimmung":
        emit("fehler", {"nachricht": "Nicht in der richtigen Phase"})
        return

    ziel_id = data.get("ziel_id")

    # Registriere Aktion
    erfolg = verarbeite_aktion(spieler, raum, "tag_wahl", ziel_id)

    if erfolg:
        # Prüfe ob alle abgestimmt haben
        if game_logic.pruefen_abstimmung_komplett(raum):
            # Alle haben abgestimmt - werte aus und wechsle Phase
            ergebnis = game_logic.werte_abstimmung_aus(raum)
            if ergebnis:
                socketio.emit("abstimmung_ergebnis", ergebnis, room=raum.code)  # pyright: ignore[reportCallIssue]

                # Wenn Opfer: töte es
                if not ergebnis.get("kein_opfer"):
                    opfer = db.session.get(Spieler, ergebnis["opfer_id"])
                    if opfer:
                        tod_ergebnis = game_logic.toete_spieler(opfer, "hinrichtung")
                        socketio.emit(
                            "spieler_gestorben",
                            {
                                "spieler_id": opfer.id,
                                "spieler_name": opfer.name,
                                "rolle": opfer.rolle,
                                "todesart": "hinrichtung",
                            },
                            room=raum.code,  # pyright: ignore[reportCallIssue]
                        )

            # Wechsle zur nächsten Phase
            _wechsel_phase_intern(raum)
        else:
            emit("aktion_bestaetigt", {"aktion": "tag_wahl"})
    else:
        emit("fehler", {"nachricht": "Abstimmung konnte nicht gespeichert werden"})


@socketio.on("hole_abstimmung_status")
def handle_hole_abstimmung_status():
    """Sends current voting status for tag_abstimmung phase"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.aktuelle_phase != "tag_abstimmung":
        return

    stats = game_logic.berechne_abstimmungs_statistik(raum)
    verbleibend = game_logic.get_verbleibende_zeit(raum)

    # Konvertiere ziel_stimmen dict für JSON-Serialisierung
    ziel_stimmen_str = {}
    for ziel_id, stimmen in stats["ziel_stimmen"].items():
        ziel_spieler = db.session.get(Spieler, int(ziel_id))
        if ziel_spieler:
            ziel_stimmen_str[ziel_spieler.name] = stimmen

    emit(  # type: ignore[call-arg]
        "abstimmung_status",
        {
            "gesamt_spieler": stats["gesamt_spieler"],
            "gesamt_votes": stats["gesamt_votes"],
            "noch_zu_waehlen": stats["noch_zu_waehlen"],
            "ziel_stimmen": ziel_stimmen_str,
            "fuehrender_name": None,
            "fuehrende_stimmen": stats["fuehrende_stimmen"],
            "sekunden_verbleibend": verbleibend,
        },
        room=request.sid,  # type: ignore[attr-defined]
    )


@socketio.on("starte_tag_abstimmung")
def handle_starte_tag_abstimmung(data):
    """Startet die tag_abstimmung Phase (nur für Erzähler)"""
    spieler = hole_aktuellen_spieler()
    if not spieler or not spieler.ist_erzaehler:
        emit("fehler", {"nachricht": "Nur der Erzähler kann diese Phase starten"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        return

    dauer = data.get("dauer_sekunden", 120)
    game_logic.starte_tag_abstimmung(raum, dauer)

    socketio.emit(
        "phase_gestartet",
        {
            "phase": "diskussion_abstimmung",
            "dauer_sekunden": dauer,
        },
        room=raum.code,  # pyright: ignore[reportCallIssue]
    )


# ============================================================================
# ERROR HANDLER
# ============================================================================


@app.errorhandler(404)
def nicht_gefunden(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_fehler(e):
    return render_template("fehler.html"), 500


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8888"))
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    # use_reloader=False verhindert gevent fork-Fehler
    socketio.run(app, debug=debug_mode, host="0.0.0.0", port=port, use_reloader=False)
