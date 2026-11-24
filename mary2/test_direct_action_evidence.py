"""Regressions: physical action evidence must be grounded in the current output."""
import json
import unittest
from unittest.mock import patch

from direct_semantic_director import validate_direct_semantic_turn


class ActionEvidenceTests(unittest.TestCase):
    def check_case(self, speech, action, evidence, fulfilled_by_director=True):
        assessment = {
            "obrigacao_usuario": {"existe": False, "atendida": True},
            "coerencia_conversacional": {"ok": True},
            "naturalidade": {"ok": True},
            "cena_atual": {
                "cumprida": True,
                "acao_fisica_obrigatoria": True,
                "evidencia": evidence,
            },
            "acoes_autorais": [{
                "id": "acao_1",
                "acao": "Mary se senta na cama, acariciando o membro de Donisete",
                "cumprida": fulfilled_by_director,
                "evidencia": evidence,
            }],
            "objetivos_guia": [{
                "objetivo": "interpretar a situação local",
                "alcancado": True,
                "fonte": "MARY",
                "evidencia": evidence,
            }],
            "contradicao_dura": {"existe": False},
            "violacao_revelacao": {"existe": False},
        }
        with patch("direct_semantic_director.chat", return_value=json.dumps(assessment)):
            return validate_direct_semantic_turn(
                api_key="test", model="test", fallback_model=None,
                row={
                    "action_guide": "Mary se senta na cama, acariciando o membro de Donisete.",
                    "speech_guide": "Interpretar: Mary se aproxima de Donisete.",
                },
                interpretation={},
                mary_text=speech,
                mary_action=action,
            )

    def test_action_grounded_in_action_channel(self):
        excerpt = "Mary se senta na cama, acariciando o membro de Donisete"
        result = self.check_case("Mary: Vem cá.", excerpt, excerpt)
        self.assertTrue(result["fulfilled"], result["missing"])
        self.assertEqual(result["scene_completion"]["authored_action_evaluations"][0]["evidence_channel"], "MARY_ACAO")

    def test_action_grounded_in_current_speech_narration(self):
        excerpt = "Ela se senta na cama, acariciando o membro de Donisete"
        result = self.check_case("Mary: Vem cá. — " + excerpt + ".", "", excerpt)
        self.assertTrue(result["fulfilled"], result["missing"])
        action = result["scene_completion"]["authored_action_evaluations"][0]
        self.assertEqual(action["evidence_channel"], "MARY_FALA")
        self.assertTrue(action["format_warning"])

    def test_promise_is_not_a_completed_action(self):
        excerpt = "Mary: Vou me sentar na cama"
        result = self.check_case(excerpt + ".", "", excerpt)
        self.assertFalse(result["fulfilled"])
        self.assertIn("Ações obrigatórias", result["missing"])

    def test_missing_current_turn_evidence_stays_pending(self):
        result = self.check_case("Mary: Vem cá.", "", "Ela se senta na cama")
        self.assertFalse(result["fulfilled"])

    def test_director_refusal_still_blocks(self):
        excerpt = "Ela se senta na cama, acariciando o membro de Donisete"
        result = self.check_case("Mary: Vem cá. — " + excerpt + ".", "", excerpt, False)
        self.assertFalse(result["fulfilled"])


if __name__ == "__main__":
    unittest.main()
