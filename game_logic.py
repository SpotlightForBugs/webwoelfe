from datetime import datetime, timedelta, timezone
import random
import json
from typing import List, Tuple, Optional
from models import db, Raum, Spieler, SpielAktion, SpielLog, ErzaehlerEvent
from logger import logger
from roles.base import SpielKontext
from roles.enums import Phase

# Get PHASEN from centralized module
from phases import get_phase_list

PHASEN = get_phase_list()


def berechne_rollen(spieler_anzahl: int, mit_erzaehler: bool = False) -> dict:
    """
    Berechnet die Rollenverteilung dynamisch basierend auf der Registry.

    Verwendet DistributionConfig der einzelnen Rollen anstelle von hardcoded Logik.
    """
    logger.debug(
        f"Calculating roles for {spieler_anzahl} players (Narrator: {mit_erzaehler})"
    )
    effektive_anzahl = spieler_anzahl
    rolle_config = {}

    if mit_erzaehler:
        rolle_config["Erzaehler"] = 1
        effektive_anzahl -= 1

    if effektive_anzahl <= 0:
        return rolle_config

    # 1. Hole alle verfügbaren Rollen
    verfuegbare_rollen = []
    from roles import RoleRegistry

    for role in RoleRegistry.get_all():
        if not role.info.distribution:
            continue

        dist = role.info.distribution

        # Check preconditions
        if effektive_anzahl < dist.min_players:
            continue

        verfuegbare_rollen.append(role)

    # 2. Sortiere nach Priorität (höhere zuerst)
    verfuegbare_rollen.sort(key=lambda r: r.info.distribution.priority, reverse=True)

    # 3. Verteile Rollen
    aktuelle_anzahl = 0
    zugewiesene_rollen = set()
    fillers = []

    for role in verfuegbare_rollen:
        dist = role.info.distribution

        if dist.is_filler:
            fillers.append(role)
            continue

        # Check exklusive Rollen
        if any(ex in zugewiesene_rollen for ex in dist.exclusive_with):
            continue

        # Check required roles (nur wenn schon verteilt)
        if dist.requires_roles:
            if not all(req in zugewiesene_rollen for req in dist.requires_roles):
                continue

        # Berechne Anzahl via Lambda
        anzahl = dist.count_func(effektive_anzahl)

        if anzahl > 0:
            # Check ob genug Platz
            if aktuelle_anzahl + anzahl > effektive_anzahl:
                continue

            rolle_config[role.info.name] = anzahl
            aktuelle_anzahl += anzahl
            zugewiesene_rollen.add(role.info.name)

    # 4. Fülle mit Filler-Rollen auf (z.B. Dorfbewohner)
    rest_plaetze = effektive_anzahl - aktuelle_anzahl

    if rest_plaetze > 0:
        if fillers:
            # Standard: Nehme den ersten Filler (meist Dorfbewohner)
            filler_role = fillers[0]
            rolle_config[filler_role.info.name] = rest_plaetze
        else:
            # Fallback wenn kein Filler definiert
            rolle_config["Dorfbewohner"] = rest_plaetze

    return rolle_config


def verteile_rollen(raum: Raum) -> dict:
    """
    Verteilt die Rollen an alle Spieler im Raum.

    Args:
        raum: Der Spielraum
    """
    logger.info(f"Distributing roles for room {raum.code}")
    spieler_liste = Spieler.query.filter_by(raum_id=raum.id).all()

    # Erzähler finden
    erzaehler = None
    for s in spieler_liste:
        if s.ist_erzaehler:
            erzaehler = s
            break

    spieler_anzahl = len(spieler_liste)

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
    random.shuffle(spieler_liste)

    # Weise Rollen zu
    ergebnis = {}
    for i, spieler_obj in enumerate(spieler_liste):
        if i < len(rollen_liste):
            spieler_obj.rolle = rollen_liste[i]
            ergebnis[spieler_obj.id] = rollen_liste[i]

    # Erzaehler bekommt spezielle Rolle
    if erzaehler:
        erzaehler.rolle = "Erzaehler"
        ergebnis[erzaehler.id] = "Erzaehler"

    # Speichern
    db.session.commit()
    logger.info(f"Roles distributed: {ergebnis}")
    return ergebnis


def starte_spiel(raum: Raum) -> bool:
    """
    Startet das Spiel.
    """
    logger.info(f"Starting game in room {raum.code}")
    try:
        # Rollen verteilen
        verteile_rollen(raum)

        # Spielstatus setzen
        raum.spiel_gestartet = True
        raum.runde = 1
        raum.aktuelle_phase = "rollen_verteilt"  # Erste Phase: Info

        # Initialisiere Phase-Generator für diesen Raum
        from phase_generator import initialize_game_phases

        initialize_game_phases(raum)

        db.session.commit()

        # Log
        log_eintrag(raum.id, "Das Spiel beginnt!", sichtbar_fuer="alle")
        logger.info(f"Game started successfully in room {raum.code}")
        return True
    except Exception as e:
        logger.error(f"Error starting game in room {raum.code}: {e}")
        print(f"Fehler beim Spielstart: {e}")
        return False


def hat_spieler_mit_rolle(raum: Raum, rolle: str) -> bool:
    """
    Prüft, ob es einen lebenden Spieler mit der gegebenen Rolle gibt.

    Args:
        raum: Der Spielraum
        rolle: Die zu prüfende Rolle

    Returns:
        True wenn die Rolle existiert, False sonst
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
    aus dem Rollen-Registry.
    """
    mapping = {}

    try:
        from roles import RoleRegistry

        for rolle in RoleRegistry.get_all():
            phase_key = _normalisiere_phase_name(rolle.get_phase_name())
            if phase_key:
                mapping[phase_key] = rolle.info.name

    except (ImportError, AttributeError) as exc:
        import traceback

        print(f"[ROLLEN] Warnung: Dynamisches Phasen-Mapping Fehler: {exc}")
        print(f"[ROLLEN] Traceback: {traceback.format_exc()}")

    return mapping


def naechste_phase(raum: Raum) -> str:
    """
    Wechselt zur naechsten Spielphase.
    Verwendet den Stateless Scheduler.
    """
    logger.info(
        f"Calculating next phase for room {raum.code} (Current: {raum.aktuelle_phase})"
    )
    from phase_generator import get_next_phase

    old_phase = raum.aktuelle_phase
    next_p = get_next_phase(raum)

    # Update Raum
    raum.aktuelle_phase = next_p

    # Check for round increment:
    # A new round starts when we transition TO any night-starting phase
    # This includes: "nacht_start", "nacht", or dynamic role phases after tag_ende
    is_entering_night = next_p in ("nacht_start", "nacht") or (
        old_phase in ("tag_ende", "hinrichtung") and "nacht" in next_p
    )

    # Only increment if we're entering night from a day phase (not on first transition)
    if is_entering_night and old_phase not in (
        "lobby",
        "rollen_verteilt",
        "nacht_start",
        "nacht",
    ):
        raum.runde += 1
        logger.info(f"Round incremented to {raum.runde}")

    db.session.commit()
    logger.info(f"Next phase: {next_p}")
    return next_p


def registriere_aktion(
    raum_id: int,
    runde: int,
    phase: str,
    aktion_typ: str,
    von_spieler_id: int,
    ziel_spieler_id: Optional[int] = None,
    zusatz_daten: Optional[dict] = None,
):
    """Registriert eine Spielaktion in der Datenbank"""
    logger.info(
        f"Registering action: {aktion_typ} by {von_spieler_id} -> {ziel_spieler_id} (Phase: {phase})"
    )
    aktion = SpielAktion(
        raum_id=raum_id,
        runde=runde,
        phase=phase,
        aktion_typ=aktion_typ,
        von_spieler_id=von_spieler_id,
        ziel_spieler_id=ziel_spieler_id,
        zusatz_daten=json.dumps(zusatz_daten) if zusatz_daten else None,
    )
    db.session.add(aktion)
    db.session.commit()
    return aktion


def toete_spieler(spieler: Spieler, todesart: str) -> dict:
    """
    Tötet einen Spieler und führt Konsequenzen aus (z.B. Jäger, Verliebte).
    """
    logger.info(
        f"Killing player {spieler.name} (ID: {spieler.id}, Role: {spieler.rolle}) - Cause: {todesart}"
    )
    if not spieler.ist_am_leben:
        logger.warning(f"Player {spieler.name} is already dead")
        return {"tote": [], "folge_aktionen": []}

    spieler.ist_am_leben = False
    spieler.status = "tot"

    # Todeszeitpunkt speichern (für Statistiken etc.)
    # spieler.gestorben_am = datetime.utcnow() # Feld existiert noch nicht im Model

    tote = [spieler]
    folge_aktionen = []

    # Log
    log_eintrag(
        spieler.raum_id,
        f"{spieler.name} ist gestorben ({todesart}).",
        sichtbar_fuer="alle",
    )

    # 1. Prüfe Verliebte (Amor)
    # Use state-based check
    verliebt_mit_id = spieler.get_state("global.verliebt_mit_id")
    if verliebt_mit_id:
        partner = db.session.get(Spieler, verliebt_mit_id)
        if partner and partner.ist_am_leben:
            logger.info(f"Lover {partner.name} dies of broken heart")
            log_eintrag(
                spieler.raum_id,
                f"{partner.name} stirbt aus Liebeskummer!",
                sichtbar_fuer="alle",
            )
            # Rekursiver Aufruf für Partner
            res = toete_spieler(partner, "liebeskummer")
            tote.extend(res["tote"])
            folge_aktionen.extend(res["folge_aktionen"])

    # 2. Prüfe "On Death" Effekte via Registry
    from roles import RoleRegistry

    # Get the raum for context
    raum = db.session.get(Raum, spieler.raum_id)
    if not raum:
        logger.error(f"Room not found for player {spieler.name}")
        db.session.commit()
        return {"tote": tote, "folge_aktionen": folge_aktionen}

    # Check effects for the dying player (e.g., Jäger)
    role_obj = RoleRegistry.get(spieler.rolle)
    if role_obj and hasattr(role_obj, "on_eigener_tod"):
        try:
            alle_spieler = Spieler.query.filter_by(
                raum_id=raum.id, ist_erzaehler=False
            ).all()
            kontext = SpielKontext(
                raum_id=spieler.raum_id,
                runde=raum.runde,
                phase=Phase.TAG if "tag" in raum.aktuelle_phase else Phase.NACHT,
                aktiver_spieler_id=spieler.id,
                lebende_spieler=[s.id for s in alle_spieler if s.ist_am_leben],
                tote_spieler=[s.id for s in alle_spieler if not s.ist_am_leben],
            )

            result = role_obj.on_eigener_tod(spieler, todesart, kontext)
            if result and result.erfolg:
                # Apply state updates generically
                if result.state_updates:
                    for state_key, state_value in result.state_updates.items():
                        spieler.set_state(state_key, state_value)

                # Add any follow-up actions from effects
                for effect_key, effect_value in result.effekte.items():
                    if effect_value is True:  # Boolean flags indicate actions
                        folge_aktionen.append(effect_key)

                if result.nachricht:
                    log_eintrag(
                        spieler.raum_id,
                        result.nachricht,
                        sichtbar_fuer=result.log_sichtbar_fuer or "alle",
                    )
        except Exception as e:
            logger.error(f"Error calling on_eigener_tod for {spieler.rolle}: {e}")

    # 3. Check effects for others (e.g. Wildes Kind, Hund)
    # This requires scanning all players or having a listener system
    # For now, we hardcode the known ones or migrate them to a listener system later

    # Wildes Kind / Vorbild
    # Check if any player has this player as "vorbild_id"
    # This requires iterating all players or a query
    # Optimization: Query JSON field? SQLite JSON support varies.
    # Better: Iterate living players with roles that care.
    # ... (Implementation of Wildes Kind etc. would go here)

    db.session.commit()
    return {"tote": tote, "folge_aktionen": folge_aktionen}


def pruefe_spielende(raum: Raum) -> Optional[dict]:
    """
    Prüft ob das Spiel vorbei ist.
    """
    logger.debug(f"Checking win conditions for room {raum.code}")
    lebende = hole_lebende_spieler(raum)

    if not lebende:
        logger.info("Game over: No survivors")
        return {
            "gewinner": "niemand",
            "nachricht": "Alle sind gestorben. Das Dorf ist ausgelöscht.",
        }

    # Zähle Teams
    werwoelfe = 0
    dorfbewohner = 0
    andere = 0

    from roles import RoleRegistry

    for s in lebende:
        role = RoleRegistry.get(s.rolle)
        if not role:
            dorfbewohner += 1  # Fallback
            continue

        team = role.info.team

        if team.value == "werwolf":
            werwoelfe += 1
        elif team.value == "dorf":
            dorfbewohner += 1
        else:
            andere += 1  # Solo, etc.

    logger.debug(f"Stats: WW={werwoelfe}, Dorf={dorfbewohner}, Andere={andere}")

    # Get all players for context
    alle_spieler = Spieler.query.filter_by(raum_id=raum.id, ist_erzaehler=False).all()
    tote_spieler_ids = [s.id for s in alle_spieler if not s.ist_am_leben]

    # Build context for win condition checks
    kontext = SpielKontext(
        raum_id=raum.id,
        runde=raum.runde,
        phase=Phase.TAG if "tag" in raum.aktuelle_phase else Phase.NACHT,
        aktiver_spieler_id=0,  # Not relevant for win checks
        lebende_spieler=[s.id for s in lebende],
        tote_spieler=tote_spieler_ids,
    )

    # 1. Check role-specific solo win conditions (highest priority)
    # Examples: Weißer Wolf, Flötenspieler, etc.
    for s in lebende:
        role = RoleRegistry.get(s.rolle)
        if role:
            # Check role's berechne_gewinn method
            gewonnen_team = role.berechne_gewinn(s, kontext)
            if gewonnen_team and gewonnen_team.value == "solo":
                logger.info(f"Game over: {s.rolle} wins solo")
                return {
                    "gewinner": s.rolle.lower().replace(" ", "_"),
                    "nachricht": f"{s.rolle} hat alle anderen vernichtet und gewinnt allein!",
                    "team": "solo",
                    "spieler_id": s.id,
                }

    # 2. Werwölfe gewinnen
    # Wenn Werwölfe >= Dorfbewohner (und keine Solo-Rollen mehr da sind, die das verhindern)
    # Note: Solo roles with special win conditions are checked first
    if werwoelfe >= (dorfbewohner + andere):
        logger.info("Game over: Werewolves win")
        return {
            "gewinner": "werwolf",
            "nachricht": "Die Werwölfe haben die Überhand gewonnen!",
            "team": "werwolf",
        }

    # 3. Dorf gewinnt
    if werwoelfe == 0 and andere == 0:
        logger.info("Game over: Villagers win")
        return {
            "gewinner": "dorf",
            "nachricht": "Alle Werwölfe wurden vernichtet. Das Dorf hat gewonnen!",
            "team": "dorf",
        }

    # 4. Gemischtes Paar (Amor) gewinnt
    # Wenn nur noch 2 Spieler leben und sie verliebt sind (und in verschiedenen Teams waren)
    if len(lebende) == 2:
        s1 = lebende[0]
        s2 = lebende[1]
        if s1.get_state("global.verliebt_mit_id") == s2.id:
            logger.info("Game over: Lovers win")
            return {
                "gewinner": "verliebte",
                "nachricht": "Die Verliebten haben als einzige überlebt und gewinnen gemeinsam!",
                "team": "verliebte",
            }

    # Spiel geht weiter
    return None


def log_eintrag(raum_id: int, nachricht: str, sichtbar_fuer: str = "alle") -> SpielLog:
    """Erstellt einen Log-Eintrag"""
    # logger.debug(f"Game log: {nachricht} (Visible to: {sichtbar_fuer})") # Too verbose
    log = SpielLog(raum_id=raum_id, nachricht=nachricht, sichtbar_fuer=sichtbar_fuer)
    db.session.add(log)
    db.session.commit()
    return log


# ============================================================================
# TAG-ABSTIMMUNG LOGIK
# ============================================================================


def starte_tag_abstimmung(raum: Raum, dauer_sekunden: int = 120):
    """Startet die Tag-Abstimmungsphase (Diskussion + Voting)"""
    logger.info(f"Starting day voting in room {raum.code} for {dauer_sekunden}s")
    raum.aktuelle_phase = "tag_abstimmung"
    raum.timer_start = datetime.now(timezone.utc)
    raum.timer_duration = dauer_sekunden
    raum.phase_votes = "{}"  # Reset votes
    db.session.commit()

    log_eintrag(raum.id, "Die Diskussion beginnt! Ihr könnt jetzt abstimmen.", "alle")


def get_verbleibende_zeit(raum: Raum) -> int:
    """Gibt die verbleibenden Sekunden für die aktuelle Phase zurück"""
    if not raum.timer_start or not raum.timer_duration:
        return 0

    # Handle both timezone-aware and naive datetimes for backwards compatibility
    now = datetime.now(timezone.utc)
    timer_start = raum.timer_start
    if timer_start.tzinfo is None:
        # Naive datetime - assume UTC
        timer_start = timer_start.replace(tzinfo=timezone.utc)

    vergangen = (now - timer_start).total_seconds()
    rest = max(0, int(raum.timer_duration - vergangen))
    return rest


def timer_abgelaufen(raum: Raum) -> bool:
    """Prüft ob der Timer abgelaufen ist"""
    return get_verbleibende_zeit(raum) <= 0


def speichere_abstimmungs_vote(raum: Raum, voter_id: int, target_id: int):
    """Speichert eine Stimme im JSON-Feld des Raums"""
    logger.debug(f"Saving vote: {voter_id} -> {target_id}")
    try:
        votes = json.loads(raum.phase_votes or "{}")
    except (json.JSONDecodeError, TypeError):
        votes = {}

    votes[str(voter_id)] = target_id
    raum.phase_votes = json.dumps(votes)
    db.session.commit()


def berechne_abstimmungs_statistik(raum: Raum) -> dict:
    """Berechnet aktuelle Statistik der Abstimmung"""
    try:
        votes = json.loads(raum.phase_votes or "{}")
    except (json.JSONDecodeError, TypeError):
        votes = {}

    lebende = hole_lebende_spieler(raum)
    gesamt_spieler = len(lebende)

    # Zähle Stimmen pro Ziel
    ziel_stimmen = {}
    for vid, tid in votes.items():
        # Prüfe ob Voter noch lebt (wichtig bei Disconnects/Kills während Phase)
        # (Optional, hier nehmen wir alle gespeicherten Votes)
        tid_str = str(tid)
        ziel_stimmen[tid_str] = ziel_stimmen.get(tid_str, 0) + 1

    # Führender
    fuehrender_id = None
    fuehrende_stimmen = 0

    for tid, count in ziel_stimmen.items():
        if count > fuehrende_stimmen:
            fuehrende_stimmen = count
            fuehrender_id = int(tid)
        elif count == fuehrende_stimmen:
            fuehrender_id = None  # Unentschieden

    return {
        "gesamt_spieler": gesamt_spieler,
        "gesamt_votes": len(votes),
        "noch_zu_waehlen": gesamt_spieler - len(votes),
        "ziel_stimmen": ziel_stimmen,  # {target_id: count}
        "fuehrender_id": fuehrender_id,
        "fuehrende_stimmen": fuehrende_stimmen,
    }


def pruefen_abstimmung_komplett(raum: Raum) -> bool:
    """Prüft ob alle lebenden Spieler abgestimmt haben"""
    try:
        votes = json.loads(raum.phase_votes or "{}")
    except (json.JSONDecodeError, TypeError):
        votes = {}

    lebende = hole_lebende_spieler(raum)

    # Check if every living player has an entry in votes
    for s in lebende:
        if str(s.id) not in votes:
            return False

    logger.info(f"Voting complete in room {raum.code}")
    return True


def werte_abstimmung_aus(raum: Raum) -> dict:
    """
    Wertet das Endergebnis der Abstimmung aus.
    Gibt dict zurück mit Ergebnis-Daten.
    """
    logger.info(f"Evaluating voting results for room {raum.code}")
    stats = berechne_abstimmungs_statistik(raum)

    if not stats["fuehrender_id"]:
        logger.info("Voting result: Tie/No result")
        return {
            "kein_opfer": True,
            "nachricht": "Unentschieden! Niemand wird gehängt.",
            "stimmen": stats["ziel_stimmen"],
        }

    # Prüfe Mehrheit (optional: absolute Mehrheit erforderlich?)
    # Hier: Einfache Mehrheit reicht

    opfer = db.session.get(Spieler, stats["fuehrender_id"])
    if not opfer:
        logger.error(f"Voting victim not found: {stats['fuehrender_id']}")
        return {
            "kein_opfer": True,
            "nachricht": "Fehler: Gewähltes Opfer nicht gefunden.",
            "stimmen": stats["ziel_stimmen"],
        }

    logger.info(f"Voting result: {opfer.name} chosen to die")
    return {
        "kein_opfer": False,
        "opfer_id": opfer.id,
        "opfer_name": opfer.name,
        "opfer_rolle": opfer.rolle,  # Wird erst nach Tod angezeigt eigentlich
        "stimmen": stats["ziel_stimmen"],
        "nachricht": f"{opfer.name} wurde vom Dorf verurteilt.",
    }


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================


def hole_lebende_spieler(raum: Raum) -> List[Spieler]:
    """Gibt Liste aller lebenden Spieler zurück"""
    return Spieler.query.filter_by(
        raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False
    ).all()


def ist_werwolf_rolle(rolle_name: str) -> bool:
    """Prüft ob eine Rolle zum Werwolf-Team gehört"""
    # logger.debug(f"Checking if role is werewolf: {rolle_name}") # Too verbose
    if not rolle_name:
        return False
    from roles import RoleRegistry

    r = RoleRegistry.get(rolle_name)
    if r:
        return r.info.team.value == "werwolf"
    return "Werwolf" in rolle_name  # Fallback


def hat_spieler_gewaehlt(spieler: Spieler, raum: Raum, phase: str) -> bool:
    """Prüft ob Spieler in dieser Phase schon eine Aktion gemacht hat"""
    # logger.debug(f"Checking if {spieler.name} voted in {phase}") # Too verbose
    aktion = SpielAktion.query.filter_by(
        raum_id=raum.id,
        runde=raum.runde,
        phase=phase,
        von_spieler_id=spieler.id,
    ).first()
    return aktion is not None


def alle_haben_gewaehlt(raum: Raum, phase: str, rolle: str | None = None) -> bool:
    """
    Prüft ob alle berechtigten Spieler (optional gefiltert nach Rolle)
    in dieser Phase eine Aktion durchgeführt haben.
    """
    logger.debug(f"Checking if all voted in {phase} (Role filter: {rolle})")
    lebende = hole_lebende_spieler(raum)

    for s in lebende:
        if rolle and s.rolle != rolle:
            continue

        if not hat_spieler_gewaehlt(s, raum, phase):
            return False

    return True


def werwolf_abstimmung(raum: Raum) -> Optional[dict]:
    """
    Ermittelt das Opfer der Werwölfe.
    Bei Gleichstand entscheidet der Zufall (oder Urwolf/Anführer wenn implementiert).
    """
    logger.info(f"Evaluating werewolf vote for room {raum.code}")
    aktionen = SpielAktion.query.filter(
        SpielAktion.raum_id == raum.id,
        SpielAktion.runde == raum.runde,
        SpielAktion.phase == "werwolf_phase",
        SpielAktion.aktion_typ.in_(["werwolf_wahl", "toeten"]),
    ).all()

    if not aktionen:
        logger.info("No werewolf votes found")
        return None

    stimmen = {}
    for a in aktionen:
        if a.ziel_spieler_id:
            stimmen[a.ziel_spieler_id] = stimmen.get(a.ziel_spieler_id, 0) + 1

    if not stimmen:
        return None

    # Finde Ziel mit meisten Stimmen
    max_stimmen = max(stimmen.values())
    kandidaten = [zid for zid, s in stimmen.items() if s == max_stimmen]

    # Bei Gleichstand: Zufall
    opfer_id = random.choice(kandidaten)
    logger.info(f"Werewolf victim selected: {opfer_id}")

    return {"opfer_id": opfer_id}
