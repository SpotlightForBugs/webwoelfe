import os
from roles import RoleRegistry
from roles.base import RollenInfo
from logger import logger

def generate_characters_css():
    """
    Generates static/css/characters.css based on Role definitions.
    """
    logger.info("Generating characters.css from Role definitions...")

    css_content = [
        "/**",
        " * Character & Village Styling",
        " * AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY",
        " * Generated from Role definitions on server start",
        " */",
        "",
        "/* ============================================================================",
        "   BASE AVATAR STYLING",
        "   ============================================================================ */",
        "",
        ".spieler-avatar {",
        "  width: 70px;",
        "  height: 70px;",
        "  border-radius: 50%;",
        "  margin: 0 auto 0.75rem;",
        "  display: flex;",
        "  align-items: center;",
        "  justify-content: center;",
        "  font-size: 2rem;",
        "  color: white;",
        "  position: relative;",
        "  background: linear-gradient(145deg, #4a5568 0%, #2d3748 100%);",
        "  border: 3px solid #5a6678;",
        "  box-shadow:",
        "    0 4px 15px rgba(0, 0, 0, 0.3),",
        "    inset 0 2px 10px rgba(255, 255, 255, 0.1);",
        "  transition: all 0.3s ease;",
        "}",
        "",
        "/* Aura/Glow effect behind avatar */",
        ".spieler-avatar::before {",
        "  content: '';",
        "  position: absolute;",
        "  inset: -6px;",
        "  border-radius: 50%;",
        "  background: transparent;",
        "  z-index: -1;",
        "  transition: all 0.3s ease;",
        "}",
        "",
        ".spieler-card:hover:not(.tot) .spieler-avatar::before {",
        "  background: radial-gradient(",
        "    circle,",
        "    rgba(212, 175, 55, 0.2) 0%,",
        "    transparent 70%",
        "  );",
        "}",
        "",
        "/* Character icons instead of initials */",
        ".spieler-avatar i {",
        "  font-size: 1.8rem;",
        "}",
        "",
        "/* ============================================================================",
        "   DYNAMIC ROLE STYLES",
        "   ============================================================================ */",
        ""
    ]

    # Helper to darken color
    def darken_color(hex_color, factor=0.8):
        if not hex_color or not hex_color.startswith('#'):
            return hex_color
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
        except:
            return hex_color

    # Iterate all roles
    for role in RoleRegistry.get_all():
        info = role.info
        css_class = info.computed_css_class

        # Defaults if not set
        grad_from = info.avatar_gradient_from or info.farbe or "#4a5568"
        grad_to = info.avatar_gradient_to or darken_color(grad_from)
        border = info.avatar_border_color or info.farbe or "#5a6678"
        badge = info.badge_emoji or ""

        # Generate CSS block for this role
        role_css = [
            f"/* {info.name} */",
            f".spieler-avatar.rolle-{css_class},",
            f".spieler-avatar[data-role='{css_class}'] {{",
            f"  background: linear-gradient(145deg, {grad_from} 0%, {grad_to} 100%);",
            f"  border-color: {border};",
            "}",
            ""
        ]

        if badge:
            role_css.extend([
                f".spieler-avatar.rolle-{css_class}::after,",
                f".spieler-avatar[data-role='{css_class}']::after {{",
                f"  content: '{badge}';",
                "  position: absolute;",
                "  top: -8px;",
                "  right: -8px;",
                "  font-size: 1rem;",
                "  filter: drop-shadow(0 0 5px rgba(0, 0, 0, 0.5));",
                "}",
                ""
            ])

        # Badge styling for role tags
        role_css.extend([
            f".rolle-badge.rolle-{css_class} {{",
            f"  background: linear-gradient(135deg, {grad_from} 0%, {grad_to} 100%);",
            "  color: white;",
            "}",
            ""
        ])

        css_content.extend(role_css)

    # Add Team Fallbacks
    css_content.extend([
        "/* ============================================================================",
        "   TEAM FALLBACKS",
        "   ============================================================================ */",
        "",
        "/* Werwolf Team */",
        ".spieler-avatar[data-team='werwolf'] {",
        "  background: linear-gradient(145deg, #b91c1c 0%, #7f1d1d 100%);",
        "  border-color: #ef4444;",
        "  box-shadow:",
        "    0 4px 20px rgba(185, 28, 28, 0.4),",
        "    inset 0 2px 10px rgba(255, 255, 255, 0.1);",
        "}",
        "",
        ".spieler-avatar[data-team='werwolf']::before {",
        "  background: radial-gradient(",
        "    circle,",
        "    rgba(239, 68, 68, 0.3) 0%,",
        "    transparent 70%",
        "  );",
        "  animation: pulse-red 2s ease-in-out infinite;",
        "}",
        "",
        "/* Dorf Team */",
        ".spieler-avatar[data-team='dorf'] {",
        "  background: linear-gradient(145deg, #0369a1 0%, #075985 100%);",
        "  border-color: #0ea5e9;",
        "}",
        "",
        "/* Solo/Other */",
        ".spieler-avatar[data-team='solo'] {",
        "  background: linear-gradient(145deg, #7c3aed 0%, #5b21b6 100%);",
        "  border-color: #a78bfa;",
        "}",
        "",
        "/* ============================================================================",
        "   ANIMATIONS & EXTRAS",
        "   ============================================================================ */",
        "",
        "@keyframes pulse-red {",
        "  0%, 100% { opacity: 0.3; transform: scale(1); }",
        "  50% { opacity: 0.5; transform: scale(1.1); }",
        "}",
        "",
        "@keyframes pulse-glow {",
        "  0%, 100% { opacity: 0.7; }",
        "  50% { opacity: 1; }",
        "}",
        "",
        "@keyframes selected-pulse {",
        "  0%, 100% {",
        "    box-shadow: 0 4px 20px rgba(149, 7, 6, 0.3), inset 0 2px 10px rgba(255, 255, 255, 0.1);",
        "  }",
        "  50% {",
        "    box-shadow: 0 4px 30px rgba(149, 7, 6, 0.5), 0 0 40px rgba(149, 7, 6, 0.2), inset 0 2px 10px rgba(255, 255, 255, 0.1);",
        "  }",
        "}",
        "",
        "@keyframes heartbeat {",
        "  0%, 100% { transform: scale(1); }",
        "  25% { transform: scale(1.1); }",
        "  35% { transform: scale(1); }",
        "  45% { transform: scale(1.15); }",
        "  55% { transform: scale(1); }",
        "}",
        "",
        "/* Visibility Indicators */",
        ".spieler-card.werwolf-team-sichtbar::before {",
        "  content: '🐺';",
        "  position: absolute;",
        "  top: 5px;",
        "  left: 5px;",
        "  font-size: 1rem;",
        "  z-index: 10;",
        "  filter: drop-shadow(0 0 5px rgba(239, 68, 68, 0.8));",
        "  animation: pulse-glow 2s infinite;",
        "}",
        "",
        ".spieler-card.seherin-enthüllt-werwolf::before {",
        "  content: '👁️‍🗨️';",
        "  position: absolute;",
        "  top: 5px;",
        "  left: 5px;",
        "  font-size: 0.9rem;",
        "  z-index: 10;",
        "  animation: pulse-glow 2s infinite;",
        "}",
        "",
        ".spieler-card.seherin-enthüllt-dorf::before {",
        "  content: '✓';",
        "  position: absolute;",
        "  top: 5px;",
        "  left: 5px;",
        "  font-size: 1rem;",
        "  color: #22c55e;",
        "  font-weight: bold;",
        "  z-index: 10;",
        "}",
        "",
        ".spieler-card.verliebt::before {",
        "  content: '💕';",
        "  position: absolute;",
        "  top: 5px;",
        "  left: 5px;",
        "  font-size: 1rem;",
        "  z-index: 10;",
        "  animation: heartbeat 1.5s ease-in-out infinite;",
        "}",
        "",
        ".spieler-card.tot {",
        "  opacity: 0.5;",
        "  cursor: not-allowed;",
        "  filter: grayscale(70%);",
        "}",
        "",
        ".spieler-card.tot .spieler-avatar {",
        "  background: linear-gradient(145deg, #374151 0%, #1f2937 100%) !important;",
        "  border-color: #4b5563 !important;",
        "}",
        "",
        ".spieler-card.tot::before {",
        "  content: '💀';",
        "  position: absolute;",
        "  top: 50%;",
        "  left: 50%;",
        "  transform: translate(-50%, -50%);",
        "  font-size: 3rem;",
        "  z-index: 20;",
        "  opacity: 0.8;",
        "}",
        "",
        ".spieler-name {",
        "  font-weight: 600;",
        "  font-size: 0.95rem;",
        "  margin-top: 0.25rem;",
        "  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);",
        "}",
        "",
        ".spieler-grid {",
        "  display: grid;",
        "  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));",
        "  gap: 1.25rem;",
        "  padding: 0.5rem;",
        "}",
        "",
        "@media (min-width: 1200px) {",
        "  .spieler-grid {",
        "    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));",
        "  }",
        "}",
        "",
        ".rolle-badge {",
        "  display: inline-flex;",
        "  align-items: center;",
        "  gap: 0.5rem;",
        "  padding: 0.5rem 1rem;",
        "  border-radius: 25px;",
        "  font-weight: 600;",
        "  font-size: 0.9rem;",
        "  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);",
        "  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);",
        "  transition: all 0.3s ease;",
        "}",
        "",
        ".rolle-badge:hover {",
        "  transform: translateY(-2px);",
        "  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);",
        "}"
    ])

    # Write to file
    try:
        output_path = os.path.join("static", "css", "characters.css")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(css_content))

        logger.info(f"Successfully generated {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate CSS: {e}")

if __name__ == "__main__":
    generate_characters_css()

