"""Regression tests for parenthetical actor hints and speaker name extraction."""
import importlib.util
import sys
import types
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / "mary2"
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# Keep router tests independent from provider clients.
fake_client = types.ModuleType("openrouter_client")
fake_client.chat = lambda **kwargs: '{"kind":"dialogue","scene_direction":"","dialogue":"Oi, Mary!"}'
sys.modules.setdefault("openrouter_client", fake_client)

spec = importlib.util.spec_from_file_location("input_router_identity_test", BASE / "input_router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class TestSpeakerDirection(unittest.TestCase):
    def test_literal_actor_prefix(self):
        prefix, speaker, remaining = router.explicit_stage_prefix("(Donisete) Oi, Mary!")
        self.assertEqual(prefix, "(Donisete)")
        self.assertEqual(speaker, "Donisete")
        self.assertEqual(remaining, "Oi, Mary!")

    def test_actor_verb_and_comment(self):
        prefix, speaker, remaining = router.explicit_stage_prefix("(Janio fala, meio tímido) Olá!")
        self.assertEqual(speaker, "Janio")
        self.assertEqual(remaining, "Olá!")

    def test_plain_dialogue_no_directive(self):
        self.assertEqual(router.explicit_stage_prefix("Oi, Mary!"), ("", "", "Oi, Mary!"))

    def test_router_keeps_direction_even_if_llm_ignores_it(self):
        output = router.parse_user_input(api_key="", model="", fallback_model=None,
                                         user_role="PERSONAGEM_DA_CENA",
                                         raw_text="(Donisete) Oi, Mary!")
        self.assertEqual(output["scene_direction"], "(Donisete)")
        self.assertEqual(output["explicit_speaker"], "Donisete")
        self.assertEqual(output["dialogue"], "Oi, Mary!")


if __name__ == "__main__":
    unittest.main()
