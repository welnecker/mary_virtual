from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import sys
from typing import Any, Callable

import streamlit as st

from scenarios.card_registry import obter_card
from scenarios.stories.casada_frustrada.beat_engine import obter_beat_atual
from scenarios.stories.casada_frustrada.compact_prompt import compilar_prompt_beat
import ui.card_runtime_integration as card_integration


COMPACT_SYSTEM_PROMPT_VERSION = "casada-frustrada-system-prompt-v3-exclusive"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None

_DEFAULT_PHYSICAL = {
    "skin": "pele clara",
    "eyes": "olhos verdes",
    "hair_color": "cabelos negros",
    "hair_length": "cabelos longos",
    "hair_volume": "cabelos volumosos",
    "face": "rosto delicado com traços marcantes",
    "body_type": "corpo curvilíneo e feminino",
    "waist": "cintura fina e marcada",
    "breasts": "seios médios, naturais, firmes e empinados",
    "hips": "quadris largos",
    "buttocks": "bunda grande, carnuda, arredondada e firme",
    "legs": "coxas firmes",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict):
        return None
    if _text(value.get("scenario_id")) != "casada_frustrada":
        return None
    return value


def _recent_messages(limit: int = 6) -> list[dict[str, str]]:
    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        return []
    result: list[dict[str, str]] = []
    for item in messages[-limit:]:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content[:700]})
    return result


def _last_assistant() -> str:
    for item in reversed(_recent_messages(8)):
        if item.get("role") == "assistant":
            return _text(item.get("content"))
    return ""


def _sexual_state(kwargs: dict[str, Any]) -> dict[str, Any]:
    value = kwargs.get("sexual_state")
    if isinstance(value, dict):
        return deepcopy(value)
    relationship = kwargs.get("relationship_state")
    if isinstance(relationship, dict) and isinstance(relationship.get("sexual_state"), dict):
        return deepcopy(relationship["sexual_state"])
    stored = st.session_state.get("relationship_state")
    if isinstance(stored, dict) and isinstance(stored.get("sexual_state"), dict):
        return deepcopy(stored["sexual_state"])
    return {}


def _compact_character(card: dict[str, Any]) -> dict[str, Any]:
    character = card.get("character") if isinstance(card.get("character"), dict) else {}
    psychology = card.get("psychology") if isinstance(card.get("psychology"), dict) else {}
    voice = card.get("voice") if isinstance(card.get("voice"), dict) else {}
    public = character.get("public_identity") if isinstance(character.get("public_identity"), dict) else {}
    return {
        "identity": {
            "name": public.get("name", "Mary"),
            "age": public.get("age", 25),
            "marital_status": public.get("marital_status", "casada"),
            "archetype": character.get("archetype", "mulher casada sexualmente frustrada"),
        },
        "psychology": {
            "core": list(character.get("core_traits") or [])[:6],
            "latent": list(character.get("latent_traits") or [])[:5],
            "contradictions": list(character.get("contradictions") or [])[:4],
            "route_expression": psychology.get("route_expression", {}),
        },
        "voice": {
            "register": voice.get("default_register", "popular, íntimo e direto"),
            "humor": voice.get("humor", "contextual"),
            "sarcasm": voice.get("sarcasm", "baixo no início"),
            "question_style": voice.get("question_style", "no máximo uma pergunta"),
        },
    }


def _find_physical_profile(kwargs: dict[str, Any]) -> dict[str, Any]:
    candidates = [kwargs.get("mary_profile"), st.session_state.get("mary_profile")]
    for profile in candidates:
        if not isinstance(profile, dict):
            continue
        for candidate in (
            profile.get("physical_traits"),
            (profile.get("canon") or {}).get("physical_traits") if isinstance(profile.get("canon"), dict) else None,
            (profile.get("identity") or {}).get("physical_traits") if isinstance(profile.get("identity"), dict) else None,
        ):
            if isinstance(candidate, dict) and candidate:
                return candidate
    return {}


def _compact_physical(kwargs: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    physical = _find_physical_profile(kwargs)
    fixed = {
        key: physical.get(key) or default
        for key, default in _DEFAULT_PHYSICAL.items()
    }
    return {
        "fixed": fixed,
        "scene": {
            key: scene.get(key)
            for key in (
                "location", "time_context", "mary_clothing", "user_clothing",
                "position", "current_position", "privacy_established",
                "video_call_established", "camera_active",
            )
            if scene.get(key) not in (None, "", False)
        },
    }


def _compact_facts(scene: dict[str, Any]) -> list[str]:
    result: list[str] = []
    stored = scene.get("completed_story_facts")
    if isinstance(stored, list):
        result.extend(_text(item) for item in stored if _text(item))
    for key in (
        "phone_numbers_exchanged", "privacy_established", "video_call_established",
        "camera_positioned", "secret_meeting_arranged", "user_arrived_secret_meeting",
    ):
        if scene.get(key) is True and key not in result:
            result.append(key)
    return result[-12:]


def _build_compact_prompt(kwargs: dict[str, Any]) -> str:
    instance = _instance()
    if not isinstance(instance, dict):
        return ""
    scene = instance.get("scene_state")
    scene = scene if isinstance(scene, dict) else {}
    sexual = _sexual_state(kwargs)
    card = obter_card("casada_frustrada") or {}
    beat = obter_beat_atual(scene)
    if not beat:
        return ""

    beat_block = compilar_prompt_beat(
        scene_state=scene,
        sexual_state=sexual,
        last_mary_response=_last_assistant(),
    )
    user_message = _text(kwargs.get("user_message"))
    if not user_message:
        relationship = kwargs.get("relationship_state")
        active_turn = relationship.get("active_turn") if isinstance(relationship, dict) else {}
        user_message = _text(active_turn.get("user_text")) if isinstance(active_turn, dict) else ""

    payload = {
        "version": COMPACT_SYSTEM_PROMPT_VERSION,
        "character": _compact_character(card),
        "physical": _compact_physical(kwargs, scene),
        "route": beat.get("route"),
        "beat": beat.get("id"),
        "facts": _compact_facts(scene),
        "sexual": {
            "phase": sexual.get("scene_phase"),
            "arousal": sexual.get("arousal_level"),
            "mary_pre_orgasm": bool(sexual.get("mary_pre_orgasm")),
            "mary_orgasm_allowed": bool(sexual.get("mary_orgasm_allowed")),
            "mary_orgasm_done": bool(sexual.get("mary_orgasm_done")),
            "user_orgasm_done": bool(sexual.get("user_orgasm_done")),
            "aftercare_required": bool(sexual.get("aftercare_required")),
        },
        "recent": _recent_messages(6),
        "user_now": user_message[:700],
    }

    return f"""Você interpreta Mary, mulher brasileira adulta de 25 anos, na história Casada Frustrada.

REGRAS FIXAS
- Fale em primeira pessoa, como mulher real; nunca como assistente ou narradora explicativa.
- Preserve identidade física, psicologia, roupas, local, objetos e fatos confirmados.
- O beat abaixo é a ação obrigatória deste turno. Não abra entrevista nem outro assunto.
- Não volte a beat concluído e não execute o próximo antes da resposta do usuário.
- Sua liberdade está apenas nas palavras, humor, hesitação, ritmo e intensidade.
- No máximo uma pergunta. Não invente ação, consentimento, sensação ou orgasmo do usuário.
- Use português popular e natural, normalmente em 1 a 3 parágrafos curtos.
- Fala audível em texto normal. Pensamento privado, só quando útil: Pensamento de Mary: ...

ESTADO
{json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}

{beat_block}

SAÍDA
Produza somente a resposta de Mary e cumpra o objetivo do beat. Pare imediatamente depois dele.""".strip()


def _patch_system_prompt(module: Any) -> None:
    current = getattr(module, "montar_prompt_sistema", None)
    if not callable(current) or getattr(current, "_mary_true_compact_prompt", False):
        return

    @wraps(current)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        if _instance() is None:
            return str(current(*args, **kwargs) or "")
        compact = _build_compact_prompt(dict(kwargs))
        return compact or str(current(*args, **kwargs) or "")

    wrapper._mary_true_compact_prompt = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def _patch_narrative_direction(module: Any) -> None:
    """Impede que o cenário completo seja anexado após o prompt compacto."""

    current = getattr(module, "montar_direcao_narrativa", None)
    if not callable(current) or getattr(current, "_mary_compact_direction", False):
        return

    @wraps(current)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        if _instance() is None:
            return str(current(*args, **kwargs) or "")
        # O beat já está no prompt de sistema. Só uma ponte ativa precisa entrar.
        return _text(card_integration._bridge_prompt_block())

    wrapper._mary_compact_direction = True  # type: ignore[attr-defined]
    setattr(module, "montar_direcao_narrativa", wrapper)


def aplicar_prompt_compacto() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_system_prompt(module)
    _patch_narrative_direction(module)


def install_casada_frustrada_compact_system_prompt() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    aplicar_prompt_compacto()
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_prompt_compacto()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "COMPACT_SYSTEM_PROMPT_VERSION",
    "aplicar_prompt_compacto",
    "install_casada_frustrada_compact_system_prompt",
]
