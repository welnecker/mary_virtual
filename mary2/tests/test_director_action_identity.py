"""Regression tests for authorial action identity in semantic director."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import direct_semantic_director as director


GUIDE = "Mary caminha até a sacada da suite, vendo o azul turqueza dass águas."
ACTION = (
    "Mary sai do quarto, atravessa o corredor da suíte e chega à porta da sacada; "
    "abre-a e fica parada, olhando o horizonte onde o azul turquesa das águas "
    "se estende até o céu."
)


def evaluation(items, *, scene=True):
    return json.dumps({
        "obrigacao_usuario": {"existe": False, "atendida": True, "evidencia": ""},
        "coerencia_conversacional": {"ok": True},
        "naturalidade": {"ok": True},
        "pensamento_autoral": {"avaliado": False, "ok": True},
        "cena_atual": {"cumprida": scene, "evidencia": ACTION, "faltou": ""},
        "acoes_autorais": items,
        "objetivos_guia": [
            {"objetivo": "interpretar a situação local", "alcancado": True,
             "fonte": "MARY", "evidencia": "Mary: Oi, Silvia!"}
        ],
        "contradicao_dura": {"existe": False},
        "violacao_revelacao": {"existe": False},
        "cumpriu": True,
    }, ensure_ascii=False)


def run_director(items, *, guide=GUIDE, action=ACTION):
    with patch.object(director, "chat", return_value=evaluation(items)):
        return director.validate_direct_semantic_turn(
            api_key="test", model="openai/gpt-oss-120b",
            fallback_model=None,
            row={"action_guide": guide, "speech_guide": "Interpretar",
                 "interaction_mode": "automatico"},
            interpretation={},
            mary_text="Mary: Oi, Silvia!",
            mary_action=action,
        )


class AuthoredActionIdentityTests(unittest.TestCase):
    def test_paraphrase_identity_with_valid_id_and_literal_proof(self):
        result = run_director([{
            "id": "acao_1", "acao": ACTION,
            "cumprida": True, "evidencia": ACTION,
        }])
        self.assertTrue(result["fulfilled"])
        self.assertTrue(result["scene_completion"]["authored_action_evaluations"][0]["fulfilled"])
        self.assertIn("acao_1:", result["input_payload"])

    def test_legacy_exact_action_without_id(self):
        result = run_director([{
            "acao": GUIDE.rstrip("."), "cumprida": True, "evidencia": ACTION,
        }])
        self.assertTrue(result["fulfilled"])

    def test_wrong_id_is_rejected(self):
        result = run_director([{
            "id": "acao_2", "acao": GUIDE,
            "cumprida": True, "evidencia": ACTION,
        }])
        self.assertFalse(result["fulfilled"])
        self.assertIn("Identificador", result["scene_completion"]["authored_action_evaluations"][0]["reason"])

    def test_invalid_literal_evidence_is_rejected(self):
        result = run_director([{
            "id": "acao_1", "acao": GUIDE,
            "cumprida": True, "evidencia": "Mary teleportou para a sacada.",
        }])
        self.assertFalse(result["fulfilled"])
        self.assertIn("citação literal", result["scene_completion"]["authored_action_evaluations"][0]["reason"])

    def test_unconfirmed_action_stays_rejected(self):
        result = run_director([{
            "id": "acao_1", "acao": GUIDE,
            "cumprida": False, "evidencia": ACTION,
        }])
        self.assertFalse(result["fulfilled"])

    def test_distinct_actions_require_distinct_ids_and_evidence(self):
        guide = "Mary caminha até a sacada. Mary pega o celular."
        action = "Mary caminha até a sacada. Mary pega o celular."
        with patch.object(director, "chat", return_value=evaluation([
            {"id": "acao_1", "acao": "Mary caminha até a sacada",
             "cumprida": True, "evidencia": "Mary caminha até a sacada"},
            {"id": "acao_1", "acao": "Mary pega o celular",
             "cumprida": True, "evidencia": "Mary pega o celular"},
        ])):
            result = director.validate_direct_semantic_turn(
                api_key="test", model="openai/gpt-oss-120b",
                fallback_model=None,
                row={"action_guide": guide, "speech_guide": "Interpretar",
                     "interaction_mode": "automatico"},
                interpretation={}, mary_text="Mary: Oi, Silvia!", mary_action=action,
            )
        self.assertFalse(result["fulfilled"])
        self.assertEqual(
            [a["fulfilled"] for a in result["scene_completion"]["authored_action_evaluations"]],
            [True, False],
        )


if __name__ == "__main__":
    unittest.main()
