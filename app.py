"""
Webwoelfe - Das Online Werwolf-Spiel
Ein Echtzeit-Multiplayer Werwolf-Spiel mit WebSocket-Unterstützung.
"""

# Gevent monkey-patching MUSS vor allen anderen Imports erfolgen!
# (Gevent ist der moderne Ersatz für das deprecated eventlet)
from gevent import monkey
import gevent
import inspect
from flask_minify import Minify

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
import inspect
from datetime import datetime
import inspect

# App Konfiguration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///webwoelfe.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
Minify(app=app, html=True, js=True, cssless=True)

# Spielname als Konstante
SPIEL_NAME = "Webwölfe"

# Phasen-Konfiguration
# Wartezeit zwischen automatischen Phasenwechseln (in Sekunden)
# Mindestens 30 Sekunden um Audio-Erzählung vollständig abzuspielen
PHASE_WECHSEL_DELAY = int(os.environ.get("PHASE_DELAY", "30"))


def log_ts(msg: str):
    """Log mit Timestamp für Debugging"""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}")


# Initialisierung
db.init_app(app)
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
    result = result.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
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


# Datenbank erstellen
with app.app_context():
    db.create_all()


# Cleanup Task starten
def start_cleanup_task():
    """Startet den Hintergrund-Task zur Bereinigung alter Spiele"""
    try:
        import gevent
        from cleanup import cleanup_old_games

        def run_cleanup():
            print("[System] Cleanup-Task gestartet.")
            # Einmal beim Start ausführen
            cleanup_old_games(app, max_age_hours=24)
            while True:
                gevent.sleep(3600)  # Warte 1 Stunde
                cleanup_old_games(app, max_age_hours=24)

        gevent.spawn(run_cleanup)
    except ImportError:
        print("[System] Warnung: Gevent nicht verfügbar, Cleanup-Task deaktiviert.")
    except Exception as e:
        log_ts(f"[System] Fehler beim Starten des Cleanup-Tasks: {e}")


start_cleanup_task()


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
    spieler = Spieler(name=spieler_name[:30], session_id=session_id, raum_id=raum.id)
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
    from roles import RoleRegistry
    
    rolle = RoleRegistry.get(role_name)
    if not rolle:
        return jsonify({"success": False, "error": "Role not found"}), 404
    
    ui = rolle.get_ui_definition()
    return jsonify({
        "success": True,
        "ui": ui.to_dict(),
        "phase_name": rolle.get_phase_name(),
    })


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
    extension_filter = request.args.get('extension_pack')
    kategorie_filter = request.args.get('kategorie')
    team_filter = request.args.get('team')
    
    # Get all roles
    all_roles = RoleRegistry.get_all()
    
    # Apply filters
    filtered_roles = all_roles
    if extension_filter:
        filtered_roles = [r for r in filtered_roles if r.info.extension_pack == extension_filter]
    if kategorie_filter:
        from roles.enums import Kategorie
        filtered_roles = [r for r in filtered_roles if r.info.kategorie.value == kategorie_filter]
    if team_filter:
        from roles.enums import Team
        filtered_roles = [r for r in filtered_roles if r.info.team.value == team_filter]
    
    # Convert to dict format
    roles_data = [role.to_dict() for role in filtered_roles]
    
    # Group by extension pack for frontend convenience
    grouped_by_extension = {}
    for role in filtered_roles:
        ext_pack = role.info.extension_pack
        if ext_pack not in grouped_by_extension:
            grouped_by_extension[ext_pack] = []
        grouped_by_extension[ext_pack].append(role.to_dict())
    
    return jsonify({
        "success": True,
        "roles": roles_data,
        "grouped_by_extension": grouped_by_extension,
        "total_count": len(roles_data),
    })


@app.route("/api/role/<role_name>/info", methods=["GET"])
def get_role_info_api(role_name):
    """Get complete information about a role."""
    from roles import RoleRegistry
    
    rolle = RoleRegistry.get(role_name)
    if not rolle:
        return jsonify({"success": False, "error": "Role not found"}), 404
    
    return jsonify({
        "success": True,
        "role": rolle.to_dict(),
    })


@app.route("/api/game/<code>/phases", methods=["GET"])
def get_game_phases(code):
    """Get dynamic phase list and phase-role mapping for a specific game."""
    from phase_generator import generate_phases_for_game, get_phase_display_info, build_phase_role_mapping
    
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"success": False, "error": "Room not found"}), 404
    
    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"success": False, "error": "Not authorized"}), 403
    
    phases = generate_phases_for_game(raum)
    phase_info = [get_phase_display_info(p) for p in phases]
    phase_mapping = build_phase_role_mapping(raum)
    
    return jsonify({
        "success": True,
        "phases": phases,
        "phase_info": phase_info,
        "phase_mapping": phase_mapping,  # NEW: Which role acts in which phase
        "current_phase": raum.aktuelle_phase,
        "current_round": raum.runde,
    })


@app.route("/api/phase/<phase_name>/info", methods=["GET"])
def get_phase_info(phase_name):
    """Get display information for a phase."""
    from phase_generator import get_phase_display_info
    
    info = get_phase_display_info(phase_name)
    return jsonify({
        "success": True,
        "phase": phase_name,
        "info": info,
    })


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
    return jsonify({"success": True})


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
            log_ts(f"[PhaseCheck] Relevante Spieler für {rolle}: {[s.name for s in relevant]}")
            missing = [s.name for s in relevant if not game_logic.hat_spieler_gewaehlt(s, raum, phase)]
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
        "nacht_start",      # Übergang Tag -> Nacht
        "nacht_ende",       # Übergang Nacht -> Tag
        "tag_start",        # Übergang Nacht -> Tag
        "tag_ende",         # Übergang am Tagesende
    }
    
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
    """Client meldet dass Audio abgespielt wurde - Phase kann wechseln"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        return

    raum = db.session.get(Raum, spieler.raum_id)
    if not raum or raum.modus != "online":
        return

    gemeldete_phase = data.get("phase", "")

    # Nur der erste Spieler der meldet löst den Phasenwechsel aus
    # Prüfe ob wir noch in der gleichen Phase sind
    if raum.aktuelle_phase == gemeldete_phase:
        # WICHTIG: Nur automatische Phasen dürfen durch Audio-Ende weitergeschaltet werden!
        # Night-Phase ist NIEMALS automatisch - dort agieren Rollen!
        
        # Minimale automatische Phasen (nur Übergänge)
        AUTOMATISCHE_PHASEN = {
            "rollen_verteilt",
            "nacht_start",
            "nacht_ende",
            "tag_start",
            "tag_ende",
        }
        
        if gemeldete_phase in AUTOMATISCHE_PHASEN:
            log_ts(f"[Audio] Audio fertig für Phase {gemeldete_phase}, wechsle Phase")
            _wechsel_phase_intern(raum)
        else:
            log_ts(
                f"[Audio] Audio fertig für interaktive Phase {gemeldete_phase} - warte auf Aktion"
            )
            # Fallback-Schutz: Wenn in Online-Partys niemand handelt, darf die Phase nicht hängen bleiben
            if raum.modus == "online":
                raum_code = raum.code
                phase_bei_start = gemeldete_phase

                import gevent

                def interactive_fallback():
                    # Warte auf Standard-Timeout (z.B. 30s) – danach prüfen ob Phase noch offen ist
                    gevent.sleep(PHASE_WECHSEL_DELAY)
                    with app.app_context():
                        raum_aktuell = Raum.query.filter_by(code=raum_code).first()
                        if not raum_aktuell or raum_aktuell.aktuelle_phase != phase_bei_start:
                            return  # Phase hat sich inzwischen geändert

                        # FEHLER: Fallback für interaktive Phasen sollte nie notwendig sein!
                        logger.error(
                            f"[Phase] FALLBACK-TIMEOUT für interaktive Phase {phase_bei_start} - Dies ist ein Fehler! Spieler haben nicht reagiert."
                        )

                        # Erst reguläre Abschlussprüfung versuchen (falls Aktionen inzwischen eingetroffen sind)
                        try:
                            pruefe_phase_abschluss(raum_aktuell)
                        except Exception as exc:  # Best effort, darf den Fallback nicht blockieren
                            log_ts(f"[Phase] Fehler bei Fallback-Abschlussprüfung: {exc}")

                        # Wenn immer noch dieselbe Phase aktiv ist, erzwinge den Wechsel
                        raum_nach_pruefung = Raum.query.filter_by(code=raum_code).first()
                        if raum_nach_pruefung and raum_nach_pruefung.aktuelle_phase == phase_bei_start:
                            _wechsel_phase_intern(raum_nach_pruefung)

                gevent.spawn(interactive_fallback)


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

    # Validierung
    if not spieler.ist_am_leben and aktion_typ != "jaeger_schuss":
        emit("fehler", {"nachricht": "Du bist tot und kannst nicht handeln"})
        return

    # Aktion basierend auf Phase und Rolle verarbeiten
    erfolg = verarbeite_aktion(spieler, raum, aktion_typ, ziel_id)

    if erfolg:
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
                effekt = AKTION_TYP_EFFEKT.get(aktions_typ_enum.value if hasattr(aktions_typ_enum, 'value') else str(aktions_typ_enum))
        
        if ziel_id and effekt:
            effect_data["effekt"] = effekt
            effect_data["ziel_id"] = ziel_id

        emit("aktion_bestaetigt", effect_data)

        # Pruefen ob alle fertig sind
        pruefe_phase_abschluss(raum)
    else:
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
    log_ts(
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
        log_ts(f"[Aktion] armor_verlieben von {spieler.name} (Rolle: {spieler.rolle})")
        if spieler.rolle != "Amor" or raum.aktuelle_phase != "amor_phase":
            log_ts(
                f"[Aktion] ABGELEHNT: Rolle={spieler.rolle}, Phase={raum.aktuelle_phase}"
            )
            return False
        if not spieler.armor_verliebt:
            log_ts(f"[Aktion] ABGELEHNT: armor_verliebt bereits False")
            return False

        ziel_ids = ziel_id if isinstance(ziel_id, list) else [ziel_id]
        if len(ziel_ids) != 2:
            log_ts(f"[Aktion] ABGELEHNT: Nicht genau 2 Ziele ({len(ziel_ids)})")
            return False

        spieler1 = db.session.get(Spieler, ziel_ids[0])
        spieler2 = db.session.get(Spieler, ziel_ids[1])

        if spieler1 and spieler2:
            spieler1.verliebt_mit_id = spieler2.id
            spieler2.verliebt_mit_id = spieler1.id
            spieler.armor_verliebt = False
            db.session.commit()
            log_ts(f"[Aktion] ERFOLG: {spieler1.name} ❤️ {spieler2.name}")

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
        log_ts(f"[Aktion] FEHLER: Rolle {spieler.rolle} nicht gefunden")
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
        log_ts(
            f"[Aktion] ABGELEHNT: Falsche Phase. Erwartet={rolle_phase}, Aktuell={raum.aktuelle_phase}"
        )
        return False

    # Get the target player if specified
    ziel = db.session.get(Spieler, ziel_id) if ziel_id else None

    # Execute the role's night action
    log_ts(f"[Aktion] Ausfuehren: {spieler.rolle} -> {ziel.name if ziel else 'None'}")
    
    # Pass 'aktion' only if accepted by the method signature
    # (Fixes compatibility with legacy roles like Heiler that don't accept 'aktion')
    sig = inspect.signature(rolle_obj.on_nacht_aktion)
    call_kwargs = {}
    if "aktion" in sig.parameters:
        call_kwargs["aktion"] = aktion_typ
        
    ergebnis = rolle_obj.on_nacht_aktion(spieler, ziel, kontext, **call_kwargs)

    if ergebnis and ergebnis.erfolg:
        # Register the action
        game_logic.registriere_aktion(
            raum.id, raum.runde, rolle_phase, aktion_typ, spieler.id, ziel_id
        )

        # Apply effects from the role action
        if ergebnis.effekte:
            # Heiler protection
            if "geschuetzt" in ergebnis.effekte:
                geschuetzt_id = ergebnis.effekte["geschuetzt"]
                geschuetzt_spieler = db.session.get(Spieler, geschuetzt_id)
                if geschuetzt_spieler:
                    geschuetzt_spieler.ist_beschuetzt = True

            # Remember Heiler's target for next round
            if "heiler_ziel_merken" in ergebnis.effekte:
                spieler.heiler_geschuetzt = ergebnis.effekte["heiler_ziel_merken"]

            # Hexe potion usage
            if "heiltrank_verbraucht" in ergebnis.effekte:
                spieler.hexe_heiltrank = False
            if "gifttrank_verbraucht" in ergebnis.effekte:
                spieler.hexe_gifttrank = False

        # Send role-specific results
        if spieler.rolle == "Seherin" and ergebnis.effekte:
            # Seherin gets a special result event
            socketio.emit(
                "seherin_ergebnis",
                {
                    "ziel_name": ziel.name if ziel else "Unbekannt",
                    "ist_werwolf": ergebnis.effekte.get("ist_werwolf", False),
                    "rolle": ergebnis.effekte.get("rolle", "Unbekannt"),
                },
                room=request.sid,
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
        return True

    return False


def handle_phase_wechsel(raum, alte_phase, neue_phase):
    """Behandelt Phasenwechsel-Logik"""
    log_ts(f"[Phase] Wechsel: {alte_phase} -> {neue_phase}")

    # Heiler-Schutz zuruecksetzen am Nachtende
    if alte_phase == "heiler_phase":
        pass  # Schutz bleibt bis Nacht-Ende

    if alte_phase == "werwolf_phase":
        # Werwolf-Opfer ermitteln und an Hexe senden
        ergebnis = game_logic.werwolf_abstimmung(raum)
        if ergebnis and "opfer_id" in ergebnis:
            hexe = Spieler.query.filter_by(
                raum_id=raum.id, rolle="Hexe", ist_am_leben=True
            ).first()
            if hexe:
                opfer = db.session.get(Spieler, ergebnis["opfer_id"])
                if opfer:
                    socketio.emit(
                        "hexe_info",
                        {"opfer_name": opfer.name, "opfer_id": opfer.id},
                        room=request.sid if hasattr(request, "sid") else raum.code,
                    )

    # WICHTIG: Nacht-Tode bei nacht_ende verarbeiten!
    # Dies stellt sicher dass Tode immer verarbeitet werden, auch wenn
    # hexe_phase übersprungen wird (weil keine Hexe existiert)
    elif neue_phase == "nacht_ende":
        log_ts(f"[Nacht] Verarbeite Nacht-Ende für Runde {raum.runde}")

        werwolf_opfer = SpielAktion.query.filter(
            SpielAktion.raum_id == raum.id,
            SpielAktion.runde == raum.runde,
            SpielAktion.phase == "werwolf_phase",
            SpielAktion.aktion_typ.in_(["werwolf_wahl", "toeten"])
        ).first()

        log_ts(f"[Nacht] Werwolf-Opfer-Aktion gefunden: {werwolf_opfer is not None}")
        if werwolf_opfer:
            log_ts(f"[Nacht] Werwolf-Ziel-ID: {werwolf_opfer.ziel_spieler_id}")

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
                log_ts(
                    f"[Nacht] Werwolf-Opfer: {opfer.name}, am_leben={opfer.ist_am_leben}"
                )
            if opfer and opfer.ist_am_leben:
                # Pruefen ob geheilt
                if geheilt and geheilt.ziel_spieler_id == opfer.id:
                    log_ts(f"[Nacht] {opfer.name} wurde von Hexe geheilt!")
                # Pruefen ob vom Heiler geschuetzt
                elif opfer.ist_beschuetzt:
                    log_ts(f"[Nacht] {opfer.name} wurde vom Heiler geschützt!")
                else:
                    log_ts(f"[Nacht] {opfer.name} STIRBT durch Werwolf!")
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
                log_ts(f"[Nacht] {opfer.name} STIRBT durch Hexen-Gift!")
                game_logic.toete_spieler(opfer, "hexe")
                tote.append(
                    {"name": opfer.name, "rolle": opfer.rolle, "todesart": "hexe"}
                )

        # Heiler-Schutz zuruecksetzen
        for s in Spieler.query.filter_by(raum_id=raum.id).all():
            s.ist_beschuetzt = False
        db.session.commit()

        log_ts(f"[Nacht] Tote in dieser Nacht: {len(tote)}")
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
            log_ts(f"[Spiel] ENDE! Gewinner: {ende.get('gewinner', 'unbekannt')}")
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

        # Initialisierung für Diskussions-Phase (Timer setzen)
        if neue_phase == "diskussion_abstimmung":
            game_logic.starte_diskussion_abstimmung(raum)

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
    game_logic.starte_diskussion_abstimmung(raum, dauer)

    socketio.emit(
        "phase_gestartet",
        {
            "phase": "diskussion_abstimmung",
            "dauer_sekunden": dauer,
        },
        room=raum.code,
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
    # use_reloader=False verhindert gevent fork-Fehler
    socketio.run(app, debug=True, host="0.0.0.0", port=port, use_reloader=False)
