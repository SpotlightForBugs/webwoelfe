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
    )  # 'online' oder 'gruppe'
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
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

    # Herrchen (für Hund)
    herrchen_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=True)

    # Hund hat sein Herrchen bereits gewählt
    hund_herrchen_gewaehlt = db.Column(db.Boolean, default=False)

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


class SeherinEnthuellung(db.Model):
    """
    Snapshot der Seherin-Enthüllungen.
    
    Speichert was die Seherin ZUM ZEITPUNKT der Enthüllung gesehen hat.
    Auch wenn sich die Rolle später ändert (z.B. durch Infektion),
    bleibt die ursprüngliche Enthüllung erhalten.
    """
    __tablename__ = "seherin_enthuellung"
    
    id = db.Column(db.Integer, primary_key=True)
    raum_id = db.Column(db.Integer, db.ForeignKey("raeume.id"), nullable=False, index=True)
    seherin_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=False, index=True)
    ziel_id = db.Column(db.Integer, db.ForeignKey("spieler.id"), nullable=False)
    
    # Snapshot zum Zeitpunkt der Enthüllung
    enthuellung_typ = db.Column(db.String(20), nullable=False)  # 'gut', 'boese', 'neutral'
    gesehene_rolle = db.Column(db.String(50), nullable=True)  # Die Rolle die gesehen wurde
    runde = db.Column(db.Integer, nullable=False)  # In welcher Runde enthüllt
    enthuellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def speichere_enthuellung(seherin_id: int, ziel_id: int, raum_id: int, 
                              enthuellung_typ: str, rolle: str, runde: int):
        """Speichert eine neue Enthüllung als Snapshot"""
        # Prüfe ob bereits enthüllt
        bestehend = SeherinEnthuellung.query.filter_by(
            seherin_id=seherin_id,
            ziel_id=ziel_id,
            raum_id=raum_id
        ).first()
        
        if bestehend:
            # Bereits enthüllt - keine Änderung
            return bestehend
        
        enthuellung = SeherinEnthuellung(
            raum_id=raum_id,
            seherin_id=seherin_id,
            ziel_id=ziel_id,
            enthuellung_typ=enthuellung_typ,
            gesehene_rolle=rolle,
            runde=runde
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
        enthüllungen = SeherinEnthuellung.query.filter_by(
            seherin_id=seherin_id,
            raum_id=raum_id
        ).all()
        
        return {
            e.ziel_id: {
                'typ': e.enthuellung_typ,
                'rolle': e.gesehene_rolle,
                'runde': e.runde
            }
            for e in enthüllungen
        }
    
    # Relationships mit expliziten foreign_keys
    seherin = db.relationship("Spieler", foreign_keys=[seherin_id], backref="enthüllungen_als_seherin")
    ziel = db.relationship("Spieler", foreign_keys=[ziel_id], backref="enthüllungen_als_ziel")


# ============================================================================
# ERZÄHLER-TEXTE FÜR GRUPPEN-MODUS
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
    "hund_herrchen": {
        "text": "Der Hund erwacht. Er wählt sein Herrchen. Stirbt sein Herrchen, wird der Hund zum Werwolf!",
        "anweisung": "Der Hund öffnet die Augen und zeigt auf sein Herrchen. Merke dir diese Wahl.",
        "bedingung": {"runde": 1, "rolle_aktiv": "Hund"},
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
    "hund_verwandelt": {
        "text": "Das Herrchen des Hundes ist gestorben! Der treue Hund verwandelt sich vor Trauer in einen Werwolf!",
        "anweisung": "Der Hund wird in der nächsten Nacht mit den Werwölfen aufwachen.",
        "bedingung": {"trigger": "herrchen_stirbt"},
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
# Um eine neue Rolle hinzuzufuegen: Einfach eine .py-Datei in roles/ erstellen!
# ============================================================================


def _erstelle_rollen_dict():
    """
    Erstellt das ROLLEN-Dict dynamisch aus dem modularen System (roles/*.py).

    Neue Rollen einfach als .py-Datei in roles/ hinzufuegen - sie werden
    automatisch erkannt und registriert!
    """
    try:
        from roles import get_alle_rollen

        return get_alle_rollen()
    except Exception as e:
        print(f"[ROLLEN] Fehler beim Laden: {e}")
        return {}


# Das eigentliche ROLLEN-Dict (wird beim Import erstellt)
ROLLEN = _erstelle_rollen_dict()


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


# ============================================================================
# HELFER-FUNKTIONEN FUER ROLLEN
# Diese Funktionen nutzen das dynamische ROLLEN-Dict
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
    Sortiert nach ID innerhalb jeder Kategorie.
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


# Kategorienamen fuer UI (mit schoenen deutschen Namen)
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
    """Gibt die Anzahl aller verfuegbaren Rollen zurueck."""
    return len(_erstelle_rollen_dict())
