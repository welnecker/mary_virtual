"""Regression tests: writer/director harmony without weakening hard constraints."""

import importlib.util
import json
import sys
import types
from pathlib import Path


_module_path = Path(__file__).resolve().parents[1] / "mary2" / "direct_semantic_director.py"
_spec = importlib.util.spec_from_file_location("mary_director_harmony", _module_path)
director = importlib.util.module_from_spec(_spec)
_stub = types.ModuleType("openrouter_client")
_stub.chat = lambda **_: "{}"
_previous = sys.modules.get("openrouter_client")
try:
    sys.modules["openrouter_client"] = _stub
    _spec.loader.exec_module(director)
finally:
    if _previous is None:
        sys.modules.pop("openrouter_client", None)
    else:
        sys.modules["openrouter_client"] = _previous


def _validation(guide, objective, *, met=False, contradictory=False):
    speech = "Aceito a brincadeira, mas me conta as regras primeiro."
    response = {
        "obrigacao_usuario": {
            "existe": True,
            "requisito": "Responder à proposta de brincadeira",
            "atendida": True,
            "evidencia": "Aceito a brincadeira",
        },
        "coerencia_conversacional": {"ok": True},
        "naturalidade": {"ok": True},
        "cena_atual": {
            "cumprida": True,
            "acao_fisica_obrigatoria": False,
            "evidencia": "Aceito a brincadeira",
        },
        "objetivos_guia": [{
            "objetivo": objective,
            "alcancado": met,
            "fonte": "MARY",
            "evidencia": speech if met else "",
        }],
        "contradicao_dura": {"existe": contradictory},
        "violacao_revelacao": {"existe": False},
        "cumpriu": False,  # Director sometimes says false for an optional topic.
    }
    director.chat = lambda **_: json.dumps(response, ensure_ascii=False)
    return director.validate_direct_semantic_turn(
        api_key="test",
        model="fake",
        fallback_model=None,
        row={"speech_guide": guide, "script_name": "Cruzeiro Caribe 1"},
        interpretation={
            "user_obligation": {
                "exists": True, "requirement": "Responder à brincadeira"
            }
        },
        mary_text=speech,
        user_text="Topa a brincadeira?",
    )


def test_conditional_topic_does_not_block_the_line():
    result = _validation(
        "Se a conversa permitir, Mary menciona o que gosta em alguém.",
        "Mencionar o que gosta em alguém",
    )
    assert result["fulfilled"] is True
    assert result["elements"][0]["optional"] is True
    assert result["missing"] == ""


def test_style_avoidance_is_not_completion_requirement():
    result = _validation("Evitar metáforas ensaiadas.", "Evitar metáforas ensaiadas")
    assert result["fulfilled"] is True


def test_secondary_character_does_not_have_to_repeat_each_turn():
    result = _validation(
        "SILVIA: faz um comentário divertido ao outro rapaz.\n"
        "MARY: reage à amiga sem interromper a conversa.",
        "SILVIA: faz um comentário divertido",
    )
    assert result["fulfilled"] is True
    assert result["elements"][0]["optional"] is True


def test_same_rule_applies_to_other_secondary_characters():
    assert director._guide_objective_is_optional(
        "RICARDO: comenta discretamente",
        "RICARDO: comenta discretamente\nMARY: reage se for pertinente",
    )


def test_concrete_required_act_still_blocks_when_missing():
    result = _validation("Mary deve revelar a notícia nesta linha.", "Revelar a notícia")
    assert result["fulfilled"] is False
    assert result["elements"][0]["optional"] is False


def test_explicitly_required_secondary_action_still_blocks():
    result = _validation("SILVIA: deve avisar Mary do perigo.", "SILVIA: deve avisar Mary")
    assert result["fulfilled"] is False


def test_factual_contradiction_still_blocks_optional_line():
    result = _validation(
        "Se a conversa permitir, fazer uma pergunta pessoal.",
        "Fazer uma pergunta pessoal",
        contradictory=True,
    )
    assert result["fulfilled"] is False


def test_current_user_obligation_remains_required():
    result = _validation("Mary responde ao convite.", "Responder ao convite")
    assert result["fulfilled"] is False  # Requirement was not evidenced.


def test_mixed_guide_keeps_required_act_and_defers_conditional_addon():
    guide = (
        "Responder a quem falou. "
        "Se fizer sentido, incluir o outro rapaz com um comentário simples."
    )
    assert not director._guide_objective_is_optional("Responder a quem falou", guide)
    assert director._guide_objective_is_optional(
        "Incluir o outro rapaz com um comentário simples", guide
    )


def test_required_act_supported_by_evidence_passes_even_if_global_cumpriu_is_false():
    result = _validation(
        "Mary deve responder à proposta da brincadeira.",
        "Responder à proposta da brincadeira",
        met=True,
    )
    assert result["fulfilled"] is True


def test_explicit_mary_requirement_in_secondary_guide_is_not_dropped():
    guide = "SILVIA: pode brincar.\\nMARY: deve revelar um segredo importante."
    assert not director._guide_objective_is_optional(
        "MARY: deve revelar um segredo importante", guide
    )
