"""
Webwoelfe - Das Online Werwolf-Spiel
Ein Echtzeit-Multiplayer Werwolf-Spiel mit WebSocket-Unterstuetzung
"""

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
import game_logic
import secrets
import os
import asyncio
from datetime import datetime

# App Konfiguration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///webwoelfe.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Spielname als Konstante
SPIEL_NAME = "Webwölfe"

# Initialisierung
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Datenbank erstellen
with app.app_context():
    db.create_all()


# ============================================================================
# KONTEXT-PROZESSOR - Globale Template-Variablen
# ============================================================================


@app.context_processor
def inject_globals():
    """Stellt globale Variablen fuer alle Templates bereit"""
    return {
        "spiel_name": SPIEL_NAME,
        "alle_rollen": ROLLEN,
        "alle_teams": TEAMS,
        "rollen_nach_kategorie": get_rollen_nach_kategorie(),
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
        from audio import text_zu_audio_sync

        audio_path = text_zu_audio_sync(text, stil=stil)
        if audio_path:
            # Konvertiere relativen Pfad zu URL-Pfad
            url_path = "/" + audio_path.replace("\\", "/")
            print(f"[Audio] Generated: {url_path}")
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
    spieler_anzahl = int(request.form.get("spieler_anzahl", 8))
    spieler_name = request.form.get("spieler_name", "Spielleiter")
    ist_erzaehler = request.form.get("ist_erzaehler") == "on"

    # Raum erstellen
    raum = Raum(
        code=Raum.generiere_code(),
        name=name,
        modus=modus,
        spieler_anzahl=max(5, min(18, spieler_anzahl)),
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

    return render_template(
        "lobby.html",
        raum=raum,
        spieler=spieler,
        alle_spieler=alle_spieler,
        rollen=ROLLEN,
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
        elif spieler.rolle == "Werwolf" and s.rolle == "Werwolf":
            spieler_data["ist_werwolf"] = True
        sichere_spieler.append(spieler_data)

    # Erzähler-Text für Gruppen-Modus
    erzaehler_text = None
    if spieler.ist_erzaehler and raum.modus == "gruppe":
        phase_key = raum.aktuelle_phase
        if phase_key in ERZAEHLER_TEXTE:
            erzaehler_text = ERZAEHLER_TEXTE[phase_key]

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
    Rendert das Dorf server-seitig und gibt ein Bild zurück.

    SICHERHEIT:
    - Keine Rollen-Information im Bild
    - Nur öffentliche Daten (Namen, lebendig/tot, Sitzplatz)
    - Hinweise werden vom Server kontrolliert
    """
    raum = Raum.query.filter_by(code=code).first()
    if not raum:
        return jsonify({"error": "Raum nicht gefunden"}), 404

    spieler = hole_aktuellen_spieler()
    if not spieler or spieler.raum_id != raum.id:
        return jsonify({"error": "Nicht autorisiert"}), 403

    # Hole aktive Hinweise für diesen Raum
    hinweise = _aktive_hinweise.get(raum.id, {})

    try:
        from village_renderer import render_village_for_room

        base64_img = render_village_for_room(raum.id, hinweise)

        return jsonify(
            {
                "image": base64_img,
                "phase": raum.aktuelle_phase,
                "runde": raum.runde,
            }
        )
    except ImportError:
        # Pillow nicht installiert - Fallback
        return (
            jsonify(
                {
                    "error": "Renderer nicht verfügbar",
                    "phase": raum.aktuelle_phase,
                    "runde": raum.runde,
                }
            ),
            503,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        raum = Raum.query.get(spieler.raum_id)
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
        raum = Raum.query.get(spieler.raum_id)
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


@socketio.on("spiel_starten")
def handle_spiel_starten(data):
    """Startet das Spiel (nur Erzaehler/Ersteller)"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = Raum.query.get(spieler.raum_id)
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
    else:
        emit("fehler", {"nachricht": "Spiel konnte nicht gestartet werden"})


@socketio.on("phase_weiter")
def handle_phase_weiter():
    """Wechselt zur naechsten Phase (Erzaehler)"""
    spieler = hole_aktuellen_spieler()
    if not spieler or not spieler.ist_erzaehler:
        emit("fehler", {"nachricht": "Nur der Erzaehler kann die Phase wechseln"})
        return

    raum = Raum.query.get(spieler.raum_id)
    if not raum:
        return

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

        emit(
            "erzaehlung", {"text": erzaehlung_text, "audio": audio_path}, room=raum.code
        )

    emit(
        "phase_geaendert",
        {
            "phase": neue_phase,
            "runde": raum.runde,
            "alte_phase": alte_phase,
            "erzaehler_text": erzaehler_text,
        },
        room=raum.code,
    )


@socketio.on("aktion_ausfuehren")
def handle_aktion(data):
    """Fuehrt eine Spielaktion aus"""
    spieler = hole_aktuellen_spieler()
    if not spieler:
        emit("fehler", {"nachricht": "Nicht angemeldet"})
        return

    raum = Raum.query.get(spieler.raum_id)
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
        emit("aktion_bestaetigt", {"aktion": aktion_typ})

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

    raum = Raum.query.get(spieler.raum_id)
    if not raum:
        return

    nachricht = data.get("nachricht", "")[:500]

    # SICHER: Keine sensiblen Daten im Chat
    if not spieler.ist_am_leben:
        # Tote chatten nur mit Toten
        emit("chat_tot", {"von": spieler.name, "nachricht": nachricht}, room=raum.code)
    else:
        emit("chat", {"von": spieler.name, "nachricht": nachricht}, room=raum.code)


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

    raum = Raum.query.get(spieler.raum_id)
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

    raum = Raum.query.get(raum_id)
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
        if spieler.rolle != "Werwolf" or raum.aktuelle_phase != "werwolf_phase":
            return False
        if game_logic.hat_spieler_gewaehlt(spieler, raum, "werwolf_phase"):
            return False
        game_logic.registriere_aktion(
            raum.id, raum.runde, "werwolf_phase", "werwolf_wahl", spieler.id, ziel_id
        )
        return True

    elif aktion_typ == "seherin_sehen":
        if spieler.rolle != "Seherin" or raum.aktuelle_phase != "seherin_phase":
            return False
        ziel = Spieler.query.get(ziel_id)
        if ziel:
            # SICHER: Ergebnis nur an anfragenden Spieler senden
            ist_werwolf = ziel.rolle in [
                "Werwolf",
                "Urwolf",
                "Wolfsjunge",
                "Weisser_Wolf",
            ]
            socketio.emit(
                "seherin_ergebnis",
                {"ziel_name": ziel.name, "ist_werwolf": ist_werwolf},
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
        ziel = Spieler.query.get(ziel_id)
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

    elif aktion_typ == "armor_verlieben":
        if spieler.rolle != "Armor" or raum.aktuelle_phase != "armor_phase":
            return False
        if not spieler.armor_verliebt:
            return False

        ziel_ids = ziel_id if isinstance(ziel_id, list) else [ziel_id]
        if len(ziel_ids) != 2:
            return False

        spieler1 = Spieler.query.get(ziel_ids[0])
        spieler2 = Spieler.query.get(ziel_ids[1])

        if spieler1 and spieler2:
            spieler1.verliebt_mit_id = spieler2.id
            spieler2.verliebt_mit_id = spieler1.id
            spieler.armor_verliebt = False
            db.session.commit()

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
        return True

    elif aktion_typ == "jaeger_schuss":
        if spieler.rolle != "Jaeger" or not spieler.jaeger_schuss:
            return False
        spieler.jaeger_schuss = False
        ziel = Spieler.query.get(ziel_id)
        if ziel:
            ergebnis = game_logic.toete_spieler(ziel, "jaeger")
            # SICHER: Nur Name wird geteilt, Rolle erst nach Tod
            emit(
                "spieler_gestorben",
                {
                    "spieler_id": ziel.id,
                    "spieler_name": ziel.name,
                    "todesart": "jaeger",
                    "rolle": ziel.rolle,  # Rolle wird nach Tod enthüllt
                },
                room=raum.code,
            )
            db.session.commit()
            return True
        return False

    return False


def handle_phase_wechsel(raum, alte_phase, neue_phase):
    """Behandelt Phasenwechsel-Logik"""

    # Heiler-Schutz zuruecksetzen am Nachtende
    if alte_phase == "heiler_phase":
        pass  # Schutz bleibt bis Nacht-Ende

    if alte_phase == "werwolf_phase":
        # Werwolf-Opfer ermitteln
        ergebnis = game_logic.werwolf_abstimmung(raum)
        if ergebnis and "opfer_id" in ergebnis:
            # SICHER: Nur an Hexe senden (private Nachricht)
            hexe = Spieler.query.filter_by(
                raum_id=raum.id, rolle="Hexe", ist_am_leben=True
            ).first()
            if hexe:
                # Speichere in Session oder Temp-Daten fuer Hexe
                pass

    elif alte_phase == "hexe_phase":
        # Nacht-Ende: Tote bekannt geben
        werwolf_opfer = SpielAktion.query.filter_by(
            raum_id=raum.id,
            runde=raum.runde,
            phase="werwolf_phase",
            aktion_typ="werwolf_wahl",
        ).first()

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
            opfer = Spieler.query.get(werwolf_opfer.ziel_spieler_id)
            if opfer and opfer.ist_am_leben:
                # Pruefen ob geheilt
                if geheilt and geheilt.ziel_spieler_id == opfer.id:
                    pass  # Geheilt!
                # Pruefen ob vom Heiler geschuetzt
                elif opfer.ist_beschuetzt:
                    pass  # Geschuetzt!
                else:
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
            opfer = Spieler.query.get(vergiftet.ziel_spieler_id)
            if opfer and opfer.ist_am_leben:
                game_logic.toete_spieler(opfer, "hexe")
                tote.append(
                    {"name": opfer.name, "rolle": opfer.rolle, "todesart": "hexe"}
                )

        # Heiler-Schutz zuruecksetzen
        for s in Spieler.query.filter_by(raum_id=raum.id).all():
            s.ist_beschuetzt = False
        db.session.commit()

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
                opfer = Spieler.query.get(ergebnis["opfer_id"])
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

    if raum.aktuelle_phase == "werwolf_phase":
        werwoelfe = game_logic.hole_spieler_fuer_rolle(raum, "Werwolf")
        if all(
            game_logic.hat_spieler_gewaehlt(w, raum, "werwolf_phase") for w in werwoelfe
        ):
            socketio.emit("phase_bereit", {"phase": "werwolf_phase"}, room=raum.code)

    elif raum.aktuelle_phase == "abstimmung":
        lebende = game_logic.hole_lebende_spieler(raum)
        if all(game_logic.hat_spieler_gewaehlt(s, raum, "abstimmung") for s in lebende):
            socketio.emit("phase_bereit", {"phase": "abstimmung"}, room=raum.code)


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
    socketio.run(app, debug=True, host="0.0.0.0", port=5001)
