"""
Grundrollen Paket.

Enthält die Basis-Rollen des Spiels:
- Dorfbewohner
- Werwolf
- Seherin
- Hexe
- Jäger
- Heiler
- Amor
"""

from .dorfbewohner import Dorfbewohner
from .werwolf import Werwolf
from .seherin import Seherin
from .hexe import Hexe
from .jaeger import Jaeger
from .heiler import Heiler
from .amor import Amor

__all__ = [
    "Dorfbewohner",
    "Werwolf",
    "Seherin",
    "Hexe",
    "Jaeger",
    "Heiler",
    "Amor",
]
