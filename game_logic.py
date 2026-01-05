from datetime import datetime, timedelta
import random
import json
from typing import List, Tuple, Optional
from models import db, Raum, Spieler, SpielAktion, SpielLog, ErzaehlerEvent

# Get PHASEN from centralized module
from phases import get_phase_list

PHASEN = get_phase_list()


def berechne_rollen(spieler_anzahl: int, mit_erzaehler: bool = False) -> dict:
    """
    Berechnet die Rollenverteilung dynamisch basierend auf der Registry.

    Verwendet DistributionConfig der einzelnen Rollen anstelle von hardcoded Logik.
    """
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
        True wenn erfolgreich gestartet"""
    from roles import RoleRegistry

    spieler = Spieler.query.filter_by(raum_id=raum.id).all()

    if len(spieler) < 5:
        return False

    verteile_rollen(raum)

    raum.spiel_gestartet = True
    raum.aktuelle_phase = "rollen_verteilt"
    raum.runde = 1

    # Reset Spieler Status und initialisiere Rollen-Zustand
    for s in spieler:
        s.ist_am_leben = True
        s.status = "aktiv"
        # Initialize role-specific state from role definitions
        RoleRegistry.init_player_state(s)

    log_eintrag(raum.id, "Das Spiel hat begonnen! Die Rollen wurden verteilt.")

    db.session.commit()
    return True


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
    from scheduler import get_next_phase_state

    # 1. Berechne nächsten Zustand
    next_state = get_next_phase_state(raum)

    # 2. Update Raum
    raum.aktuelle_phase = next_state.phase

    # Store phase metadata (active role, display info) in JSON
    # This allows generic frontend handling
    data = {}
    if raum.phase_data:
        try:
            data = json.loads(raum.phase_data)
        except:
            data = {}

    data["active_role"] = next_state.active_role
    data["display_info"] = next_state.display_info

    raum.phase_data = json.dumps(data)

    # Reset Timer if phase changed?
    # (Or scheduler handles it? Scheduler is stateless.)
    # TODO: Start Timer for new phase if needed.

    db.session.commit()

    return raum.aktuelle_phase


# =============================================================================
# ROLE-DRIVEN NIGHT EXECUTION
# =============================================================================


# =============================================================================
# ROLE-DRIVEN NIGHT EXECUTION
# =============================================================================

# Deprecated night functions (get_active_roles_for_night, get_next_role_to_act,
# is_night_complete) have been replaced by scheduler.py.
# Kept ist_werwolf_rolle as general helper.


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

    Verwendet dynamische WinConditions aus der RoleRegistry.
    """
    from roles import RoleRegistry
    from roles.base import SpielKontext, Phase
    from roles.enums import Team

    lebende = hole_lebende_spieler(raum, ohne_erzaehler=True)

    # 1. Baue Kontext für Checks
    kontext = SpielKontext(
        raum_id=raum.id,
        runde=raum.runde,
        phase=Phase.TAG_START,  # Phase ist hier irrelevant für Win-Check
        aktiver_spieler_id=0,
        lebende_spieler=[s.id for s in lebende],
        tote_spieler=[],  # Optimierung: Tote werden selten gebraucht für Win-Check
    )

    # Populate Kontext-Daten
    for s in lebende:
        role = RoleRegistry.get(s.rolle)
        if role:
            kontext.spieler_rollen[s.id] = s.rolle
            kontext.spieler_teams[s.id] = role.info.team
            kontext.spieler_namen[s.id] = s.name

    # 2. Sammle alle WinConditions (auch von toten Spielern, z.B. Amor)
    conditions = []
    alle_spieler = Spieler.query.filter_by(raum_id=raum.id, ist_erzaehler=False).all()

    for s in alle_spieler:
        role = RoleRegistry.get(s.rolle)
        if role:
            for cond in role.get_win_conditions():
                conditions.append((cond, s))

    # 3. Sortiere nach Priorität (höhere zuerst)
    conditions.sort(key=lambda x: x[0].priority, reverse=True)

    # 4. Prüfe Conditions
    for cond, owner in conditions:
        try:
            if cond.check_func(owner, kontext):
                # GEWONNEN!
                winner_team = (
                    cond.team_override or RoleRegistry.get(owner.rolle).info.team
                )

                winners = []
                if winner_team == Team.VERLIEBTE:
                    # Spezialfall Verliebte
                    # Finde das Paar via Owner (Amor hat check gemacht, aber Owner ist Amor?
                    # Nein, Owner of condition is Amor, and Amor might be dead.
                    # WAIT. Roles defining conditions usually assume the role is ALIVE.
                    # Amor condition ("Lovers Win") should be checked even if Amor is DEAD?
                    # Currently I iterate LEBENDE spieler. So if Amor is dead, Lovers can't win?
                    # WRONG. Amor logic usually persists.
                    # FIX: I must iterate ALL roles in registry or handle Amor separately?
                    # Better: Amor attaches WinCondition to the LOVERS? Or Global Win Condition?
                    # For now, let's assume active players trigger win conditions.
                    # If Amor dies, Lovers can still win. But who checks it?
                    # The Lovers themselves don't have the WinCondition attached.
                    # WORKAROUND: Werwolf and Dorf checks cover 99% cases. Lovers check covers the rest.
                    # If Amor is dead, we need a way to check Lovers Win.
                    # Maybe Lovers (Verliebte) implies a Team Change?
                    pass

                # Determine winners based on Team
                winning_players = []
                for s in lebende:
                    r = RoleRegistry.get(s.rolle)
                    if not r:
                        continue

                    # Check Team
                    if r.info.team == winner_team:
                        winning_players.append(s.name)

                    # Check Global State "Verliebte" matches Team
                    # (Simplification: Just return names of team members)

                # Special logic for Lovers names if Team.VERLIEBTE
                if winner_team == Team.VERLIEBTE:
                    # Find actual lovers
                    from roles.base import get_spieler_state

                    # Iterate all alive and check if they are "verliebt"
                    # (This is inefficient but safe)
                    lovers = []
                    for l in lebende:
                        if get_spieler_state(l, "global.verliebt_mit_id"):
                            lovers.append(l.name)
                    winning_players = lovers

                return {
                    "gewinner": winner_team.value,
                    "nachricht": cond.description,
                    "spieler": winning_players,
                }

        except Exception as e:
            print(f"Error checking win condition {cond.id}: {e}")
            continue

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

    # --------------------------------------------------------------------------
    # DYNAMIC LOSE/TRIGGER CONDITIONS
    # --------------------------------------------------------------------------
    from roles import RoleRegistry
    from roles.base import SpielKontext, Phase

    # 1. Sammle Definitionen
    lose_defs = {}
    for r in RoleRegistry.get_all_roles():
        for lc in r.get_lose_conditions():
            lose_defs[lc.id] = lc

    # 2. Prüfe Conditions für lebende Spieler
    # (z.B. Wildes Kind wenn Vorbild stirbt, Amor-Verliebte wenn Partner stirbt)
    raum_obj = (
        unabh_raum if "unabh_raum" in locals() else Raum.query.get(spieler.raum_id)
    )
    lebende = hole_lebende_spieler(raum_obj, ohne_erzaehler=True)

    kontext = SpielKontext(
        raum_id=raum_obj.id,
        runde=raum_obj.runde,
        phase=Phase.NACHT,
        aktiver_spieler_id=0,
        lebende_spieler=[s.id for s in lebende],
        tote_spieler=[],
    )
    trigger_data = {"opfer": spieler, "todesart": todesart}

    for s in list(lebende):
        if not s.ist_am_leben:
            continue

        active_conds = s.get_lose_conditions()
        for cond_id, cond_ctx in active_conds.items():
            defn = lose_defs.get(cond_id)
            if defn and defn.trigger == "on_spieler_stirbt":
                try:
                    if defn.check_func(s, kontext, trigger_data):
                        log_eintrag(
                            raum_obj.id, f"{s.name} ist betroffen: {defn.description}"
                        )
                        if defn.effect == "death":
                            toete_spieler(s, todesart="kettenreaktion")
                            ergebnis["folge_aktionen"].append(f"kettenreaktion_{s.id}")
                except Exception as e:
                    print(f"Error executing LoseCondition {cond_id}: {e}")

    # Legacy-Logik für Abwärtskompatibilität
    # Jaeger stirbt - kann noch schiessen
    if spieler.rolle == "Jäger" and getattr(spieler, "jaeger_schuss", True):
        ergebnis["folge_aktionen"].append("jaeger_schuss")

    # Verliebter stirbt - Partner stirbt auch
    verliebt_mit_id = spieler.get_state("global.verliebt_mit_id")
    if verliebt_mit_id:
        partner = Spieler.query.get(verliebt_mit_id)
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
    Erstellt einen Spiellog-Eintrag und sendet ihn via Socket.

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

    # Emit log update via socket for real-time UI updates
    try:
        from app import socketio

        raum = Raum.query.get(raum_id)
        if raum:
            socketio.emit(
                "spiel_log",
                {
                    "nachricht": nachricht,
                    "sichtbar_fuer": sichtbar_fuer,
                    "zeitpunkt": (
                        eintrag.zeitpunkt.strftime("%H:%M") if eintrag.zeitpunkt else ""
                    ),
                },
                room=raum.code,
            )
    except Exception as e:
        # Don't fail if socket emission fails
        print(f"[Log] Warnung: Konnte Log nicht via Socket senden: {e}")


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
    opfer_ids = [
        int(sid) for sid, count in ziel_stimmen.items() if count == max_stimmen
    ]

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
