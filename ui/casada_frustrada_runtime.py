from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import re
import sys
import unicodedata
from typing import Any, Callable

import streamlit as st

from repositories.scenario_session_repository import salvar_instancia_cenario
from scenarios.card_registry import obter_card
from scenarios.stories.casada_frustrada.beat_graph import (
    INITIAL_BEAT,
    obter_beat,
    proximo_beat_padrao,
)


CASADA_FRUSTRADA_RUNTIME_VERSION = "casada-frustrada-runtime-v1-single-authority"
SCENARIO_ID = "casada_frustrada"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None

LEGACY_BEATS = {
    "second_encounter_in_aisle": "second_encounter",
    "first_private_message": "home_first_message",
    "first_message": "home_first_message",
    "private_call_started": "camera_confirmed",
    "visual_escalation": "ask_remove_shirt",
    "mutual_stimulation": "mutual_arousal",
    "after_call_message": "midnight_call",
    "arrival": "motel_arrival",
}

ROUTE_DEFAULT_BEAT = {
    "supermarket_encounter": "accidental_bump",
    "aisle_flirtation": "second_encounter",
    "phone_exchange": "phone_request",
    "messages": "home_first_message",
    "hidden_call": "camera_confirmed",
    "secret_meeting_plan": "midnight_call",
    "secret_meeting": "motel_arrival",
    "growing_tension": "first_physical_contact",
    "intimacy": "mary_gives_pleasure",
    "climax": "mary_first_orgasm",
    "aftercare": "aftercare",
    "future_secret": "final_departure",
}

# Um beat pode respirar por alguns turnos, mas nunca vira conversa infinita.
BEAT_TURN_BUDGET = {
    "accidental_bump": 4,
    "recognize_neighbor": 2,
    "second_encounter": 2,
    "cart_observation": 3,
    "checkout_wait": 3,
    "phone_request": 3,
    "home_first_message": 3,
    "seek_privacy": 2,
    "offer_video": 3,
    "camera_confirmed": 2,
    "ask_remove_shirt": 3,
    "react_to_torso": 2,
    "ask_remove_pants": 3,
    "mary_reveals_lingerie": 3,
    "mutual_arousal": 7,
    "user_release": 2,
    "call_interrupted": 2,
    "midnight_call": 3,
    "confirm_motel": 4,
    "motel_arrival": 3,
    "first_physical_contact": 4,
    "mary_gives_pleasure": 6,
    "mary_receives_pleasure": 7,
    "mary_first_orgasm": 3,
    "penetration": 7,
    "shared_climax": 4,
    "aftercare": 3,
    "final_departure": 2,
}

PHYSICAL_CANON = {
    "skin": "pele clara",
    "eyes": "olhos verdes",
    "hair": "cabelos negros, longos e volumosos",
    "face": "rosto delicado com traços marcantes",
    "body": "corpo curvilíneo, cintura fina, quadris largos e coxas firmes",
}



def _text(value: Any) -> str:
    return str(value or "").strip()



def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()



def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict) or _text(value.get("scenario_id")) != SCENARIO_ID:
        return None
    return value



def _messages(limit: int = 8) -> list[dict[str, str]]:
    value = st.session_state.get("messages")
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value[-limit:]:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content[:800]})
    return result



def _sexual_state() -> dict[str, Any]:
    relationship = st.session_state.get("relationship_state")
    if not isinstance(relationship, dict):
        return {}
    value = relationship.get("sexual_state")
    return deepcopy(value) if isinstance(value, dict) else {}



def _current_scene(instance: dict[str, Any]) -> dict[str, Any]:
    scene = instance.get("scene_state")
    return deepcopy(scene) if isinstance(scene, dict) else {}



def _resolve_beat(scene: dict[str, Any], instance: dict[str, Any]) -> str:
    runtime = scene.get("script_runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    candidates = (
        runtime.get("current_beat"),
        scene.get("current_beat"),
        instance.get("current_beat"),
    )
    for candidate in candidates:
        beat_id = LEGACY_BEATS.get(_text(candidate), _text(candidate))
        if obter_beat(beat_id):
            return beat_id

    route = _text(scene.get("current_route") or instance.get("current_route"))
    route_beat = ROUTE_DEFAULT_BEAT.get(route)
    if route_beat:
        return route_beat
    return INITIAL_BEAT



def _history_recovery(beat_id: str, scene: dict[str, Any]) -> str:
    history = " ".join(_normalize(item["content"]) for item in _messages(20))
    interaction_count = int(scene.get("interaction_count", 0) or 0)

    if any(term in history for term in ("video chamada", "camera", "ta me vendo", "celular na bancada")):
        if any(term in history for term in ("tira a camisa", "sem camisa", "peitoral")):
            return "react_to_torso"
        return "camera_confirmed"
    if any(term in history for term in ("motel status", "amanha ao meio dia", "encontro secreto")):
        return "confirm_motel"
    if any(term in history for term in ("seu numero", "meu numero", "anota meu numero")):
        return "home_first_message"
    if "algum tempo depois" in history or "olha voce de novo" in history:
        if any(term in history for term in ("carrinho", "cerveja", "salgadinho", "macarrao")):
            return "checkout_wait"
        return "cart_observation"

    # Sessões antigas presas na abertura não continuam fazendo entrevista.
    if beat_id == "accidental_bump" and interaction_count >= 4:
        if any(term in history for term in ("ta melhor", "esta melhor", "consigo andar", "terminar as compras")):
            return "recognize_neighbor"
    if beat_id == "second_encounter" and interaction_count >= 3:
        return "cart_observation"
    return beat_id



def _runtime_state(scene: dict[str, Any], instance: dict[str, Any]) -> tuple[dict[str, Any], str]:
    beat_id = _history_recovery(_resolve_beat(scene, instance), scene)
    runtime = scene.get("script_runtime")
    runtime = deepcopy(runtime) if isinstance(runtime, dict) else {}
    previous = _text(runtime.get("current_beat"))
    if previous != beat_id:
        runtime["turn_in_beat"] = 0
    runtime["current_beat"] = beat_id
    runtime.setdefault("completed", [])
    runtime["version"] = CASADA_FRUSTRADA_RUNTIME_VERSION
    scene["script_runtime"] = runtime
    beat = obter_beat(beat_id) or {}
    scene["current_beat"] = beat_id
    scene["current_route"] = _text(beat.get("route")) or _text(scene.get("current_route"))
    instance["current_beat"] = beat_id
    instance["current_route"] = scene["current_route"]
    instance["scene_state"] = scene
    return runtime, beat_id



def _should_advance(beat_id: str, turn_in_beat: int, user_text: str) -> bool:
    text = _normalize(user_text)
    budget = BEAT_TURN_BUDGET.get(beat_id, 3)
    if turn_in_beat >= budget:
        return True
    if beat_id == "accidental_bump" and any(term in text for term in ("ta melhor", "esta melhor", "consigo andar", "vou terminar")):
        return True
    if beat_id == "phone_request" and any(term in text for term in ("anota", "meu numero", "te passo", "pode pegar")):
        return True
    if beat_id == "offer_video" and any(term in text for term in ("pode ligar", "liga", "aceito", "chama")):
        return True
    if beat_id == "confirm_motel" and any(term in text for term in ("combinado", "estarei la", "eu vou", "fechado")):
        return True
    return False



def _advance_after_response(user_text: str) -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    scene = _current_scene(instance)
    runtime, beat_id = _runtime_state(scene, instance)
    runtime["turn_in_beat"] = int(runtime.get("turn_in_beat", 0) or 0) + 1

    if _should_advance(beat_id, runtime["turn_in_beat"], user_text):
        completed = list(runtime.get("completed") or [])
        if beat_id not in completed:
            completed.append(beat_id)
        next_beat = proximo_beat_padrao(beat_id)
        if next_beat and obter_beat(next_beat):
            runtime["current_beat"] = next_beat
            runtime["turn_in_beat"] = 0
            beat = obter_beat(next_beat) or {}
            scene["current_beat"] = next_beat
            scene["current_route"] = _text(beat.get("route"))
            instance["current_beat"] = next_beat
            instance["current_route"] = scene["current_route"]
        runtime["completed"] = completed[-40:]

    scene["script_runtime"] = runtime
    # Remove os campos verbosos que antes eram reenviados ao modelo.
    for key in ("last_director_analysis", "last_director_decision", "recommended_focus", "pending_events"):
        scene.pop(key, None)
    instance["scene_state"] = scene
    instance["scenario_prompt"] = ""
    st.session_state["scenario_instance"] = instance
    try:
        salvar_instancia_cenario(instance, houve_interacao=False)
    except Exception:
        pass



def _prepare_before_turn() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    scene = _current_scene(instance)
    _runtime_state(scene, instance)
    instance["scenario_prompt"] = ""
    st.session_state["scenario_instance"] = instance



def _character_payload() -> dict[str, Any]:
    card = obter_card(SCENARIO_ID) or {}
    character = card.get("character") if isinstance(card.get("character"), dict) else {}
    psychology = card.get("psychology") if isinstance(card.get("psychology"), dict) else {}
    voice = card.get("voice") if isinstance(card.get("voice"), dict) else {}
    return {
        "physical": PHYSICAL_CANON,
        "psychology": {
            "core": list(character.get("core_traits") or [])[:5],
            "latent": list(character.get("latent_traits") or [])[:4],
            "contradictions": list(character.get("contradictions") or [])[:3],
            "route_expression": psychology.get("route_expression", {}),
        },
        "voice": {
            "register": voice.get("default_register", "popular, íntimo e direto"),
            "humor": voice.get("humor", "contextual"),
        },
    }



def _compact_prompt() -> str:
    instance = _instance()
    if not isinstance(instance, dict):
        return ""
    scene = _current_scene(instance)
    runtime, beat_id = _runtime_state(scene, instance)
    beat = obter_beat(beat_id)
    if not beat:
        return ""
    sexual = _sexual_state()
    payload = {
        "character": _character_payload(),
        "scene": {
            key: scene.get(key)
            for key in ("location", "time_context", "mary_clothing", "user_clothing", "position", "privacy_established", "video_call_established")
            if scene.get(key) not in (None, "", False)
        },
        "script": {
            "route": beat.get("route"),
            "beat": beat_id,
            "turn_in_beat": runtime.get("turn_in_beat", 0),
            "objective": beat.get("objective"),
            "examples": list(beat.get("examples") or [])[:2],
            "avoid": list(beat.get("avoid") or [])[:4],
            "transition": beat.get("transition") or "",
        },
        "sexual": {
            "phase": sexual.get("scene_phase"),
            "arousal": sexual.get("arousal_level"),
            "mary_orgasm_allowed": bool(sexual.get("mary_orgasm_allowed")),
            "mary_orgasm_done": bool(sexual.get("mary_orgasm_done")),
            "user_orgasm_done": bool(sexual.get("user_orgasm_done")),
        },
        "recent": _messages(6),
    }
    return (
        "Você é Mary, brasileira adulta de 25 anos, na história Casada Frustrada.\n"
        "Fale em primeira pessoa, como mulher real, nunca como assistente.\n"
        "O roteiro abaixo decide O QUE acontece; você decide apenas COMO Mary fala.\n"
        "Cumpra o objetivo do beat neste turno. Não abra entrevista, não troque de assunto e não repita etapa concluída.\n"
        "Reaja brevemente ao usuário e execute o movimento obrigatório. No máximo uma pergunta.\n"
        "Não invente ação, consentimento, sensação ou orgasmo do usuário.\n"
        "Use 1 a 3 parágrafos curtos. Pensamento privado, somente quando acrescentar algo: Pensamento de Mary: ...\n"
        "ESTADO=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        "Produza somente a próxima resposta de Mary."
    )



def _local_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
    instance = _instance()
    if not isinstance(instance, dict):
        return {}
    scene = _current_scene(instance)
    _, beat_id = _runtime_state(scene, instance)
    beat = obter_beat(beat_id) or {}
    intensity = int(beat.get("intensity", 0) or 0)
    return {
        "user_action": _text(kwargs.get("user_text")),
        "user_style": "responsive",
        "scene_changed": False,
        "new_facts": [],
        "resolved_elements": [],
        "open_elements": [],
        "narrative_progress": True,
        "relationship_effect": "unchanged",
        "recommended_phase": "intimacy" if beat.get("sexual_phase") == "active" else "familiarity",
        "recommended_focus": _text(beat.get("objective")),
        "mary_initiative_strength": 3 if intensity >= 3 else 1,
        "action_choice": "lead" if intensity >= 2 else "react",
        "should_create_hook": False,
        "mary_should_add_affordance": False,
        "seduction_level": intensity,
        "seduction_progress_allowed": intensity >= 1,
        "sexual_reciprocity_evidence": False,
        "intimate_action_started": beat.get("sexual_phase") == "active",
        "consent_confirmed": False,
        "sexual_scene_phase": beat.get("sexual_phase", "idle"),
        "sexual_turn_intent": "continue" if intensity >= 2 else "none",
        "ending_signal": False,
        "satisfaction_signal": False,
        "user_disengaged": False,
        "confidence": 1.0,
        "recommended_route": beat.get("route", ""),
        "recommended_beat": beat_id,
        "_scenario_id": SCENARIO_ID,
    }



def _patch_main() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return

    prompt_builder = getattr(module, "montar_prompt_sistema", None)
    if callable(prompt_builder) and not getattr(prompt_builder, "_casada_single_runtime", False):
        @wraps(prompt_builder)
        def prompt_wrapper(*args: Any, **kwargs: Any) -> str:
            return _compact_prompt() if _instance() is not None else str(prompt_builder(*args, **kwargs) or "")
        prompt_wrapper._casada_single_runtime = True  # type: ignore[attr-defined]
        setattr(module, "montar_prompt_sistema", prompt_wrapper)

    direction_builder = getattr(module, "montar_direcao_narrativa", None)
    if callable(direction_builder) and not getattr(direction_builder, "_casada_single_runtime", False):
        @wraps(direction_builder)
        def direction_wrapper(*args: Any, **kwargs: Any) -> str:
            if _instance() is None:
                return str(direction_builder(*args, **kwargs) or "")
            return ""
        direction_wrapper._casada_single_runtime = True  # type: ignore[attr-defined]
        setattr(module, "montar_direcao_narrativa", direction_wrapper)

    analyzer = getattr(module, "analisar_turno_cenario", None)
    if callable(analyzer) and not getattr(analyzer, "_casada_single_runtime", False):
        @wraps(analyzer)
        def analysis_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return _local_analysis(*args, **kwargs) if _instance() is not None else analyzer(*args, **kwargs)
        analysis_wrapper._casada_single_runtime = True  # type: ignore[attr-defined]
        setattr(module, "analisar_turno_cenario", analysis_wrapper)

    processor = getattr(module, "processar_interacao", None)
    if callable(processor) and not getattr(processor, "_casada_single_runtime", False):
        @wraps(processor)
        def process_wrapper(*args: Any, **kwargs: Any) -> Any:
            if _instance() is None:
                return processor(*args, **kwargs)
            _prepare_before_turn()
            prompt = kwargs.get("prompt")
            if prompt is None and args:
                prompt = args[0]
            result = processor(*args, **kwargs)
            _advance_after_response(_text(prompt))
            return result
        process_wrapper._casada_single_runtime = True  # type: ignore[attr-defined]
        setattr(module, "processar_interacao", process_wrapper)



def install_casada_frustrada_runtime() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _patch_main()
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        _patch_main()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_RUNTIME_VERSION",
    "install_casada_frustrada_runtime",
]
