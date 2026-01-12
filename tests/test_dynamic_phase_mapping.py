"""Tests for dynamic phase mapping.

The phase system has TWO concepts:
1. Core phases (lobby, nacht_start, tag_abstimmung, etc.) - defined in phases.py
2. Role-specific phases (werwolf_phase, seherin_phase, etc.) - generated dynamically

Role-specific phases are NOT in the core PHASEN list - they are generated
from the RoleRegistry and used during the NACHT phase.
"""

import unittest

from phases import get_phase_list
from game_logic import phasennamen_zu_rollen_mapping

PHASEN = get_phase_list()


class DynamicPhaseMappingTests(unittest.TestCase):
    def test_registry_driven_mapping_includes_core_roles(self):
        """Core roles should have phase mappings."""
        mapping = phasennamen_zu_rollen_mapping()

        self.assertIn("werwolf_phase", mapping)
        self.assertEqual(mapping["werwolf_phase"], "Werwolf")

        self.assertIn("seherin_phase", mapping)
        self.assertEqual(mapping["seherin_phase"], "Seherin")

    def test_umlaut_names_are_normalized(self):
        """Umlaut characters should be normalized in phase names."""
        mapping = phasennamen_zu_rollen_mapping()

        # Umlaut-Varianten müssen normalisiert werden
        self.assertIn("jaeger_phase", mapping)
        self.assertEqual(mapping["jaeger_phase"], "Jäger")

        self.assertIn("weisser_wolf_phase", mapping)
        self.assertEqual(mapping["weisser_wolf_phase"], "Weißer Wolf")

    def test_mapping_phase_names_follow_convention(self):
        """All role phase names should follow the naming convention.
        
        Role-specific phases are NOT in the core PHASEN list.
        They follow the pattern: role_name_phase (lowercase, underscores).
        """
        mapping = phasennamen_zu_rollen_mapping()

        for phase_name in mapping.keys():
            # All role phases should end with _phase
            self.assertTrue(
                phase_name.endswith("_phase"),
                f"Phase '{phase_name}' should end with '_phase'"
            )
            # All role phases should be lowercase with underscores
            self.assertEqual(
                phase_name,
                phase_name.lower(),
                f"Phase '{phase_name}' should be lowercase"
            )
            # No spaces allowed
            self.assertNotIn(
                " ",
                phase_name,
                f"Phase '{phase_name}' should not contain spaces"
            )

    def test_core_phases_are_separate_from_role_phases(self):
        """Core phases should be distinct from role phases."""
        mapping = phasennamen_zu_rollen_mapping()
        
        # Core phases should NOT be in the role mapping
        for core_phase in PHASEN:
            self.assertNotIn(
                core_phase,
                mapping,
                f"Core phase '{core_phase}' should not be in role mapping"
            )


if __name__ == "__main__":
    unittest.main()
