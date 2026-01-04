"""
Audio-System für Webwölfe
Verwendet edge-tts für Text-to-Speech
Erzeugt Erzähler-Audio für Online-Modus
"""

import asyncio
import edge_tts
import os
import hashlib
import threading
from pathlib import Path
import requests

# Ordner für Audio-Cache
AUDIO_CACHE_DIR = Path("static/audio/cache")
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Lock und Tracking für gleichzeitige Audio-Generierung (verhindert Race Conditions)
_audio_generation_lock = threading.Lock()
_audio_in_progress: dict[str, threading.Event] = {}

ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "g1jpii0iyvtRs8fqXsd1")
ELEVENLABS_MODEL = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ENABLE_ELEVENLABS = os.environ.get("ENABLE_ELEVENLABS", "false").lower() == "true"

# Deutsche Stimmen für edge-tts
STIMMEN = {
    "maennlich": "de-DE-ConradNeural",  # Männliche deutsche Stimme
    "weiblich": "de-DE-KatjaNeural",  # Weibliche deutsche Stimme
    "dramatisch": "de-DE-ConradNeural",  # Für dramatische Momente
    "fluestern": "de-DE-KatjaNeural",  # Für Flüster-Effekte
}

# Standard-Stimme für Erzähler
DEFAULT_VOICE = "de-DE-ConradNeural"

# Audio-Einstellungen pro Kontext
AUDIO_EINSTELLUNGEN = {
    "normal": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "dramatisch": {
        "rate": "-10%",
        "pitch": "-5Hz",
        "volume": "+10%",
    },
    "fluestern": {
        "rate": "-20%",
        "pitch": "+5Hz",
        "volume": "-30%",
    },
    "aufgeregt": {
        "rate": "+15%",
        "pitch": "+10Hz",
        "volume": "+5%",
    },
    "langsam": {
        "rate": "-25%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
}


def generiere_audio_hash(text: str, stimme: str, stil: str) -> str:
    """Generiert einen eindeutigen Hash für Audio-Caching."""
    content = f"{text}_{stimme}_{stil}"
    return hashlib.md5(content.encode()).hexdigest()


def elevenlabs_aktiv() -> bool:
    """Prüft, ob ElevenLabs aktiviert und konfiguriert ist."""
    return ENABLE_ELEVENLABS and bool(ELEVENLABS_API_KEY)


def text_zu_audio_elevenlabs(
    text: str,
    stimme: str | None = None,
    stil: str = "normal",
    force_regenerate: bool = False,
) -> str | None:
    """
    ElevenLabs Text-to-Speech mit Caching und Lock gegen Race Conditions.

    Returns None, falls ElevenLabs nicht aktiviert oder nicht konfiguriert ist.
    """
    if not elevenlabs_aktiv():
        print("[ELEVENLABS] Nicht aktiviert oder kein API-Key")
        return None

    voice_id = stimme or ELEVENLABS_VOICE_ID
    audio_hash = generiere_audio_hash(text, f"11_{voice_id}", stil)
    cache_key = f"11_{audio_hash}"
    audio_datei = AUDIO_CACHE_DIR / f"{cache_key}.mp3"

    # Schneller Check ohne Lock - wenn Datei existiert, sofort zurückgeben
    if audio_datei.exists() and not force_regenerate:
        print(f"[ELEVENLABS] Cache-Hit: {audio_datei}")
        return str(audio_datei)

    # Lock-basierte Synchronisation für gleichzeitige Anfragen
    with _audio_generation_lock:
        # Prüfe erneut nach Lock-Erwerb (könnte inzwischen generiert worden sein)
        if audio_datei.exists() and not force_regenerate:
            print(f"[ELEVENLABS] Cache-Hit (nach Lock): {audio_datei}")
            return str(audio_datei)

        # Prüfe ob bereits eine Generierung für diesen Key läuft
        if cache_key in _audio_in_progress:
            wait_event = _audio_in_progress[cache_key]
            print(f"[ELEVENLABS] Warte auf laufende Generierung: {cache_key[:20]}...")
        else:
            # Markiere als "in Bearbeitung"
            wait_event = threading.Event()
            _audio_in_progress[cache_key] = wait_event
            wait_event = None  # Wir sind der Generator

    # Falls wir warten müssen (anderer Thread generiert gerade)
    if wait_event is not None:
        wait_event.wait(timeout=60)  # Max 60 Sekunden warten
        if audio_datei.exists():
            print(f"[ELEVENLABS] Cache-Hit (nach Warten): {audio_datei}")
            return str(audio_datei)
        # Andere Generierung fehlgeschlagen, wir geben None zurück
        print(f"[ELEVENLABS] Andere Generierung fehlgeschlagen")
        return None

    # Wir sind verantwortlich für die Generierung
    response = None
    try:
        print(f"[ELEVENLABS] Generiere Audio für: {text[:50]}...")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Accept": "audio/mpeg"}
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.9,
                "style": 0.55 if stil == "dramatisch" else 0.25,
                "use_speaker_boost": True,
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        audio_datei.write_bytes(response.content)
        print(f"[ELEVENLABS] Gespeichert: {audio_datei}")
        return str(audio_datei)
    except requests.exceptions.HTTPError as e:
        if response is not None and response.status_code == 429:
            print(f"[ELEVENLABS] Rate-Limit erreicht! Fallback zu edge-tts...")
        elif response is not None:
            print(f"[ELEVENLABS] HTTP-Fehler {response.status_code}: {e}")
        else:
            print(f"[ELEVENLABS] HTTP-Fehler: {e}")
        return None
    except (requests.RequestException, IOError) as e:
        print(f"[ELEVENLABS] API-Fehler: {e}")
        return None
    finally:
        # Entferne aus in_progress und signalisiere wartenden Threads
        with _audio_generation_lock:
            if cache_key in _audio_in_progress:
                _audio_in_progress[cache_key].set()  # Signal an wartende Threads
                del _audio_in_progress[cache_key]


def text_zu_audio_elevenlabs_sync(
    text: str,
    stimme: str | None = None,
    stil: str = "normal",
    force_regenerate: bool = False,
) -> str | None:
    """Synchroner Wrapper für die ElevenLabs API."""
    return text_zu_audio_elevenlabs(
        text, stimme=stimme, stil=stil, force_regenerate=force_regenerate
    )


async def text_zu_audio(
    text: str,
    stimme: str = DEFAULT_VOICE,
    stil: str = "normal",
    force_regenerate: bool = False,
) -> str:
    """
    Wandelt Text in Audio um und gibt den Dateipfad zurück.
    Bevorzugt ElevenLabs über EdgeTTS (auch über gecachtes EdgeTTS).

    Args:
        text: Der zu sprechende Text
        stimme: Die edge-tts Stimme (de-DE-ConradNeural, de-DE-KatjaNeural)
        stil: Der Sprechstil (normal, dramatisch, fluestern, aufgeregt, langsam)
        force_regenerate: Wenn True, wird auch gecachtes Audio neu generiert

    Returns:
        Relativer Pfad zur Audio-Datei
    """
    # Generiere Hash für Caching (EdgeTTS)
    audio_hash = generiere_audio_hash(text, stimme, stil)
    audio_datei = AUDIO_CACHE_DIR / f"{audio_hash}.mp3"

    # ElevenLabs verwendet eigenen Cache mit "11_" Prefix
    elevenlabs_hash = generiere_audio_hash(text, f"11_{ELEVENLABS_VOICE_ID}", stil)
    elevenlabs_datei = AUDIO_CACHE_DIR / f"11_{elevenlabs_hash}.mp3"

    # 1. Wenn ElevenLabs aktiv ist, bevorzuge ElevenLabs (auch über gecachtes EdgeTTS)
    if elevenlabs_aktiv():
        # Prüfe ob ElevenLabs-Cache existiert
        if elevenlabs_datei.exists() and not force_regenerate:
            print(f"[ELEVENLABS] Cache-Hit: {elevenlabs_datei}")
            return str(elevenlabs_datei)

        # Versuche ElevenLabs zu generieren
        result = text_zu_audio_elevenlabs(
            text, stil=stil, force_regenerate=force_regenerate
        )
        if result:
            return result

        # ElevenLabs fehlgeschlagen, Fallback zu EdgeTTS unten
        print("[ELEVENLABS] Fehlgeschlagen, Fallback zu EdgeTTS...")

    # 2. Prüfe ob EdgeTTS bereits gecacht
    if audio_datei.exists() and not force_regenerate:
        print(f"[EDGE-TTS] Cache-Hit: {audio_datei}")
        return str(audio_datei)

    # 3. Generiere mit EdgeTTS
    print(f"[EDGE-TTS] Generiere Audio für: {text[:50]}...")

    # Hole Einstellungen für den Stil
    einstellungen = AUDIO_EINSTELLUNGEN.get(stil, AUDIO_EINSTELLUNGEN["normal"])

    try:
        # Erstelle TTS-Kommunikation
        communicate = edge_tts.Communicate(
            text=text,
            voice=stimme,
            rate=einstellungen["rate"],
            pitch=einstellungen["pitch"],
            volume=einstellungen["volume"],
        )

        # Speichere Audio
        await communicate.save(str(audio_datei))
        print(f"[EDGE-TTS] Gespeichert: {audio_datei}")
    except Exception as e:
        print(f"[EDGE-TTS] Fehler: {e}")

    return str(audio_datei)


def text_zu_audio_sync(
    text: str,
    stimme: str = DEFAULT_VOICE,
    stil: str = "normal",
    force_regenerate: bool = False,
) -> str:
    """Synchrone Wrapper-Funktion für text_zu_audio."""
    return asyncio.run(text_zu_audio(text, stimme, stil, force_regenerate))


async def generiere_phasen_audio():
    """Generiert alle Standard-Phasen-Audio-Dateien vorab."""
    from models import PHASEN_TEXTE

    print("Generiere Phasen-Audio...")

    for phase_id, phase_info in PHASEN_TEXTE.items():
        text = phase_info.get("text", "")
        if text:
            # Bestimme Stil basierend auf Phase
            stil = "normal"
            if "werwolf" in phase_id.lower():
                stil = "dramatisch"
            elif "tot" in text.lower() or "stirbt" in text.lower():
                stil = "dramatisch"
            elif "schläft" in text.lower():
                stil = "langsam"

            datei = await text_zu_audio(text, stil=stil)
            print(f"  {phase_id}: {datei}")

    print("Fertig!")


async def generiere_rollen_audio():
    """Generiert Erzähler-Audio für alle Rollen."""
    from roles import RoleRegistry

    print("Generiere Rollen-Audio...")

    for rolle in RoleRegistry.get_all():
        rolle_dict = rolle.to_dict()
        rolle_name = rolle.info.name

        # Nacht-Text
        nacht_text = rolle_dict.get("erzaehler_nacht")
        if nacht_text:
            datei = await text_zu_audio(nacht_text, stil="langsam")
            print(f"  {rolle_name} (Nacht): {datei}")

        # Tag-Text
        tag_text = rolle_dict.get("erzaehler_tag")
        if tag_text and "{" not in tag_text:  # Nur statische Texte
            datei = await text_zu_audio(tag_text, stil="normal")
            print(f"  {rolle_name} (Tag): {datei}")

    print("Fertig!")


async def dynamischer_text_zu_audio(
    template: str, variablen: dict, stil: str = "normal"
) -> str:
    """
    Generiert Audio für dynamische Texte mit Variablen.

    Args:
        template: Text-Template mit {variablen}
        variablen: Dictionary mit Variablen-Werten
        stil: Sprechstil

    Returns:
        Pfad zur Audio-Datei
    """
    # Ersetze Variablen im Template
    text = template.format(**variablen)

    # Generiere Audio (wird gecacht wenn gleicher Text)
    return await text_zu_audio(text, stil=stil)


# Hinweis-Audio-Effekte
HINWEIS_AUDIO = {
    "heulen_fern": {
        "beschreibung": "Fernes Wolfsheulen",
        "datei": "distant_howl.mp3",
    },
    "kratzen": {
        "beschreibung": "Kratzendes Geräusch",
        "datei": "scratch.mp3",
    },
    "herzschlag": {
        "beschreibung": "Schneller Herzschlag",
        "datei": "heartbeat_fast.mp3",
    },
    "fluestern": {
        "beschreibung": "Unverständliches Flüstern",
        "datei": "whisper.mp3",
    },
    "stolpern": {
        "beschreibung": "Stolper-Geräusch",
        "datei": "stumble.mp3",
    },
    "kichern": {
        "beschreibung": "Böses Kichern",
        "datei": "evil_chuckle.mp3",
    },
    "schatten": {
        "beschreibung": "Schatten-Swoosh",
        "datei": "shadow_swoosh.mp3",
    },
    "verdaechtig": {
        "beschreibung": "Verdächtiges Geräusch",
        "datei": "suspicious.mp3",
    },
}


async def generiere_hinweis_audio_mit_tts():
    """
    Generiert Hinweis-Audio mit TTS falls nicht vorhanden.
    Für einfache Geräusche verwenden wir kurze gesprochene Texte.
    """
    texte = {
        "distant_howl": "Auuuuuu...",
        "scratch": "*kratz kratz*",
        "heartbeat_fast": "Bum bum bum bum",
        "whisper": "*psst psst*",
        "stumble": "*stolper*",
        "evil_chuckle": "He he he...",
        "shadow_swoosh": "*wusch*",
        "suspicious": "Hmm...",
    }

    audio_dir = Path("static/audio/hints")
    audio_dir.mkdir(parents=True, exist_ok=True)

    for name, text in texte.items():
        datei = audio_dir / f"{name}.mp3"
        if not datei.exists():
            communicate = edge_tts.Communicate(
                text=text, voice="de-DE-KatjaNeural", rate="-20%", volume="-10%"
            )
            await communicate.save(str(datei))
            print(f"  Hinweis-Audio erstellt: {name}")


async def generiere_erzaehler_audio_cache():
    """
    Pre-generiert alle Erzähler-Audio-Dateien für den Online-Modus.
    Sollte beim Server-Start oder manuell ausgeführt werden.
    """
    from models import ERZAEHLER_PHASEN, ERZAEHLER_EVENTS

    print("=" * 60)
    print("Generiere Erzähler-Audio-Cache...")
    print("=" * 60)

    alle_texte = []

    # Sammle alle Phasen-Texte
    for phase_id, phase_info in ERZAEHLER_PHASEN.items():
        text = phase_info.get("text", "")
        if text:
            stil = "dramatisch" if "werwolf" in phase_id.lower() else "normal"
            alle_texte.append((phase_id, text, stil))

    # Sammle alle Event-Texte
    for event_id, event_info in ERZAEHLER_EVENTS.items():
        text = event_info.get("text", "")
        if text and "{" not in text:  # Nur statische Texte
            stil = (
                "dramatisch"
                if "werwolf" in event_id.lower() or "tot" in text.lower()
                else "normal"
            )
            alle_texte.append((event_id, text, stil))

    print(f"Gefunden: {len(alle_texte)} Texte zu generieren")

    generated = 0
    cached = 0

    for name, text, stil in alle_texte:
        audio_hash = generiere_audio_hash(text, DEFAULT_VOICE, stil)
        audio_datei = AUDIO_CACHE_DIR / f"{audio_hash}.mp3"

        if audio_datei.exists():
            cached += 1
            continue

        try:
            # Versuche ElevenLabs wenn aktiv
            if elevenlabs_aktiv():
                result = text_zu_audio_elevenlabs(text, stil=stil)
                if result:
                    generated += 1
                    print(f"  ✓ {name} (ElevenLabs)")
                    continue

            # Fallback zu edge-tts
            await text_zu_audio(text, stil=stil)
            generated += 1
            print(f"  ✓ {name} (edge-tts)")
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    print("-" * 60)
    print(f"Fertig! Generiert: {generated}, Bereits gecacht: {cached}")
    print("=" * 60)


def generiere_erzaehler_audio_cache_sync():
    """Synchroner Wrapper für generiere_erzaehler_audio_cache."""
    asyncio.run(generiere_erzaehler_audio_cache())


# CLI für Audio-Generierung
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        befehl = sys.argv[1]

        if befehl == "phasen":
            asyncio.run(generiere_phasen_audio())
        elif befehl == "rollen":
            asyncio.run(generiere_rollen_audio())
        elif befehl == "hinweise":
            asyncio.run(generiere_hinweis_audio_mit_tts())
        elif befehl == "erzaehler":
            asyncio.run(generiere_erzaehler_audio_cache())
        elif befehl == "alle":
            asyncio.run(generiere_erzaehler_audio_cache())
            asyncio.run(generiere_phasen_audio())
            asyncio.run(generiere_rollen_audio())
            asyncio.run(generiere_hinweis_audio_mit_tts())
        elif befehl == "test":
            # Test mit einem Text
            test_text = "Das Dorf schläft ein. Alle Spieler schließen die Augen."
            datei = text_zu_audio_sync(test_text, stil="langsam")
            print(f"Test-Audio erstellt: {datei}")
        else:
            print(f"Unbekannter Befehl: {befehl}")
            print("Verfügbare Befehle: phasen, rollen, hinweise, erzaehler, alle, test")
    else:
        print("Webwölfe Audio-Generator")
        print("Usage: python audio.py [phasen|rollen|hinweise|erzaehler|alle|test]")
