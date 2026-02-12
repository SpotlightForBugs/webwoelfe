/**
 * Village3D Integration — Socket.IO ↔ Babylon.js bridge
 *
 * Listens for game events on a Socket.IO client and forwards them
 * to a Village3DBabylon renderer instance.  Dispatches CustomEvents
 * on `window` so the surrounding UI can react without coupling to
 * this module.
 *
 * Replaces the old VillageIntegration.ts (TypeScript / PlayCanvas).
 */

/** @param {number} ms */
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

export class VillageIntegration {
  /** @type {import('socket.io-client').Socket} */
  #socket;

  /** @type {import('./village3d_babylon.js').Village3DBabylon} */
  #village;

  /** @type {AbortController} – used to tear down window listeners */
  #abort = new AbortController();

  /**
   * @param {import('socket.io-client').Socket} socket  Socket.IO client
   * @param {import('./village3d_babylon.js').Village3DBabylon} village3d  Babylon renderer
   */
  constructor(socket, village3d) {
    this.#socket = socket;
    this.#village = village3d;

    this.#bindSocketEvents();
  }

  // ===========================================================================
  // Socket.IO listeners
  // ===========================================================================

  #bindSocketEvents() {
    const s = this.#socket;

    s.on('phase_update',         (d) => this.#onPhaseUpdate(d));
    s.on('spieler_gestorben',    (d) => this.#onSpielerGestorben(d));
    s.on('stimme_abgegeben',     (d) => this.#onStimmeAbgegeben(d));
    s.on('hinweis_zeigen',       (d) => this.#onHinweisZeigen(d));
    s.on('abstimmung_ergebnis',  (d) => this.#onAbstimmungErgebnis(d));
    s.on('spiel_ende',           (d) => this.#onSpielEnde(d));
    s.on('nacht_ergebnis',       (d) => this.#onNachtErgebnis(d));
    s.on('chat_nachricht',       (d) => this.#onChatNachricht(d));
    s.on('aktion_bestaetigt',    (d) => this.#onAktionBestaetigt(d));
  }

  // ===========================================================================
  // Event handlers
  // ===========================================================================

  /**
   * phase_update
   * @param {{
   *   phase: string,
   *   runde?: number,
   *   display_info?: object,
   *   erzaehler_text?: string,
   *   is_night?: boolean,
   *   active_role?: string,
   *   werwolf_opfer_id?: number,
   *   werwolf_opfer_name?: string
   * }} data
   */
  #onPhaseUpdate(data) {
    const {
      phase,
      runde,
      display_info,
      erzaehler_text,
      is_night = false,
      active_role,
      werwolf_opfer_id,
      werwolf_opfer_name,
    } = data;

    // Day / night lighting
    this.#village.setTimeOfDay(is_night);

    // Victim highlight
    if (werwolf_opfer_id) {
      this.#village.highlightVictim(werwolf_opfer_id);
    } else {
      this.#village.clearVictimHighlight();
    }

    // Notify UI
    this.#dispatch('village3d:phaseOverlay', {
      phase,
      runde,
      display_info,
      erzaehler_text,
      active_role,
      werwolf_opfer_id,
      werwolf_opfer_name,
    });

    // Top bar (only if the village exposes it)
    if (typeof this.#village.updateTopBar === 'function') {
      this.#village.updateTopBar(phase, runde);
    }
  }

  /**
   * spieler_gestorben
   * @param {{
   *   spieler_id: number,
   *   spieler_name: string,
   *   todesart: string,
   *   display_text?: string
   * }} data
   */
  async #onSpielerGestorben(data) {
    const { spieler_id, spieler_name, todesart, display_text } = data;

    // Camera focus on the dying player
    this.#village.focusOnPlayer(spieler_id);
    this.#dispatch('village3d:cameraFocus', { spieler_id });

    // Short pause so the camera arrives before the status changes
    await delay(500);

    this.#village.updatePlayerStatus(spieler_id, false);

    // Death text
    const text = display_text || `${spieler_name} ist gestorben.`;
    this.#dispatch('village3d:eliminationText', { spieler_id, spieler_name, todesart, text });

    // Visual effect
    this.#village.showActionEffect(spieler_id, 'attack');
  }

  /**
   * stimme_abgegeben
   * @param {{
   *   waehler_id: number,
   *   waehler_name: string,
   *   ziel_id: number,
   *   ziel_name: string
   * }} data
   */
  #onStimmeAbgegeben(data) {
    const { waehler_name, ziel_id } = data;

    this.#village.showVoteIndicator(ziel_id, waehler_name);
    this.#village.highlightPlayer(ziel_id, '#ffd700');
  }

  /**
   * hinweis_zeigen
   * @param {{
   *   spielerId?: number,
   *   spieler_id?: number,
   *   hintTyp?: string,
   *   type?: string,
   *   typ?: string
   * }} data
   */
  #onHinweisZeigen(data) {
    const playerId = data.spielerId ?? data.spieler_id;
    const type     = data.hintTyp   ?? data.type ?? data.typ;

    if (playerId != null && type) {
      this.#village.showHint(playerId, type);
    }
  }

  /**
   * abstimmung_ergebnis
   * @param {{
   *   hingerichtet_id?: number,
   *   hingerichtet_name?: string,
   *   display_text?: string,
   *   stimmen: Array<{spieler_id: number, stimmen: number}>
   * }} data
   */
  async #onAbstimmungErgebnis(data) {
    const { hingerichtet_id, hingerichtet_name, display_text } = data;

    if (hingerichtet_id) {
      this.#village.focusOnPlayer(hingerichtet_id);
      this.#dispatch('village3d:cameraFocus', { spieler_id: hingerichtet_id });

      await delay(500);

      this.#village.updatePlayerStatus(hingerichtet_id, false);

      const text = display_text || `${hingerichtet_name} wurde hingerichtet.`;
      this.#dispatch('village3d:eliminationText', {
        spieler_id: hingerichtet_id,
        spieler_name: hingerichtet_name,
        todesart: 'vote',
        text,
      });
    }
  }

  /**
   * spiel_ende
   * @param {{
   *   gewinner: string,
   *   display_title?: string,
   *   display_message?: string,
   *   spieler?: Array<{id:number, name:string, rolle:string, ist_gewinner:boolean, ist_am_leben:boolean}>
   * }} data
   */
  #onSpielEnde(data) {
    this.#dispatch('village3d:gameEnd', {
      gewinner:        data.gewinner,
      display_title:   data.display_title   || 'Spiel beendet',
      display_message: data.display_message || `${data.gewinner} haben gewonnen!`,
      spieler:         data.spieler || [],
    });
  }

  /**
   * nacht_ergebnis
   * @param {{ tote?: Array<{id:number, name:string, todesart:string, display_text?:string}> }} data
   */
  async #onNachtErgebnis(data) {
    const tote = data.tote;
    if (!Array.isArray(tote) || tote.length === 0) return;

    for (const death of tote) {
      this.#village.focusOnPlayer(death.id);
      this.#dispatch('village3d:cameraFocus', { spieler_id: death.id });

      await delay(500);

      this.#village.updatePlayerStatus(death.id, false);

      const text = death.display_text || `${death.name} wurde getötet.`;
      this.#dispatch('village3d:eliminationText', {
        spieler_id: death.id,
        spieler_name: death.name,
        todesart: death.todesart,
        text,
      });

      // Pause between deaths so the player can follow along
      await delay(1000);
    }
  }

  /**
   * chat_nachricht
   * @param {{ spieler_id: number, name: string, nachricht: string }} data
   */
  #onChatNachricht(data) {
    const { spieler_id, name, nachricht } = data;

    this.#village.showChatBubble(spieler_id, nachricht);
    this.#village.addChatMessage(name, nachricht);
  }

  /**
   * aktion_bestaetigt
   * @param {{ erfolg: boolean, nachricht: string, effekt?: string, ziel_id?: number }} data
   */
  #onAktionBestaetigt(data) {
    const { erfolg, effekt, ziel_id } = data;

    if (erfolg && effekt && ziel_id != null) {
      this.#village.showActionEffect(ziel_id, effekt);
    }
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  /**
   * Dispatch a CustomEvent on window.
   * @param {string} name
   * @param {object} detail
   */
  #dispatch(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  // ===========================================================================
  // Cleanup
  // ===========================================================================

  destroy() {
    this.#abort.abort();

    const events = [
      'phase_update',
      'spieler_gestorben',
      'stimme_abgegeben',
      'hinweis_zeigen',
      'abstimmung_ergebnis',
      'spiel_ende',
      'nacht_ergebnis',
      'chat_nachricht',
      'aktion_bestaetigt',
    ];

    for (const ev of events) {
      this.#socket.off(ev);
    }
  }
}

export default VillageIntegration;
