# Plan: Migrate All Roles to Dynamic Phase & Style System

**TL;DR:** Currently, frontend phase detection (`nachtPhasen`, `knownDayPhases`) and role styling (`.rolle-*` CSS classes) are partially hardcoded. This plan migrates ALL roles (~60+) to a fully dynamic system where roles define their own phase behavior, visual styles, and CSS classes via the existing `RollenInfo` and `Role` base class, eliminating hardcoded frontend lists.

## Current State Analysis

### Backend (Python)

- **Role System:** Well-structured with `Role` base class in `roles/base.py`
- **Registry:** Auto-discovery system in `roles/__init__.py` that imports all role files
- **Phase Generation:** `phase_generator.py` dynamically builds phases from active roles
- **RollenInfo:** Already has `icon`, `farbe`, `prioritaet`, but lacks `css_class`, gradient colors, emoji badges

### Frontend (JavaScript/CSS)

- **Hardcoded Phase Lists:**
  - `spiel.html:1446` - `nachtPhasen = ['nacht_start', 'seherin_phase', 'werwolf_phase', 'hexe_phase', 'amor_phase']`
  - `spiel.html:1899` - `knownDayPhases = ['tag_start', 'diskussion', 'abstimmung', ...]`
- **Hardcoded CSS:** `characters.css` has ~30 hardcoded `.rolle-*` selectors, missing many roles
- **Dynamic Loading:** Already uses `/api/role/{name}/ui` for button configs

### Role Files Structure

```
roles/
├── grundrollen/    (7 roles: amor, dorfbewohner, heiler, hexe, jaeger, seherin, werwolf)
├── dorfbewohner/   (9 roles)
├── werwolf/        (11 roles)
├── seher/          (7 roles)
├── hexe/           (5 roles)
├── heiler/         (4 roles)
├── jaeger/         (10 roles)
├── spezial/        (10 roles)
├── boese/          (3 roles)
├── solo/           (3 roles)
└── sonstige/       (10 roles)
```

**Total: ~69 roles** that need migration

---

## Steps

### Step 1: Extend `RollenInfo` with Visual/Styling Properties

**File:** `roles/base.py`

Add new fields to `RollenInfo` dataclass:

```python
@dataclass
class RollenInfo:
    # ...existing fields...

    # NEW: Visual styling fields
    css_class: str = ""  # Already exists but unused - use for override
    avatar_gradient_from: str = ""  # e.g., "#b91c1c"
    avatar_gradient_to: str = ""    # e.g., "#7f1d1d"
    avatar_border_color: str = ""   # e.g., "#ef4444"
    badge_emoji: str = ""           # e.g., "🐺"

    # Auto-generate css_class from name if not set
    @property
    def computed_css_class(self) -> str:
        if self.css_class:
            return self.css_class
        return self.name.lower().replace(" ", "-").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
```

### Step 2: Create API Endpoint `/api/roles/styles`

**File:** `app.py`

```python
@app.route('/api/roles/styles')
def get_all_role_styles():
    """Returns all role visual definitions for dynamic CSS."""
    styles = {}
    for role in RoleRegistry.get_all():
        info = role.info
        styles[info.name] = {
            "css_class": info.computed_css_class,
            "icon": info.icon,
            "farbe": info.farbe,
            "team": info.team.value,
            "avatar_gradient_from": info.avatar_gradient_from or info.farbe,
            "avatar_gradient_to": info.avatar_gradient_to or _darken_color(info.farbe),
            "avatar_border_color": info.avatar_border_color or info.farbe,
            "badge_emoji": info.badge_emoji or "",
        }
    return jsonify({"success": True, "styles": styles})
```

### Step 3: Refactor `characters.css` to Use Data Attributes

**File:** `static/css/characters.css`

Replace hardcoded selectors with dynamic `[data-role]` selectors:

```css
/* Dynamic role styling via data attributes */
.spieler-avatar[data-role] {
  /* Base styling - will be overridden by inline styles from API */
}

/* Keep a few common base styles for teams */
.spieler-avatar[data-team="werwolf"] {
  --glow-color: rgba(185, 28, 28, 0.4);
}

.spieler-avatar[data-team="dorf"] {
  --glow-color: rgba(59, 130, 246, 0.3);
}
```

### Step 4: Update `spiel.html` to Consume Dynamic Data

**File:** `templates/spiel.html`

Replace hardcoded arrays with API calls:

```javascript
// REMOVE these hardcoded arrays:
// let nachtPhasen = ['nacht_start', 'seherin_phase', ...];
// const knownDayPhases = ['tag_start', 'diskussion', ...];

// ADD: Fetch from API on load
let allPhaseInfo = {};
let allRoleStyles = {};

async function loadGameMetadata() {
  // Load phase info from existing API
  const phaseResp = await fetch(`/api/game/${raumCode}/phases`);
  const phaseData = await phaseResp.json();
  if (phaseData.success) {
    allPhaseInfo = phaseData.phase_info || {};
  }

  // Load role styles
  const styleResp = await fetch("/api/roles/styles");
  const styleData = await styleResp.json();
  if (styleData.success) {
    allRoleStyles = styleData.styles;
    applyDynamicRoleStyles();
  }
}

function isNightPhase(phase) {
  // Dynamic detection instead of hardcoded list
  const info = allPhaseInfo[phase];
  if (info && info.is_night !== undefined) return info.is_night;

  // Fallback heuristic
  return phase.includes("nacht") || phase.endsWith("_phase");
}

function applyDynamicRoleStyles() {
  // Apply inline styles to player cards based on role
  document.querySelectorAll(".spieler-avatar[data-role]").forEach((el) => {
    const roleName = el.dataset.role;
    const style = allRoleStyles[roleName];
    if (style) {
      el.style.setProperty(
        "--avatar-gradient-from",
        style.avatar_gradient_from,
      );
      el.style.setProperty("--avatar-gradient-to", style.avatar_gradient_to);
      el.style.setProperty("--avatar-border-color", style.avatar_border_color);
    }
  });
}
```

### Step 5: Migrate ALL Role Files

For each role file, add the styling fields. Example migration:

**Before (`roles/grundrollen/werwolf.py`):**

```python
@property
def info(self) -> RollenInfo:
    return RollenInfo(
        id=2,
        name="Werwolf",
        team=Team.WERWOLF,
        kategorie=Kategorie.GRUNDROLLEN,
        beschreibung="...",
        icon="fa-solid fa-paw",
        farbe="#dc2626",
        prioritaet=50,
        # ...
    )
```

**After:**

```python
@property
def info(self) -> RollenInfo:
    return RollenInfo(
        id=2,
        name="Werwolf",
        team=Team.WERWOLF,
        kategorie=Kategorie.GRUNDROLLEN,
        beschreibung="...",
        icon="fa-solid fa-paw",
        farbe="#dc2626",
        prioritaet=50,
        # NEW styling fields
        avatar_gradient_from="#b91c1c",
        avatar_gradient_to="#7f1d1d",
        avatar_border_color="#ef4444",
        badge_emoji="🐺",
        # ...
    )
```

### Step 6: Add CSS Generation Script (Optional)

**File:** `scripts/generate_role_css.py`

```python
"""Generate characters.css from role definitions."""
from roles import RoleRegistry

def generate_css():
    css_lines = ["/* AUTO-GENERATED - DO NOT EDIT */\n"]

    for role in RoleRegistry.get_all():
        info = role.info
        css_lines.append(f"""
.spieler-avatar.rolle-{info.computed_css_class} {{
    background: linear-gradient(145deg, {info.avatar_gradient_from} 0%, {info.avatar_gradient_to} 100%);
    border-color: {info.avatar_border_color};
}}
""")
        if info.badge_emoji:
            css_lines.append(f"""
.spieler-avatar.rolle-{info.computed_css_class}::after {{
    content: "{info.badge_emoji}";
    position: absolute;
    top: -8px;
    right: -8px;
    font-size: 0.9rem;
}}
""")

    return "\n".join(css_lines)
```

---

## Role Migration Checklist

### Grundrollen (7)

- [ ] `amor.py` - 💕
- [ ] `dorfbewohner.py` - 🏠
- [ ] `heiler.py` - 💚
- [ ] `hexe.py` - 🧪
- [ ] `jaeger.py` - 🎯
- [ ] `seherin.py` - 👁️
- [ ] `werwolf.py` - 🐺

### Dorfbewohner (9)

- [ ] `alter_mann.py`
- [ ] `dorfdepp.py` - 🤪
- [ ] `drei_brueder.py`
- [ ] `freimaurer.py`
- [ ] `griesgram.py`
- [ ] `hund.py` - 🐕
- [ ] `jesus.py`
- [ ] `tonks.py`
- [ ] `zwei_schwestern.py`

### Werwolf-Varianten (11)

- [ ] `einsamer_wolf.py`
- [ ] `lupin.py`
- [ ] `polarwolf.py`
- [ ] `teenager_werwolf.py`
- [ ] `urwolf.py`
- [ ] `weisser_wolf.py`
- [ ] `werwolfseherin.py`
- [ ] `wildes_kind.py`
- [ ] `wolfsjunge.py`
- [ ] `wolf_im_schafspelz.py`

### Seher (7)

- [ ] `aurenseherin.py`
- [ ] `baerenbaendiger.py`
- [ ] `demoskopin.py`
- [ ] `medium.py` - 🔮
- [ ] `paranormaler_ermittler_billig.py`
- [ ] `seherlehrling.py`
- [ ] `tratschweib.py`

### Hexe (5)

- [ ] `giftmischerin.py`
- [ ] `hahn.py`
- [ ] `kraeuterweib.py`
- [ ] `sandmann.py`
- [ ] `zauberer.py`

### Heiler (4)

- [ ] `ergebene_magd.py`
- [ ] `leibwaechter.py` - 🛡️
- [ ] `oma.py`
- [ ] `prostituierte.py` - 💋

### Jaeger (10)

- [ ] `buddler.py`
- [ ] `drachenbaendiger.py`
- [ ] `flammenmann.py`
- [ ] `gaukler.py`
- [ ] `inquisitor.py`
- [ ] `kamikaze.py`
- [ ] `koenig.py`
- [ ] `prinz.py`
- [ ] `pyromane.py`
- [ ] `tanklastwagenfahrer.py`

### Spezial (10)

- [ ] `buergermeister.py` - 👑
- [ ] `chemielaborant.py`
- [ ] `dunkler_priester.py`
- [ ] `fluechtlinge.py`
- [ ] `hure.py`
- [ ] `mordlustiger.py`
- [ ] `nutte.py`
- [ ] `rabe.py`
- [ ] `selbstmoerder.py`
- [ ] `zahnarzt.py`

### Böse (3)

- [ ] `hexenmeister.py`
- [ ] `vampir.py` - 🦇
- [ ] `zombie.py` - 🧟

### Solo (3)

- [ ] `floetenspieler.py`
- [ ] `henker.py` - ⚔️
- [ ] `selbstmoerder.py`

### Sonstige (10)

- [ ] `buergermeister.py`
- [ ] `dieb.py`
- [ ] `doppelgaenger.py`
- [ ] `engel.py` - 😇
- [ ] `gerber.py`
- [ ] `kleines_maedchen.py`
- [ ] `kuh.py`
- [ ] `putzfrau.py`
- [ ] `suendenbock.py`

---

## Further Considerations

1. **Performance:** Cache role styles in localStorage with version key from server
2. **Backward Compatibility:** DO NOT Keep legacy `.rolle-werwolf` classes as aliases during migration
3. **Test Coverage:** Extend `tests/test_all_roles.py` to verify all roles have styling fields
4. **Phase Info API:** Extend `/api/game/{code}/phases` to include `is_night` boolean per phase

## Dependencies

- `phase_generator.py` - Already generates dynamic phases, no changes needed
- `registry.py` - Already collects all roles, no changes needed
- `game_logic.py` - May need updates if phase detection logic is refactored
