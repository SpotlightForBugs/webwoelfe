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
    PHASEN,
    TEAMS,
    ERZAEHLER_TEXTE,
    get_rollen_nach_kategorie,
    get_rollen_nach_kategorie_liste,
    get_rollen_anzahl,
)
from roles import get_rollen_nach_erweiterung, ERWEITERUNG_INFO, KATEGORIE_INFO
import game_logic
import secrets
import os
import random
from datetime import datetime

# App Konfiguration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///webwoelfe.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
        if elevenlabs_aktiv():
            audio_path = text_zu_audio_elevenlabs_sync(text, stil=stil)

        if not audio_path:
            audio_path = text_zu_audio_sync(text, stil=stil)

        if audio_path:
            # Konvertiere relativen Pfad zu URL-Pfad
            url_path = "/" + audio_path.replace("\\", "/")
            log_ts(f"[Audio] Generated: {url_path}")
            return url_path
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
        if phase_key in ERZAEHLER_TEXTE:
            erzaehler_text = ERZAEHLER_TEXTE[phase_key]

    # Bereite enthuellung für Template vor (ziel_id -> 'gut'/'boese')
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


@app.route("/api/village/test")
def api_village_test():
    """Test-Endpoint für Village Rendering (nur Entwicklung)"""
    try:
        from village_renderer import generate_test_village

        base64_img = generate_test_village()
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Village Test</title></head>
        <body style="background: #1a1a2e; display: flex; flex-direction: column; align-items: center; padding: 40px; font-family: sans-serif;">
            <h1 style="color: #c41e3a;">Server-Side Village Rendering</h1>
            <p style="color: #888;">Dieses Bild wurde komplett auf dem Server gerendert. Der Client hat keinen Zugriff auf Spielzustand!</p>
            <img src="{base64_img}" style="border: 3px solid #333; border-radius: 12px; max-width: 100%;">
        </body>
        </html>
        """
    except ImportError as e:
        return (
            f"<h1>Pillow nicht installiert!</h1><p>pip install pillow</p><pre>{e}</pre>",
            503,
        )


# ============================================================================
# WEBSOCKET EVENTS - SICHER: Keine sensiblen Daten werden gebroadcastet
# ============================================================================


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
                and raum.aktuelle_phase in ERZAEHLER_TEXTE
            ):
                erzaehler_info = ERZAEHLER_TEXTE[raum.aktuelle_phase]
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
            if raum.aktuelle_phase in ERZAEHLER_TEXTE:
                erzaehler_info = ERZAEHLER_TEXTE[raum.aktuelle_phase]
                erzaehlung_text = erzaehler_info.get("text", "")
                audio_path = None
                if erzaehlung_text:
                    audio_path = generiere_erzaehler_audio(
                        erzaehlung_text, stil="normal"
                    )
                socketio.emit(
                    "erzaehlung",
                    {"text": erzaehlung_text, "audio": audio_path},
                    room=raum.code,
                )

            # Starte automatische Phasen-Progression
            import threading

            def auto_advance_initial():
                import time

                time.sleep(5)  # 5 Sekunden für Rollen-Verteilung
                with app.app_context():
                    raum_aktuell = db.session.get(Raum, raum.id)
                    if (
                        raum_aktuell
                        and raum_aktuell.aktuelle_phase == "rollen_verteilt"
                    ):
                        _wechsel_phase_intern(raum_aktuell)

            threading.Thread(target=auto_advance_initial, daemon=True).start()
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
    if raum.modus == "gruppe" and neue_phase in ERZAEHLER_TEXTE:
        erzaehler_text = ERZAEHLER_TEXTE[neue_phase]

    # Online-Modus: Automatische Erzählung mit Audio senden
    if raum.modus == "online" and neue_phase in ERZAEHLER_TEXTE:
        erzaehler_info = ERZAEHLER_TEXTE[neue_phase]
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

    # Automatische Phasen: Diese brauchen keine Spieler-Interaktion
    # und sollen nach Audio-Wiedergabe automatisch weiterschalten
    AUTOMATISCHE_PHASEN = {
        "rollen_verteilt",
        "nacht_start",
        "nacht_ende",
        "tag_start",
        "tag_ende",
        "verliebte_info",
        "baerenbaendiger_brummen",
        "demoskopin_info",
        "abstimmung_ergebnis",
        "prinz_enthuellung",
        "hahn_enthuellung",
        "putzfrau_info",
        "zwei_schwestern_phase",  # Info-only
        "drei_brueder_phase",  # Info-only
        "freimaurer_phase",  # Info-only
        "fluechtlinge_phase",  # Info-only
    }

    if raum.modus == "online" and neue_phase in AUTOMATISCHE_PHASEN:
        # Markiere Raum als "wartet auf Audio"
        # Der Client sendet 'audio_fertig' wenn Audio abgespielt wurde
        # Fallback: Nach PHASE_WECHSEL_DELAY Sekunden automatisch weiter
        raum_code = raum.code
        phase_bei_start = neue_phase

        import threading

        def auto_advance_fallback():
            import time

            # Warte auf Fallback-Timeout (falls Audio nicht abgespielt wird)
            time.sleep(PHASE_WECHSEL_DELAY)
            with app.app_context():
                raum_aktuell = Raum.query.filter_by(code=raum_code).first()
                if raum_aktuell and raum_aktuell.aktuelle_phase == phase_bei_start:
                    # Phase wurde noch nicht gewechselt (Audio-Event kam nicht an)
                    log_ts(
                        f"[Phase] Fallback-Timeout für {phase_bei_start}, wechsle Phase"
                    )
                    _wechsel_phase_intern(raum_aktuell)

        threading.Thread(target=auto_advance_fallback, daemon=True).start()


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
        log_ts(f"[Audio] Audio fertig für Phase {gemeldete_phase}, wechsle Phase")
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

    # Validierung
    if not spieler.ist_am_leben and aktion_typ != "jaeger_schuss":
        emit("fehler", {"nachricht": "Du bist tot und kannst nicht handeln"})
        return

    # Aktion basierend auf Phase und Rolle verarbeiten
    erfolg = verarbeite_aktion(spieler, raum, aktion_typ, ziel_id)

    if erfolg:
        # Map action types to 3D effect types
        effect_map = {
            "hexe_heilen": "heal",
            "heiler_schuetzen": "protect",
            "hexe_toeten": "poison",
            "werwolf_wahl": "attack",
            "armor_verlieben": "love",
        }

        effect_data = {"aktion": aktion_typ}
        if ziel_id and aktion_typ in effect_map:
            effect_data["effekt"] = effect_map[aktion_typ]
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
    """Verarbeitet eine Spielaktion"""

    if aktion_typ == "werwolf_wahl":
        log_ts(
            f"[Aktion] werwolf_wahl von {spieler.name} (Rolle: {spieler.rolle}) für Ziel-ID: {ziel_id}"
        )
        if (
            not game_logic.ist_werwolf_rolle(spieler.rolle)
            or raum.aktuelle_phase != "werwolf_phase"
        ):
            log_ts(
                f"[Aktion] ABGELEHNT: Rolle={spieler.rolle}, Phase={raum.aktuelle_phase}"
            )
            return False
        if game_logic.hat_spieler_gewaehlt(spieler, raum, "werwolf_phase"):
            log_ts(f"[Aktion] ABGELEHNT: {spieler.name} hat bereits gewählt")
            return False
        game_logic.registriere_aktion(
            raum.id, raum.runde, "werwolf_phase", "werwolf_wahl", spieler.id, ziel_id
        )
        log_ts(f"[Aktion] ERFOLG: Werwolf {spieler.name} wählt Ziel-ID {ziel_id}")
        return True

    elif aktion_typ == "seherin_sehen":
        if spieler.rolle != "Seherin" or raum.aktuelle_phase != "seherin_phase":
            return False
        ziel = db.session.get(Spieler, ziel_id)
        if ziel:
            # SICHER: Ergebnis nur an anfragenden Spieler senden
            from roles import RoleRegistry
            from roles.enums import SichtTyp

            ziel_rolle = RoleRegistry.get(ziel.rolle)
            if ziel_rolle:
                sicht = ziel_rolle.sichtbar_als_fuer("Seherin")
                rollen_name = ziel_rolle.sichtbare_rolle_fuer("Seherin")
            else:
                sicht = SichtTyp.DORF
                rollen_name = ziel.rolle or "Unbekannt"

            ist_werwolf = sicht == SichtTyp.WERWOLF
            socketio.emit(
                "seherin_ergebnis",
                {
                    "ziel_name": ziel.name,
                    "ist_werwolf": ist_werwolf,
                    "rolle": rollen_name,
                },
                room=request.sid,
            )
            game_logic.registriere_aktion(
                raum.id, raum.runde, "seherin_phase", "sehen", spieler.id, ziel_id
            )
            return True
        return False

    elif aktion_typ == "heiler_schuetzen":
        if spieler.rolle != "Heiler" or raum.aktuelle_phase != "heiler_phase":
            return False
        # Nicht zweimal denselben schuetzen
        if spieler.heiler_geschuetzt == ziel_id:
            emit(
                "fehler",
                {
                    "nachricht": "Du kannst nicht zweimal hintereinander denselben Spieler schuetzen!"
                },
            )
            return False
        spieler.heiler_geschuetzt = ziel_id
        ziel = db.session.get(Spieler, ziel_id)
        if ziel:
            ziel.ist_beschuetzt = True
        game_logic.registriere_aktion(
            raum.id, raum.runde, "heiler_phase", "schuetzen", spieler.id, ziel_id
        )
        db.session.commit()
        return True

    elif aktion_typ == "hexe_heilen":
        if spieler.rolle != "Hexe" or raum.aktuelle_phase != "hexe_phase":
            return False
        if not spieler.hexe_heiltrank:
            return False
        spieler.hexe_heiltrank = False
        game_logic.registriere_aktion(
            raum.id, raum.runde, "hexe_phase", "heilen", spieler.id, ziel_id
        )
        db.session.commit()
        return True

    elif aktion_typ == "hexe_toeten":
        if spieler.rolle != "Hexe" or raum.aktuelle_phase != "hexe_phase":
            return False
        if not spieler.hexe_gifttrank:
            return False
        spieler.hexe_gifttrank = False
        game_logic.registriere_aktion(
            raum.id, raum.runde, "hexe_phase", "vergiften", spieler.id, ziel_id
        )
        db.session.commit()
        return True

    elif aktion_typ == "hexe_nichts":
        if spieler.rolle != "Hexe" or raum.aktuelle_phase != "hexe_phase":
            return False
        game_logic.registriere_aktion(
            raum.id, raum.runde, "hexe_phase", "nichts", spieler.id
        )
        db.session.commit()
        return True

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
            return True
        return False

    elif aktion_typ == "tag_wahl":
        if raum.aktuelle_phase != "abstimmung":
            return False
        if game_logic.hat_spieler_gewaehlt(spieler, raum, "abstimmung"):
            return False
        game_logic.registriere_aktion(
            raum.id, raum.runde, "abstimmung", "tag_wahl", spieler.id, ziel_id
        )
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
        return True

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

    # ==========================================================================
    # GENERIC ACTION HANDLER for all other roles
    # Uses the Role classes to process actions dynamically
    # ==========================================================================
    else:
        from roles import RoleRegistry
        from roles.base import SpielKontext

        # Get the player's role class
        rolle_obj = RoleRegistry.get(spieler.rolle)
        if not rolle_obj:
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

        kontext = SpielKontext(
            raum_id=raum.id,
            runde=raum.runde,
            phase=raum.aktuelle_phase,
            aktiver_spieler_id=spieler.id,
            lebende_spieler=lebende,
            tote_spieler=tote,
        )

        # Check if the current phase matches the role's phase
        rolle_phase = rolle_obj.get_phase_name()
        if raum.aktuelle_phase != rolle_phase:
            return False

        # Get the target player if specified
        ziel = db.session.get(Spieler, ziel_id) if ziel_id else None

        # Execute the role's night action
        ergebnis = rolle_obj.on_nacht_aktion(spieler, ziel, kontext)

        if ergebnis and ergebnis.erfolg:
            # Register the action
            game_logic.registriere_aktion(
                raum.id, raum.runde, rolle_phase, aktion_typ, spieler.id, ziel_id
            )

            # Send result to the player
            if ergebnis.nachricht:
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

        werwolf_opfer = SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            phase="werwolf_phase",
            aktion_typ="werwolf_wahl",
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

        # Spielende pruefen
        ende = game_logic.pruefe_spielende(raum)
        if ende:
            raum.aktuelle_phase = "spiel_ende"
            db.session.commit()
            socketio.emit("spiel_ende", ende, room=raum.code)


def pruefe_phase_abschluss(raum):
    """Prueft ob die aktuelle Phase abgeschlossen werden kann"""

    # Stelle sicher dass wir aktuelle Daten haben
    db.session.expire_all()

    if raum.aktuelle_phase == "amor_phase":
        # Amor hat sein Liebespaar gewählt - Phase ist fertig
        amor_spieler = game_logic.hole_spieler_fuer_rolle(raum, "Amor")
        if not amor_spieler:
            # Kein Amor vorhanden - Phase überspringen
            _wechsel_phase_intern(raum)
            return
        # Prüfe ob alle Amors (normalerweise nur 1) ihre Aktion ausgeführt haben
        alle_fertig = all(not a.armor_verliebt for a in amor_spieler)
        if alle_fertig:
            log_ts(f"[Phase] amor_phase abgeschlossen, wechsle Phase")
            socketio.emit("phase_bereit", {"phase": "amor_phase"}, room=raum.code)
            # Wechsle automatisch zur nächsten Phase
            _wechsel_phase_intern(raum)

    elif raum.aktuelle_phase == "seherin_phase":
        # Seherin hat ihre Aktion ausgeführt
        seherin_spieler = game_logic.hole_spieler_fuer_rolle(raum, "Seherin")
        if not seherin_spieler:
            _wechsel_phase_intern(raum)
            return
        alle_fertig = all(
            game_logic.hat_spieler_gewaehlt(s, raum, "seherin_phase")
            for s in seherin_spieler
        )
        if alle_fertig:
            log_ts(f"[Phase] seherin_phase abgeschlossen, wechsle Phase")
            socketio.emit("phase_bereit", {"phase": "seherin_phase"}, room=raum.code)
            _wechsel_phase_intern(raum)

    elif raum.aktuelle_phase == "hexe_phase":
        # Hexe hat ihre Aktion ausgeführt (heilen, töten, oder nichts tun)
        hexe_spieler = game_logic.hole_spieler_fuer_rolle(raum, "Hexe")
        if not hexe_spieler:
            _wechsel_phase_intern(raum)
            return
        alle_fertig = all(
            game_logic.hat_spieler_gewaehlt(h, raum, "hexe_phase") for h in hexe_spieler
        )
        if alle_fertig:
            log_ts(f"[Phase] hexe_phase abgeschlossen, wechsle Phase")
            socketio.emit("phase_bereit", {"phase": "hexe_phase"}, room=raum.code)
            _wechsel_phase_intern(raum)

    elif raum.aktuelle_phase == "heiler_phase":
        # Heiler hat seine Aktion ausgeführt
        heiler_spieler = game_logic.hole_spieler_fuer_rolle(raum, "Heiler")
        if not heiler_spieler:
            _wechsel_phase_intern(raum)
            return
        alle_fertig = all(
            game_logic.hat_spieler_gewaehlt(h, raum, "heiler_phase")
            for h in heiler_spieler
        )
        if alle_fertig:
            log_ts(f"[Phase] heiler_phase abgeschlossen, wechsle Phase")
            socketio.emit("phase_bereit", {"phase": "heiler_phase"}, room=raum.code)
            _wechsel_phase_intern(raum)

    elif raum.aktuelle_phase == "werwolf_phase":
        werwoelfe = game_logic.hole_spieler_fuer_rolle(raum, "Werwolf")
        if not werwoelfe:
            _wechsel_phase_intern(raum)
            return
        if all(
            game_logic.hat_spieler_gewaehlt(w, raum, "werwolf_phase") for w in werwoelfe
        ):
            log_ts(f"[Phase] werwolf_phase abgeschlossen, wechsle Phase")
            socketio.emit("phase_bereit", {"phase": "werwolf_phase"}, room=raum.code)
            _wechsel_phase_intern(raum)

    elif raum.aktuelle_phase == "abstimmung":
        lebende = game_logic.hole_lebende_spieler(raum)
        if all(game_logic.hat_spieler_gewaehlt(s, raum, "abstimmung") for s in lebende):
            log_ts(f"[Phase] abstimmung abgeschlossen, wechsle Phase")
            socketio.emit("phase_bereit", {"phase": "abstimmung"}, room=raum.code)
            _wechsel_phase_intern(raum)

    # ==========================================================================
    # GENERIC PHASE COMPLETION HANDLER
    # Handles all other role phases dynamically
    # ==========================================================================
    else:
        from roles import RoleRegistry

        # Try to find a role matching the current phase
        aktuelle_phase = raum.aktuelle_phase

        # Mapping of phases to role names (extended list)
        phase_rolle_map = {
            "seherlehrling_phase": "Seherlehrling",
            "aurenseherin_phase": "Aurenseherin",
            "medium_phase": "Medium",
            "tratschweib_phase": "Tratschweib",
            "paranormal_billig_phase": "Paranormaler Ermittler (billig)",
            "werwolfseherin_phase": "Werwolfseherin",
            "demoskopin_phase": "Demoskopin",
            "baerenbaendiger_phase": "Bärenbändiger",
            "leibwaechter_phase": "Leibwächter",
            "prostituierte_phase": "Prostituierte",
            "hure_phase": "Prostituierte",
            "nutte_phase": "Prostituierte",
            "ergebene_magd_phase": "Ergebene Magd",
            "oma_phase": "Oma",
            "hexenmeister_phase": "Hexenmeister",
            "giftmischerin_phase": "Giftmischerin",
            "kraeuterweib_phase": "Kräuterweib",
            "zauberer_phase": "Zauberer",
            "sandmann_phase": "Sandmann",
            "hahn_phase": "Hahn",
            "kamikaze_phase": "Kamikaze",
            "prinz_phase": "Prinz",
            "koenig_phase": "König",
            "buddler_phase": "Buddler",
            "pyromane_phase": "Pyromane",
            "flammenmann_phase": "Flammenmann",
            "drachenbaendiger_phase": "Drachenbändiger",
            "gaukler_phase": "Gaukler",
            "inquisitor_phase": "Inquisitor",
            "tanklastwagenfahrer_phase": "Tanklastwagenfahrer",
            "einsamer_wolf_phase": "Einsamer Wolf",
            "urwolf_phase": "Urwolf",
            "weisser_wolf_phase": "Weißer Wolf",
            "mordlustiger_phase": "Mordlustiger Werwolf",
            "wildes_kind_phase": "Wildes Kind",
            "wolfsjunge_phase": "Wolfsjunge",
            "teenager_werwolf_phase": "Teenager-Werwolf",
            "polarwolf_phase": "Polarwolf",
            "lupin_phase": "Lupin",
            "wolf_im_schafspelz_phase": "Wolf im Schafspelz",
            "vampir_phase": "Vampir",
            "zombie_phase": "Zombie",
            "floetenspieler_phase": "Flötenspieler",
            "henker_phase": "Henker",
            "selbstmoerder_phase": "Selbstmörder",
            "dieb_phase": "Dieb",
            "doppelgaenger_phase": "Doppelgänger",
            "dunkler_priester_phase": "Dunkler Priester",
            "hund_phase": "Hund",
            "tonks_phase": "Tonks",
            "griesgram_phase": "Griesgram",
            "jesus_phase": "Jesus",
            "rabe_phase": "Rabe",
            "zahnarzt_phase": "Zahnarzt",
            "engel_phase": "Engel",
            "gerber_phase": "Gerber",
            "kleines_maedchen_phase": "Kleines Mädchen",
            "putzfrau_phase": "Putzfrau",
        }

        rolle_name = phase_rolle_map.get(aktuelle_phase)
        if rolle_name:
            rolle_spieler = game_logic.hole_spieler_fuer_rolle(raum, rolle_name)
            if not rolle_spieler:
                # No player with this role - skip phase
                _wechsel_phase_intern(raum)
                return

            alle_fertig = all(
                game_logic.hat_spieler_gewaehlt(s, raum, aktuelle_phase)
                for s in rolle_spieler
            )
            if alle_fertig:
                log_ts(f"[Phase] {aktuelle_phase} abgeschlossen, wechsle Phase")
                socketio.emit("phase_bereit", {"phase": aktuelle_phase}, room=raum.code)
                _wechsel_phase_intern(raum)


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
