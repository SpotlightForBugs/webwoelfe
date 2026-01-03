# Webwölfe

**Das klassische Werwolf-Partyspiel - jetzt digital!**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

Webwölfe ist eine moderne, webbasierte Implementation des beliebten Gesellschaftsspiels "Werwolf" (auch bekannt als "Mafia" oder "Werwölfe von Düsterwald"). Spiele mit deinen Freunden - egal ob im selben Raum oder über das Internet verteilt!

## Features

- **Zwei Spielmodi**: 
  - Online (jeder auf eigenem Gerät mit 3D-Dorf, automatischer Erzähler) 
  - Gruppen-Modus (alle zusammen vor Ort, mit Erzähler-Unterstützung)
- **Sitzordnung per Drag & Drop**: Spieler können ihre physische Sitzordnung im Kreis festlegen - wichtig für Nachbar-Mechaniken!
- **3D-Dorfvisualisierung**: Interaktives 3D-Dorf zeigt alle Spieler im Kreis
- **Echtzeit-Updates**: WebSocket-basierte Kommunikation für nahtloses Gameplay
- **45+ Rollen**: Von Grundrollen bis Community-Kreationen ([Quelle](https://werwolf.fandom.com/de/wiki/Werwolf-Rollen-Sammlung))
- **Anti-Cheat**: Schutz gegen DevTools/F12-Spicken
- **Responsive Design**: Funktioniert auf Desktop und Mobilgeräten
- **Atmosphärisches Design**: Dunkles Theme mit stimmungsvoller Gestaltung
- **Erzähler-Texte**: Vorgefertigte Texte für den Gruppen-Modus

## Verfügbare Rollen

### Grundrollen
- **Werwolf** - Töte jede Nacht einen Dorfbewohner
- **Dorfbewohner** - Finde und eliminiere die Werwölfe
- **Seherin** - Erfahre die wahre Identität eines Spielers
- **Hexe** - Heiltrank & Gifttrank (je einmal nutzbar)
- **Jäger** - Nimm jemanden mit in den Tod
- **Heiler** - Schütze einen Spieler pro Nacht
- **Amor** - Verliebe zwei Spieler

### Erweiterte Rollen
- **Weißer Wolf** - Gewinnt alleine, kann Mitwölfe töten
- **Urwolf** - Kann Dorfbewohner infizieren
- **Alter Mann** - Überlebt ersten Wolfsangriff
- **Zwei Schwestern** - Kennen sich gegenseitig
- **Vampir** - Verwandle Spieler in Vampire
- **Flötenspieler** - Verzaubere alle zum Sieg
- ... und viele mehr!

## Installation

### Voraussetzungen
- Python 3.10 oder höher
- pip

### Schritte

```bash
# Repository klonen
git clone https://github.com/SpotlightForBugs/webwoelfe.git
cd webwoelfe

# Virtuelle Umgebung erstellen (empfohlen)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python app.py
```

### Optionale Erzähler-Stimme über ElevenLabs

Wenn du die natürlich klingende ElevenLabs-Stimme nutzen möchtest, setze folgende Umgebungsvariablen:

- `ENABLE_ELEVENLABS=true`
- `ELEVENLABS_API_KEY=<dein API Key>`
- `ELEVENLABS_VOICE_ID=g1jpii0iyvtRs8fqXsd1` (Standardstimme aus dem Beispiel)

Alle erzeugten Audios werden im lokalen Cache (`static/audio/cache`) abgelegt, damit Ansagen nicht erneut generiert werden müssen.

Die Anwendung läuft dann unter `http://localhost:5001`

## Spielablauf

1. **Raum erstellen**: Ein Spieler erstellt einen Raum und erhält einen 6-stelligen Code
2. **Beitreten**: Andere Spieler treten mit dem Code bei
3. **Spiel starten**: Bei mindestens 5 Spielern kann das Spiel gestartet werden
4. **Rollen erhalten**: Jeder Spieler bekommt eine geheime Rolle zugeteilt
5. **Tag & Nacht**: Das Spiel wechselt zwischen Tag- und Nachtphasen
6. **Gewinnen**: Dorf gewinnt wenn alle Wölfe tot sind, Wölfe gewinnen bei Mehrheit

## Spielmodi

### Online-Modus
- Jeder Spieler auf eigenem Gerät
- **Kein Erzähler nötig** - das Spiel erzählt automatisch
- Automatische Nachrichten und Anweisungen
- Perfekt für Remote-Spielrunden

### Gruppen-Modus
- Alle zusammen vor Ort
- Mit menschlichem Erzähler
- **Erzähler erhält vorgefertigte Texte** zum Vorlesen
- Klassisches Spielerlebnis
- Perfekt für Partys und Spieleabende

## Technologie-Stack

- **Backend**: Python/Flask mit Flask-SocketIO
- **Datenbank**: SQLite mit SQLAlchemy ORM
- **Frontend**: Vanilla JS, CSS3, HTML5
- **Echtzeit**: WebSockets via Socket.IO
- **Icons**: FontAwesome 6
- **Fonts**: Cinzel & Crimson Pro (Google Fonts)

## Projektstruktur

```
webwoelfe/
|-- app.py              # Flask-Anwendung & WebSocket-Events
|-- models.py           # SQLAlchemy-Modelle & Rollen-Definitionen
|-- game_logic.py       # Spiellogik (Phasen, Abstimmungen, etc.)
|-- requirements.txt    # Python-Abhängigkeiten
|-- templates/          # Jinja2-Templates
|   |-- struktur.html   # Basis-Template mit Anti-Cheat
|   |-- index.html      # Startseite
|   |-- lobby.html      # Warteraum
|   |-- spiel.html      # Hauptspiel-Interface
|   +-- rollen.html     # Rollenübersicht
|-- static/
|   +-- images/         # Favicon & Grafiken
+-- instance/
    +-- webwoelfe.db    # SQLite-Datenbank
```

## Sicherheit

Webwölfe enthält Schutzmaßnahmen gegen Spicken:
- DevTools-Erkennung (F12, Ctrl+Shift+I, etc.)
- Rechtsklick deaktiviert
- Console-Logging deaktiviert
- Sensible Spielerinformationen werden serverseitig validiert

## Beitragen

Beiträge sind willkommen! Bitte lies [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

## Lizenz

Dieses Projekt steht unter der GNU General Public License v3.0 - siehe [LICENSE](LICENSE) für Details.

## Autoren

- [@SpotlightForBugs](https://www.github.com/SpotlightForBugs)
- [@Heizkoerper](https://www.github.com/Heizkoerper)
- [@BlackTesseract](https://www.github.com/BlackTesseract)
- @Zora

---

*Inspiriert von "Werwölfe von Düsterwald" und der [Werwolf Wiki Rollen-Sammlung](https://werwolf.fandom.com/de/wiki/Werwolf-Rollen-Sammlung)*
