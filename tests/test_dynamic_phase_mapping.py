import unittest

from game_logic import PHASEN, phasennamen_zu_rollen_mapping


class DynamicPhaseMappingTests(unittest.TestCase):
    def test_registry_driven_mapping_includes_core_roles(self):
        mapping = phasennamen_zu_rollen_mapping()

        self.assertIn('werwolf_phase', mapping)
        self.assertEqual(mapping['werwolf_phase'], 'Werwolf')

        self.assertIn('seherin_phase', mapping)
        self.assertEqual(mapping['seherin_phase'], 'Seherin')

    def test_umlaut_names_are_normalized(self):
        mapping = phasennamen_zu_rollen_mapping()

        # Umlaut-Varianten müssen in den PHASEN-Schlüsselraum übersetzt werden.
        self.assertIn('jaeger_phase', mapping)
        self.assertEqual(mapping['jaeger_phase'], 'Jäger')

        self.assertIn('weisser_wolf_phase', mapping)
        self.assertEqual(mapping['weisser_wolf_phase'], 'Weißer Wolf')

    def test_mapping_only_contains_known_phases(self):
        mapping = phasennamen_zu_rollen_mapping()

        for phase_name in mapping.keys():
            self.assertIn(phase_name, PHASEN)


if __name__ == '__main__':
    unittest.main()
