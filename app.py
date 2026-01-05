"""
Webwoelfe - Das Online Werwolf-Spiel
Ein Echtzeit-Multiplayer Werwolf-Spiel mit WebSocket-Unterstützung.
"""

# Gevent monkey-patching MUSS vor allen anderen Imports erfolgen!
# (Gevent ist der moderne Ersatz für das deprecated eventlet)
from gevent import monkey

monkey.patch_all()

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import (
    db,
    Raum,
    Spieler,
    SpielAktion,
    SpielLog,
    ROLLEN,
    get_rollen_nach_kategorie,
    get_rollen_nach_kategorie_liste,
    get_rollen_anzahl,
    PHASEN,
    ERZAEHLER_EVENTS,
)
from constants import TEAMS
from roles import get_rollen_nach_erweiterung, ERWEITERUNG_INFO, KATEGORIE_INFO
from roles.registry import RoleRegistry
import game_logic
import secrets
import os
import random
from datetime import datetime
from logger import logger

# App Konfiguration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///webwoelfe.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Spielname als Konstante
SPIEL_NAME = "Webwölfe"

# Phasen-Konfiguration
# Wartezeit zwischen automatischen Phasenwechseln (in Sekunden)
# Mindestens 30 Sekunden um Audio-Erzählung vollständig abzuspielen
PHASE_WECHSEL_DELAY = int(os.environ.get("PHASE_DELAY", "30"))


def log_ts(msg: str):
    """Log mit Timestamp für Debugging - DEPRECATED, use logger instead"""
    logger.info(msg)


# Initialisierung
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

# Datenbank erstellen
with app.app_context():
    db.create_all()


# =============================================================================
# JINJA TEMPLATE FILTERS
# =============================================================================

@app.template_filter('css_class')
def to_css_class(role_name):
    """
    Konvertiert einen Rollennamen in einen CSS-Klassen-Namen.
    Uses RoleRegistry if available.
    """
    # logger.debug(f"Converting role name to css class: {role_name}") # Too verbose
    if not role_name:
        return 'unbekannt'
        
    # Try Registry first
    from roles import RoleRegistry
    r = RoleRegistry.get(role_name)
    if r and hasattr(r.info, 'css_class') and r.info.css_class:
        return r.info.css_class
        
    # Fallback to standard normalization
    return role_name.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss').replace(' ', '-')


# Cleanup Task starten
def start_cleanup_task():
    """Startet den Hintergrund-Task zur Bereinigung alter Spiele"""
    logger.info("Initializing cleanup task...")
    try:
        import gevent
        from cleanup import cleanup_old_games

        def run_cleanup():
            logger.info("[System] Cleanup-Task gestartet.")
            # Einmal beim Start ausführen
            cleanup_old_games(app, max_age_hours=24)
            while True:
                gevent.sleep(3600)  # Warte 1 Stunde
                cleanup_old_games(app, max_age_hours=24)

        gevent.spawn(run_cleanup)
    except ImportError:
        logger.warning("[System] Warnung: Gevent nicht verfügbar, Cleanup-Task deaktiviert.")
    except Exception as e:
        logger.error(f"[System] Fehler beim Starten des Cleanup-Tasks: {e}")


start_cleanup_task()

# Generate CSS on startup
try:
    from generate_css import generate_characters_css
    logger.info("Generating CSS...")
    generate_characters_css()
except Exception as e:
    logger.error(f"[System] Failed to generate CSS: {e}")


# ============================================================================
# KONTEXT-PROZESSOR - Globale Template-Variablen
# ============================================================================


@app.context_processor
def inject_globals():
    """Stellt globale Variablen fuer alle Templates bereit"""
    # logger.debug("Injecting globals into template") # Too verbose
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
    logger.info("Accessing index page")
    return render_template("index.html")


@app.route("/rollen")
def rollen_uebersicht():
    """Uebersicht aller Rollen"""
    logger.info("Accessing roles overview")
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

    logger.info(f"Creating new room: {name} (Mode: {modus}, Narrator: {erzaehler_modus})")

    # Raum erstellen
    # Spieleranzahl wird jetzt dynamisch aus der Lobby berechnet – keine manuelle Eingabe nötig
    raum = Raum(
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
    spieler = Spieler(
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

    logger.info(f"Room created: {raum.code} by {spieler.name}")
    return redirect(url_for("lobby", code=raum.code))


@app.route("/raum/beitreten", methods=["POST"])
def raum_beitreten():
    """Tritt einem existierenden Raum bei"""
    code = request.form.get("code", "").upper().strip()
    spieler_name = request.form.get("spieler_name", "Spieler")

    logger.info(f"Player {spieler_name} attempting to join room {code}")

    raum = Raum.query.filter_by(code=code).first()

    if not raum:
        logger.warning(f"Join failed: Room {code} not found")
        return render_template("index.html", fehler="Raum nicht gefunden!")

    if raum.spiel_gestartet:
        logger.warning(f"Join failed: Game in room {code} already started")
        return render_template("index.html", fehler="Das Spiel hat bereits begonnen!")

    # Pruefen ob Name bereits vergeben
    existiert = Spieler.query.filter_by(raum_id=raum.id, name=spieler_name[:30]).first()
    if existiert:
        logger.warning(f"Join failed: Name {spieler_name} already taken in room {code}")
        return render_template("index.html", fehler="Dieser Name ist bereits vergeben!")

    # Spieler erstellen
    session_id = Spieler.generiere_session()
    spieler = Spieler(name=spieler_name[:30], session_id=session_id, raum_id=raum.id)
    db.session.add(spieler)
    db.session.commit()

    session["spieler_session"] = session_id
    session["raum_code"] = raum.code

    logger.info(f"Player {spieler.name} joined room {code}")
    return redirect(url_for("lobby", code=raum.code))


@app.route("/lobby/<code>")
def lobby(code):
    """Lobby-Ansicht eines Raums"""
    logger.info(f"Accessing lobby for room {code}")
    raum = Raum.query.filter_by(code=code).first_or_404()
    spieler = hole_aktuellen_spieler()

    if not spieler or spieler.raum_id != raum.id:
        logger.warning(f"Unauthorized lobby access attempt for room {code}")
        return redirect(url_for("index"))

    if raum.spiel_gestartet:
        logger.info(f"Redirecting to game for room {code} (game started)")
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
    logger.info(f"Accessing game view for room {code}")
    raum = Raum.query.filter_by(code=code).first_or_404()
    spieler = hole_aktuellen_spieler()

    if not spieler or spieler.raum_id != raum.id:
        logger.warning(f"Unauthorized game access attempt for room {code}")
        return redirect(url_for("index"))

    if not raum.spiel_gestartet:
        logger.info(f"Redirecting to lobby for room {code} (game not started)")
        return redirect(url_for("lobby", code=code))

    alle_spieler = Spieler.query.filter_by(raum_id=raum.id).order_by(Spieler.name).all()
    lebende = [s for s in alle_spieler if s.ist_am_leben]

    # Rolle-Info holen - SICHER: Nur eigene Rolle wird mitgegeben
    rolle_info = ROLLEN.get(spieler.rolle, {})

    # Debug logging für Rolle
    if spieler.rolle:
        logger.info(
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
        logs = (
            SpielLog.query.filter(
                SpielLog.raum_id == raum.id,
                db.or_(
                    SpielLog.sichtbar_fuer == "alle",
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

        if spieler.rolle and "Seher" in spieler.rolle:
            seherin_enthuellung = SeherinEnthuellung.hole_enthuellung(
                spieler.id, raum.id
            )
    except Exception:
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
        # Werwoelfe sehen sich gegenseitig
        elif game_logic.ist_werwolf_rolle(
            spieler.rolle
        ) and game_logic.ist_werwolf_rolle(s.rolle):
            spieler_data["ist_werwolf"] = True
        sichere_spieler.append(spieler_data)

    # Erzähler-Text für Gruppen-Modus
    erzaehler_text = None
    if spieler.ist_erzaehler and raum.modus == "gruppe":
        phase_key = raum.aktuelle_phase
        # Map phase to event if possible, or use generic text
        # ERZAEHLER_TEXTE is gone, use ERZAEHLER_EVENTS or Role info
        # For now, we can try to find an event matching the phase
        # or just skip it if not found.
        # Legacy support:
        if phase_key in ERZAEHLER_EVENTS:
             erzaehler_text = ERZAEHLER_EVENTS[phase_key]

    enthuellung = {
        ziel_id: data["typ"] for ziel_id, data in seherin_enthuellung.items()
    }

    # =========================================================================
    # DYNAMIC STATE EFFECTS
    # Get all global state definitions for dynamic UI effects
    # =========================================================================
    from roles import RoleRegistry, get_spieler_state, get_player_visual_effects, get_role_state_display

    global_state_defs = RoleRegistry.get_all_global_state_definitions()

    # Get verliebt_mit_id from state for template (still needed for backward compat)
    verliebt_mit_id = spieler.get_state("global.verliebt_mit_id")

    # Build player visual effects map: {player_id: [effect_dicts]}
    player_effects = {}
    for s in alle_spieler:
        effects = get_player_visual_effects(s, global_state_defs, spieler.id)
        if effects:
            player_effects[s.id] = effects

    # Get dynamic role state display for sidebar (replaces hardcoded Hexe/Jäger checks)
    role_state_display = get_role_state_display(spieler)

    # Get the visible role for the current player (handles Hund, etc.)
    sichtbare_rolle = rolle_info.get("name", spieler.rolle) if rolle_info else spieler.rolle
    if spieler.rolle:
        role_obj = RoleRegistry.get(spieler.rolle)
        if role_obj:
            sichtbare_rolle = role_obj.get_sichtbare_rolle(spieler)

    # =========================================================================
    # DYNAMIC ROLE STYLES
    # Build role style data for dynamic CSS generation in template
    # =========================================================================
    rollen_styles = {}
    for role in RoleRegistry.get_all():
        info = role.info
        # Normalize role name to CSS class name
        css_name = info.name.lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        rollen_styles[css_name] = {
            'name': info.name,
            'farbe': info.farbe,
            'icon': info.icon,
            'team': info.team.value,
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
        verliebt_mit_id=verliebt_mit_id,  # From state (backward compat)
        player_effects=player_effects,  # Dynamic visual effects
        global_state_defs=global_state_defs,  # For template logic
        sichtbare_rolle=sichtbare_rolle,  # What player sees as their role
        rollen_styles=rollen_styles,  # Dynamic role colors/icons for CSS
        role_state_display=role_state_display,  # Dynamic role state for sidebar
    )


# ============================================================================
# ROLE API - Dynamic UI and Phase Generation
# ============================================================================


@app.route("/api/role/<role_name>/ui", methods=["GET"])
def get_role_ui(role_name):
    """Get UI definition for a specific role."""
    logger.debug(f"Fetching UI definition for role: {role_name}")
    from roles import RoleRegistry

    rolle = RoleRegistry.get(role_name)
    if not rolle:
        logger.warning(f"Role not found for UI request: {role_name}")
        return jsonify({"success": False, "error": "Role not found"}), 404

    ui = rolle.get_ui_definition()
    return jsonify(
        {
            "success": True,
            "ui": ui.to_dict(),
            "phase_name": rolle.get_phase_name(),
        }
    )


@app.route("/api/roles", methods=["GET"])
def get_roles():
    """Gibt alle verfügbaren Rollen zurück."""
    logger.debug("Fetching all roles")
    return jsonify(get_rollen_nach_erweiterung())


@app.route('/api/roles/styles')
def get_all_role_styles():
    """Returns all role visual definitions for dynamic CSS."""
    logger.debug("Fetching all role styles")
    styles = {}
    for role in RoleRegistry.get_all():
        info = role.info

        # Helper to darken color if needed (simple version)
        def _darken_color(hex_color, factor=0.8):
            if not hex_color or not hex_color.startswith('#'):
                return hex_color
            try:
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
            except:
                return hex_color

        styles[info.name] = {
            "css_class": info.computed_css_class,
            "icon": info.icon,
            "farbe": info.farbe,
            "team": info.team.value,
            "avatar_gradient_from": info.avatar_gradient_from or info.farbe,
            "avatar_gradient_to": info.avatar_gradient_to or _darken_color(info.farbe),
            "avatar_border_color": info.avatar_border_color or info.farbe,
            "badge_emoji": info.badge_emoji or "",
        }
    return jsonify({"success": True, "styles": styles})


@app.route("/api/role/<role_name>/info", methods=["GET"])
def get_role_info(role_name):
    """Get complete information about a role."""
    logger.debug(f"Fetching info for role: {role_name}")
    from roles import RoleRegistry

    rolle = RoleRegistry.get(role_name)
    if not rolle:
        logger.warning(f"Role not found for info request: {role_name}")
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
    logger.debug(f"Fetching game phases for room {code}")
    from phase_generator import (
        generate_phases_for_game,
        get_phase_display_info,
        build_phase_role_mapping,
    )

    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        logger.warning(f"Room not found for phases request: {code}")
        return jsonify({"success": False, "error": "Room not found"}), 404

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        logger.warning(f"Unauthorized phases request for room {code}")
        return jsonify({"success": False, "error": "Not authorized"}), 403

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
    logger.debug(f"Fetching info for phase: {phase_name}")
    from phase_generator import get_phase_display_info

    info = get_phase_display_info(phase_name)
    return jsonify(
        {
            "success": True,
            "phase": phase_name,
            "info": info,
        }
    )


# ============================================================================
# SITZORDNUNG API - Drag & Drop Sitzplatzwahl
# ============================================================================


@app.route("/api/sitzordnung/<code>", methods=["GET"])
def get_sitzordnung(code):
    """Gibt die aktuelle Sitzordnung zurück"""
    logger.debug(f"Fetching seating order for room {code}")
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
    logger.debug(f"Fetching role preview for room {code}")
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
    logger.info(f"Updating seating order for room {code}")
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Raum nicht gefunden"}), 404

    if raum.spiel_gestartet:
        return jsonify({"success": False, "error": "Spiel bereits gestartet"}), 400

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
    socketio.emit("sitzordnung_aktualisiert", {"ordnung": ordnung}, room=raum.code)

    return jsonify({"success": True})


@app.route("/api/phase_role_mapping", methods=["GET"])
def get_phase_role_mapping():
    """
    Gibt ein Mapping von Phasen zu Rollen zurück.
    Ermöglicht Frontend die dynamische Bestimmung ob ein Spieler in einer Phase aktiv ist.
    """
    logger.debug("Fetching phase-role mapping")
    from roles import RoleRegistry
    from phases import get_phase_list

    mapping = {}

    # Mapping für Nacht-Phasen
    for role in RoleRegistry.get_all():
        if role.info.nacht_aktiv:
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





@app.route("/api/raum/<code>/erzaehler/random", methods=["POST"])
def waehle_zufaelligen_erzaehler(code):
    """Wählt einen zufälligen Erzähler aus allen Spielern des Raums."""
    logger.info(f"Selecting random narrator for room {code}")
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
        room=raum.code,
    )

    return jsonify(
        {"success": True, "erzaehler": {"id": erzaehler.id, "name": erzaehler.name}}
    )


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================


def hole_aktuellen_spieler():
    """Holt den aktuellen Spieler basierend auf der Session"""
    session_id = session.get("spieler_session")
    if not session_id:
        return None
    return Spieler.query.filter_by(session_id=session_id).first()


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
    # logger.debug(f"Fetching village data for room {code}") # Too verbose for frequent polling
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
        room=raum.code,
    )


@socketio.on("connect")
def handle_connect():
    """Spieler verbindet sich"""
    spieler = hole_aktuellen_spieler()
    if spieler and spieler.raum_id:
        logger.info(f"Socket connected: {spieler.name} (ID: {spieler.id})")
        raum = db.session.get(Raum, spieler.raum_id)
        if raum:
            join_room(raum.code)
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
                room=raum.code,
            )
            # Sende aktualisierte Rollenvorschau an alle
            sende_rollen_vorschau_update(raum)


@socketio.on("disconnect")
def handle_disconnect():
    """Spieler trennt Verbindung"""
    spieler = hole_aktuellen_spieler()
    if spieler and spieler.raum_id:
        logger.info(f"Socket disconnected: {spieler.name} (ID: {spieler.id})")
        raum = db.session.get(Raum, spieler.raum_id)
        if raum:
            leave_room(raum.code)
            emit(
                "spieler_getrennt",
                {"spieler_id": spieler.id, "spieler_name": spieler.name},
                room=raum.code,
            )
            # Sende aktualisierte Rollenvorschau an alle
            sende_rollen_vorschau_update(raum)


@socketio.on("raum_beitreten")
def handle_raum_beitreten(data):
    """Spieler tritt Raum-Channel bei"""
    code = data.get("code")
    logger.info(f"Socket joining room channel: {code}")
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
                room=code,
            )

            # Online-Modus: Sende Erzählung für aktuelle Phase wenn Spiel läuft
            if (
                raum.modus == "online"
                and raum.spiel_gestartet
            ):
                # Try to find event for phase
                event_key = raum.aktuelle_phase
                if event_key in ERZAEHLER_EVENTS:
                    erzaehler_info = ERZAEHLER_EVENTS[event_key]
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
        logger.warning("Game start attempt without login")
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        logger.warning("Game start attempt for non-existent room")
        emit("fehler", {"nachricht": "Raum nicht gefunden"})
        return

    logger.info(f"Starting game in room {raum.code} (requested by {spieler.name})")

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
        emit(
            "spiel_gestartet",
            {"phase": raum.aktuelle_phase, "runde": raum.runde},
            room=raum.code,
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
                    room=raum.code,
                )

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

    logger.info(f"Phase advance requested by {spieler.name} in room {raum.code}")

    # Im Online-Modus darf der Admin/Creator die Phase weiterschalten (automatisch vom Client getriggert).
    # Im Gruppen-Modus darf nur der Erzähler manuell weiterschalten.
    is_admin = raum.erzaehler_id == spieler.id
    if raum.modus != "online" and not spieler.ist_erzaehler:
        emit("fehler", {"nachricht": "Nur der Erzähler kann die Phase wechseln"})
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
    logger.debug(f"Checking phase completion for {phase} in room {raum.code}")

    # Use RoleRegistry for dynamic phase-to-role mapping instead of hardcoded dict
    rolle_obj = RoleRegistry.get_role_for_phase(phase)
    rolle = rolle_obj.info.name if rolle_obj else None

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
    else:
        return

    if alle_fertig:
        logger.info(f"[Phase] Alle Aktionen in {phase} abgeschlossen, wechsle Phase")
        _wechsel_phase_intern(raum)


def _wechsel_phase_intern(raum):
    """
    Interne Funktion für Phasenwechsel.
    Wird rekursiv aufgerufen für automatische Phasen.
    """
    alte_phase = raum.aktuelle_phase
    neue_phase = game_logic.naechste_phase(raum)

    logger.info(f"Internal phase change: {alte_phase} -> {neue_phase} (Room: {raum.code})")

    # Phase-spezifische Aktionen
    handle_phase_wechsel(raum, alte_phase, neue_phase)

    # Erzähler-Text für Gruppen-Modus
    erzaehler_text = None
    if raum.modus == "gruppe" and neue_phase in ERZAEHLER_EVENTS:
        erzaehler_text = ERZAEHLER_EVENTS[neue_phase]

    # Online-Modus: Automatisch die erste Phase (rollen_verteilt) anzeigen und weiterschalten
    if raum.modus == "online":
        erzaehlung_text = ""

        # 1. Versuche dynamischen Text von der Rolle zu holen
        from roles import RoleRegistry
        from roles.base import SpielKontext, Phase

        role_obj = RoleRegistry.get_role_for_phase(neue_phase)
        if role_obj:
            # Kontext erstellen für dynamische Text-Generierung
            lebende = [s.id for s in Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False).all()]
            tote = [s.id for s in Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=False, ist_erzaehler=False).all()]

            kontext = SpielKontext(
                raum_id=raum.id,
                runde=raum.runde,
                phase=Phase.NACHT, # Meistens Nacht-Phasen
                aktiver_spieler_id=0,
                lebende_spieler=lebende,
                tote_spieler=tote
            )

            dynamic_text = role_obj.get_erzaehler_nacht_text(kontext)
            if dynamic_text:
                erzaehlung_text = dynamic_text

        # NO FALLBACKS ALLOWED - If dynamic text is missing, no text is shown.

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
            "erzaehlung", {"text": erzaehlung_text, "audio": audio_path}, room=raum.code
        )

    socketio.emit(
        "phase_geaendert",
        {
            "phase": neue_phase,
            "runde": raum.runde,
            "alte_phase": alte_phase,
            "erzaehler_text": erzaehler_text,
        },
        room=raum.code,
    )

    # Automatische Phasen: Nur reine Übergangs-Phasen die keine Aktion erfordern
    # WICHTIG: Night-Phase ist NIEMALS automatisch - dort agieren Rollen!
    # Diese Liste ist absichtlich minimal:
    AUTOMATISCHE_PHASEN = {
        "rollen_verteilt",  # Info-Phase nach Spielstart
        "tag_start",  # Übergang Nacht -> Tag
        "tag_ende",  # Übergang am Tagesende
    }

    ist_automatische_phase = neue_phase in AUTOMATISCHE_PHASEN

    # NO FALLBACKS ALLOWED - If audio fails or client disconnects, the game halts.
    # This is intentional per user request.


# Socket-Handler für Audio-Fertig-Event
@socketio.on("audio_fertig")
def handle_audio_fertig(data):
    """Client meldet dass Audio abgespielt wurde - Phase kann wechseln"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.modus != "online":
        return

    gemeldete_phase = data.get("phase", "")
    logger.debug(f"Audio finished reported for phase {gemeldete_phase} by {spieler.name}")

    # Nur der erste Spieler der meldet löst den Phasenwechsel aus
    # Prüfe ob wir noch in der gleichen Phase sind
    if raum.aktuelle_phase == gemeldete_phase:
        # WICHTIG: Nur automatische Phasen dürfen durch Audio-Ende weitergeschaltet werden!
        # Night-Phase ist NIEMALS automatisch - dort agieren Rollen!

        # Minimale automatische Phasen (nur Übergänge)
        AUTOMATISCHE_PHASEN = {
            "rollen_verteilt",
            "tag_start",
            "tag_ende",
        }

        if gemeldete_phase in AUTOMATISCHE_PHASEN:
            logger.info(f"[Audio] Audio fertig für Phase {gemeldete_phase}, wechsle Phase")
            _wechsel_phase_intern(raum)
        else:
            logger.info(
                f"[Audio] Audio fertig für interaktive Phase {gemeldete_phase} - warte auf Aktion"
            )
            # NO FALLBACKS ALLOWED - Game waits for player action.


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

    logger.info(f"Action request: {aktion_typ} by {spieler.name} -> Target: {ziel_id}")

    # Validierung
    if not spieler.ist_am_leben and aktion_typ != "jaeger_schuss":
        logger.warning(f"Action denied: Player {spieler.name} is dead")
        emit("fehler", {"nachricht": "Du bist tot und kannst nicht handeln"})
        return

    # Aktion basierend auf Phase und Rolle verarbeiten
    erfolg = verarbeite_aktion(spieler, raum, aktion_typ, ziel_id)

    if erfolg:
        logger.info(f"Action successful: {aktion_typ}")
        # Map action types to 3D effect types
        # Base mapping for common action types
        from roles.enums import AktionsTyp

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

        # Legacy mapping for specific action strings (backwards compatibility)
        legacy_effect_map = {
            "hexe_heilen": "heal",
            "heiler_schuetzen": "protect",
            "hexe_toeten": "poison",
            "hexe_vergiften": "poison",
            "werwolf_wahl": "attack",
            "armor_verlieben": "love",
            "seherin_sehen": "reveal",
        }

        effect_data = {"aktion": aktion_typ}

        # Try to determine effect from action type
        effekt = legacy_effect_map.get(aktion_typ)
        if not effekt:
            # Try to extract base action type (e.g., "sandmann_einschlaefern" -> check role)
            from roles import RoleRegistry

            rolle_obj = RoleRegistry.get(spieler.rolle)
            if rolle_obj:
                aktions_typ_enum = rolle_obj.aktions_typ
                effekt = AKTION_TYP_EFFEKT.get(
                    aktions_typ_enum.value
                    if hasattr(aktions_typ_enum, "value")
                    else str(aktions_typ_enum)
                )

        if ziel_id and effekt:
            effect_data["effekt"] = effekt
            effect_data["ziel_id"] = ziel_id

        emit("aktion_bestaetigt", effect_data)

        # Pruefen ob alle fertig sind
        pruefe_phase_abschluss(raum)
    else:
        logger.warning(f"Action failed: {aktion_typ}")
        emit("fehler", {"nachricht": "Aktion konnte nicht ausgefuehrt werden"})


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
    logger.info(f"Chat message from {spieler.name} in room {raum.code}")

    # SICHER: Keine sensiblen Daten im Chat
    if not spieler.ist_am_leben:
        # Tote chatten nur mit Toten
        emit(
            "chat_tot",
            {"von": spieler.name, "nachricht": nachricht, "spieler_id": spieler.id},
            room=raum.code,
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
            room=raum.code,
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

    logger.info(f"Hint request: {hinweis_typ} by {spieler.name} (Self-triggered: {selbst_ausgeloest})")

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
            "timestamp": datetime.utcnow().isoformat(),
        },
        room=raum.code,
    )

    # Log für Erzähler
    log = SpielLog(
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
    """
    from models import HINWEIS_CHANCEN
    import random

    # logger.debug(f"Generating random hints for room {raum_id}") # Too verbose

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
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=raum.code,
        )


# ============================================================================
# SPIELLOGIK HELFER
# ============================================================================


def verarbeite_aktion(spieler, raum, aktion_typ, ziel_id):
    """
    Verarbeitet eine Spielaktion.

    Refactored to use Role classes for validation and execution where possible.
    Some actions still require special handling (tag_wahl, jaeger_schuss).
    """
    logger.info(
        f"[Aktion] {aktion_typ} von {spieler.name} (Rolle: {spieler.rolle}) für Ziel-ID: {ziel_id}"
    )

    # Special case: Day voting (not role-specific)
    if aktion_typ == "tag_wahl":
        # Unterstütze beide alte "abstimmung" und neue "diskussion_abstimmung" Phase
        if raum.aktuelle_phase not in ["abstimmung", "diskussion_abstimmung"]:
            return False
        if game_logic.hat_spieler_gewaehlt(spieler, raum, raum.aktuelle_phase):
            return False
        game_logic.registriere_aktion(
            raum.id, raum.runde, raum.aktuelle_phase, "tag_wahl", spieler.id, ziel_id
        )
        # Speichere Vote in phase_votes JSON für live Updates
        if raum.aktuelle_phase == "diskussion_abstimmung":
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
                room=raum.code,
            )
            # Sende aktuelle Abstimmungs-Statistik für diskussion_abstimmung Phase
            if raum.aktuelle_phase == "diskussion_abstimmung":
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
                    room=raum.code,
                )
        return True

    # Special case: Jäger's last shot (happens after death, not in a phase)
    elif aktion_typ == "jaeger_schuss":
        if spieler.rolle != "Jäger" or not spieler.jaeger_schuss:
            return False
        spieler.jaeger_schuss = False
        ziel = db.session.get(Spieler, ziel_id)
        if ziel:
            logger.info(f"Jäger shot executed on {ziel.name}")
            game_logic.toete_spieler(ziel, "jaeger")
            # SICHER: Nur Name wird geteilt, Rolle erst nach Tod
            emit(
                "spieler_gestorben",
                {
                    "spieler_id": ziel.id,
                    "spieler_name": ziel.name,
                    "todesart": "jaeger",
                    "rolle": ziel.rolle,  # Rolle wird nach Tod enthuellt
                },
                room=raum.code,
            )
            db.session.commit()
            return True
        return False

    # Special case: Amor's love connection (requires 2 targets)
    elif aktion_typ == "armor_verlieben":
        logger.info(f"[Aktion] armor_verlieben von {spieler.name} (Rolle: {spieler.rolle})")
        if spieler.rolle != "Amor" or raum.aktuelle_phase != "amor_phase":
            logger.warning(
                f"[Aktion] ABGELEHNT: Rolle={spieler.rolle}, Phase={raum.aktuelle_phase}"
            )
            return False
        if not spieler.armor_verliebt:
            logger.warning(f"[Aktion] ABGELEHNT: armor_verliebt bereits False")
            return False

        ziel_ids = ziel_id if isinstance(ziel_id, list) else [ziel_id]
        if len(ziel_ids) != 2:
            logger.warning(f"[Aktion] ABGELEHNT: Nicht genau 2 Ziele ({len(ziel_ids)})")
            return False

        spieler1 = db.session.get(Spieler, ziel_ids[0])
        spieler2 = db.session.get(Spieler, ziel_ids[1])

        if spieler1 and spieler2:
            # Use state-based storage
            spieler1.set_state("global.verliebt_mit_id", spieler2.id)
            spieler2.set_state("global.verliebt_mit_id", spieler1.id)
            db.session.commit()
            logger.info(f"[Aktion] ERFOLG: {spieler1.name} ❤️ {spieler2.name}")

            # SICHER: Verliebte werden privat informiert
            game_logic.log_eintrag(
                raum.id,
                f"Du bist verliebt in {spieler2.name}!",
                sichtbar_fuer=str(spieler1.id),
            )
            game_logic.log_eintrag(
                raum.id,
                f"Du bist verliebt in {spieler1.name}!",
                sichtbar_fuer=str(spieler2.id),
            )

            # WICHTIG: Aktion registrieren, damit Phasenwechsel ausgelöst wird
            game_logic.registriere_aktion(
                raum.id,
                raum.runde,
                raum.aktuelle_phase,
                "armor_verlieben",
                spieler.id,
                ziel_ids[0],  # Erstes Ziel als Referenz
            )

            return True
        return False

    # ==========================================================================
    # GENERIC ACTION HANDLER for all roles
    # Uses the Role classes to process actions dynamically
    # ==========================================================================

    # Try generic handler first
    from roles import RoleRegistry
    from roles.base import SpielKontext
    from roles.enums import Phase

    # Get the player's role class
    rolle_obj = RoleRegistry.get(spieler.rolle)
    if not rolle_obj:
        logger.error(f"[Aktion] FEHLER: Rolle {spieler.rolle} nicht gefunden")
        return False

    # Build a SpielKontext for the role
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
    )

    # Check if the current phase matches the role's phase
    rolle_phase = rolle_obj.get_phase_name()
    if raum.aktuelle_phase != rolle_phase:
        logger.warning(
            f"[Aktion] ABGELEHNT: Falsche Phase. Erwartet={rolle_phase}, Aktuell={raum.aktuelle_phase}"
        )
        return False

    # Get the target player(s) if specified
    ziel = None
    if ziel_id:
        if isinstance(ziel_id, list):
             # Resolve list of IDs to list of objects
             ziel = [db.session.get(Spieler, zid) for zid in ziel_id]
             # Filter out None values just in case
             ziel = [z for z in ziel if z]
             if not ziel: # If all invalid
                 ziel = None
        else:
             ziel = db.session.get(Spieler, ziel_id)

    # Execute the role's night action
    logger.info(f"[Aktion] Ausfuehren: {spieler.rolle} -> {ziel.name if ziel else 'None'}")
    ergebnis = rolle_obj.on_nacht_aktion(spieler, ziel, kontext)

    if ergebnis and ergebnis.erfolg:
        # Register the action
        game_logic.registriere_aktion(
            raum.id, raum.runde, rolle_phase, aktion_typ, spieler.id, ziel_id
        )

        # Apply effects from the role action
        if ergebnis.effekte:
            # Generic Effect Processor
            # Effects are keyed like "state_key" -> value
            # The Role class defines what states it uses.
            # Example: {"hexe.heiltrank": False, "global.verliebt_mit_id": 5}
            
            for effect_key, effect_value in ergebnis.effekte.items():
                # Check if it's a state key (contains a dot = role.field)
                if "." in effect_key:
                    # Set player state dynamically
                    spieler.set_state(effect_key, effect_value)
                    
            # Legacy effect handling (for backwards compatibility)
            # TODO: Migrate all roles to use state keys instead of these
            if "geschuetzt" in ergebnis.effekte:
                geschuetzt_id = ergebnis.effekte["geschuetzt"]
                geschuetzt_spieler = db.session.get(Spieler, geschuetzt_id)
                if geschuetzt_spieler:
                    geschuetzt_spieler.set_state("heiler.beschuetzt", True)

        # Send role-specific results
        # Send role-specific results (Generic)
        if hasattr(ergebnis, "private_infos") and ergebnis.private_infos:
            for pid, info in ergebnis.private_infos.items():
                p_sock_id = None # Need to find socket ID for player ID
                # We don't have direct mapping here easily without tracking.
                # But we can emit to the room and let client filter if we trust it,
                # OR better: use socketio.emit to room=player_session_id if we had it.
                # Current app structure uses room=code for game.
                # We can use room=sid for requests, but here the recipients are distinct.
                
                # Helper to find session/sid for player:
                p_obj = db.session.get(Spieler, pid)
                if p_obj: 
                    # We can target the player via a room named after their ID if we joined them to it?
                    # Or just emit "private_info" to the game room with "recipient_id"
                    socketio.emit("private_info", {"recipient_id": pid, "payload": info}, room=raum.code)

        # Legacy Seherin Support (can be removed if Seherin migrated to private_infos)
        if spieler.rolle == "Seherin" and ergebnis.effekte and not getattr(ergebnis, "private_infos", None):
             socketio.emit(
                "seherin_ergebnis",
                {
                    "ziel_name": ziel.name if ziel else "Unbekannt",
                    "ist_werwolf": ergebnis.effekte.get("ist_werwolf", False),
                    "rolle": ergebnis.effekte.get("rolle", "Unbekannt"),
                },
                room=request.sid,
            )
        
        if ergebnis.nachricht or ergebnis.effekte:
            # Determine visual effect (from Role or Default)
            # Default fallback mapping
            from roles.enums import AktionsTyp
            visual_effect = "sparkle"
            
            DEFAULT_EFFECTS = {
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
            
            # Check if result has visual_effect or map from action type
            if hasattr(ergebnis, 'visual_effect') and ergebnis.visual_effect:
                visual_effect = ergebnis.visual_effect
            else:
                visual_effect = DEFAULT_EFFECTS.get(aktion_typ, "sparkle")

            # Generic result message for the actor
            emit(
                "aktion_ergebnis",
                {
                    "nachricht": ergebnis.nachricht,
                    "effekte": ergebnis.effekte,
                    "ziel_id": ziel_id,
                    "effekt": visual_effect 
                },
            )

        db.session.commit()
        return True

    return False


def handle_phase_wechsel(raum, alte_phase, neue_phase):
    """Behandelt Phasenwechsel-Logik"""
    logger.info(f"[Phase] Wechsel: {alte_phase} -> {neue_phase}")

    # Heiler-Schutz zuruecksetzen am Nachtende
    if alte_phase == "heiler_phase":
        pass  # Schutz bleibt bis Nacht-Ende

    
    
    # Generic Phase Start Info (Scheduler Based)
    # --------------------------------------------------------------------------
    import json
    from roles import RoleRegistry
    from roles.base import SpielKontext, Phase
    
    # Load Scheduler Data
    phase_data = {}
    if raum.phase_data:
        try:
            phase_data = json.loads(raum.phase_data)
        except:
            pass
            
    active_role = phase_data.get('active_role')
    display_info = phase_data.get('display_info')
    
    # 1. Broadcast Generic Phase Update (Public)
    socketio.emit("phase_update", {
        "phase": neue_phase,       # e.g. "nacht"
        "active_role": active_role, # e.g. "Seherin" (or None)
        "display_info": display_info # UI Metadata
    }, room=raum.code)
    
    # 2. Send Private Info to Active Player
    if active_role:
        role_obj = RoleRegistry.get(active_role)
        if role_obj:
            # Find active player(s)
            # Handle list for group roles? generic get_phase_start_info usually for specific player.
            # But get_phase_start_info takes (spieler, kontext). 
            # We iterate all potential active players of this role.
            active_players = Spieler.query.filter_by(raum_id=raum.id, rolle=active_role, ist_am_leben=True).all()
            
            # Helper to get Werwolf Victim (generic)
            # TODO: Move this logic into Werwolf.get_phase_start_info or generic "Context Builder"
            werwolf_opfer_id = None
            if active_role == "Hexe":
                 # Hexe needs victim info. 
                 # We can rely on Hexe.get_phase_start_info fetching it via Context?
                 # Need to populate context.
                 # Optimization: game_logic.werwolf_abstimmung(raum) call?
                 res = game_logic.werwolf_abstimmung(raum)
                 if res:
                     werwolf_opfer_id = res.get("opfer_id")
                     
            # Build Context
            lebende = [s.id for s in Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False).all()]
            tote = [s.id for s in Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=False, ist_erzaehler=False).all()]
            
            kontext = SpielKontext(
                raum_id=raum.id,
                runde=raum.runde,
                phase=Phase.NACHT, 
                aktiver_spieler_id=0,
                lebende_spieler=lebende,
                tote_spieler=tote,
                werwolf_opfer_id=werwolf_opfer_id,
                spieler_namen={s.id: s.name for s in Spieler.query.filter_by(raum_id=raum.id).all()}
            )
            
            for player in active_players:
                info = role_obj.get_phase_start_info(player, kontext)
                if info:
                    # Emit private info
                    socketio.emit("private_phase_info", {
                        "recipient_id": player.id,
                        "payload": info
                    }, room=raum.code)
                    
                    # Legacy Compatibility (e.g. for Hexe JS handler if not updated yet)
                    if active_role == "Hexe":
                        socketio.emit("hexe_info", info, room=raum.code) # TODO: Remove after frontend update

  
    elif neue_phase == "nacht_ende":
        logger.info(f"[Nacht] Verarbeite Nacht-Ende für Runde {raum.runde}")

        werwolf_opfer = SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            phase="werwolf_phase",
            aktion_typ="werwolf_wahl",
        ).first()

        logger.debug(f"[Nacht] Werwolf-Opfer-Aktion gefunden: {werwolf_opfer is not None}")
        if werwolf_opfer:
            logger.debug(f"[Nacht] Werwolf-Ziel-ID: {werwolf_opfer.ziel_spieler_id}")

        geheilt = SpielAktion.query.filter_by(
            raum_id=raum.id, runde=raum.runde, phase="hexe_phase", aktion_typ="heilen"
        ).first()

        vergiftet = SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            phase="hexe_phase",
            aktion_typ="vergiften",
        ).first()

        tote = []

        # Werwolf-Opfer (wenn nicht geheilt oder geschuetzt)
        if werwolf_opfer and werwolf_opfer.ziel_spieler_id:
            opfer = db.session.get(Spieler, werwolf_opfer.ziel_spieler_id)
            if opfer:
                logger.debug(
                    f"[Nacht] Werwolf-Opfer: {opfer.name}, am_leben={opfer.ist_am_leben}"
                )
            if opfer and opfer.ist_am_leben:
                # Pruefen ob geheilt
                if geheilt and geheilt.ziel_spieler_id == opfer.id:
                    logger.info(f"[Nacht] {opfer.name} wurde von Hexe geheilt!")
                # Pruefen ob vom Heiler geschuetzt
                elif opfer.ist_beschuetzt:
                    logger.info(f"[Nacht] {opfer.name} wurde vom Heiler geschützt!")
                else:
                    logger.info(f"[Nacht] {opfer.name} STIRBT durch Werwolf!")
                    game_logic.toete_spieler(opfer, "werwolf")
                    tote.append(
                        {
                            "name": opfer.name,
                            "rolle": opfer.rolle,
                            "todesart": "werwolf",
                        }
                    )

        # Hexen-Gift-Opfer
        if vergiftet and vergiftet.ziel_spieler_id:
            opfer = db.session.get(Spieler, vergiftet.ziel_spieler_id)
            if opfer and opfer.ist_am_leben:
                logger.info(f"[Nacht] {opfer.name} STIRBT durch Hexen-Gift!")
                game_logic.toete_spieler(opfer, "hexe")
                tote.append(
                    {"name": opfer.name, "rolle": opfer.rolle, "todesart": "hexe"}
                )

        # Heiler-Schutz zuruecksetzen
        for s in Spieler.query.filter_by(raum_id=raum.id).all():
            s.ist_beschuetzt = False
        db.session.commit()

        logger.info(f"[Nacht] Tote in dieser Nacht: {len(tote)}")
        if tote:
            socketio.emit("nacht_ergebnis", {"tote": tote}, room=raum.code)
        else:
            socketio.emit(
                "nacht_ergebnis",
                {"tote": [], "nachricht": "Niemand ist in der Nacht gestorben."},
                room=raum.code,
            )

        # Spielende pruefen
        ende = game_logic.pruefe_spielende(raum)
        if ende:
            logger.info(f"[Spiel] ENDE! Gewinner: {ende.get('gewinner', 'unbekannt')}")
            raum.aktuelle_phase = "spiel_ende"
            db.session.commit()
            socketio.emit("spiel_ende", ende, room=raum.code)

    elif alte_phase == "abstimmung":
        # Tag-Abstimmung auswerten
        ergebnis = game_logic.tag_abstimmung(raum)

        if ergebnis:
            if ergebnis.get("kein_opfer"):
                socketio.emit(
                    "abstimmung_ergebnis",
                    {"kein_opfer": True, "nachricht": ergebnis.get("nachricht")},
                    room=raum.code,
                )
            else:
                opfer = db.session.get(Spieler, ergebnis["opfer_id"])
                if opfer:
                    tod_ergebnis = game_logic.toete_spieler(opfer, "abstimmung")
                    socketio.emit(
                        "abstimmung_ergebnis",
                        {
                            "opfer_name": ergebnis["opfer_name"],
                            "opfer_rolle": ergebnis["opfer_rolle"],
                            "stimmen": ergebnis["stimmen"],
                            "jaeger_aktiv": "jaeger_schuss"
                            in tod_ergebnis.get("folge_aktionen", []),
                        },
                        room=raum.code,
                    )

                    # Jaeger-Phase einschalten wenn noetig
                    if "jaeger_schuss" in tod_ergebnis.get("folge_aktionen", []):
                        raum.aktuelle_phase = "jaeger_phase"
                        db.session.commit()

        # Spielende pruefen
        ende = game_logic.pruefe_spielende(raum)
        if ende:
            raum.aktuelle_phase = "spiel_ende"
            db.session.commit()
            socketio.emit("spiel_ende", ende, room=raum.code)


# ============================================================================
# DISKUSSION & ABSTIMMUNG PHASE - Timer & Voting Display
# ============================================================================


@socketio.on("timer_tick")
def handle_timer_tick():
    """Sendet Timer-Updates an alle Spieler in einem Raum"""
    # logger.debug("Timer tick") # Too verbose
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.aktuelle_phase != "diskussion_abstimmung":
        return

    verbleibend = game_logic.get_verbleibende_zeit(raum)
    abgelaufen = game_logic.timer_abgelaufen(raum)

    emit(
        "timer_update",
        {
            "sekunden_verbleibend": verbleibend,
            "timer_abgelaufen": abgelaufen,
        },
        room=raum.code,
    )

    # Wenn Timer abgelaufen und Phase noch nicht gewechselt, wechsle jetzt
    if abgelaufen and raum.aktuelle_phase == "diskussion_abstimmung":
        # Werte Abstimmung aus
        ergebnis = game_logic.werte_abstimmung_aus(raum)
        if ergebnis:
            socketio.emit("abstimmung_ergebnis", ergebnis, room=raum.code)

            # Wenn Opfer: töte es
            if not ergebnis.get("kein_opfer"):
                opfer = db.session.get(Spieler, ergebnis["opfer_id"])
                if opfer:
                    tod_ergebnis = game_logic.toete_spieler(opfer, "abstimmung")
                    socketio.emit(
                        "spieler_gestorben",
                        {
                            "spieler_id": opfer.id,
                            "spieler_name": opfer.name,
                            "rolle": opfer.rolle,
                            "todesart": "abstimmung",
                        },
                        room=raum.code,
                    )

        # Wechsle zur nächsten Phase
        _wechsel_phase_intern(raum)


@socketio.on("spieler_abstimmen")
def handle_spieler_abstimmen(data):
    """Registriert die Abstimmung eines Spielers in der diskussion_abstimmung Phase"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.aktuelle_phase != "diskussion_abstimmung":
        emit("fehler", {"nachricht": "Nicht in der richtigen Phase"})
        return

    ziel_id = data.get("ziel_id")
    logger.info(f"Player {spieler.name} voted for {ziel_id}")

    # Registriere Aktion
    erfolg = verarbeite_aktion(spieler, raum, "tag_wahl", ziel_id)

    if erfolg:
        # Prüfe ob alle abgestimmt haben
        if game_logic.pruefen_abstimmung_komplett(raum):
            # Alle haben abgestimmt - werte aus und wechsle Phase
            ergebnis = game_logic.werte_abstimmung_aus(raum)
            if ergebnis:
                socketio.emit("abstimmung_ergebnis", ergebnis, room=raum.code)

                # Wenn Opfer: töte es
                if not ergebnis.get("kein_opfer"):
                    opfer = db.session.get(Spieler, ergebnis["opfer_id"])
                    if opfer:
                        tod_ergebnis = game_logic.toete_spieler(opfer, "abstimmung")
                        socketio.emit(
                            "spieler_gestorben",
                            {
                                "spieler_id": opfer.id,
                                "spieler_name": opfer.name,
                                "rolle": opfer.rolle,
                                "todesart": "abstimmung",
                            },
                            room=raum.code,
                        )

            # Wechsle zur nächsten Phase
            _wechsel_phase_intern(raum)
        else:
            emit("aktion_bestaetigt", {"aktion": "tag_wahl"})
    else:
        emit("fehler", {"nachricht": "Abstimmung konnte nicht gespeichert werden"})


@socketio.on("hole_abstimmung_status")
def handle_hole_abstimmung_status():
    """Sends current voting status for diskussion_abstimmung phase"""
    # logger.debug("Fetching voting status") # Too verbose
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.aktuelle_phase != "diskussion_abstimmung":
        return

    stats = game_logic.berechne_abstimmungs_statistik(raum)
    verbleibend = game_logic.get_verbleibende_zeit(raum)

    # Konvertiere ziel_stimmen dict für JSON-Serialisierung
    ziel_stimmen_str = {}
    for ziel_id, stimmen in stats["ziel_stimmen"].items():
        ziel_spieler = db.session.get(Spieler, int(ziel_id))
        if ziel_spieler:
            ziel_stimmen_str[ziel_spieler.name] = stimmen

    emit(
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
        room=request.sid,
    )


@socketio.on("starte_diskussion_abstimmung")
def handle_starte_diskussion_abstimmung(data):
    """Startet die diskussion_abstimmung Phase (nur für Erzähler)"""
    spieler = hole_aktuellen_spieler()
    if not spieler or not spieler.ist_erzaehler:
        emit("fehler", {"nachricht": "Nur der Erzähler kann diese Phase starten"})
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        return

    dauer = data.get("dauer_sekunden", 120)
    logger.info(f"Starting discussion/voting phase for {dauer}s in room {raum.code}")
    game_logic.starte_diskussion_abstimmung(raum, dauer)

    socketio.emit(
        "phase_gestartet",
        {
            "phase": "diskussion_abstimmung",
            "dauer_sekunden": dauer,
        },
        room=raum.code,
    )

