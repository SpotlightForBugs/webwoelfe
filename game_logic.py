"""
Spiellogik fuer das Werwolf-Spiel
"""
import random
from models import db, Raum, Spieler, SpielAktion, SpielLog, ROLLEN, PHASEN


def berechne_rollen(spieler_anzahl: int, mit_erzaehler: bool = False) -> dict:
    """
    Berechnet die Rollenverteilung basierend auf der Spieleranzahl.
    
    Args:
        spieler_anzahl: Anzahl der Spieler
        mit_erzaehler: Ob ein Erzaehler dabei ist
        
    Returns:
        Dictionary mit Rollen und deren Anzahl
    """
    effektive_anzahl = spieler_anzahl - (1 if mit_erzaehler else 0)
    
    werwolf_anzahl = max(1, effektive_anzahl // 4)
    hexe_anzahl = 1 if effektive_anzahl >= 6 else 0
    seherin_anzahl = 1 if effektive_anzahl >= 5 else 0
    jaeger_anzahl = 1 if effektive_anzahl >= 10 else 0
    armor_anzahl = 1 if effektive_anzahl >= 8 else 0
    
    dorfbewohner_anzahl = effektive_anzahl - werwolf_anzahl - hexe_anzahl - seherin_anzahl - jaeger_anzahl - armor_anzahl
    
    rollen = {}
    
    if mit_erzaehler:
        rollen['Erzaehler'] = 1
        
    rollen['Werwolf'] = werwolf_anzahl
    
    if hexe_anzahl > 0:
        rollen['Hexe'] = hexe_anzahl
    if seherin_anzahl > 0:
        rollen['Seherin'] = seherin_anzahl
    if jaeger_anzahl > 0:
        rollen['Jaeger'] = jaeger_anzahl
    if armor_anzahl > 0:
        rollen['Armor'] = armor_anzahl
        
    if dorfbewohner_anzahl > 0:
        rollen['Dorfbewohner'] = dorfbewohner_anzahl
    
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
        spieler_anzahl + (1 if erzaehler else 0),
        mit_erzaehler=bool(erzaehler)
    )
    
    # Erstelle Liste aller zu verteilenden Rollen
    rollen_liste = []
    for rolle, anzahl in rollen_verteilung.items():
        if rolle != 'Erzaehler':
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
        erzaehler.rolle = 'Erzaehler'
        ergebnis[erzaehler.id] = 'Erzaehler'
    
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
    raum.aktuelle_phase = 'rollen_verteilt'
    raum.runde = 1
    
    # Reset Spieler Status
    for s in spieler:
        s.ist_am_leben = True
        s.status = 'aktiv'
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
    return Spieler.query.filter_by(raum_id=raum.id, rolle=rolle, ist_am_leben=True).first() is not None


def phasennamen_zu_rollen_mapping() -> dict:
    """
    Erstellt ein Mapping zwischen Phasennamen und erforderlichen Rollen.
    
    Returns:
        Dictionary mit Phase zu Rolle Mapping
    """
    return {
        'dieb_phase': 'Dieb',
        'doppelgaenger_phase': 'Doppelgaenger',
        'armor_phase': 'Armor',
        'priester_dunkel_phase': 'Dunkler Priester',
        'wildes_kind_phase': 'Wildes Kind',
        'hund_phase': 'Hund',
        'schwestern_phase': 'Zwei Schwestern',
        'brueder_phase': 'Zwei Brueder',
        'freimaurer_phase': 'Freimaurer',
        'fluechtlinge_phase': 'Fluechtlinge',
        'sandmann_phase': 'Sandmann',
        'seherin_phase': 'Seherin',
        'seherlehrling_phase': 'Seherlehrling',
        'aurenseherin_phase': 'Aurenseherin',
        'medium_phase': 'Medium',
        'tratschweib_phase': 'Tratschweib',
        'paranormal_billig_phase': 'Paranormal Billig',
        'werwolfseherin_phase': 'Werwolfseherin',
        'heiler_phase': 'Heiler',
        'leibwaechter_phase': 'Leibwaechter',
        'hure_phase': 'Hure',
        'prostituierte_phase': 'Prostituierte',
        'nutte_phase': 'Nutte',
        'einsamerwolf_phase': 'Einsamer Wolf',
        'urwolf_phase': 'Urwolf',
        'weisser_wolf_phase': 'Weisser Wolf',
        'mordlustiger_phase': 'Mordlustiger',
        'hexe_phase': 'Hexe',
        'hexenmeister_phase': 'Hexenmeister',
        'giftmischerin_phase': 'Giftmischerin',
        'kraeuterweib_phase': 'Kraeuterweib',
        'zauberer_phase': 'Zauberer',
        'zahnarzt_phase': 'Zahnarzt',
        'rabe_phase': 'Rabe',
        'floetenspieler_phase': 'Floetenspieler',
        'vampir_phase': 'Vampir',
        'zombie_phase': 'Zombie',
        'pyromane_phase': 'Pyromane',
        'tonks_phase': 'Tonks',
        'buddler_phase': 'Buddler',
        'baerenbaendiger_brummen': 'Baerenbandiger',
        'demoskopin_info': 'Demoskopin',
        'prinz_enthuellung': 'Prinz',
        'jaeger_phase': 'Jaeger',
        'kamikaze_phase': 'Kamikaze',
        'hahn_enthuellung': 'Hahn',
        'putzfrau_info': 'Putzfrau',
    }


def naechste_phase(raum: Raum) -> str:
    """
    Wechselt zur naechsten Spielphase.
    
    Args:
        raum: Der Spielraum
        
    Returns:
        Name der neuen Phase
    """
    aktuelle_idx = PHASEN.index(raum.aktuelle_phase)
    phase_mapping = phasennamen_zu_rollen_mapping()
    
    # Spezielle Phasen-Logik
    if raum.aktuelle_phase == 'armor_phase':
        # Armor nur in Runde 1
        if raum.runde > 1:
            naechste_idx = PHASEN.index('seherin_phase')
        else:
            naechste_idx = aktuelle_idx + 1
    elif raum.aktuelle_phase == 'verliebte_info':
        if raum.runde > 1:
            naechste_idx = PHASEN.index('seherin_phase')
        else:
            naechste_idx = aktuelle_idx + 1
    elif raum.aktuelle_phase == 'tag_ende':
        raum.runde += 1
        naechste_idx = PHASEN.index('nacht_start')
    elif raum.aktuelle_phase == 'spiel_ende':
        naechste_idx = aktuelle_idx  # Bleibt bei spiel_ende
    else:
        naechste_idx = aktuelle_idx + 1
    
    # Pruefe ob die naechste Phase eine erforderliche Rolle hat
    max_iterations = len(PHASEN)
    iterations = 0
    while iterations < max_iterations:
        if naechste_idx >= len(PHASEN):
            naechste_idx = PHASEN.index('nacht_start')
            raum.runde += 1
            iterations += 1
            continue
        
        naechste_phase_name = PHASEN[naechste_idx]
        
        # Prüfe ob diese Phase eine erforderliche Rolle benötigt
        if naechste_phase_name in phase_mapping:
            erforderliche_rolle = phase_mapping[naechste_phase_name]
            # Wenn Rolle nicht vorhanden ist, überspringe diese Phase
            if not hat_spieler_mit_rolle(raum, erforderliche_rolle):
                naechste_idx += 1
                iterations += 1
                continue
        
        # Phase ist gültig
        break
    
    if naechste_idx >= len(PHASEN):
        naechste_idx = PHASEN.index('nacht_start')
        raum.runde += 1
        
    raum.aktuelle_phase = PHASEN[naechste_idx]
    db.session.commit()
    
    return raum.aktuelle_phase


def pruefe_spielende(raum: Raum) -> dict | None:
    """
    Prueft ob das Spiel zu Ende ist.
    
    Args:
        raum: Der Spielraum
        
    Returns:
        Dictionary mit Gewinner-Info oder None wenn Spiel weitergeht
    """
    lebende = Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False).all()
    
    werwoelfe = [s for s in lebende if s.rolle == 'Werwolf']
    dorfbewohner = [s for s in lebende if s.rolle != 'Werwolf']
    
    # Verliebten-Check
    verliebte = Spieler.query.filter(
        Spieler.raum_id == raum.id,
        Spieler.verliebt_mit_id.isnot(None)
    ).all()
    
    if len(verliebte) == 2 and all(v.ist_am_leben for v in verliebte):
        # Pruefen ob nur noch die Verliebten leben
        if len(lebende) == 2:
            rollen = {v.rolle for v in verliebte}
            if 'Werwolf' in rollen and len(rollen) > 1:
                return {
                    'gewinner': 'verliebte',
                    'nachricht': 'Die Verliebten haben gewonnen! Ihre Liebe hat alle ueberwunden.',
                    'spieler': [v.name for v in verliebte]
                }
    
    # Keine Werwoelfe mehr
    if len(werwoelfe) == 0:
        return {
            'gewinner': 'dorf',
            'nachricht': 'Das Dorf hat gewonnen! Alle Werwoelfe wurden eliminiert.',
            'spieler': [s.name for s in dorfbewohner]
        }
    
    # Werwoelfe in Ueberzahl oder Gleichstand
    if len(werwoelfe) >= len(dorfbewohner):
        return {
            'gewinner': 'werwolf',
            'nachricht': 'Die Werwoelfe haben gewonnen! Das Dorf ist gefallen.',
            'spieler': [s.name for s in werwoelfe]
        }
    
    return None


def toete_spieler(spieler: Spieler, todesart: str = 'unbekannt') -> dict:
    """
    Toetet einen Spieler.
    
    Args:
        spieler: Der zu toetende Spieler
        todesart: Art des Todes (werwolf, abstimmung, hexe, jaeger)
        
    Returns:
        Dictionary mit Todes-Informationen
    """
    spieler.ist_am_leben = False
    spieler.status = 'tot'
    
    ergebnis = {
        'spieler_id': spieler.id,
        'spieler_name': spieler.name,
        'rolle': spieler.rolle,
        'todesart': todesart,
        'folge_aktionen': []
    }
    
    # Jaeger stirbt - kann noch schiessen
    if spieler.rolle == 'Jaeger' and spieler.jaeger_schuss:
        ergebnis['folge_aktionen'].append('jaeger_schuss')
    
    # Verliebter stirbt - Partner stirbt auch
    if spieler.verliebt_mit_id:
        partner = Spieler.query.get(spieler.verliebt_mit_id)
        if partner and partner.ist_am_leben:
            ergebnis['folge_aktionen'].append('partner_stirbt')
            ergebnis['partner'] = partner.name
    
    log_eintrag(
        spieler.raum_id,
        f"{spieler.name} ist gestorben. (Todesart: {todesart})"
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
        phase='werwolf_phase',
        aktion_typ='werwolf_wahl'
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
        'opfer_id': opfer_id,
        'opfer_name': opfer.name if opfer else 'Unbekannt',
        'stimmen': max_stimmen
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
        raum_id=raum.id,
        runde=raum.runde,
        phase='abstimmung',
        aktion_typ='tag_wahl'
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
        return {'kein_opfer': True, 'nachricht': 'Niemand wurde gewaehlt.'}
    
    # Finde Opfer (meiste Stimmen)
    max_stimmen = max(stimmen.values())
    opfer_ids = [sid for sid, count in stimmen.items() if count == max_stimmen]
    
    # Mehrheit erforderlich
    lebende = Spieler.query.filter_by(raum_id=raum.id, ist_am_leben=True, ist_erzaehler=False).count()
    if max_stimmen <= lebende // 2:
        return {'kein_opfer': True, 'nachricht': 'Keine Mehrheit erreicht.'}
    
    # Bei Gleichstand: niemand stirbt
    if len(opfer_ids) > 1:
        return {'kein_opfer': True, 'nachricht': 'Stimmengleichheit - niemand stirbt.'}
    
    opfer_id = opfer_ids[0]
    opfer = Spieler.query.get(opfer_id)
    
    return {
        'opfer_id': opfer_id,
        'opfer_name': opfer.name if opfer else 'Unbekannt',
        'opfer_rolle': opfer.rolle if opfer else 'Unbekannt',
        'stimmen': max_stimmen
    }


def log_eintrag(raum_id: int, nachricht: str, sichtbar_fuer: str = 'alle'):
    """
    Erstellt einen Spiellog-Eintrag.
    
    Args:
        raum_id: ID des Raums
        nachricht: Log-Nachricht
        sichtbar_fuer: Wer kann den Eintrag sehen
    """
    eintrag = SpielLog(
        raum_id=raum_id,
        nachricht=nachricht,
        sichtbar_fuer=sichtbar_fuer
    )
    db.session.add(eintrag)
    db.session.commit()


def registriere_aktion(raum_id: int, runde: int, phase: str, 
                       aktion_typ: str, von_spieler_id: int, 
                       ziel_spieler_id: int = None):
    """
    Registriert eine Spielaktion.
    """
    aktion = SpielAktion(
        raum_id=raum_id,
        runde=runde,
        phase=phase,
        aktion_typ=aktion_typ,
        von_spieler_id=von_spieler_id,
        ziel_spieler_id=ziel_spieler_id
    )
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
        raum_id=raum.id, 
        rolle=rolle,
        ist_am_leben=True
    ).all()


def hat_spieler_gewaehlt(spieler: Spieler, raum: Raum, phase: str) -> bool:
    """
    Prueft ob ein Spieler in der aktuellen Phase bereits gewaehlt hat.
    """
    aktion = SpielAktion.query.filter_by(
        raum_id=raum.id,
        runde=raum.runde,
        phase=phase,
        von_spieler_id=spieler.id
    ).first()
    return aktion is not None


def alle_haben_gewaehlt(raum: Raum, phase: str, rolle: str = None) -> bool:
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


