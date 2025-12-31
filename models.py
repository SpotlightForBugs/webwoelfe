"""
Datenbankmodelle für das Webwölfe-Spiel
Alle Rollen basierend auf: https://werwolf.fandom.com/de/wiki/Werwolf-Rollen-Sammlung
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets

db = SQLAlchemy()


class Raum(db.Model):
    """Ein Spielraum/Lobby"""

    __tablename__ = "raeume"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    modus = db.Column(
        db.String(20), nullable=False, default="online"
    )  # 'gruppe' oder 'online'
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    spieler_anzahl = db.Column(db.Integer, default=8)
    spiel_gestartet = db.Column(db.Boolean, default=False)
    aktuelle_phase = db.Column(db.String(30), default="lobby")
    runde = db.Column(db.Integer, default=0)
    erzaehler_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)

    # Rollen-Konfiguration (JSON der aktivierten Rollen)
    aktive_rollen = db.Column(db.Text, default="{}")

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
    beigetreten_am = db.Column(db.DateTime, default=datetime.utcnow)

    # Composite indexes for common query patterns in large games
    __table_args__ = (
        db.Index("idx_spieler_raum_leben", "raum_id", "ist_am_leben"),
        db.Index("idx_spieler_raum_rolle", "raum_id", "rolle"),
        db.Index("idx_spieler_raum_erzaehler", "raum_id", "ist_erzaehler"),
    )

    # Sitzplatz-System für Nachbar-Mechanik und 3D-Visualisierung
    sitzplatz = db.Column(db.Integer, nullable=True)  # Position im Kreis (0-n)
    # Nachbarn werden dynamisch berechnet basierend auf sitzplatz

    # Spezielle Fähigkeiten Status
    hexe_heiltrank = db.Column(db.Boolean, default=True)
    hexe_gifttrank = db.Column(db.Boolean, default=True)
    jaeger_schuss = db.Column(db.Boolean, default=True)
    armor_verliebt = db.Column(db.Boolean, default=True)
    heiler_geschuetzt = db.Column(
        db.Integer, nullable=True
    )  # ID des zuletzt geschützten Spielers

    # Einmalige Fähigkeiten
    urwolf_infektion = db.Column(db.Boolean, default=True)  # Kann noch infizieren
    kamikaze_bombe = db.Column(db.Boolean, default=True)  # Kann sich noch opfern
    jesus_auferstehung = db.Column(db.Boolean, default=True)  # Kann noch auferstehen
    leibwaechter_opfer = db.Column(db.Boolean, default=True)  # Kann sich noch opfern

    # Spezielle Rollen-Flags
    ist_infiziert = db.Column(db.Boolean, default=False)  # Urwolf-Infektion
    ist_verzaubert = db.Column(db.Boolean, default=False)  # Flötenspieler-Verzauberung
    ist_verflucht = db.Column(db.Boolean, default=False)  # Fluch (wird zum Werwolf)
    ist_beschuetzt = db.Column(
        db.Boolean, default=False
    )  # Heiler-Schutz für diese Nacht
    ist_stumm = db.Column(db.Boolean, default=False)  # Kräuterweib-Stummheit
    ist_vergiftet = db.Column(db.Integer, default=0)  # Giftmischerin - Tage bis Tod
    rabe_markiert = db.Column(db.Boolean, default=False)  # Rabe-Markierung
    alter_mann_leben = db.Column(db.Integer, default=2)  # Anzahl Leben

    # Verliebt mit
    verliebt_mit_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)

    # Vorbild (für Wildes Kind)
    vorbild_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)

    # Doppelgänger-Ziel
    doppelgaenger_ziel_id = db.Column(
        db.Integer, db.ForeignKey("spieler.id"), nullable=True
    )

    # Henker-Ziel
    henker_ziel_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)

    @staticmethod
    def generiere_session():
        """Generiert eine einzigartige Session-ID"""
        return secrets.token_hex(32)

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
        if rechts and rechts.id != links.id:  # Vermeidung bei nur 2 Spielern
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
    zeitpunkt = db.Column(db.DateTime, default=datetime.utcnow)

    von_spieler = db.relationship("Spieler", foreign_keys=[von_spieler_id])
    ziel_spieler = db.relationship("Spieler", foreign_keys=[ziel_spieler_id])


class SpielLog(db.Model):
    """Spielverlauf-Protokoll"""

    __tablename__ = "spiellog"

    id = db.Column(db.Integer, primary_key=True)
    raum_id = db.Column(db.Integer, db.ForeignKey("raeume.id"), nullable=False)
    nachricht = db.Column(db.Text, nullable=False)
    zeitpunkt = db.Column(db.DateTime, default=datetime.utcnow)
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
    gespielt_am = db.Column(db.DateTime, default=datetime.utcnow)

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
        event = ErzaehlerEvent(
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
    # Position im 3D-Raum (Einheitskreis um Lagerfeuer)
    winkel = db.Column(db.Float, nullable=False)  # Winkel in Grad (0-360)
    radius = db.Column(db.Float, default=5.0)  # Abstand vom Zentrum
    # Visuelle Eigenschaften
    avatar_typ = db.Column(db.String(20), default="default")  # Charakter-Modell

    spieler = db.relationship("Spieler", backref="position_3d")


# ============================================================================
# ERZÄHLER-TEXTE FÜR LOKALEN MODUS
# ============================================================================

# PHASE-BASIERTE TEXTE (werden jede Runde wiederholt)
ERZAEHLER_PHASEN = {
    "nacht_start": {
        "text": "Das Dorf schläft ein. Alle Spieler schließen die Augen.",
        "anweisung": "Warte bis alle Spieler die Augen geschlossen haben.",
        "wiederholbar": True,
    },
    "werwolf_phase": {
        "text": "Die Werwölfe erwachen. Sie erkennen sich und wählen gemeinsam ein Opfer.",
        "anweisung": "Die Werwölfe öffnen die Augen, schauen sich an und zeigen stumm auf ihr Opfer. Bestätige das Opfer mit einem Nicken.",
        "wiederholbar": True,
    },
    "seherin_phase": {
        "text": "Die Seherin erwacht und wählt einen Spieler, dessen Identität sie erfahren möchte.",
        "anweisung": "Die Seherin öffnet die Augen und zeigt auf einen Spieler. Zeige ihr mit Daumen hoch (Dorf) oder runter (Wolf) die Zugehörigkeit.",
        "wiederholbar": True,
    },
    "hexe_phase": {
        "text": "Die Hexe erwacht. Sie erfährt das Opfer der Werwölfe.",
        "anweisung": "Die Hexe öffnet die Augen. Zeige auf das Werwolf-Opfer. Frage mit Gesten: Heiltrank? Gifttrank?",
        "wiederholbar": True,
    },
    "heiler_phase": {
        "text": "Der Heiler erwacht und wählt einen Spieler, den er in dieser Nacht beschützen möchte.",
        "anweisung": "Der Heiler öffnet die Augen und zeigt auf den zu schützenden Spieler. Bestätige mit einem Nicken.",
        "wiederholbar": True,
    },
    "tag_start": {
        "text": "Die Sonne geht auf. Das Dorf erwacht.",
        "anweisung": "Alle öffnen die Augen. Verkünde die Opfer der Nacht.",
        "wiederholbar": True,
    },
    "diskussion": {
        "text": "Die Dorfbewohner diskutieren. Wer könnte ein Werwolf sein?",
        "anweisung": "Die Spieler diskutieren frei. Als Erzähler greifst du nur bei Regelfragen ein.",
        "wiederholbar": True,
    },
    "abstimmung": {
        "text": "Die Abstimmung beginnt. Jeder Spieler zeigt auf den Verdächtigen.",
        "anweisung": "Bei 3 zeigen alle gleichzeitig. Zähle die Stimmen.",
        "wiederholbar": True,
    },
}

# EVENT-BASIERTE TEXTE (nur einmal pro Spiel!)
ERZAEHLER_EVENTS = {
    # === ERSTE NACHT EVENTS (nur in Runde 1) ===
    "erste_nacht_intro": {
        "text": "Willkommen in Düsterwald! Die erste Nacht bricht herein. In diesem Dorf verbergen sich Werwölfe unter den friedlichen Bewohnern.",
        "anweisung": "Lies diesen Text atmosphärisch vor. Dann beginne mit den Rollen.",
        "bedingung": {"runde": 1, "phase": "nacht"},
        "einmalig": True,
    },
    "armor_verliebte": {
        "text": "Amor erwacht in dieser ersten Nacht. Er wählt zwei Spieler, die sich unsterblich verlieben werden. Ihre Schicksale sind nun für immer verbunden.",
        "anweisung": "Amor öffnet die Augen und zeigt auf zwei Spieler. Berühre diese leicht an der Schulter.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Amor"},
        "einmalig": True,
    },
    "verliebte_erfahren": {
        "text": "Die Verliebten erwachen kurz und erkennen einander. Sie dürfen die Augen öffnen und sich ansehen.",
        "anweisung": "Die beiden Verliebten öffnen kurz die Augen, lächeln sich an, und schließen sie wieder.",
        "bedingung": {"nach_event": "armor_verliebte"},
        "einmalig": True,
    },
    "wildes_kind_vorbild": {
        "text": "Das Wilde Kind erwacht. Es wählt ein Vorbild. Sollte dieses Vorbild sterben, wird das Kind zum Werwolf.",
        "anweisung": "Das Wilde Kind öffnet die Augen und zeigt auf sein Vorbild. Merke dir diese Wahl.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Wildes Kind"},
        "einmalig": True,
    },
    "werwolf_erste_nacht": {
        "text": "Die Werwölfe erwachen zum ersten Mal. Sie öffnen die Augen und erkennen ihre Mitstreiter.",
        "anweisung": "Die Werwölfe öffnen die Augen und schauen sich an. Sie wählen noch kein Opfer - nur kennenlernen!",
        "bedingung": {"runde": 1, "phase": "werwolf"},
        "einmalig": True,
    },
    "drei_brueder_treffen": {
        "text": "Die drei Brüder erwachen. Sie öffnen die Augen und erkennen einander als Verbündete.",
        "anweisung": "Die Brüder öffnen kurz die Augen und schauen sich an.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Drei Brüder"},
        "einmalig": True,
    },
    "zwei_schwestern_treffen": {
        "text": "Die zwei Schwestern erwachen. Sie erkennen einander als Verbündete.",
        "anweisung": "Die Schwestern öffnen kurz die Augen und schauen sich an.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Zwei Schwestern"},
        "einmalig": True,
    },
    "freimaurer_treffen": {
        "text": "Die Freimaurer erwachen. Sie erkennen ihre Logenbrüder und wissen, wem sie vertrauen können.",
        "anweisung": "Die Freimaurer öffnen die Augen und schauen sich an.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Freimaurer"},
        "einmalig": True,
    },
    "doppelgaenger_wahl": {
        "text": "Der Doppelgänger erwacht. Er wählt einen Spieler, dessen Rolle er übernehmen wird, sollte dieser sterben.",
        "anweisung": "Der Doppelgänger zeigt auf einen Spieler. Merke dir diese Wahl.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Doppelgänger"},
        "einmalig": True,
    },
    # === EREIGNIS-EVENTS (passieren bei bestimmten Aktionen) ===
    "jaeger_stirbt": {
        "text": "Der Jäger wurde getötet! Mit seinem letzten Atemzug greift er zur Flinte und feuert einen finalen Schuss ab!",
        "anweisung": "Der Jäger öffnet die Augen und zeigt auf sein Opfer. Dieses stirbt sofort.",
        "bedingung": {"trigger": "spieler_stirbt", "rolle": "Jäger"},
        "einmalig": False,  # Kann bei mehreren Jägern mehrfach passieren
    },
    "hexe_heiltrank_leer": {
        "text": "Die Hexe hat ihren Heiltrank bereits verbraucht.",
        "anweisung": "Zeige der Hexe, dass sie nicht heilen kann (Kopfschütteln).",
        "bedingung": {"trigger": "hexe_kein_heiltrank"},
        "einmalig": True,
    },
    "hexe_gifttrank_leer": {
        "text": "Die Hexe hat ihren Gifttrank bereits verbraucht.",
        "anweisung": "Zeige der Hexe, dass sie nicht vergiften kann.",
        "bedingung": {"trigger": "hexe_kein_gifttrank"},
        "einmalig": True,
    },
    "urwolf_infiziert": {
        "text": "Der Urwolf hat sein Opfer infiziert statt getötet! Das Opfer wird zum Werwolf erwachen...",
        "anweisung": "Berühre das Opfer leicht - es wird in der nächsten Nacht als Werwolf erwachen.",
        "bedingung": {"trigger": "urwolf_infektion"},
        "einmalig": True,
    },
    "wildes_kind_verwandelt": {
        "text": "Das Vorbild des Wilden Kindes ist gestorben! Das Kind verwandelt sich in einen Werwolf!",
        "anweisung": "Das Wilde Kind wird in der nächsten Nacht mit den Werwölfen aufwachen.",
        "bedingung": {"trigger": "vorbild_stirbt"},
        "einmalig": True,
    },
    "jesus_aufersteht": {
        "text": "Jesus ist gestorben... aber wartet! Nach drei Tagen ist er wieder auferstanden!",
        "anweisung": "Jesus kehrt ins Spiel zurück. Ein Wunder!",
        "bedingung": {"trigger": "jesus_auferstehung"},
        "einmalig": True,
    },
    "alter_mann_stirbt_dorf": {
        "text": "Der Alte Mann wurde vom Dorf hingerichtet! Vor Enttäuschung verflucht er das Dorf - alle Spezialrollen verlieren ihre Fähigkeiten!",
        "anweisung": "Seherin, Hexe, Heiler etc. verlieren ihre Nachtaktionen.",
        "bedingung": {"trigger": "alter_mann_gehaengt"},
        "einmalig": True,
    },
    "pyromane_zuendet": {
        "text": "Der Pyromane hat ein Haus angezündet! Das Feuer breitet sich aus und tötet auch die Nachbarn!",
        "anweisung": "Der Pyromane und seine beiden Nachbarn sterben in den Flammen.",
        "bedingung": {"trigger": "pyromane_aktion"},
        "einmalig": True,
    },
    # === SPIELENDE EVENTS ===
    "dorf_gewonnen": {
        "text": "Das Dorf hat gewonnen! Alle Werwölfe wurden eliminiert. Die Dorfbewohner können wieder in Frieden leben.",
        "anweisung": "Gratuliere dem Dorf! Decke alle Rollen auf.",
        "bedingung": {"trigger": "spielende", "gewinner": "dorf"},
        "einmalig": True,
    },
    "werwolf_gewonnen": {
        "text": "Die Werwölfe haben gewonnen! Sie sind nun in der Überzahl und übernehmen das Dorf.",
        "anweisung": "Die Werwölfe haben gewonnen. Decke alle Rollen auf.",
        "bedingung": {"trigger": "spielende", "gewinner": "werwolf"},
        "einmalig": True,
    },
    "verliebte_gewonnen": {
        "text": "Die Verliebten haben gewonnen! Ihre Liebe hat alle Hindernisse überwunden. Sie sind die letzten Überlebenden.",
        "anweisung": "Die Verliebten sind die letzten Überlebenden. Romantisches Ende!",
        "bedingung": {"trigger": "spielende", "gewinner": "verliebte"},
        "einmalig": True,
    },
    "selbstmoerder_gewonnen": {
        "text": "Der Selbstmörder hat es geschafft! Er wurde vom Dorf hingerichtet und hat sein Ziel erreicht.",
        "anweisung": "Der Selbstmörder gewinnt alleine!",
        "bedingung": {"trigger": "spielende", "gewinner": "selbstmoerder"},
        "einmalig": True,
    },
}


# Hilfsfunktion zum Abrufen des richtigen Erzähler-Texts
def hole_erzaehler_text(raum_id, event_typ, kontext=None):
    """
    Gibt den passenden Erzählertext zurück, wenn er noch nicht gespielt wurde.
    kontext: Dict mit Variablen für Platzhalter (z.B. {opfer}, {spieler})
    """
    # Prüfe ob Event bereits gespielt
    if ERZAEHLER_EVENTS.get(event_typ, {}).get("einmalig", True):
        if ErzaehlerEvent.event_bereits_gespielt(raum_id, event_typ):
            return None

    event = ERZAEHLER_EVENTS.get(event_typ) or ERZAEHLER_PHASEN.get(event_typ)
    if not event:
        return None

    text = event["text"]
    anweisung = event.get("anweisung", "")

    # Platzhalter ersetzen
    if kontext:
        for key, value in kontext.items():
            text = text.replace("{" + key + "}", str(value))
            anweisung = anweisung.replace("{" + key + "}", str(value))

    return {
        "text": text,
        "anweisung": anweisung,
        "einmalig": event.get("einmalig", False),
    }


# Legacy-Kompatibilität
ERZAEHLER_TEXTE = ERZAEHLER_PHASEN


# ============================================================================
# HINWEIS-SYSTEM FÜR ONLINE-MODUS
# Subtile visuelle/akustische Hinweise zur Werwolf-Erkennung
# Prozentbasiert, nicht spezifisch, ausbalanciert
# ============================================================================

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
        "audio": "shadow_swoosh.mp3",
        "verdaechtigkeit": 0.2,
    },
    "heulen_fern": {
        "name": "Fernes Heulen",
        "beschreibung": "Ein leises, fernes Wolfsheulen ist zu hören",
        "dauer_ms": 2000,
        "css_class": None,
        "audio": "distant_howl.mp3",
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
        "audio": "scratch.mp3",
        "verdaechtigkeit": 0.35,
    },
    "herzschlag": {
        "name": "Schneller Herzschlag",
        "beschreibung": "Ein schneller Herzschlag pulsiert",
        "dauer_ms": 1500,
        "css_class": "hint-heartbeat",
        "audio": "heartbeat_fast.mp3",
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
        "audio": "whisper.mp3",
        "verdaechtigkeit": 0.25,
    },
    "selbst_verdaechtigung": {
        "name": "Selbst-Verdächtigung",
        "beschreibung": "Der Spieler macht sich selbst verdächtig (Selbstmörder)",
        "dauer_ms": 1000,
        "css_class": "hint-sus-self",
        "audio": "suspicious.mp3",
        "verdaechtigkeit": 0.5,  # Spieler-kontrolliert
    },
    "stolpern": {
        "name": "Stolpern",
        "beschreibung": "Der Spieler scheint zu stolpern",
        "dauer_ms": 500,
        "css_class": "hint-stumble",
        "audio": "stumble.mp3",
        "verdaechtigkeit": 0.1,
    },
    "kichern": {
        "name": "Böses Kichern",
        "beschreibung": "Ein leises, böses Kichern",
        "dauer_ms": 800,
        "css_class": None,
        "audio": "evil_chuckle.mp3",
        "verdaechtigkeit": 0.45,
    },
}

# ============================================================================
# HINWEIS-KONFIGURATION FÜR REMOTE-PLAY
# WICHTIG: Im Remote-Modus können Spieler KEINE Audio von anderen Geräten hören!
# Daher: Hinweise werden als SYNCHRONISIERTE VISUELLE EVENTS an ALLE gesendet
# ============================================================================

HINWEIS_MODUS = {
    "lokal": {
        # Im lokalen Modus: Audio + Visual für den Erzähler
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
    "werwolf": {
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
    "selbst_verdaechtigung": {
        "nachricht": "{spieler} verhält sich verdächtig!",
        "3d_effekt": "suspicious_behavior",
    },
}

# Spezielle Rollen-Hinweise (überschreiben Team-Standard)
SPEZIAL_HINWEISE = {
    "Selbstmörder": {
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
    "Gerber": {
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": ["selbst_verdaechtigung", "nervoes"],
        "hinweise_pro_tag": 2,
        "beschreibung": "Du kannst dich verdächtig machen, um gehängt zu werden.",
    },
    "Dorfdepp": {
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": ["stolpern", "nervoes"],
        "hinweise_pro_tag": 2,
        "beschreibung": "Mach dich zum Deppen und wirke verdächtig!",
    },
    "Engel": {
        "kann_hinweis_senden": True,
        "verfuegbare_hinweise": ["gluehen", "selbst_verdaechtigung"],
        "hinweise_pro_tag": 2,
        "beschreibung": "Du musst in der ersten Runde sterben! Ziehe Aufmerksamkeit auf dich.",
    },
    "Weißer Wolf": {
        # Besonders unauffällig unter Wölfen
        "basis_chance_override": 0.08,  # Niedrigere Chance als normale Werwölfe
        "hinweise": ["schatten"],
    },
    "Wolfshund": {
        # Je nach Entscheidung verschiedene Hinweise
        "dynamisch": True,
    },
}

# Spielregeln/Varianten für Regelauswahl
SPIEL_REGELN = {
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
# ROLLEN DEFINITIONEN - Vollständige Sammlung
# Basierend auf: https://werwolf.fandom.com/de/wiki/Werwolf-Rollen-Sammlung
# Icons: FontAwesome 6 (https://fontawesome.com/icons)
# ============================================================================

ROLLEN = {
    # ========================================================================
    # 1-9 GRUNDROLLEN
    # ========================================================================
    "Dorfbewohner": {
        "id": 1,
        "team": "dorf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist ein einfacher Dorfbewohner. Hilf dem Dorf, die Werwölfe zu entlarven! Du hast keine speziellen Fähigkeiten, aber deine Stimme zählt.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-user",
        "farbe": "#6b7280",
        "erzaehler_nacht": "Der Dorfbewohner schläft friedlich. Er hat keine nächtlichen Fähigkeiten.",
        "erzaehler_tag": "Der Dorfbewohner erwacht und hofft, die Wölfe zu entlarven. Seine Stimme ist seine einzige Waffe.",
        "hinweis_config": None,  # Keine speziellen Hinweise
    },
    "Werwolf": {
        "id": 2,
        "team": "werwolf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist ein Werwolf! Jede Nacht ermordest du gemeinsam mit deinen Werwolf-Gefährten einen Dorfbewohner. Bleibe unentdeckt!",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-solid fa-paw",
        "farbe": "#dc2626",
        "erzaehler_nacht": "Die Werwölfe erwachen, erkennen sich und wählen gemeinsam ein Opfer aus.",
        "erzaehler_tag": None,
    },
    "Seherin": {
        "id": 3,
        "team": "dorf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist die Seherin. Jede Nacht kannst du die wahre Identität eines Spielers erfahren - ob er ein Werwolf ist oder nicht.",
        "nacht_aktiv": True,
        "prioritaet": 20,
        "icon": "fa-solid fa-eye",
        "farbe": "#7c3aed",
        "erzaehler_nacht": "Die Seherin erwacht und zeigt auf einen Spieler. Du zeigst ihr mit Daumen hoch (Dorf) oder runter (Werwolf) die Zugehörigkeit.",
        "erzaehler_tag": None,
    },
    "Hexe": {
        "id": 4,
        "team": "dorf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist die Hexe. Du hast einen Heiltrank (rettet das Werwolf-Opfer) und einen Gifttrank (tötet einen Spieler). Jeder Trank kann nur einmal verwendet werden!",
        "nacht_aktiv": True,
        "prioritaet": 60,
        "icon": "fa-solid fa-hat-wizard",
        "farbe": "#059669",
        "erzaehler_nacht": "Die Hexe erwacht. Zeige auf das Werwolf-Opfer. Frage: Heiltrank einsetzen? (Daumen hoch/runter) Gifttrank einsetzen? (Zeige auf Spieler oder schüttle Kopf)",
        "erzaehler_tag": None,
    },
    "Jäger": {
        "id": 5,
        "team": "dorf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist der Jäger. Wenn du stirbst, kannst du einen letzten Schuss abfeuern und einen Spieler deiner Wahl mit in den Tod reißen!",
        "nacht_aktiv": False,
        "prioritaet": 99,
        "icon": "fa-solid fa-crosshairs",
        "farbe": "#b45309",
        "erzaehler_nacht": "Der Jäger schläft mit seiner Flinte unter dem Kopfkissen. Bereit für seinen letzten Schuss.",
        "erzaehler_tag": "Der Jäger ist gestorben! Mit zitternder Hand hebt er seine Flinte. Auf wen feuert er seinen letzten Schuss?",
        "hinweis_config": None,
    },
    "Heiler": {
        "id": 6,
        "team": "dorf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist der Heiler. Jede Nacht kannst du einen Spieler vor dem Werwolf-Angriff schützen. Du darfst nicht zweimal hintereinander denselben Spieler schützen!",
        "nacht_aktiv": True,
        "prioritaet": 55,
        "icon": "fa-solid fa-heart-pulse",
        "farbe": "#10b981",
        "erzaehler_nacht": "Der Heiler erwacht und zeigt auf den Spieler, den er diese Nacht beschützen möchte. Nicht denselben wie letzte Nacht!",
        "erzaehler_tag": None,
    },
    "Amor": {
        "id": 7,
        "team": "dorf",
        "kategorie": "grundrollen",
        "beschreibung": "Du bist Amor. In der ersten Nacht wählst du zwei Spieler, die sich unsterblich verlieben. Stirbt einer, stirbt auch der andere. Die Verliebten gewinnen nur gemeinsam!",
        "nacht_aktiv": True,
        "prioritaet": 5,
        "icon": "fa-solid fa-heart",
        "farbe": "#ec4899",
        "erzaehler_nacht": "Amor erwacht (nur erste Nacht) und zeigt auf zwei Spieler, die sich verlieben sollen. Berühre beide leicht an der Schulter.",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 10-19 DORFBEWOHNER-VARIANTEN
    # ========================================================================
    "Alter Mann": {
        "id": 11,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist der Alte Mann. Du überlebst den ersten Werwolf-Angriff! Aber Vorsicht: Wirst du vom Dorf gehängt, verlieren alle Spezialrollen ihre Fähigkeiten.",
        "nacht_aktiv": False,
        "prioritaet": 98,
        "icon": "fa-solid fa-person-cane",
        "farbe": "#78716c",
        "erzaehler_nacht": "Der Alte Mann schläft tief. Seine zähe Haut hat schon manchen Biss überstanden.",
        "erzaehler_tag": "Der Alte Mann erwacht. Falls er von Wölfen angegriffen wurde, hat er überlebt! Aber Vorsicht: Hängt das Dorf ihn, verlieren alle Spezialrollen ihre Kräfte.",
        "hinweis_config": None,
    },
    "Dorfdepp": {
        "id": 12,
        "team": "solo",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist der Dorfdepp. Du gewinnst, wenn du vom Dorf gehängt wirst. Du gewinnst mit dem eigentlichen Gewinner.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-face-grin-tongue",
        "farbe": "#f59e0b",
        "erzaehler_nacht": "Der Dorfdepp schläft und träumt davon, endlich ernst genommen zu werden... oder auch nicht.",
        "erzaehler_tag": "Der Dorfdepp stolpert durch den Tag. Sein Ziel: So verdächtig wie möglich wirken, ohne ein Werwolf zu sein!",
        "hinweis_config": "Dorfdepp",  # Kann sich selbst verdächtig machen
    },
    "Drei Brüder": {
        "id": 13,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist einer der drei Brüder. In der ersten Nacht erkennt ihr euch gegenseitig. Ihr dürft jede Nacht kurz die Augen öffnen und euch absprechen.",
        "nacht_aktiv": True,
        "prioritaet": 8,
        "icon": "fa-solid fa-people-group",
        "farbe": "#4f46e5",
        "erzaehler_nacht": "Die drei Brüder erwachen und erkennen sich. Sie dürfen sich kurz absprechen.",
        "erzaehler_tag": None,
    },
    "Zwei Schwestern": {
        "id": 14,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist eine der zwei Schwestern. In der ersten Nacht erkennt ihr euch gegenseitig. Ihr dürft jede Nacht kurz die Augen öffnen und euch absprechen.",
        "nacht_aktiv": True,
        "prioritaet": 8,
        "icon": "fa-solid fa-user-group",
        "farbe": "#f472b6",
        "erzaehler_nacht": "Die zwei Schwestern erwachen und erkennen sich. Sie dürfen sich kurz absprechen.",
        "erzaehler_tag": None,
    },
    "Freimaurer": {
        "id": 15,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist ein Freimaurer. In der ersten Nacht erkennen sich alle Freimaurer gegenseitig. Ihr wisst, dass ihr auf der gleichen Seite steht.",
        "nacht_aktiv": True,
        "prioritaet": 9,
        "icon": "fa-solid fa-building-columns",
        "farbe": "#3b82f6",
        "erzaehler_nacht": "Die Freimaurer erwachen und erkennen sich gegenseitig.",
        "erzaehler_tag": None,
    },
    "Griesgram": {
        "id": 16,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist der Griesgram. Du bist immer schlecht gelaunt und stimmst immer mit JA bei Hinrichtungen. Deine Stimme zählt aber trotzdem!",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-face-angry",
        "farbe": "#6b7280",
        "erzaehler_nacht": "Der Griesgram wälzt sich mürrisch im Bett. Selbst im Schlaf ist er schlecht gelaunt.",
        "erzaehler_tag": "Der Griesgram erwacht grantig. Er stimmt IMMER für eine Hinrichtung - egal wer vorgeschlagen wird!",
        "hinweis_config": None,
    },
    "Jesus": {
        "id": 17,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist Jesus. Wenn du stirbst, kannst du einmalig nach 3 Tagen auferstehen und weiterspielen! Die Auferstehung geschieht automatisch.",
        "nacht_aktiv": False,
        "prioritaet": 97,
        "icon": "fa-solid fa-cross",
        "farbe": "#fbbf24",
        "erzaehler_nacht": "Jesus ruht friedlich. Der Tod ist für ihn nur ein vorübergehender Zustand.",
        "erzaehler_tag": "Falls Jesus vor 3 Tagen gestorben ist: Ein Wunder geschieht! Jesus erhebt sich und kehrt triumphierend ins Spiel zurück!",
        "hinweis_config": None,
    },
    "Tonks": {
        "id": 18,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist Tonks, ein Metamorphmagus! Einmal pro Spiel kannst du deine Rolle mit einem zufälligen toten Spieler tauschen und seine Fähigkeiten übernehmen.",
        "nacht_aktiv": True,
        "prioritaet": 75,
        "icon": "fa-solid fa-masks-theater",
        "farbe": "#a855f7",
        "erzaehler_nacht": "Tonks erwacht. Möchte sie ihre Rolle mit einem toten Spieler tauschen? (Einmal pro Spiel)",
        "erzaehler_tag": None,
    },
    "Hund": {
        "id": 19,
        "team": "dorf",
        "kategorie": "dorfbewohner",
        "beschreibung": "Du bist der treue Hund. Du wählst in der ersten Nacht ein Herrchen. Stirbt dein Herrchen, wechselst du zum Team der Werwölfe über!",
        "nacht_aktiv": True,
        "prioritaet": 7,
        "icon": "fa-solid fa-dog",
        "farbe": "#a16207",
        "erzaehler_nacht": "Der Hund erwacht (nur erste Nacht) und wählt sein Herrchen.",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 20-29 WERWOLF-VARIANTEN
    # ========================================================================
    "Weißer Wolf": {
        "id": 21,
        "team": "solo",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Weiße Wolf! Du jagst mit den Wölfen, aber jede zweite Nacht kannst du zusätzlich einen Mitwerwolf töten. Du gewinnst nur alleine!",
        "nacht_aktiv": True,
        "prioritaet": 52,
        "icon": "fa-solid fa-paw",
        "farbe": "#f5f5f4",
        "erzaehler_nacht": "Der Weiße Wolf erwacht (jede zweite Nacht). Möchte er einen Mitwerwolf töten?",
        "erzaehler_tag": None,
    },
    "Polarwolf": {
        "id": 22,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Polarwolf. Du bist immun gegen die Kälte - der Sandmann kann dich nicht einschläfern und der Jäger verfehlt dich immer!",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-solid fa-snowflake",
        "farbe": "#e0f2fe",
        "erzaehler_nacht": "Der Polarwolf ist immun gegen Sandmann und Jäger.",
        "erzaehler_tag": None,
    },
    "Wolf im Schafspelz": {
        "id": 23,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Wolf im Schafspelz. Für die Seherin erscheinst du als harmloser Dorfbewohner! Nur die Aurenseherin erkennt dein böses Herz.",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-brands fa-bluesky",
        "farbe": "#fef3c7",
        "erzaehler_nacht": "Der Wolf im Schafspelz erscheint der Seherin als Dorfbewohner!",
        "erzaehler_tag": None,
    },
    "Teenager-Werwolf": {
        "id": 24,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Teenager-Werwolf. Du bist rebellisch - einmal pro Spiel kannst du dich weigern, beim Werwolf-Angriff mitzumachen, ohne aufzufallen.",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-solid fa-paw",
        "farbe": "#f97316",
        "erzaehler_nacht": "Der Teenager-Werwolf kann einmal pro Spiel den Angriff verweigern.",
        "erzaehler_tag": None,
    },
    "Wildes Kind": {
        "id": 25,
        "team": "dorf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist das Wilde Kind. In der ersten Nacht wählst du ein Vorbild. Solange es lebt, bist du Dorfbewohner. Stirbt es, wirst du zum Werwolf!",
        "nacht_aktiv": True,
        "prioritaet": 6,
        "icon": "fa-solid fa-child",
        "farbe": "#92400e",
        "erzaehler_nacht": "Das Wilde Kind erwacht (erste Nacht) und wählt sein Vorbild.",
        "erzaehler_tag": "Das Vorbild des Wilden Kindes ist gestorben - es wird zum Werwolf!",
    },
    "Lupin": {
        "id": 26,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist Lupin. Du verwandelst dich nur bei Vollmond - in geraden Runden bist du ein harmloser Mensch (erscheinst so für Seherin), in ungeraden ein Wolf!",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-solid fa-moon",
        "farbe": "#ca8a04",
        "erzaehler_nacht": "Lupin ist in geraden Runden Mensch, in ungeraden Wolf.",
        "erzaehler_tag": None,
    },
    "Werwolfseherin": {
        "id": 27,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist die Werwolfseherin. Du bist ein Werwolf mit Seher-Kräften! Jede Nacht erfährst du die Rolle eines Spielers (nach dem Werwolf-Angriff).",
        "nacht_aktiv": True,
        "prioritaet": 65,
        "icon": "fa-solid fa-eye",
        "farbe": "#b91c1c",
        "erzaehler_nacht": "Die Werwolfseherin erwacht nach den Werwölfen und erfährt die Rolle eines Spielers.",
        "erzaehler_tag": None,
    },
    "Wolfsjunge": {
        "id": 28,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Wolfsjunge. Wenn ein anderer Werwolf stirbt, verwandelst du dich vor Wut - in der nächsten Nacht töten die Wölfe ZWEI Opfer!",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-solid fa-paw",
        "farbe": "#991b1b",
        "erzaehler_nacht": "Ein Werwolf ist gestorben - der Wolfsjunge ist wütend! Heute Nacht zwei Opfer!",
        "erzaehler_tag": None,
    },
    "Urwolf": {
        "id": 29,
        "team": "werwolf",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Urwolf. Einmal pro Spiel kannst du statt zu töten einen Dorfbewohner infizieren - dieser wird zum Werwolf und erwacht als solcher!",
        "nacht_aktiv": True,
        "prioritaet": 51,
        "icon": "fa-solid fa-virus",
        "farbe": "#7f1d1d",
        "erzaehler_nacht": "Der Urwolf kann einmal pro Spiel einen Spieler infizieren statt zu töten.",
        "erzaehler_tag": None,
    },
    "Einsamer Wolf": {
        "id": 30,
        "team": "solo",
        "kategorie": "werwolf",
        "beschreibung": "Du bist der Einsame Wolf. Du kennst die anderen Wölfe nicht und sie kennen dich nicht. Du tötest alleine und gewinnst nur, wenn DU der letzte Wolf bist!",
        "nacht_aktiv": True,
        "prioritaet": 48,
        "icon": "fa-solid fa-paw",
        "farbe": "#4c1d95",
        "erzaehler_nacht": "Der Einsame Wolf erwacht separat und wählt sein eigenes Opfer.",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 30-39 SEHENDE ROLLEN
    # ========================================================================
    "Seherlehrling": {
        "id": 31,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist der Seherlehrling. Du hast noch keine Fähigkeiten, aber wenn die Seherin stirbt, übernimmst du ihre Kraft und kannst ab dann jede Nacht sehen!",
        "nacht_aktiv": False,
        "prioritaet": 21,
        "icon": "fa-solid fa-graduation-cap",
        "farbe": "#8b5cf6",
        "erzaehler_nacht": "Der Seherlehrling übernimmt die Fähigkeit der Seherin, falls diese stirbt.",
        "erzaehler_tag": "Die Seherin ist tot! Der Seherlehrling übernimmt ihre Fähigkeiten.",
    },
    "Aurenseherin": {
        "id": 32,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist die Aurenseherin. Du siehst nicht die Rolle, aber die Aura - ob jemand Böses im Sinn hat. Verliebte und Verzauberte haben veränderte Auren!",
        "nacht_aktiv": True,
        "prioritaet": 22,
        "icon": "fa-solid fa-star",
        "farbe": "#c084fc",
        "erzaehler_nacht": "Die Aurenseherin erwacht und erfährt die Aura eines Spielers (gut/böse/verändert).",
        "erzaehler_tag": None,
    },
    "Medium": {
        "id": 33,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist das Medium. Jede Nacht kannst du mit einem bereits gestorbenen Spieler kommunizieren und erfährst seine wahre Rolle und letzte Worte.",
        "nacht_aktiv": True,
        "prioritaet": 23,
        "icon": "fa-solid fa-ghost",
        "farbe": "#a78bfa",
        "erzaehler_nacht": "Das Medium erwacht und wählt einen Toten zur Kommunikation. Flüstere ihm die Rolle zu.",
        "erzaehler_tag": None,
    },
    "Demoskopin": {
        "id": 34,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist die Demoskopin. Du kennst die Meinungsumfragen! Am Anfang jeder Tagphase erfährst du, wer die meisten Stimmen bekommen würde.",
        "nacht_aktiv": False,
        "prioritaet": 85,
        "icon": "fa-solid fa-chart-column",
        "farbe": "#06b6d4",
        "erzaehler_nacht": "Die Demoskopin analysiert auch nachts die Stimmung im Dorf.",
        "erzaehler_tag": "Die Demoskopin erwacht mit frischen Umfragewerten! Sie weiß, wer heute die meisten Stimmen bekommen würde.",
        "hinweis_config": None,
    },
    "Tratschweib": {
        "id": 35,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist das Tratschweib. Du hörst alles! Jede Nacht erfährst du zwei zufällige Spieler und ob sie im gleichen Team sind oder nicht.",
        "nacht_aktiv": True,
        "prioritaet": 24,
        "icon": "fa-solid fa-comment-dots",
        "farbe": "#e11d48",
        "erzaehler_nacht": "Das Tratschweib erwacht und erfährt, ob zwei zufällige Spieler im gleichen Team sind.",
        "erzaehler_tag": None,
    },
    "Paranormaler Ermittler (billig)": {
        "id": 36,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist der Paranormale Ermittler mit billiger Kristallkugel. Du kannst sehen, aber die Ergebnisse sind zu 30% falsch! Vertraue deinen Visionen nicht blind.",
        "nacht_aktiv": True,
        "prioritaet": 25,
        "icon": "fa-solid fa-eye-slash",
        "farbe": "#a3a3a3",
        "erzaehler_nacht": "Der Paranormale Ermittler erwacht. ACHTUNG: 30% Chance auf falsches Ergebnis!",
        "erzaehler_tag": None,
    },
    "Bärenbändiger": {
        "id": 37,
        "team": "dorf",
        "kategorie": "seher",
        "beschreibung": "Du bist der Bärenbändiger. Dein Bär brummt morgens, wenn ein Werwolf neben dir sitzt! Alle hören das Brummen, aber nur du weißt was es bedeutet.",
        "nacht_aktiv": False,
        "prioritaet": 86,
        "icon": "fa-solid fa-paw",
        "farbe": "#78350f",
        "erzaehler_nacht": "Der Bär des Bärenbändigers schläft unruhig. Er spürt die Wölfe in der Nähe...",
        "erzaehler_tag": "GRRRR! Der Bär des Bärenbändigers brummt laut! Das bedeutet: Mindestens ein Werwolf sitzt direkt neben dem Bärenbändiger!",
        "hinweis_config": None,
    },
    # ========================================================================
    # 40-49 HEXEN UND ÄHNLICHE ROLLEN
    # ========================================================================
    "Kräuterweib": {
        "id": 41,
        "team": "dorf",
        "kategorie": "hexe",
        "beschreibung": "Du bist das Kräuterweib. Jede Nacht kannst du einem Spieler einen Trank geben, der ihn am nächsten Tag stumm macht - er darf nicht sprechen!",
        "nacht_aktiv": True,
        "prioritaet": 61,
        "icon": "fa-solid fa-leaf",
        "farbe": "#16a34a",
        "erzaehler_nacht": "Das Kräuterweib erwacht und wählt einen Spieler, der morgen stumm sein wird.",
        "erzaehler_tag": "{spieler} wurde vom Kräuterweib verstummt und darf heute nicht sprechen!",
    },
    "Giftmischerin": {
        "id": 42,
        "team": "werwolf",
        "kategorie": "hexe",
        "beschreibung": "Du bist die Giftmischerin. Du gehörst zu den Wölfen! Einmal pro Spiel kannst du einen Spieler vergiften, der nach 2 Tagen stirbt (wenn nicht geheilt).",
        "nacht_aktiv": True,
        "prioritaet": 62,
        "icon": "fa-solid fa-skull-crossbones",
        "farbe": "#4ade80",
        "erzaehler_nacht": "Die Giftmischerin kann einmal pro Spiel einen Spieler vergiften (Tod nach 2 Tagen).",
        "erzaehler_tag": None,
    },
    "Zauberer": {
        "id": 43,
        "team": "dorf",
        "kategorie": "hexe",
        "beschreibung": "Du bist der Zauberer. Du hast 3 Zauber: Schutz (1x), Sicht (1x) und Schweigen (1x). Setze sie weise ein, denn jeder Zauber wirkt nur einmal!",
        "nacht_aktiv": True,
        "prioritaet": 63,
        "icon": "fa-solid fa-wand-magic-sparkles",
        "farbe": "#3b0764",
        "erzaehler_nacht": "Der Zauberer erwacht. Welchen Zauber möchte er einsetzen? (Schutz/Sicht/Schweigen)",
        "erzaehler_tag": None,
    },
    "Sandmann": {
        "id": 44,
        "team": "dorf",
        "kategorie": "hexe",
        "beschreibung": "Du bist der Sandmann. Jede Nacht kannst du einen Spieler einschläfern - dieser kann seine Nachtaktion nicht ausführen und verschläft die Phase!",
        "nacht_aktiv": True,
        "prioritaet": 15,
        "icon": "fa-solid fa-bed",
        "farbe": "#ddd6fe",
        "erzaehler_nacht": "Der Sandmann erwacht zuerst und wählt einen Spieler, der diese Nacht verschläft.",
        "erzaehler_tag": None,
    },
    "Hahn": {
        "id": 45,
        "team": "dorf",
        "kategorie": "hexe",
        "beschreibung": "Du bist der Hahn. Du krähst bei Sonnenaufgang! Wenn du stirbst, wird die Identität des Spielers, der dich getötet hat, enthüllt.",
        "nacht_aktiv": False,
        "prioritaet": 96,
        "icon": "fa-solid fa-sun",
        "farbe": "#dc2626",
        "erzaehler_nacht": "Der Hahn schläft auf seinem Hühnerstall. Er wird jeden Mörder entlarven, der ihn tötet.",
        "erzaehler_tag": "KIKERIKI! Der Hahn wurde getötet! Mit letzter Kraft verrät er seinen Mörder: Es war {moerder}!",
        "hinweis_config": None,
    },
    # ========================================================================
    # 50-59 JÄGER UND AGGRESSIVE ROLLEN
    # ========================================================================
    "Prinz": {
        "id": 51,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Prinz. Du kannst nicht durch die Dorfabstimmung gehängt werden! Wenn die Mehrheit dich wählt, wird deine Identität enthüllt aber du lebst.",
        "nacht_aktiv": False,
        "prioritaet": 97,
        "icon": "fa-solid fa-crown",
        "farbe": "#fbbf24",
        "erzaehler_nacht": "Der Prinz ruht in seinem königlichen Bett. Niemand würde es wagen, ihn zu erhängen.",
        "erzaehler_tag": "HALT! Das Dorf wählte den Prinzen! Er offenbart seine Identität und kann NICHT gehängt werden!",
        "hinweis_config": None,
    },
    "Flammenmann": {
        "id": 52,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Flammenmann. Einmal pro Spiel kannst du während des Tages ein Haus anzünden - alle Spieler darin (Links und Rechts neben dir) sterben!",
        "nacht_aktiv": False,
        "prioritaet": 94,
        "icon": "fa-solid fa-fire",
        "farbe": "#ea580c",
        "erzaehler_nacht": "Der Flammenmann träumt von lodernden Flammen. Er wartet auf den richtigen Moment.",
        "erzaehler_tag": "FEUER! Der Flammenmann zündet sein Haus an! Die Flammen greifen auf die Nachbarhäuser über - alle Nachbarn sterben!",
        "hinweis_config": None,
    },
    "Drachenbändiger": {
        "id": 53,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Drachenbändiger. Dein Drache beschützt dich - wer dich angreift, wird von deinem Drachen getötet! Funktioniert nur einmal.",
        "nacht_aktiv": False,
        "prioritaet": 93,
        "icon": "fa-solid fa-dragon",
        "farbe": "#7c3aed",
        "erzaehler_nacht": "Der Drachenbändiger schläft friedlich, sein Drache wacht über ihn mit feurigem Atem.",
        "erzaehler_tag": "FEUER-ATEM! Der Drache des Drachenbändigers verbrennt seinen Angreifer zu Asche!",
        "hinweis_config": None,
    },
    "Tanklastwagenfahrer": {
        "id": 54,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Tanklastwagenfahrer. Einmal pro Spiel kannst du während des Tages jemanden überfahren - dieser Spieler stirbt sofort!",
        "nacht_aktiv": False,
        "prioritaet": 92,
        "icon": "fa-solid fa-truck",
        "farbe": "#64748b",
        "erzaehler_nacht": "Der Tanklastwagenfahrer parkt seinen Laster. Er wartet auf den richtigen Moment.",
        "erzaehler_tag": "HUUUP! Der Tanklastwagenfahrer startet seinen Motor und überfährt {spieler}! Keine Chance zu überleben!",
        "hinweis_config": None,
    },
    "Inquisitor": {
        "id": 55,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Inquisitor. Einmal pro Spiel kannst du während des Tages einen Spieler verhören - gesteht er nicht (Werwolf), stirbt er sofort!",
        "nacht_aktiv": False,
        "prioritaet": 91,
        "icon": "fa-solid fa-scale-balanced",
        "farbe": "#1e3a8a",
        "erzaehler_nacht": "Der Inquisitor schärft sein Schwert der Gerechtigkeit im Schlaf.",
        "erzaehler_tag": 'Der Inquisitor tritt vor! "Im Namen der Wahrheit - GESTEHE!" Ist das Ziel ein Werwolf, stirbt es auf der Stelle!',
        "hinweis_config": None,
    },
    "König": {
        "id": 56,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der König. Deine Stimme zählt doppelt bei allen Abstimmungen! Aber wenn du stirbst, darf das Dorf einen neuen König wählen.",
        "nacht_aktiv": False,
        "prioritaet": 95,
        "icon": "fa-solid fa-chess-king",
        "farbe": "#ca8a04",
        "erzaehler_nacht": "Der König ruht auf seinem Thron. Seine Stimme wiegt schwerer als alle anderen.",
        "erzaehler_tag": "Der König ist gefallen! Sein Erbe muss bestimmt werden - das Dorf wählt einen neuen König mit doppelter Stimme!",
        "hinweis_config": None,
    },
    "Buddler": {
        "id": 57,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Buddler. Jede Nacht kannst du ein Grab ausgraben und erfährst die Todesursache des Spielers - Werwolf, Abstimmung, Gift oder Anderes.",
        "nacht_aktiv": True,
        "prioritaet": 80,
        "icon": "fa-solid fa-shovel",
        "farbe": "#78716c",
        "erzaehler_nacht": "Der Buddler erwacht und wählt ein Grab. Flüstere ihm die Todesursache zu.",
        "erzaehler_tag": None,
    },
    "Pyromane": {
        "id": 58,
        "team": "solo",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Pyromane. Jede Nacht kannst du ein Haus mit Benzin übergießen. Einmal pro Spiel kannst du alle übergossenen Häuser anzünden - das Feuer tötet auch die NACHBARN (links und rechts)!",
        "nacht_aktiv": True,
        "prioritaet": 75,
        "icon": "fa-solid fa-fire-flame-curved",
        "farbe": "#f97316",
        "erzaehler_nacht": "Der Pyromane erwacht. Möchtest du ein Haus mit Benzin übergießen - oder alle übergossenen Häuser ANZÜNDEN?",
        "erzaehler_tag": "FEUER! Der Pyromane hat zugeschlagen! Die Flammen verschlingen {opfer} und breiten sich auf die Nachbarhäuser aus!",
        "nutzt_nachbarn": True,  # Markiert diese Rolle als nachbar-relevant
        "gewinnbedingung": "Überlebe bis zum Schluss und zünde mindestens ein Haus an.",
    },
    "Gaukler": {
        "id": 59,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Gaukler. Einmal pro Spiel kannst du während des Tages zwei Spieler ihre Plätze tauschen lassen - alle Effekte wechseln mit!",
        "nacht_aktiv": False,
        "prioritaet": 90,
        "icon": "fa-solid fa-masks-theater",
        "farbe": "#c026d3",
        "erzaehler_nacht": "Der Gaukler probt seine Tricks im Schlaf. Ein Meister der Verwirrung.",
        "erzaehler_tag": "HOKUSPOKUS! Der Gaukler wirbelt herum und lässt {spieler1} und {spieler2} ihre Plätze tauschen! Alle Effekte wandern mit!",
        "hinweis_config": None,
    },
    "Kamikaze": {
        "id": 60,
        "team": "dorf",
        "kategorie": "jaeger",
        "beschreibung": "Du bist der Kamikaze. Jede Nacht wirst du gefragt, ob du jemanden töten willst. Wenn ja, stirbt dein Opfer - aber du auch! Wenn du den letzten Werwolf tötest, gewinnst du mit dem Dorf.",
        "nacht_aktiv": True,
        "prioritaet": 76,
        "icon": "fa-solid fa-bomb",
        "farbe": "#ef4444",
        "erzaehler_nacht": "Der Kamikaze erwacht. Möchte er sich opfern und jemanden mitnehmen?",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 60-69 HEILER UND SCHÜTZENDE ROLLEN
    # ========================================================================
    "Ergebene Magd": {
        "id": 61,
        "team": "dorf",
        "kategorie": "heiler",
        "beschreibung": "Du bist die Ergebene Magd. Wenn eine wichtige Rolle (Seherin, Hexe, Jäger) stirbt, übernimmst du ihre Identität und Fähigkeiten!",
        "nacht_aktiv": False,
        "prioritaet": 95,
        "icon": "fa-solid fa-broom",
        "farbe": "#14b8a6",
        "erzaehler_nacht": "Die Ergebene Magd ruht im Hintergrund, bereit ihre Herrin zu ersetzen wenn nötig.",
        "erzaehler_tag": "Die Ergebene Magd tritt vor! Sie übernimmt die Rolle und Fähigkeiten der verstorbenen {rolle}!",
        "hinweis_config": None,
    },
    "Hure": {
        "id": 62,
        "team": "dorf",
        "kategorie": "heiler",
        "beschreibung": "Du bist die Hure. Jede Nacht besuchst du einen Spieler und schützt ihn vor Werwölfen. Aber: Besuchst du einen Werwolf, stirbst DU!",
        "nacht_aktiv": True,
        "prioritaet": 45,
        "icon": "fa-solid fa-heart",
        "farbe": "#db2777",
        "erzaehler_nacht": "Die Hure erwacht und wählt einen Spieler zum Besuchen.",
        "erzaehler_tag": None,
    },
    "Prostituierte": {
        "id": 63,
        "team": "dorf",
        "kategorie": "heiler",
        "beschreibung": "Du bist die Prostituierte. Jede Nacht kannst du bei einem Spieler schlafen - ihr beide seid diese Nacht geschützt, aber er sieht deine Rolle!",
        "nacht_aktiv": True,
        "prioritaet": 46,
        "icon": "fa-solid fa-bed",
        "farbe": "#f43f5e",
        "erzaehler_nacht": "Die Prostituierte erwacht und wählt einen Spieler für die Nacht.",
        "erzaehler_tag": None,
    },
    "Oma": {
        "id": 64,
        "team": "dorf",
        "kategorie": "heiler",
        "beschreibung": "Du bist die Oma. Du bist alt und schwach - die Werwölfe verschonen dich aus Mitleid! Du kannst nicht von Wölfen getötet werden.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-person-dress",
        "farbe": "#fda4af",
        "erzaehler_nacht": "Die Oma schnarcht leise in ihrem Bett. Die Werwölfe haben Mitleid mit der alten Frau.",
        "erzaehler_tag": "Die Werwölfe haben die Oma verschont! Sie ist zu alt und schwach - kein würdiger Gegner für die Bestien.",
        "hinweis_config": None,
    },
    "Leibwächter": {
        "id": 65,
        "team": "dorf",
        "kategorie": "heiler",
        "beschreibung": "Du bist der Leibwächter. Jede Nacht wählst du einen Spieler zum Schützen. Wird dieser angegriffen, stirbst DU stattdessen!",
        "nacht_aktiv": True,
        "prioritaet": 56,
        "icon": "fa-solid fa-shield-halved",
        "farbe": "#0d9488",
        "erzaehler_nacht": "Der Leibwächter erwacht und wählt einen Spieler zum Beschützen.",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 70-79 AMOR UND SPEZIALROLLEN
    # ========================================================================
    "Dunkler Priester": {
        "id": 71,
        "team": "werwolf",
        "kategorie": "spezial",
        "beschreibung": "Du bist der Dunkle Priester. Wie Amor wählst du zwei Spieler die sich verlieben - aber du gehörst zu den Wölfen und gewinnst mit ihnen!",
        "nacht_aktiv": True,
        "prioritaet": 5,
        "icon": "fa-solid fa-church",
        "farbe": "#18181b",
        "erzaehler_nacht": "Der Dunkle Priester erwacht (erste Nacht) und wählt zwei Spieler zum Verlieben.",
        "erzaehler_tag": None,
    },
    "Zahnarzt": {
        "id": 72,
        "team": "dorf",
        "kategorie": "spezial",
        "beschreibung": "Du bist der Zahnarzt. Jede Nacht kannst du einem Spieler den Mund zunähen - er kann am nächsten Tag nicht abstimmen, nur sprechen!",
        "nacht_aktiv": True,
        "prioritaet": 66,
        "icon": "fa-solid fa-tooth",
        "farbe": "#ffffff",
        "erzaehler_nacht": "Der Zahnarzt erwacht und wählt einen Spieler, der morgen nicht abstimmen darf.",
        "erzaehler_tag": "{spieler} wurde vom Zahnarzt behandelt und darf heute nicht abstimmen!",
    },
    "Rabe": {
        "id": 73,
        "team": "dorf",
        "kategorie": "spezial",
        "beschreibung": "Du bist der Rabe. Jede Nacht markierst du einen Spieler. Dieser erhält am nächsten Tag automatisch 2 Extra-Stimmen gegen sich!",
        "nacht_aktiv": True,
        "prioritaet": 65,
        "icon": "fa-solid fa-crow",
        "farbe": "#1f2937",
        "erzaehler_nacht": "Der Rabe erwacht und markiert einen Spieler (+2 Stimmen gegen ihn morgen).",
        "erzaehler_tag": "{spieler} wurde vom Raben markiert und hat +2 Stimmen gegen sich!",
    },
    "Selbstmörder": {
        "id": 74,
        "team": "solo",
        "kategorie": "spezial",
        "beschreibung": "Du bist der Selbstmörder. Du gewinnst NUR wenn du vom Dorf gehängt wirst! Versuche verdächtig zu wirken, ohne zu offensichtlich zu sein.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-skull",
        "farbe": "#374151",
        "erzaehler_nacht": "Der Selbstmörder liegt wach und plant, wie er morgen möglichst verdächtig wirken kann.",
        "erzaehler_tag": "Der Selbstmörder erwacht mit einem finsteren Plan. Sein Ziel: Vom Dorf gehängt werden! Aber nicht zu offensichtlich...",
        "hinweis_config": "Selbstmörder",  # Kann aktiv Hinweise auf sich ziehen!
    },
    "Chemielaborant": {
        "id": 75,
        "team": "dorf",
        "kategorie": "spezial",
        "beschreibung": "Du bist der Chemielaborant. Wenn du stirbst, sterben deine beiden nächsten lebenden Nachbarn mit dir! Das kann nicht verhindert werden (Ausnahme: Nachbar ist bei der Hure).",
        "nacht_aktiv": False,
        "prioritaet": 97,
        "icon": "fa-solid fa-flask",
        "farbe": "#10b981",
        "erzaehler_nacht": "Der Chemielaborant experimentiert selbst im Schlaf. Ein gefährlicher Nachbar...",
        "erzaehler_tag": "KABOOM! Der Chemielaborant ist tot und seine instabilen Chemikalien explodieren! Seine beiden Nachbarn sterben mit ihm!",
        "hinweis_config": None,
    },
    "Flüchtlinge": {
        "id": 76,
        "team": "dorf",
        "kategorie": "spezial",
        "beschreibung": "Du bist ein Flüchtling. Alle Flüchtlinge kennen sich und halten zusammen. Ihr müsst bis zum Ende überleben um zu gewinnen!",
        "nacht_aktiv": True,
        "prioritaet": 10,
        "icon": "fa-solid fa-person-running",
        "farbe": "#0ea5e9",
        "erzaehler_nacht": "Die Flüchtlinge erwachen und erkennen sich gegenseitig.",
        "erzaehler_tag": None,
    },
    "Nutte": {
        "id": 77,
        "team": "dorf",
        "kategorie": "spezial",
        "beschreibung": "Du bist die Nutte. Jede Nacht wählst du einen Spieler, bei dem du übernachtest. Wird dieser von Werwölfen getötet, stirbst auch du! Aber: Wirst du selbst gewählt, überlebst du (du bist ja nicht zuhause).",
        "nacht_aktiv": True,
        "prioritaet": 47,
        "icon": "fa-solid fa-house-user",
        "farbe": "#ec4899",
        "erzaehler_nacht": "Die Nutte erwacht und wählt einen Spieler, bei dem sie übernachtet.",
        "erzaehler_tag": None,
    },
    "Mordlustiger": {
        "id": 78,
        "team": "solo",
        "kategorie": "spezial",
        "beschreibung": "Du bist der Mordlustige. Du gewinnst, wenn du der letzte überlebende Spieler bist! Jede Nacht kannst du einen Spieler ermorden.",
        "nacht_aktiv": True,
        "prioritaet": 49,
        "icon": "fa-solid fa-user-ninja",
        "farbe": "#7f1d1d",
        "erzaehler_nacht": "Der Mordlustige erwacht und wählt sein nächtliches Opfer.",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 80-89 VAMPIRE UND BÖSE ROLLEN
    # ========================================================================
    "Vampir": {
        "id": 81,
        "team": "vampir",
        "kategorie": "boese",
        "beschreibung": "Du bist ein Vampir! Jede zweite Nacht kannst du einen Spieler in einen Vampir verwandeln. Ihr gewinnt, wenn mehr Vampire als andere leben!",
        "nacht_aktiv": True,
        "prioritaet": 53,
        "icon": "fa-solid fa-tooth",
        "farbe": "#7c2d12",
        "erzaehler_nacht": "Die Vampire erwachen (jede zweite Nacht) und wählen einen Spieler zur Verwandlung.",
        "erzaehler_tag": None,
    },
    "Hexenmeister": {
        "id": 82,
        "team": "werwolf",
        "kategorie": "boese",
        "beschreibung": "Du bist der Hexenmeister. Du gehörst zu den Wölfen und hast einen Fluchzauber - der Verfluchte wird zum Werwolf wenn er angegriffen wird!",
        "nacht_aktiv": True,
        "prioritaet": 68,
        "icon": "fa-solid fa-hat-wizard",
        "farbe": "#4c1d95",
        "erzaehler_nacht": "Der Hexenmeister kann einen Spieler verfluchen (wird bei Angriff zum Wolf).",
        "erzaehler_tag": None,
    },
    "Flötenspieler": {
        "id": 83,
        "team": "solo",
        "kategorie": "boese",
        "beschreibung": "Du bist der Flötenspieler. Jede Nacht verzauberst du zwei Spieler. Du gewinnst wenn alle lebenden Spieler verzaubert sind!",
        "nacht_aktiv": True,
        "prioritaet": 70,
        "icon": "fa-solid fa-music",
        "farbe": "#84cc16",
        "erzaehler_nacht": "Der Flötenspieler erwacht und verzaubert zwei Spieler.",
        "erzaehler_tag": None,
    },
    "Zombie": {
        "id": 84,
        "team": "zombie",
        "kategorie": "boese",
        "beschreibung": "Du bist ein Zombie! Jede Nacht infizierst du einen Spieler. Stirbt ein Infizierter, wird er zum Zombie. Ihr gewinnt bei Zombie-Mehrheit!",
        "nacht_aktiv": True,
        "prioritaet": 54,
        "icon": "fa-solid fa-biohazard",
        "farbe": "#4ade80",
        "erzaehler_nacht": "Die Zombies erwachen und infizieren einen Spieler.",
        "erzaehler_tag": None,
    },
    # ========================================================================
    # 90-99 SONSTIGE ROLLEN
    # ========================================================================
    "Putzfrau": {
        "id": 91,
        "team": "dorf",
        "kategorie": "sonstige",
        "beschreibung": "Du bist die Putzfrau. Wenn jemand stirbt, räumst du auf und erfährst dabei seine wahre Rolle. Du teilst dein Wissen mit dem Dorf.",
        "nacht_aktiv": False,
        "prioritaet": 88,
        "icon": "fa-solid fa-spray-can-sparkles",
        "farbe": "#06b6d4",
        "erzaehler_nacht": "Die Putzfrau wischt durch die leeren Häuser und sammelt wertvolle Informationen.",
        "erzaehler_tag": "Die Putzfrau hat beim Aufräumen etwas gefunden! Sie enthüllt die wahre Rolle des Toten: {rolle}!",
        "hinweis_config": None,
    },
    "Gerber": {
        "id": 92,
        "team": "solo",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Gerber. Du gewinnst wenn du gehängt wirst! Aber anders als der Selbstmörder - wenn du gewinnst, verlieren ALLE anderen!",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-face-angry",
        "farbe": "#78350f",
        "erzaehler_nacht": "Der Gerber arbeitet an seinen stinkenden Fellen. Ein verbitterter Mann mit einem düsteren Plan.",
        "erzaehler_tag": "ÜBERRASCHUNG! Der Gerber wurde gehängt und er lacht triumphierend! Sein Fluch verflucht das gesamte Dorf - ALLE verlieren außer ihm!",
        "hinweis_config": "Gerber",  # Kann sich selbst verdächtig machen
    },
    "Doppelgänger": {
        "id": 93,
        "team": "dorf",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Doppelgänger. In der ersten Nacht wählst du einen Spieler. Stirbt dieser, übernimmst du seine Rolle und sein Team!",
        "nacht_aktiv": True,
        "prioritaet": 4,
        "icon": "fa-solid fa-clone",
        "farbe": "#6366f1",
        "erzaehler_nacht": "Der Doppelgänger erwacht (erste Nacht) und wählt sein Ziel.",
        "erzaehler_tag": "Das Ziel des Doppelgängers ist tot! Er übernimmt dessen Rolle.",
    },
    "Henker": {
        "id": 94,
        "team": "solo",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Henker. Dir wird zu Beginn ein Ziel zugeteilt. Du gewinnst wenn dein Ziel vom Dorf gehängt wird! Danach wirst du Dorfbewohner.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-gavel",
        "farbe": "#4b5563",
        "erzaehler_nacht": "Der Henker erfährt sein Ziel: {ziel}",
        "erzaehler_tag": "Das Ziel des Henkers wurde gehängt! Der Henker hat gewonnen und wird zum Dorfbewohner.",
    },
    "Kleines Mädchen": {
        "id": 95,
        "team": "dorf",
        "kategorie": "sonstige",
        "beschreibung": "Du bist das Kleine Mädchen. Du darfst nachts blinzeln um die Werwölfe zu beobachten! Aber Vorsicht: Wirst du erwischt, stirbst du sofort!",
        "nacht_aktiv": True,
        "prioritaet": 50,
        "icon": "fa-solid fa-child-dress",
        "farbe": "#fbbf24",
        "erzaehler_nacht": "Das Kleine Mädchen darf während der Werwolf-Phase blinzeln - auf eigene Gefahr!",
        "erzaehler_tag": None,
    },
    "Dieb": {
        "id": 96,
        "team": "dorf",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Dieb. Zu Beginn siehst du zwei übrige Rollen und darfst dir eine aussuchen. Ist ein Werwolf dabei, musst du ihn wählen!",
        "nacht_aktiv": True,
        "prioritaet": 1,
        "icon": "fa-solid fa-mask",
        "farbe": "#1e293b",
        "erzaehler_nacht": "Der Dieb erwacht zuerst und sieht zwei Rollen. Er muss eine wählen.",
        "erzaehler_tag": None,
    },
    "Bürgermeister": {
        "id": 97,
        "team": "dorf",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Bürgermeister. Deine Stimme zählt doppelt! Bei deinem Tod bestimmst du deinen Nachfolger, der deine Macht erbt.",
        "nacht_aktiv": False,
        "prioritaet": 95,
        "icon": "fa-solid fa-user-tie",
        "farbe": "#1e40af",
        "erzaehler_nacht": "Der Bürgermeister ruht in seinem Rathaus. Seine Stimme hat doppeltes Gewicht.",
        "erzaehler_tag": "Der Bürgermeister ist gefallen! Mit letzter Kraft zeigt er auf seinen Nachfolger, der das Amt und die doppelte Stimme erbt!",
        "hinweis_config": None,
    },
    "Sündenbock": {
        "id": 98,
        "team": "dorf",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Sündenbock. Wenn es bei einer Abstimmung ein Unentschieden gibt, stirbst DU anstelle der anderen! Versuche das zu verhindern.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-person-falling",
        "farbe": "#a8a29e",
        "erzaehler_nacht": "Der Sündenbock ahnt, dass er heute vielleicht für die Unentschlossenheit anderer sterben wird.",
        "erzaehler_tag": "UNENTSCHIEDEN bei der Abstimmung! Das Dorf kann sich nicht einigen - also muss der Sündenbock sterben!",
        "hinweis_config": None,
    },
    "Engel": {
        "id": 99,
        "team": "solo",
        "kategorie": "sonstige",
        "beschreibung": "Du bist der Engel. Du gewinnst NUR wenn du in der ersten Runde (Tag oder Nacht) stirbst! Danach wirst du zum normalen Dorfbewohner.",
        "nacht_aktiv": False,
        "prioritaet": 100,
        "icon": "fa-solid fa-feather",
        "farbe": "#fef3c7",
        "erzaehler_nacht": "Der Engel wartet sehnsüchtig auf seinen frühen Tod, um in den Himmel aufzusteigen.",
        "erzaehler_tag": "Der Engel ist in der ersten Runde gestorben! Seine Flügel erstrahlen und er steigt siegreich in den Himmel auf!",
        "hinweis_config": "Engel",  # Kann sich verdächtig machen um schnell zu sterben
    },
}


# Spielphasen in korrekter Reihenfolge
PHASEN = [
    "lobby",
    "rollen_verteilt",
    "nacht_start",
    # Erste-Nacht-Phasen (nur Runde 1)
    "dieb_phase",
    "doppelgaenger_phase",
    "armor_phase",
    "priester_dunkel_phase",
    "wildes_kind_phase",
    "hund_phase",
    "schwestern_phase",
    "brueder_phase",
    "freimaurer_phase",
    "fluechtlinge_phase",
    "verliebte_info",
    # Reguläre Nacht-Phasen
    "sandmann_phase",
    "seherin_phase",
    "seherlehrling_phase",
    "aurenseherin_phase",
    "medium_phase",
    "tratschweib_phase",
    "paranormal_billig_phase",
    "werwolfseherin_phase",
    "heiler_phase",
    "leibwaechter_phase",
    "hure_phase",
    "prostituierte_phase",
    "nutte_phase",
    "werwolf_phase",
    "einsamerwolf_phase",
    "urwolf_phase",
    "weisser_wolf_phase",
    "mordlustiger_phase",
    "hexe_phase",
    "hexenmeister_phase",
    "giftmischerin_phase",
    "kraeuterweib_phase",
    "zauberer_phase",
    "zahnarzt_phase",
    "rabe_phase",
    "floetenspieler_phase",
    "vampir_phase",
    "zombie_phase",
    "pyromane_phase",
    "tonks_phase",
    "buddler_phase",
    "nacht_ende",
    # Tag-Phasen
    "tag_start",
    "baerenbaendiger_brummen",
    "demoskopin_info",
    "diskussion",
    "abstimmung",
    "abstimmung_ergebnis",
    "prinz_enthuellung",
    "jaeger_phase",
    "kamikaze_phase",
    "hahn_enthuellung",
    "putzfrau_info",
    "tag_ende",
    "spiel_ende",
]


# Rollen-Konfiguration nach Spielerzahl (Empfehlung)
# For games larger than defined here, use berechne_rollen() from game_logic.py
ROLLEN_EMPFEHLUNG = {
    5: ["Werwolf", "Werwolf", "Seherin", "Dorfbewohner", "Dorfbewohner"],
    6: ["Werwolf", "Werwolf", "Seherin", "Hexe", "Dorfbewohner", "Dorfbewohner"],
    7: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    8: [
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    9: [
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
    10: [
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
    11: [
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
    12: [
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
    13: [
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
    14: [
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
    15: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    16: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Prinz",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    17: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Urwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Prinz",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
    ],
    18: [
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Werwolf",
        "Urwolf",
        "Seherin",
        "Hexe",
        "Jaeger",
        "Amor",
        "Heiler",
        "Alter Mann",
        "Medium",
        "Rabe",
        "Prinz",
        "Floetenspieler",
        "Dorfbewohner",
        "Dorfbewohner",
        "Dorfbewohner",
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
    team_andere = 0  # Vampire, Zombie, etc.

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
        "werwolf_prozent": round(team_werwolf / total * 100, 1) if total > 0 else 0,
        "solo_prozent": round(team_solo / total * 100, 1) if total > 0 else 0,
        "andere_prozent": round(team_andere / total * 100, 1) if total > 0 else 0,
        "rollen": rollen,
        "balance_ratio": f"1:{round(team_dorf / team_werwolf, 1) if team_werwolf > 0 else 0}",
    }


# Teams und ihre Gewinnbedingungen
TEAMS = {
    "dorf": {
        "name": "Das Dorf",
        "beschreibung": "Eliminiert alle Werwölfe und andere Bedrohungen!",
        "farbe": "#3b82f6",
    },
    "werwolf": {
        "name": "Die Werwölfe",
        "beschreibung": "Bringt das Dorf in die Minderheit!",
        "farbe": "#dc2626",
    },
    "vampir": {
        "name": "Die Vampire",
        "beschreibung": "Verwandelt alle lebenden Spieler in Vampire!",
        "farbe": "#7c2d12",
    },
    "zombie": {
        "name": "Die Zombies",
        "beschreibung": "Infiziert alle Spieler und erreicht die Mehrheit!",
        "farbe": "#4ade80",
    },
    "solo": {
        "name": "Einzelspieler",
        "beschreibung": "Erreiche dein persönliches Ziel!",
        "farbe": "#6b7280",
    },
    "verliebte": {
        "name": "Die Verliebten",
        "beschreibung": "Überlebt gemeinsam bis zum Ende!",
        "farbe": "#ec4899",
    },
}


# Rollen nach Kategorie gruppiert (für UI)
def get_rollen_nach_kategorie():
    """Gibt alle Rollen gruppiert nach Kategorie zurück als dict[kategorie][rolle_name] = rolle_data"""
    kategorien = {}
    for rolle_name, rolle_data in ROLLEN.items():
        kat = rolle_data.get("kategorie", "sonstige")
        if kat not in kategorien:
            kategorien[kat] = {}
        kategorien[kat][rolle_name] = rolle_data

    return kategorien


# Rollen nach Kategorie als Liste (für rollen.html)
def get_rollen_nach_kategorie_liste():
    """Gibt alle Rollen gruppiert nach Kategorie zurück als Liste"""
    kategorien = {}
    for rolle_name, rolle_data in ROLLEN.items():
        kat = rolle_data.get("kategorie", "sonstige")
        if kat not in kategorien:
            kategorien[kat] = []
        kategorien[kat].append({"name": rolle_name, **rolle_data})

    # Sortiere nach ID innerhalb jeder Kategorie
    for kat in kategorien:
        kategorien[kat].sort(key=lambda x: x["id"])

    return kategorien


# Kategorienamen für UI (mit schönen deutschen Namen)
KATEGORIE_NAMEN = {
    "grundrollen": "Grundrollen",
    "dorfbewohner": "Dorfbewohner-Varianten",
    "werwolf": "Werwolf-Varianten",
    "seher": "Sehende Rollen",
    "hexe": "Hexen & Zauberer",
    "jaeger": "Jäger & Kämpfer",
    "heiler": "Heiler & Beschützer",
    "spezial": "Spezialrollen",
    "boese": "Böse Wesen",
    "sonstige": "Sonstige Rollen",
}


# Rollen-Anzahl
def get_rollen_anzahl():
    """Gibt die Anzahl aller verfügbaren Rollen zurück"""
    return len(ROLLEN)
