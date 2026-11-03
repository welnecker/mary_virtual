"""Regression for line progression: negative constraints are not objectives."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mary2"))
from direct_semantic_director import _evidence_source, _is_guardrail_objective, validate_direct_semantic_turn


class DirectLineProgressionTests(unittest.TestCase):
    def test_negative_instructions_are_not_completion_goals(self):
        for value in ("Não presumir intenções", "Sem inventar fatos", "Evitar repetição"):
            self.assertTrue(_is_guardrail_objective(value), value)
        self.assertFalse(_is_guardrail_objective("Conversar sobre os planos"))
        self.assertFalse(_is_guardrail_objective("Perguntar o que querem fazer"))

    def test_quotes_are_checked_against_real_speech(self):
        entries = [("MARY", "A gente pode conversar sobre os planos depois.")]
        self.assertEqual(
            _evidence_source("FALA: 'A gente pode conversar sobre os planos depois.'", entries),
            "MARY",
        )
        self.assertEqual(_evidence_source("FALA: 'Inventei uma conversa que nunca ocorreu'", entries), "")

    def test_line_finishes_when_positive_goal_is_grounded(self):
        answer = "E vocês, o que querem fazer durante a viagem?"
        parsed = {
            "obrigacao_usuario": {"existe": False, "atendida": True},
            "coerencia_conversacional": {"ok": True},
            "naturalidade": {"ok": True},
            "cena_atual": {"cumprida": True, "acao_fisica_obrigatoria": False, "evidencia": answer},
            "objetivos_guia": [
                {"objetivo": "Conversar sobre planos", "alcancado": True,
                 "fonte": "MARY", "evidencia": answer},
                {"objetivo": "Não presumir intenções", "alcancado": True,
                 "fonte": "FALA-GUIA ORIGINAL",
                 "evidencia": "Mary pergunta em vez de presumir."},
            ],
            "contradicao_dura": {"existe": False},
            "violacao_revelacao": {"existe": False},
            "cumpriu": True,
        }
        with patch("direct_semantic_director.chat", return_value=json.dumps(parsed)):
            result = validate_direct_semantic_turn(
                api_key="fake", model="fake", fallback_model=None,
                row={"speech_guide": "Conversar sobre planos sem presumir intenções"},
                interpretation={}, mary_text=answer,
            )
        self.assertTrue(result["fulfilled"], result["missing"])
        self.assertFalse(result["elements"][1]["is_constraint"] is False)

    def test_hallucinated_positive_evidence_still_blocks(self):
        answer = "Tudo bem, vamos conversar."
        parsed = {
            "obrigacao_usuario": {"existe": False, "atendida": True},
            "coerencia_conversacional": {"ok": True},
            "naturalidade": {"ok": True},
            "cena_atual": {"cumprida": True, "acao_fisica_obrigatoria": False, "evidencia": answer},
            "objetivos_guia": [{"objetivo": "Perguntar sobre planos", "alcancado": True,
                                "evidencia": "E vocês, quais são os planos?"}],
            "contradicao_dura": {"existe": False},
            "violacao_revelacao": {"existe": False},
            "cumpriu": True,
        }
        with patch("direct_semantic_director.chat", return_value=json.dumps(parsed)):
            result = validate_direct_semantic_turn(
                api_key="fake", model="fake", fallback_model=None,
                row={"speech_guide": "Perguntar sobre planos"},
                interpretation={}, mary_text=answer,
            )
        self.assertFalse(result["fulfilled"])


if __name__ == "__main__":
    unittest.main()
