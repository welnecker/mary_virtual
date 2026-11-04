"""Focused prompt-contract checks for conversational initiative pilot."""
import importlib.util
import sys
import types
from pathlib import Path


def _load_writer():
    path = Path(__file__).resolve().parents[1] / "mary2" / "direct_script.py"
    spec = importlib.util.spec_from_file_location("mary2_direct_script_initiative", path)
    module = importlib.util.module_from_spec(spec)
    previous = {name: sys.modules.get(name) for name in ("gspread", "openrouter_client")}
    sys.modules["gspread"] = types.ModuleType("gspread")
    stub = types.ModuleType("openrouter_client")
    stub.chat = lambda **_: ""
    sys.modules["openrouter_client"] = stub
    try:
        spec.loader.exec_module(module)
    finally:
        for name, original in previous.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module


writer = _load_writer()


def _prompt(user_text, guide="", thoughts=""):
    return writer.build_direct_writer_prompt(
        row={
            "order": 6,
            "speech_guide": guide,
            "thought_guide": thoughts,
            "permanent_memory": "Mary gosta de humor, mas respeita escolhas.",
            "instant_memory": "Os quatro estão sentados à mesa.",
            "revelation_policy": "",
            "style": "espontânea",
        },
        recent_messages=[
            {"role": "assistant", "content": "Doni, inventa uma brincadeira aí!"},
        ],
        user_text=user_text,
    )


def test_blank_thought_guide_stays_blank_and_thought_is_optional():
    prompt = _prompt("Vamos conversar primeiro.")
    assert "Pensamento-guia:" not in prompt
    assert "FORMATO PADRÃO: [FALA]" in prompt
    assert "[PENSAMENTO] só para intenção espontânea significativa" in prompt
    assert "Sem iniciativa significativa, omita [PENSAMENTO]" in prompt
    assert "nesta ordem: [AÇÃO], [FALA], [PENSAMENTO]" not in prompt


def test_optional_invitation_does_not_claim_acceptance():
    prompt = _prompt(
        "Depois a gente brinca. Me conta de você.",
        "Mary pode convidar Donisete a inventar uma brincadeira.",
    )
    assert "recusada ou ignorada, siga a conversa sem cobrar" in prompt
    assert "A proposta não vira fato realizado nem objetivo obrigatório da linha." in prompt
    assert "Depois a gente brinca. Me conta de você." in prompt


def test_accepted_activity_can_continue_without_new_topic():
    prompt = _prompt(
        "Vamos girar a garrafa, mas primeiro decidimos as regras.",
        "Se fizer sentido, Mary pode sugerir uma brincadeira.",
    )
    assert "Continue uma brincadeira ou conversa enquanto render novos acontecimentos" in prompt
    assert "se aceita, acompanhe regras e consequências" in prompt
    assert "Vamos girar a garrafa, mas primeiro decidimos as regras." in prompt


def test_thought_is_not_duplicated_in_writer_contract():
    prompt = _prompt("Prazer, eu sou Donisete.")
    assert prompt.count("[PENSAMENTO] só para intenção espontânea significativa") == 1
    assert "CONTINUIDADE E INICIATIVA" in prompt


def test_thought_guide_does_not_require_thought_block():
    prompt = _prompt("Eu topo.", thoughts="Mary considera uma iniciativa inesperada.")
    assert "Pensamento-guia: Mary considera uma iniciativa inesperada." in prompt
    assert "não obriga emissão" in prompt


def test_parser_accepts_thought_before_speech_and_speech_alone():
    path = Path(__file__).resolve().parents[1] / "mary2" / "output_filter.py"
    spec = importlib.util.spec_from_file_location("mary2_output_filter_initiative", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parts = module.parse_mary_components(
        "[PENSAMENTO] Vou chamar o Doni para brincar.\n"
        "[FALA] Doni, inventa uma brincadeira aí!"
    )
    assert parts["thought"] == "Vou chamar o Doni para brincar."
    assert parts["speech"] == "Doni, inventa uma brincadeira aí!"
    assert parts["action"] == ""
    only_speech = module.parse_mary_components("[FALA] Prazer, Donisete!")
    assert only_speech == {"speech": "Prazer, Donisete!", "thought": "", "action": ""}
