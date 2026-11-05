"""Regression checks: inferred challenges must not become lasting decisions."""
import importlib.util
import json
import sys
import types
from pathlib import Path


def _module():
    path = Path(__file__).resolve().parents[1] / "mary2" / "conversation_state.py"
    spec = importlib.util.spec_from_file_location("conversation_state_guard_test", path)
    module = importlib.util.module_from_spec(spec)
    stub = types.ModuleType("openrouter_client")
    stub.chat = lambda **_: ""
    original = sys.modules.get("openrouter_client")
    sys.modules["openrouter_client"] = stub
    try:
        spec.loader.exec_module(module)
    finally:
        if original is None:
            sys.modules.pop("openrouter_client", None)
        else:
            sys.modules["openrouter_client"] = original
    return module


cs = _module()


def _interpret(speech, proposed, evidence):
    parsed = {
        "speaker": "MARY",
        "move": "brincar",
        "tone": "provocador",
        "open_thread": "a outra pessoa pode responder",
        "facts_created": [],
        "decisions_created": [proposed],
        "decision_evidence": [evidence],
    }
    return cs.normalize_conversation_state(cs._ground_decisions(parsed, speech))


def test_challenge_does_not_become_decision():
    state = _interpret(
        "Se você quer tanto assim, talvez tenha que se esforçar.",
        "Mary decide testar Donisete",
        "Se você quer tanto assim, talvez tenha que se esforçar.",
    )
    assert state["decisions_created"] == []
    assert state["move"] == "brincar"
    assert state["tone"] == "provocador"


def test_no_evidence_discards_model_inference():
    state = _interpret("Gostei de você, Doni.", "Mary decide se afastar", "")
    assert state["decisions_created"] == []


def test_invented_evidence_cannot_create_decision():
    state = _interpret("Que surpresa boa!", "Mary decide aceitar", "Eu aceito o convite.")
    assert state["decisions_created"] == []


def test_explicit_choice_kept_verbatim_not_model_paraphrase():
    state = _interpret(
        "Eu não quero ir agora. Prefiro ficar aqui.",
        "Mary decide definitivamente abandonar o outro personagem",
        "Eu não quero ir agora.",
    )
    assert state["decisions_created"] == ["Eu não quero ir agora."]


def test_old_snapshot_decisions_without_evidence_are_dropped():
    old = {
        "speaker": "MARY",
        "move": "desafiar",
        "open_thread": "convencer Mary",
        "decisions_created": ["Mary decide testar Donisete"],
    }
    state = cs.normalize_conversation_state(old)
    assert state["decisions_created"] == []
    assert state["move"] == "desafiar"
    assert "não é decisão nem obrigação" in cs.format_conversation_state(state)


def test_context_response_saves_only_grounded_quote(monkeypatch):
    def fake_chat(**kwargs):
        return json.dumps({
            "speaker": "MARY", "move": "reagir", "target": "Donisete",
            "topic": "convite", "meaning": "Mary prefere ficar",
            "tone": "firme", "open_thread": "", "facts_created": [],
            "decisions_created": ["Mary rompe a relação"],
            "decision_evidence": ["Eu prefiro ficar aqui."],
        })
    monkeypatch.setattr(cs, "chat", fake_chat)
    state = cs.analyze_mary_move(
        api_key="test", model="test", fallback_model=None,
        mary_text="Eu prefiro ficar aqui.", user_text="Você vem?",
    )
    assert state["decisions_created"] == ["Eu prefiro ficar aqui."]
