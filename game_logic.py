"""
Spiellogik fuer das Werwolf-Spiel
"""

import random
from typing import Optional, List, Tuple
from models import db, Raum, Spieler, SpielAktion, SpielLog, ROLLEN
from phases import get_phase_list, is_nacht_phase, get_next_phase, Phase
import json
from datetime import datetime, timedelta

# Get PHASEN from centralized module
PHASEN = get_phase_list()


def berechne_rollen(spieler_anzahl: int, mit_erzaehler: bool = False) -> dict:
    """
    Berechnet die Rollenverteilung basierend auf der Spieleranzahl.

    Balanced for games from 5 to 1000+ players.

    Balance ratios (based on research):
    - Werewolves: ~20-22% of players (1 wolf per 4-5 villagers)
    - Special village roles: Scale with player count
    - Wolves:Villagers:Specials ratio around 1:2:1 to 1:3:1
    - Solo/neutral roles added sparingly in larger games

    Args:
        spieler_anzahl: Anzahl der Spieler
        mit_erzaehler: Ob ein Erzaehler dabei ist

    Returns:
        Dictionary mit Rollen und deren Anzahl
    """
    effektive_anzahl = spieler_anzahl - (1 if mit_erzaehler else 0)

    if effektive_anzahl < 5:
        effektive_anzahl = 5  # Minimum players

    rollen = {}

    if mit_erzaehler:
        rollen["Erzaehler"] = 1

    # ========================================================================
    # WEREWOLF TEAM CALCULATION (Target: ~20-25% of players)
    # ========================================================================
    # Base werewolf count: 1 per 4 players (minimum 2 for games 6+)
    # For large games, slightly lower ratio to balance voting power
    if effektive_anzahl <= 5:
        werwolf_basis = 1
    elif effektive_anzahl <= 10:
        # Bei 6-10 Spielern: mindestens 2 Werwölfe
        werwolf_basis = max(2, (effektive_anzahl + 2) // 4)
    elif effektive_anzahl <= 50:
        werwolf_basis = max(2, effektive_anzahl // 4)
    elif effektive_anzahl <= 200:
        # For medium-large games: ~18-20% wolves
        werwolf_basis = max(5, int(effektive_anzahl * 0.20))
    else:
        # For massive games (500+): ~15-18% wolves (voting power is strong)
        werwolf_basis = max(20, int(effektive_anzahl * 0.17))

    # Add werewolf variants for large games
    rollen["Werwolf"] = werwolf_basis

    # Special werewolf roles (scale with game size)
    if effektive_anzahl >= 13:
        rollen["Weißer Wolf"] = max(1, effektive_anzahl // 100)  # Solo wolf
    if effektive_anzahl >= 17:
        rollen["Urwolf"] = max(1, effektive_anzahl // 150)
    if effektive_anzahl >= 25:
        rollen["Wolfsjunge"] = max(1, effektive_anzahl // 200)
    if effektive_anzahl >= 100:
        rollen["Wolf im Schafspelz"] = max(1, effektive_anzahl // 150)
    if effektive_anzahl >= 200:
        rollen["Werwolfseherin"] = max(1, effektive_anzahl // 250)
    if effektive_anzahl >= 300:
        rollen["Einsamer Wolf"] = max(1, effektive_anzahl // 400)

    # ========================================================================
    # VILLAGE SPECIAL ROLES (Scale to provide balance)
    # ========================================================================
    # Information roles (critical for village success in large games)
    if effektive_anzahl >= 5:
        rollen["Seherin"] = max(1, effektive_anzahl // 50)  # 1 per 50 players
    if effektive_anzahl >= 6:
        rollen["Hexe"] = max(1, effektive_anzahl // 75)  # Heals + kills
    if effektive_anzahl >= 8:
        rollen["Amor"] = max(1, effektive_anzahl // 150)
    if effektive_anzahl >= 10:
        rollen["Jäger"] = max(1, effektive_anzahl // 60)  # Death trigger
    if effektive_anzahl >= 12:
        rollen["Heiler"] = max(1, effektive_anzahl // 80)  # Protection

    # More advanced roles for larger games
    if effektive_anzahl >= 15:
        rollen["Alter Mann"] = max(1, effektive_anzahl // 100)
    if effektive_anzahl >= 18:
        rollen["Medium"] = max(1, effektive_anzahl // 100)
    if effektive_anzahl >= 20:
        rollen["Rabe"] = max(1, effektive_anzahl // 120)
    if effektive_anzahl >= 25:
        rollen["Prinz"] = max(1, effektive_anzahl // 150)
    if effektive_anzahl >= 30:
        rollen["Bürgermeister"] = max(1, effektive_anzahl // 200)
    if effektive_anzahl >= 35:
        rollen["Leibwächter"] = max(1, effektive_anzahl // 150)
    if effektive_anzahl >= 40:
        rollen["Aurenseherin"] = max(1, effektive_anzahl // 200)
    if effektive_anzahl >= 50:
        rollen["Seherlehrling"] = max(1, effektive_anzahl // 150)
    if effektive_anzahl >= 60:
        rollen["Tratschweib"] = max(1, effektive_anzahl // 200)
    if effektive_anzahl >= 75:
        rollen["Bärenbändiger"] = max(1, effektive_anzahl // 250)

    # Group knowledge roles for very large games
    if effektive_anzahl >= 80:
        schwestern_paare = max(1, effektive_anzahl // 200)
        rollen["Zwei Schwestern"] = schwestern_paare * 2
    if effektive_anzahl >= 100:
        brueder_gruppen = max(1, effektive_anzahl // 250)
        rollen["Drei Brüder"] = brueder_gruppen * 3
    if effektive_anzahl >= 120:
        freimaurer_anzahl = max(2, effektive_anzahl // 150)
        rollen["Freimaurer"] = freimaurer_anzahl

    # Defensive/utility roles for massive games
    if effektive_anzahl >= 150:
        rollen["Kräuterweib"] = max(1, effektive_anzahl // 300)
        rollen["Zauberer"] = max(1, effektive_anzahl // 350)
    if effektive_anzahl >= 200:
        rollen["Hure"] = max(1, effektive_anzahl // 300)
        rollen["Doppelgänger"] = max(1, effektive_anzahl // 400)
    if effektive_anzahl >= 300:
        rollen["Sandmann"] = max(1, effektive_anzahl // 400)
        rollen["Buddler"] = max(1, effektive_anzahl // 500)
    if effektive_anzahl >= 400:
        rollen["Ergebene Magd"] = max(1, effektive_anzahl // 500)
        rollen["Demoskopin"] = max(1, effektive_anzahl // 500)
    if effektive_anzahl >= 500:
        rollen["Putzfrau"] = max(1, effektive_anzahl // 600)
        rollen["Gaukler"] = max(1, effektive_anzahl // 600)

    # Aggressive village roles for balance in huge games
    if effektive_anzahl >= 100:
        rollen["Kamikaze"] = max(1, effektive_anzahl // 300)
    if effektive_anzahl >= 200:
        rollen["Flammenmann"] = max(1, effektive_anzahl // 500)
    if effektive_anzahl >= 400:
        rollen["Inquisitor"] = max(1, effektive_anzahl // 600)

    # ========================================================================
    # SOLO/NEUTRAL ROLES (Sparsely added - max ~3-5% of players)
    # ========================================================================
    if effektive_anzahl >= 15:
        rollen["Dorfdepp"] = max(1, effektive_anzahl // 200)
    if effektive_anzahl >= 50:
        rollen["Flötenspieler"] = max(1, effektive_anzahl // 250)
    if effektive_anzahl >= 100:
        rollen["Selbstmörder"] = max(1, effektive_anzahl // 300)
    if effektive_anzahl >= 150:
        rollen["Henker"] = max(1, effektive_anzahl // 400)
    if effektive_anzahl >= 300:
        rollen["Gerber"] = max(1, effektive_anzahl // 500)
    if effektive_anzahl >= 400:
        rollen["Pyromane"] = max(1, effektive_anzahl // 600)
    if effektive_anzahl >= 500:
        rollen["Engel"] = max(1, effektive_anzahl // 700)

    # ========================================================================
    # OTHER TEAMS (Vampires, Zombies - added in very large games)
    # ========================================================================
    if effektive_anzahl >= 200:
        rollen["Vampir"] = max(1, effektive_anzahl // 300)
    if effektive_anzahl >= 400:
        rollen["Zombie"] = max(1, effektive_anzahl // 500)

    # ========================================================================
    # EVIL SUPPORT ROLES (to help werewolf team in large games)
    # ========================================================================
    if effektive_anzahl >= 75:
        rollen["Giftmischerin"] = max(1, effektive_anzahl // 250)
    if effektive_anzahl >= 150:
        rollen["Hexenmeister"] = max(1, effektive_anzahl // 400)
    if effektive_anzahl >= 300:
        rollen["Dunkler Priester"] = max(1, effektive_anzahl // 500)

    # ========================================================================
    # DORFBEWOHNER (Fill remaining slots)
    # ========================================================================
    total_special_roles = sum(v for k, v in rollen.items() if k != "Erzaehler")
    dorfbewohner_anzahl = effektive_anzahl - total_special_roles

    if dorfbewohner_anzahl > 0:
        rollen["Dorfbewohner"] = dorfbewohner_anzahl
    elif dorfbewohner_anzahl < 0:
        # Too many special roles - reduce werewolves to compensate
        ueberschuss = abs(dorfbewohner_anzahl)
        print(
            f"Adjusting roles: reducing Werwolf from {rollen.get('Werwolf', 0)} by {ueberschuss} to fit player count."
        )
        if rollen.get("Werwolf", 0) > ueberschuss:
            rollen["Werwolf"] -= ueberschuss
        else:
            # Recalculate - this shouldn't happen with proper ratios
            print("Recalculating roles due to excess special roles...")
            rollen["Dorfbewohner"] = 1

    return rollen


def verteile_rollen(raum: Raum) -> dict:
    """
    Verteilt die Rollen an alle Spieler im Raum.

    Args:
        raum: Der Spielraum

    Returns:
        Dictionary mit Spieler-ID zu Rolle Mapping
    """
    spieler = Spieler.query.filter_by(raum_id=raum.id, ist_erzaehler=False).all()
    spieler_anzahl = len(spieler)

    erzaehler = Spieler.query.filter_by(raum_id=raum.id, ist_erzaehler=True).first()

    rollen_verteilung = berechne_rollen(
        spieler_anzahl + (1 if erzaehler else 0), mit_erzaehler=bool(erzaehler)
    )

    # Erstelle Liste aller zu verteilenden Rollen
    rollen_liste = []
    for rolle, anzahl in rollen_verteilung.items():
        if rolle != "Erzaehler":
            rollen_liste.extend([rolle] * anzahl)

    # Mische die Rollen
    random.shuffle(rollen_liste)
    random.shuffle(spieler)

    # Weise Rollen zu
    ergebnis = {}
    for i, spieler_obj in enumerate(spieler):
        if i < len(rollen_liste):
            spieler_obj.rolle = rollen_liste[i]
            ergebnis[spieler_obj.id] = rollen_liste[i]

    # Erzaehler bekommt spezielle Rolle
    if erzaehler:
        erzaehler.rolle = "Erzaehler"
        ergebnis[erzaehler.id] = "Erzaehler"

    db.session.commit()
    return ergebnis


def starte_spiel(raum: Raum) -> bool:
    """
    Startet das Spiel im Raum.

    Args:
        raum: Der Spielraum

    Returns:
        True wenn erfolgreich gestartet
    """
    spieler = Spieler.query.filter_by(raum_id=raum.id).all()

    if len(spieler) < 5:
        return False

    verteile_rollen(raum)

    raum.spiel_gestartet = True
    raum.aktuelle_phase = "rollen_verteilt"
    raum.runde = 1

    # Reset Spieler Status
    for s in spieler:
        s.ist_am_leben = True
        s.status = "aktiv"
        s.hexe_heiltrank = True
        s.hexe_gifttrank = True
        s.jaeger_schuss = True
        s.armor_verliebt = True
        s.verliebt_mit_id = None

    log_eintrag(raum.id, "Das Spiel hat begonnen! Die Rollen wurden verteilt.")

    db.session.commit()
    return True


def hat_spieler_mit_rolle(raum: Raum, rolle: str) -> bool:
    """
    Prueft ob es einen lebenden Spieler mit der gegebenen Rolle gibt.

    Args:
        raum: Der Spielraum
        rolle: Die zu prüfende Rolle

    Returns:
        True wenn Rolle existiert, False sonst
    """
    return (
        Spieler.query.filter_by(raum_id=raum.id, rolle=rolle, ist_am_leben=True).first()
        is not None
    )


def _normalisiere_phase_name(phase_name: str) -> str:
    """Bringt dynamische Phasennamen in das PHASEN-Schema."""

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }

    normalisiert = phase_name.strip().lower()
    for alt, neu in replacements.items():
        normalisiert = normalisiert.replace(alt, neu)

    normalisiert = normalisiert.replace(" ", "_")
    while "__" in normalisiert:
        normalisiert = normalisiert.replace("__", "_")
    return normalisiert


def phasennamen_zu_rollen_mapping() -> dict:
    """
    Erstellt ein Mapping zwischen Phasennamen und erforderlichen Rollen dynamisch
    aus dem Rollen-Registry, so dass neue Rollen keinen Hardcode mehr benötigen.
    """

    mapping = {}

    try:
        from roles import RoleRegistry

        for rolle in RoleRegistry.get_all():
            # Bevorzugt den von der Rolle gelieferten Namen, normalisiert ihn aber
            # in das bestehende PHASEN-Schema (ae/oe/ue/ss statt Umlaute).
            kandidaten = [rolle.get_phase_name(), f"{rolle.info.name}_phase"]
            for kandidat in kandidaten:
                phase_key = _normalisiere_phase_name(kandidat)
                if phase_key in PHASEN:
                    mapping.setdefault(phase_key, rolle.info.name)
                    break
    except (ImportError, AttributeError) as exc:
        import traceback

        print(f"[ROLLEN] Warnung: Dynamisches Phasen-Mapping deaktiviert: {exc}")
        print(f"[ROLLEN] Traceback: {traceback.format_exc()}")

    # Fallback: baue das Mapping aus dem Legacy-ROLLEN-Dict, falls die Registry
    # einmal nicht initialisiert werden konnte (z.B. in minimalen Testumgebungen).
    if not mapping:
        for rollen_name in ROLLEN.keys():
            phase_key = _normalisiere_phase_name(f"{rollen_name}_phase")
            if phase_key in PHASEN:
                mapping[phase_key] = rollen_name

    # Spezielle Info-Phasen, die eine bestimmte Rolle erfordern
    # Diese folgen nicht dem _phase-Schema, müssen aber trotzdem übersprungen werden
    SPEZIELLE_PHASEN_MAPPING = {
        "verliebte_info": "Amor",  # Nur relevant wenn Amor im Spiel
        "baerenbaendiger_brummen": "Bärenbändiger",  # Nur relevant wenn Bärenbändiger im Spiel
        "demoskopin_info": "Demoskopin",  # Nur relevant wenn Demoskopin im Spiel
        "prinz_enthuellung": "Prinz",  # Nur relevant wenn Prinz im Spiel
        "hahn_enthuellung": "Hahn",  # Nur relevant wenn Hahn im Spiel
        "putzfrau_info": "Putzfrau",  # Nur relevant wenn Putzfrau im Spiel
    }
    mapping.update(SPEZIELLE_PHASEN_MAPPING)

    return mapping


def naechste_phase(raum: Raum) -> str:
    """
    Wechselt zur naechsten Spielphase.
    
    Mit der vereinfachten Phasen-Architektur gibt es nur noch
    Kern-Phasen: lobby, rollen_verteilt, nacht, tag_start, 
    diskussion, abstimmung, hinrichtung, tag_ende, spiel_ende.
    
    Rollen agieren WÄHREND der nacht-Phase basierend auf ihrer Priorität.

    Args:
        raum: Der Spielraum

    Returns:
        Name der neuen Phase
    """
    current = raum.aktuelle_phase
    
    # Phase-Übergangslogik
    phase_transitions = {
        "lobby": "rollen_verteilt",
        "rollen_verteilt": "nacht",
        "nacht": "tag_start",
        "tag_start": "diskussion",
        "diskussion": "abstimmung",
        "abstimmung": "hinrichtung",
        "hinrichtung": "tag_ende",
        "tag_ende": "nacht",  # Neuer Tag-Nacht-Zyklus
        "spiel_ende": "spiel_ende",  # Bleibt hier
    }
    
    # Spezialfall: tag_ende erhöht die Runde
    if current == "tag_ende":
        raum.runde += 1
    
    # Nächste Phase bestimmen
    neue_phase = phase_transitions.get(current, "nacht")
    
    raum.aktuelle_phase = neue_phase
    db.session.commit()

    return raum.aktuelle_phase


# =============================================================================
# ROLE-DRIVEN NIGHT EXECUTION
# =============================================================================

def get_active_roles_for_night(raum: Raum) -> List[Tuple]:
    """
    Get all roles that should act this night, sorted by priority.
    
    Roles define when they act via is_active_on_every_night() and
    is_active_on_first_night(). This function collects all active roles
    for the current night and returns them sorted by priority.
    
    Returns:
        List of (role, spieler) tuples sorted by priority
    """
    from roles import RoleRegistry
    
    active_roles = []
    lebende_spieler = hole_lebende_spieler(raum)
    
    for spieler in lebende_spieler:
        role = RoleRegistry.get(spieler.rolle)
        if not role:
            continue
        
        # Check if role is active this night
        is_first_night = raum.runde == 1
        
        try:
            # First night: check is_active_on_first_night OR is_active_on_every_night
            if is_first_night:
                aktiv = role.is_active_on_first_night() or role.is_active_on_every_night()
            else:
                aktiv = role.is_active_on_every_night()
            
            if aktiv:
                active_roles.append((role, spieler))
        except AttributeError:
            # Role doesn't have these methods - treat as not active
            pass
    
    # Sort by priority (lower = earlier)
    active_roles.sort(key=lambda x: x[0].info.prioritaet)
    
    return active_roles


def get_next_role_to_act(raum: Raum, current_role_name: Optional[str] = None) -> Optional[Tuple]:
    """
    Get the next role that should act in the night.
    
    Args:
        raum: The game room
        current_role_name: Name of role that just finished (None for first)
        
    Returns:
        (role, spieler) tuple or None if night is over
    """
    active_roles = get_active_roles_for_night(raum)
    
    if not active_roles:
        return None
    
    if current_role_name is None:
        # Return first role
        return active_roles[0] if active_roles else None
    
    # Find current role and return next
    for i, (role, spieler) in enumerate(active_roles):
        if role.info.name == current_role_name:
            if i + 1 < len(active_roles):
                return active_roles[i + 1]
            return None  # Night is over
    
    return None


def is_night_complete(raum: Raum) -> bool:
    """
    Check if all night actions are complete.
    
    Returns:
        True if all active roles have acted or skipped
    """
    # Night is complete when we're ready to transition to tag_start
    # This is checked by the action handler after each role acts
    return False  # Placeholder - handled by UI flow


def ist_werwolf_rolle(rolle: str) -> bool:
    """
    Prueft ob eine Rolle zum Werwolf-Team gehoert.
    Beruecksichtigt alle Werwolf-Varianten.
    """
    from roles import RoleRegistry
    from roles.enums import Team

    rolle_obj = RoleRegistry.get(rolle)
    if rolle_obj:
        return rolle_obj.info.team == Team.WERWOLF

    rolle_info = ROLLEN.get(rolle, {})
    if rolle_info:
        return rolle_info.get("team") == "werwolf"

    return "werwolf" in (rolle or "").lower()


def pruefe_spielende(raum: Raum) -> dict | None:
    """
    Prueft ob das Spiel zu Ende ist.

    Args:
        raum: Der Spielraum

    Returns:
        Dictionary mit Gewinner-Info oder None wenn Spiel weitergeht
    """
    lebende = Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).all()

    # Beruecksichtige alle Werwolf-Varianten
    werwoelfe = [s for s in lebende if ist_werwolf_rolle(s.rolle)]
    dorfbewohner = [s for s in lebende if not ist_werwolf_rolle(s.rolle)]

    # Verliebten-Check
    verliebte = Spieler.query.filter(
        Spieler.raum_id == raum.id, Spieler.verliebt_mit_id.isnot(None)
    ).all()

    if len(verliebte) == 2 and all(v.ist_am_leben for v in verliebte):
        # Pruefen ob nur noch die Verliebten leben
        if len(lebende) == 2:
            rollen = {v.rolle for v in verliebte}
            # Pruefen ob ein Verliebter ein Wolf ist
            hat_wolf = any(ist_werwolf_rolle(r) for r in rollen)
            if hat_wolf and len(rollen) > 1:
                return {
                    "gewinner": "verliebte",
                    "nachricht": "Die Verliebten haben gewonnen! Ihre Liebe hat alle ueberwunden.",
                    "spieler": [v.name for v in verliebte],
                }

    # Keine Werwoelfe mehr
    if len(werwoelfe) == 0:
        return {
            "gewinner": "dorf",
            "nachricht": "Das Dorf hat gewonnen! Alle Werwoelfe wurden eliminiert.",
            "spieler": [s.name for s in dorfbewohner],
        }

    # Werwoelfe in Ueberzahl oder Gleichstand
    if len(werwoelfe) >= len(dorfbewohner):
        return {
            "gewinner": "werwolf",
            "nachricht": "Die Werwoelfe haben gewonnen! Das Dorf ist gefallen.",
            "spieler": [s.name for s in werwoelfe],
        }

    return None


def toete_spieler(spieler: Spieler, todesart: str = "unbekannt") -> dict:
    """
    Toetet einen Spieler und ruft die entsprechenden Rollen-Trigger auf.

    Args:
        spieler: Der zu toetende Spieler
        todesart: Art des Todes (werwolf, abstimmung, hexe, jaeger)

    Returns:
        Dictionary mit Todes-Informationen
    """
    from roles import RoleRegistry
    from roles.base import SpielKontext
    from roles.enums import Phase

    spieler.ist_am_leben = False
    spieler.status = "tot"

    ergebnis = {
        "spieler_id": spieler.id,
        "spieler_name": spieler.name,
        "rolle": spieler.rolle,
        "todesart": todesart,
        "folge_aktionen": [],
        "rollen_effekte": [],
    }

    # Baue SpielKontext für Rollen-Trigger
    raum = Raum.query.get(spieler.raum_id)
    alle_spieler = Spieler.query.filter_by(raum_id=spieler.raum_id).all()
    lebende_ids = [s.id for s in alle_spieler if s.ist_am_leben and s.id != spieler.id]
    tote_ids = [s.id for s in alle_spieler if not s.ist_am_leben]

    kontext = SpielKontext(
        raum_id=spieler.raum_id,
        runde=raum.runde if raum else 1,
        phase=Phase.TAG_START,
        aktiver_spieler_id=spieler.id,
        lebende_spieler=lebende_ids,
        tote_spieler=tote_ids,
    )

    # Füge dynamische Attribute für Rollen hinzu
    kontext.spieler_rollen = {s.id: RoleRegistry.get(s.rolle) for s in alle_spieler}
    kontext.spieler_namen = {s.id: s.name for s in alle_spieler}
    kontext.spieler_teams = {}
    for s in alle_spieler:
        rolle_obj = RoleRegistry.get(s.rolle)
        if rolle_obj:
            kontext.spieler_teams[s.id] = rolle_obj.info.team

    # 1. Rufe on_eigener_tod für den sterbenden Spieler auf
    sterbende_rolle = RoleRegistry.get(spieler.rolle)
    if sterbende_rolle:
        eigener_tod_ergebnis = sterbende_rolle.on_eigener_tod(
            spieler, todesart, kontext
        )
        if eigener_tod_ergebnis:
            ergebnis["rollen_effekte"].append(
                {
                    "spieler_id": spieler.id,
                    "typ": "eigener_tod",
                    "ergebnis": eigener_tod_ergebnis,
                }
            )
            # Verarbeite spezielle Effekte
            if eigener_tod_ergebnis.effekte.get("spiel_ende"):
                ergebnis["spiel_ende"] = True
                ergebnis["gewinner"] = eigener_tod_ergebnis.effekte.get("gewinner")

    # 2. Rufe on_spieler_stirbt für alle anderen lebenden Spieler auf
    for anderer in alle_spieler:
        if anderer.id == spieler.id or not anderer.ist_am_leben:
            continue
        andere_rolle = RoleRegistry.get(anderer.rolle)
        if andere_rolle:
            stirbt_ergebnis = andere_rolle.on_spieler_stirbt(
                anderer, spieler, todesart, kontext
            )
            if stirbt_ergebnis:
                ergebnis["rollen_effekte"].append(
                    {
                        "spieler_id": anderer.id,
                        "typ": "on_spieler_stirbt",
                        "ergebnis": stirbt_ergebnis,
                    }
                )
                # Verarbeite Team-Wechsel (z.B. Hund wird Werwolf)
                if stirbt_ergebnis.effekte.get("verwandlung"):
                    neues_team = stirbt_ergebnis.effekte.get("neues_team")
                    if neues_team:
                        anderer.aktuelles_team = neues_team

    # Legacy-Logik für Abwärtskompatibilität
    # Jaeger stirbt - kann noch schiessen
    if spieler.rolle == "Jäger" and getattr(spieler, "jaeger_schuss", True):
        ergebnis["folge_aktionen"].append("jaeger_schuss")

    # Verliebter stirbt - Partner stirbt auch
    if spieler.verliebt_mit_id:
        partner = Spieler.query.get(spieler.verliebt_mit_id)
        if partner and partner.ist_am_leben:
            ergebnis["folge_aktionen"].append("partner_stirbt")
            ergebnis["partner"] = partner.name

    log_eintrag(
        spieler.raum_id, f"{spieler.name} ist gestorben. (Todesart: {todesart})"
    )

    db.session.commit()
    return ergebnis


def werwolf_abstimmung(raum: Raum) -> dict | None:
    """
    Wertet die Werwolf-Abstimmung aus.

    Args:
        raum: Der Spielraum

    Returns:
        Ergebnis der Abstimmung oder None
    """
    aktionen = SpielAktion.query.filter_by(
        raum_id=raum.id,
        runde=raum.runde,
        phase="werwolf_phase",
        aktion_typ="werwolf_wahl",
    ).all()

    if not aktionen:
        return None

    # Zaehle Stimmen
    stimmen = {}
    for aktion in aktionen:
        ziel_id = aktion.ziel_spieler_id
        stimmen[ziel_id] = stimmen.get(ziel_id, 0) + 1

    # Finde Opfer (meiste Stimmen)
    max_stimmen = max(stimmen.values())
    opfer_ids = [sid for sid, count in stimmen.items() if count == max_stimmen]

    # Bei Gleichstand: zufaellig waehlen
    opfer_id = random.choice(opfer_ids)
    opfer = Spieler.query.get(opfer_id)

    return {
        "opfer_id": opfer_id,
        "opfer_name": opfer.name if opfer else "Unbekannt",
        "stimmen": max_stimmen,
    }


def tag_abstimmung(raum: Raum) -> dict | None:
    """
    Wertet die Tag-Abstimmung aus.

    Args:
        raum: Der Spielraum

    Returns:
        Ergebnis der Abstimmung oder None
    """
    aktionen = SpielAktion.query.filter_by(
        raum_id=raum.id, runde=raum.runde, phase="abstimmung", aktion_typ="tag_wahl"
    ).all()

    if not aktionen:
        return None

    # Zaehle Stimmen
    stimmen = {}
    for aktion in aktionen:
        ziel_id = aktion.ziel_spieler_id
        if ziel_id:  # None = Enthaltung
            stimmen[ziel_id] = stimmen.get(ziel_id, 0) + 1

    if not stimmen:
        return {"kein_opfer": True, "nachricht": "Niemand wurde gewaehlt."}

    # Finde Opfer (meiste Stimmen)
    max_stimmen = max(stimmen.values())
    opfer_ids = [sid for sid, count in stimmen.items() if count == max_stimmen]

    # Mehrheit erforderlich
    lebende = Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).count()
    if max_stimmen <= lebende // 2:
        return {"kein_opfer": True, "nachricht": "Keine Mehrheit erreicht."}

    # Bei Gleichstand: niemand stirbt
    if len(opfer_ids) > 1:
        return {"kein_opfer": True, "nachricht": "Stimmengleichheit - niemand stirbt."}

    opfer_id = opfer_ids[0]
    opfer = Spieler.query.get(opfer_id)

    return {
        "opfer_id": opfer_id,
        "opfer_name": opfer.name if opfer else "Unbekannt",
        "opfer_rolle": opfer.rolle if opfer else "Unbekannt",
        "stimmen": max_stimmen,
    }


def log_eintrag(raum_id: int, nachricht: str, sichtbar_fuer: str = "alle"):
    """
    Erstellt einen Spiellog-Eintrag.

    Args:
        raum_id: ID des Raums
        nachricht: Log-Nachricht
        sichtbar_fuer: Wer kann den Eintrag sehen
    """
    eintrag = SpielLog()
    eintrag.raum_id = raum_id
    eintrag.nachricht = nachricht
    eintrag.sichtbar_fuer = sichtbar_fuer
    db.session.add(eintrag)
    db.session.commit()


def registriere_aktion(
    raum_id: int,
    runde: int,
    phase: str,
    aktion_typ: str,
    von_spieler_id: int,
    ziel_spieler_id: Optional[int] = None,
):
    """
    Registriert eine Spielaktion.
    """
    aktion = SpielAktion()
    aktion.raum_id = raum_id
    aktion.runde = runde
    aktion.phase = phase
    aktion.aktion_typ = aktion_typ
    aktion.von_spieler_id = von_spieler_id
    aktion.ziel_spieler_id = ziel_spieler_id
    db.session.add(aktion)
    db.session.commit()
    return aktion


def hole_lebende_spieler(raum: Raum, ohne_erzaehler: bool = True) -> list:
    """
    Gibt alle lebenden Spieler zurueck.
    """
    query = Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=True)
    if ohne_erzaehler:
        query = query.filter_by(ist_erzaehler=False)
    return query.all()


def hole_spieler_fuer_rolle(raum: Raum, rolle: str) -> list:
    """
    Gibt alle Spieler einer bestimmten Rolle zurueck.
    """
    return Spieler.query.filter_by(
        raum_id=raum.id, rolle=rolle, ist_am_leben=True
    ).all()


def hat_spieler_gewaehlt(spieler: Spieler, raum: Raum, phase: str) -> bool:
    """
    Prueft ob ein Spieler in der aktuellen Phase bereits gewaehlt hat.
    """
    aktion = SpielAktion.query.filter_by(
        raum_id=raum.id, runde=raum.runde, phase=phase, von_spieler_id=spieler.id
    ).first()
    return aktion is not None


def alle_haben_gewaehlt(raum: Raum, phase: str, rolle: Optional[str] = None) -> bool:
    """
    Prueft ob alle relevanten Spieler in der Phase gewaehlt haben.
    """
    if rolle:
        spieler = hole_spieler_fuer_rolle(raum, rolle)
    else:
        spieler = hole_lebende_spieler(raum)

    for s in spieler:
        if not hat_spieler_gewaehlt(s, raum, phase):
            return False
    return True


# ============================================================================
# DISKUSSION & ABSTIMMUNG PHASE FUNKTIONEN
# ============================================================================


def starte_diskussion_abstimmung(raum: Raum, dauer_sekunden: int = 120):
    """
    Startet die diskussion_abstimmung Phase mit Timer.

    Args:
        raum: Der Spielraum
        dauer_sekunden: Dauer der Phase in Sekunden (default: 120)
    """
    raum.aktuelle_phase = "diskussion_abstimmung"
    raum.timer_start = datetime.utcnow()
    raum.timer_duration = dauer_sekunden
    raum.phase_votes = "{}"  # Reset votes
    db.session.commit()


def get_verbleibende_zeit(raum: Raum) -> int:
    """
    Berechnet die verbleibende Zeit der aktuellen Phase in Sekunden.

    Args:
        raum: Der Spielraum

    Returns:
        Verbleibende Sekunden (0 wenn abgelaufen)
    """
    if not raum.timer_start:
        return 0

    elapsed = (datetime.utcnow() - raum.timer_start).total_seconds()
    remaining = max(0, raum.timer_duration - int(elapsed))
    return remaining


def timer_abgelaufen(raum: Raum) -> bool:
    """
    Prüft ob der Timer abgelaufen ist.

    Args:
        raum: Der Spielraum

    Returns:
        True wenn Timer abgelaufen
    """
    return get_verbleibende_zeit(raum) <= 0


def speichere_abstimmungs_vote(raum: Raum, waehler_id: int, ziel_id: int):
    """
    Speichert eine Abstimmungsstimme im phase_votes JSON.

    Args:
        raum: Der Spielraum
        waehler_id: ID des wählenden Spielers
        ziel_id: ID des gewählten Spielers (None für Enthaltung)
    """
    try:
        votes = json.loads(raum.phase_votes or "{}")
    except json.JSONDecodeError:
        votes = {}

    votes[str(waehler_id)] = ziel_id
    raum.phase_votes = json.dumps(votes)
    db.session.commit()


def berechne_abstimmungs_statistik(raum: Raum) -> dict:
    """
    Berechnet die aktuelle Abstimmungsstatistik.

    Args:
        raum: Der Spielraum

    Returns:
        Dict mit Statistiken:
        - gesamt_spieler: Anzahl wahlberechtigter Spieler
        - gesamt_votes: Anzahl abgegebener Stimmen
        - noch_zu_waehlen: Anzahl noch nicht gewählt
        - ziel_stimmen: Dict {ziel_id: anzahl}
        - fuehrender_id: ID des führenden Kandidaten
        - fuehrende_stimmen: Anzahl Stimmen für den Führenden
    """
    lebende = Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).all()
    gesamt_spieler = len(lebende)

    try:
        votes = json.loads(raum.phase_votes or "{}")
    except json.JSONDecodeError:
        votes = {}

    gesamt_votes = len(votes)
    noch_zu_waehlen = gesamt_spieler - gesamt_votes

    # Zähle Stimmen pro Ziel
    ziel_stimmen = {}
    for waehler_id, ziel_id in votes.items():
        if ziel_id is not None:  # None = Enthaltung
            ziel_stimmen[ziel_id] = ziel_stimmen.get(ziel_id, 0) + 1

    # Finde Führenden
    fuehrender_id = None
    fuehrende_stimmen = 0
    if ziel_stimmen:
        fuehrender_id = max(ziel_stimmen.keys(), key=lambda k: ziel_stimmen[k])
        fuehrende_stimmen = ziel_stimmen[fuehrender_id]

    return {
        "gesamt_spieler": gesamt_spieler,
        "gesamt_votes": gesamt_votes,
        "noch_zu_waehlen": noch_zu_waehlen,
        "ziel_stimmen": ziel_stimmen,
        "fuehrender_id": fuehrender_id,
        "fuehrende_stimmen": fuehrende_stimmen,
    }


def pruefen_abstimmung_komplett(raum: Raum) -> bool:
    """
    Prüft ob alle Spieler abgestimmt haben.

    Args:
        raum: Der Spielraum

    Returns:
        True wenn alle abgestimmt haben
    """
    stats = berechne_abstimmungs_statistik(raum)
    return stats["noch_zu_waehlen"] == 0


def werte_abstimmung_aus(raum: Raum) -> dict:
    """
    Wertet die diskussion_abstimmung Phase aus.

    Args:
        raum: Der Spielraum

    Returns:
        Ergebnis der Abstimmung
    """
    stats = berechne_abstimmungs_statistik(raum)
    ziel_stimmen = stats["ziel_stimmen"]

    if not ziel_stimmen:
        return {"kein_opfer": True, "nachricht": "Niemand wurde gewählt."}

    # Finde Maximum
    max_stimmen = max(ziel_stimmen.values())
    opfer_ids = [int(sid) for sid, count in ziel_stimmen.items() if count == max_stimmen]

    # Mehrheit erforderlich
    lebende = Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).count()

    if max_stimmen <= lebende // 2:
        return {"kein_opfer": True, "nachricht": "Keine Mehrheit erreicht."}

    # Bei Gleichstand: niemand stirbt
    if len(opfer_ids) > 1:
        return {"kein_opfer": True, "nachricht": "Stimmengleichheit - niemand stirbt."}

    opfer_id = opfer_ids[0]
    opfer = Spieler.query.get(opfer_id)

    # Reset votes nach Auswertung
    raum.phase_votes = "{}"
    raum.timer_start = None
    db.session.commit()

    return {
        "opfer_id": opfer_id,
        "opfer_name": opfer.name if opfer else "Unbekannt",
        "opfer_rolle": opfer.rolle if opfer else "Unbekannt",
        "stimmen": max_stimmen,
    }

