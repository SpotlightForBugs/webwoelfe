# Hint Audio Files

This directory contains audio files for the hint system in online multiplayer mode.

## Audio Files

The following audio files are used for hints:

- `shadow_swoosh.mp3` - Schatten-Swoosh Geräusch
- `distant_howl.mp3` - Fernes Wolfsheulen
- `scratch.mp3` - Kratzgeräusch
- `heartbeat_fast.mp3` - Schneller Herzschlag
- `whisper.mp3` - Unverständliches Flüstern
- `suspicious.mp3` - Verdächtiges Geräusch
- `stumble.mp3` - Stolper-Geräusch
- `evil_chuckle.mp3` - Böses Kichern

## Automatic TTS Fallback

If audio files are not present, the system automatically generates them using Text-to-Speech (TTS) via `edge-tts`.

The TTS fallback uses the hint description to generate spoken audio.

## Generating Audio Files

To pre-generate all hint audio files, run:

```bash
python3 audio.py hinweise
```

This requires the `edge-tts` package to be installed:

```bash
pip install edge-tts
```

## Custom Audio Files

You can replace the TTS-generated files with custom sound effects by placing your own `.mp3` files in this directory with the same filenames.

Custom audio files will be used instead of TTS if they exist.
