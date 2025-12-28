"""
Audio-System für Webwölfe
Verwendet edge-tts für Text-to-Speech
Erzeugt Erzähler-Audio für Online-Modus
"""

import asyncio
import edge_tts
import os
import hashlib
from pathlib import Path

# Ordner für Audio-Cache
AUDIO_CACHE_DIR = Path("static/audio/cache")
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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


async def text_zu_audio(
    text: str,
    stimme: str = DEFAULT_VOICE,
    stil: str = "normal",
    force_regenerate: bool = False,
) -> str:
    """
    Wandelt Text in Audio um und gibt den Dateipfad zurück.

    Args:
        text: Der zu sprechende Text
        stimme: Die edge-tts Stimme (de-DE-ConradNeural, de-DE-KatjaNeural)
        stil: Der Sprechstil (normal, dramatisch, fluestern, aufgeregt, langsam)
        force_regenerate: Wenn True, wird auch gecachtes Audio neu generiert

    Returns:
        Relativer Pfad zur Audio-Datei
    """
    # Generiere Hash für Caching
    audio_hash = generiere_audio_hash(text, stimme, stil)
    audio_datei = AUDIO_CACHE_DIR / f"{audio_hash}.mp3"

    # Prüfe ob bereits gecacht
    if audio_datei.exists() and not force_regenerate:
        return str(audio_datei)

    # Hole Einstellungen für den Stil
    einstellungen = AUDIO_EINSTELLUNGEN.get(stil, AUDIO_EINSTELLUNGEN["normal"])

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
    from models import ROLLEN

    print("Generiere Rollen-Audio...")

    for rolle_name, rolle_info in ROLLEN.items():
        # Nacht-Text
        nacht_text = rolle_info.get("erzaehler_nacht")
        if nacht_text:
            datei = await text_zu_audio(nacht_text, stil="langsam")
            print(f"  {rolle_name} (Nacht): {datei}")

        # Tag-Text
        tag_text = rolle_info.get("erzaehler_tag")
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
        elif befehl == "alle":
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
            print("Verfügbare Befehle: phasen, rollen, hinweise, alle, test")
    else:
        print("Webwölfe Audio-Generator")
        print("Usage: python audio.py [phasen|rollen|hinweise|alle|test]")
