"""Safety and backward-compatibility checks for optional multi-character script lines."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mary2"))

from multi_character import (
    guide_characters, multi_character_contract, parsed_character_blocks,
    verify_character_blocks, formatted_components,
)
from output_filter import parse_mary_components


class MultiCharacterTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "action_guide": "SILVIA: sorri para Mary.\nMARY: vira-se para a amiga.",
            "thought_guide": "SILVIA: gosta de brincar.\nMARY: fica divertida.",
            "speech_guide": "SILVIA: provoca a amiga.\nMARY: reage e pergunta sobre aventura.",
        }

    def test_no_opt_in_for_old_prose(self):
        legacy = {
            "action_guide": "Silvia ri e Mary dá corda para amiga.",
            "thought_guide": "Minha amiga adora me entregar.",
            "speech_guide": "Aproveitar a deixa de Silvia.",
        }
        self.assertEqual(guide_characters(legacy), {})
        self.assertEqual(multi_character_contract(legacy), "")

    def test_interpretar_is_not_a_character(self):
        self.assertEqual(guide_characters({"speech_guide": "Interpretar: Mary responde."}), {})

    def test_one_or_multiple_characters_across_three_columns(self):
        self.assertEqual(
            guide_characters(self.row)["silvia"],
            {"AÇÃO", "PENSAMENTO", "FALA"},
        )
        self.assertIn("SILVIA", multi_character_contract(self.row))

    def test_approved_attributed_turn(self):
        raw = (
            "[AÇÃO: SILVIA] Silvia ri.\n"
            "[FALA: SILVIA] Mary, você apronta!\n"
            "[PENSAMENTO: SILVIA] Ela vai me matar por isso.\n"
            "[AÇÃO: MARY] Mary vira o rosto.\n"
            "[PENSAMENTO: MARY] Ai, Silvia!\n"
            "[FALA: MARY] Você não presta! E vocês, rapazes?"
        )
        self.assertEqual(verify_character_blocks(raw, self.row), (True, ""))
        parsed = parse_mary_components(raw)
        self.assertIn("**Silvia:**", parsed["speech"])
        self.assertIn("**Mary:**", parsed["speech"])
        self.assertIn("Silvia:", parsed["thought"])
        self.assertIn("Mary:", parsed["action"])

    def test_missing_secondary_speech_must_not_pass(self):
        raw = "[AÇÃO: MARY] Mary sorri.\n[FALA: MARY] Silvia me conhece!"
        allowed, issue = verify_character_blocks(raw, self.row)
        self.assertFalse(allowed)
        self.assertIn("Faltou", issue)

    def test_unapproved_voice_rejected(self):
        raw = "[FALA: ROGER] Olá!\n[FALA: SILVIA] Oi!"
        allowed, _ = verify_character_blocks(raw, self.row)
        self.assertFalse(allowed)

    def test_no_dialogue_for_user_controlled_character(self):
        row = {"speech_guide": "SILVIA: fala brevemente.\nMARY: responde."}
        raw = "[FALA: SILVIA] Oi.\n[FALA: MARY] Olá."
        self.assertFalse(verify_character_blocks(raw, row, user_speaker="Silvia")[0])
        self.assertTrue(
            verify_character_blocks("[FALA: MARY] Olá.", row, user_speaker="Silvia")[0]
        )

    def test_legacy_parser_stays_unchanged(self):
        parsed = parse_mary_components(
            "[AÇÃO] Mary sorri.\n[FALA] Oi!\n[PENSAMENTO] Que surpresa!"
        )
        self.assertEqual(parsed["action"], "Mary sorri.")
        self.assertEqual(parsed["speech"], "Oi!")
        self.assertEqual(parsed["thought"], "Que surpresa!")


if __name__ == "__main__":
    unittest.main()
