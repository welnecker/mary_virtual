"""Regression: Interpretar completion follows authorial obligations, not invented evidence."""
import importlib.util
import json
import sys
import types
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "mary2" / "direct_semantic_director.py"
    spec = importlib.util.spec_from_file_location("director_unblock_regression", path)
    module = importlib.util.module_from_spec(spec)
    stub = types.ModuleType("openrouter_client")
    stub.chat = lambda **_: ""
    previous = sys.modules.get("openrouter_client")
    sys.modules["openrouter_client"] = stub
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("openrouter_client", None)
        else:
            sys.modules["openrouter_client"] = previous
    return module


director = _load()


def _check(*, guide, scene_claim=True, invented_evidence=True, director_physical=True,
           mary_action="", hard_contradiction=False):
    quote = "Mary faz uma ação que nunca aconteceu" if invented_evidence else "Mary acena."
    response = {
        "obrigacao_usuario": {"existe": True, "requisito": "Responder",
                              "atendida": True, "evidencia": "Respondeu"},
        "coerencia_conversacional": {"ok": True},
        "naturalidade": {"ok": True},
        "cena_atual": {"cumprida": scene_claim,
                       "acao_fisica_obrigatoria": director_physical,
                       "acontecimento": "Continuação da conversa",
                       "evidencia": quote, "faltou": ""},
        "objetivos_guia": [{"objetivo": "interpretar a situação local",
                            "alcancado": True, "fonte": "USUÁRIO",
                            "evidencia": "A decisão já foi tomada"}],
        "contradicao_dura": {"existe": hard_contradiction},
        "violacao_revelacao": {"existe": False},
        "cumpriu": scene_claim,
    }
    director.chat = lambda **_: json.dumps(response, ensure_ascii=False)
    return director.validate_direct_semantic_turn(
        api_key="test", model="test", fallback_model=None,
        row={"speech_guide": guide, "script_name": "Cruzeiro Caribe2",
             "action_guide": "Mary brinca com a decisão; se já aconteceu, segue."},
        interpretation={"user_obligation": {"exists": True, "requirement": "Responder"}},
        mary_text="A decisão já foi tomada. Vamos continuar.",
        mary_action=mary_action,
        user_text="A decisão já foi tomada",
    )


def test_interpretar_does_not_stall_on_invented_citation_and_optional_gesture():
    result = _check(
        guide="Interpretar: se a escolha já apareceu, Mary continua a conversa.",
    )
    assert result["fulfilled"] is True
    assert result["scene_completion"]["evidence_grounded"] is False
    assert result["scene_completion"]["director_physical_claim"] is True
    assert result["scene_completion"]["physical_required_by_author"] is False


def test_interpretar_unfulfilled_scene_does_not_advance():
    result = _check(guide="Interpretar: continuar a conversa", scene_claim=False)
    assert result["fulfilled"] is False


def test_hard_contradiction_still_blocks_completion():
    result = _check(guide="Interpretar: continuar a conversa", hard_contradiction=True)
    assert result["fulfilled"] is False


def test_explicit_required_mary_movement_blocks_without_action():
    result = _check(guide="Interpretar: Mary deve abrir a porta antes de entrar.")
    assert result["fulfilled"] is False
    assert result["scene_completion"]["physical_required_by_author"] is True


def test_explicit_required_mary_movement_accepts_real_action_evidence():
    # Check the physical evidence helper independently of the Director's
    # broader natural-language assessment.
    assert director._explicit_physical_requirement(
        speech_guide="Mary deve abrir a porta.", action_guide=""
    )
    assert director._evidence_source(
        "Mary abre a porta.", [("MARY_ACAO", "Mary abre a porta.")]
    ) == "MARY_ACAO"


def test_conditional_physical_opportunity_is_not_mandatory():
    assert not director._explicit_physical_requirement(
        speech_guide="Se fizer sentido, Mary deve abrir a porta.", action_guide=""
    )
