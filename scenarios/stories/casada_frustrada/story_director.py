from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from .beat_graph import BEAT_ORDER, obter_beat, proximo_beat_padrao
from .canonical_memory import atualizar_memoria_canonica, memoria_canonica_para_prompt
from .prompt_context import montar_contexto_interpretativo
from .screenplay_executor import (
    construir_trava_de_roteiro,
    observar_execucao_motel,
    proximo_beat_motel,
)
from .story_observer import observar_estado_narrativo
from .story_sync import reconciliar_posicao_narrativa


STORY_DIRECTOR_VERSION = "casada-frustrada-story-director-v5-event-driven-screenplay"

# Estes beats terminam pela própria emissão de Mary. Eles não dependem de uma
# ação posterior do usuário para que o grafo siga adiante.
AUTOCOMPLETE_ON_EMIT = {
    "first_farewell",
    "car_farewell",
    "end_first_call",
    "good_night",
    "motel_preparation",
    "heels_and_panties",
    "oral_admiration",
    "request_her_pleasure",
    "first_orgasm_build",
    "post_oral_tease",
    "praise_lover",
    "penetration_rhythm",
    "second_orgasm_build",
    "post_penetration",
    "clean_with_mouth",
    "final_departure",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _history(messages: list[dict[str, Any]], role: str = "") -> str:
    parts: list[str] = []
    for item in messages[-120:]:
        if not isinstance(item, dict):
            continue
        item_role = _text(item.get("role"))
        if item_role not in {"user", "assistant"} or (role and item_role != role):
            continue
        content = _normalize(item.get("content"))
        if content:
            parts.append(content)
    return " ".join(parts)


def _latest(messages: list[dict[str, Any]], role: str) -> str:
    for item in reversed(messages):
        if isinstance(item, dict) and _text(item.get("role")) == role:
            return _normalize(item.get("content"))
    return ""


def _contains(text: str, *markers: str) -> bool:
    return any(marker in text for marker in markers)


def _legacy_position(instance: dict[str, Any]) -> tuple[str, str]:
    scene = instance.get("scene_state")
    scene = scene if isinstance(scene, dict) else {}
    runtime = scene.get("script_runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    beat = _text(runtime.get("current_beat") or scene.get("current_beat") or instance.get("current_beat"))
    route = _text(scene.get("current_route") or instance.get("current_route"))
    beat_data = obter_beat(beat) or {}
    return _text(beat_data.get("route")) or route, beat


def _advance_emitted_beat(scene: dict[str, Any], route: str, beat: str) -> tuple[str, str, str]:
    """Advance only from an execution event recorded by the application.

    Dialogue wording is deliberately ignored. The prior director records
    ``directed_beat``; the runtime records ``last_mary_response`` after Mary
    actually speaks. Their conjunction proves that Mary emitted that beat.
    """
    directed = _text(scene.get("directed_beat"))
    emitted = bool(_text(scene.get("last_mary_response")))
    already_advanced = _text(scene.get("advanced_from_beat"))

    # Migration for sessions created before directed_beat existed. good_night is
    # intrinsically self-completing, so a persisted Mary response is sufficient.
    legacy_good_night = beat == "good_night" and emitted
    proven_emission = directed == beat and emitted

    beat_data = obter_beat(beat) or {}
    gate = _text(beat_data.get("gate"))
    autocompletes = not gate or beat in AUTOCOMPLETE_ON_EMIT

    if not autocompletes or already_advanced == beat or not (proven_emission or legacy_good_night):
        return route, beat, ""

    next_beat = proximo_beat_padrao(beat)
    if not next_beat:
        return route, beat, ""

    next_data = obter_beat(next_beat) or {}
    scene["advanced_from_beat"] = beat
    completed = list(scene.get("completed_script_beats") or [])
    if beat not in completed:
        completed.append(beat)
    scene["completed_script_beats"] = completed
    return _text(next_data.get("route")) or route, next_beat, "beat_graph_advanced_after_mary_emission"


def _call_visual_state(messages: list[dict[str, Any]], previous: Any) -> dict[str, bool]:
    state = deepcopy(previous) if isinstance(previous, dict) else {}
    history = _history(messages)
    assistant = _history(messages, "assistant")
    user = _history(messages, "user")
    checks = {
        "video_call_established": _contains(history, "ta me vendo", "esta me vendo", "camera ligada", "chamada de video", "celular aqui na bancada"),
        "user_shirt_removed": _contains(user, "tirei a camisa", "sem camisa", "agora da pra ver", "mostrei o peitoral"),
        "user_pants_removed": _contains(user, "tirei a calca", "sem calca", "fiquei de cueca", "so de cueca"),
        "mary_dress_removed": _contains(assistant, "vou tirar o vestido", "tirei o vestido", "fiquei de calcinha e sutia", "so de calcinha e sutia"),
        "mary_bra_removed": _contains(assistant, "tirei o sutia", "vou tirar o sutia", "sem sutia"),
        "user_underwear_removed": _contains(user, "tirei a cueca", "sem cueca", "estou nu", "to nu"),
        "mary_panties_removed": _contains(assistant, "vou tirar a calcinha", "tirei a calcinha", "sem calcinha"),
        "mutual_masturbation_started": _contains(history, "masturbacao mutua", "se toca ai", "vou me masturbar", "estou me tocando", "to me tocando"),
        "user_climax_confirmed": _contains(user, "gozei", "estou gozando", "to gozando", "vou gozar agora"),
        "first_call_ended": _contains(assistant, "preciso desligar", "te ligo quando meu marido", "vou desligar", "daqui a pouco eu te chamo"),
    }
    for key, detected in checks.items():
        state[key] = bool(state.get(key)) or detected
    return state


def _resolve_hidden_call_beat(messages: list[dict[str, Any]], visual: dict[str, bool], fallback: str) -> str:
    assistant = _history(messages, "assistant")
    if visual.get("user_climax_confirmed"):
        return "react_user_climax"
    if visual.get("mutual_masturbation_started"):
        return "urge_user_climax"
    if visual.get("mary_panties_removed"):
        return "propose_mutual_masturbation"
    if visual.get("user_underwear_removed"):
        if _contains(assistant, "entre meus seios", "colocar ela aqui"):
            return "mary_remove_panties"
        if _contains(assistant, "que rola", "voce e gostoso"):
            return "breast_fantasy"
        return "react_nudity"
    if visual.get("mary_bra_removed"):
        return "ask_remove_underwear"
    if visual.get("mary_dress_removed"):
        return "invite_bra_request"
    if visual.get("user_pants_removed"):
        return "mary_remove_dress" if _contains(assistant, "olha esse volume", "volume na cueca") else "react_underwear"
    if visual.get("user_shirt_removed"):
        return "ask_remove_pants" if _contains(assistant, "voce e gostoso", "que peitoral", "to vermelha") else "react_torso"
    if visual.get("video_call_established"):
        return "ask_remove_shirt" if _contains(assistant, "voce e lindo", "posso te pedir uma coisa") else "admire_video"
    return fallback if fallback in BEAT_ORDER and (obter_beat(fallback) or {}).get("route") == "hidden_call" else "camera_setup"


def _resolve_meeting_plan_beat(messages: list[dict[str, Any]], fallback: str) -> str:
    """Resolve only gated decisions; never use old dialogue to replay a beat."""
    latest_user = _latest(messages, "user")
    latest_assistant = _latest(messages, "assistant")
    user_awake = _contains(latest_user, "acordei", "to acordado", "estou acordado", "to ouvindo", "oi mary")
    user_accepts = _contains(latest_user, "sim", "claro", "pode ser", "vamos", "topo", "aceito", "combinado", "fechado")

    if fallback == "midnight_return" and (user_awake or _contains(latest_assistant, "ta acordado", "esta acordado")):
        return "propose_motel"
    if fallback == "propose_motel" and user_accepts:
        return "name_motel"
    if fallback == "name_motel" and user_accepts:
        return "demand_no_show"
    return fallback if fallback in {"midnight_return", "propose_motel", "name_motel", "demand_no_show", "good_night", "motel_preparation"} else "midnight_return"


def _motel_present(messages: list[dict[str, Any]]) -> bool:
    history = _history(messages)
    user = _history(messages, "user")
    return _contains(history, "motel status", "peguei uma suite", "estou na suite", "cheguei no motel") and _contains(
        user, "cheguei", "to entrando", "estou entrando", "to aqui", "estou aqui", "sentindo seu abraco", "chup", "plaf"
    )


def _apply_memory_authority(route: str, beat: str, memory_prompt: dict[str, Any], messages: list[dict[str, Any]]) -> tuple[str, str, str]:
    unlocked = set(memory_prompt.get("unlocked_ids") or [])
    history = _history(messages)
    if "first_private_messages" in unlocked and route in {"supermarket_encounter", "aisle_flirtation", "phone_exchange"}:
        if _contains(history, "posso te chamar por video", "te chamar por video", "te achei muito atraente"):
            return "messages", "offer_video", "canonical_memory_forced_messages"
        if _contains(history, "banheiro", "falar com voce em paz", "mais a vontade"):
            return "messages", "admit_neediness", "canonical_memory_forced_messages"
        return "messages", "home_first_message", "canonical_memory_forced_messages"
    if "exchanged_phone_numbers" in unlocked and beat in {"request_phone", "exchange_numbers"}:
        return "messages", "home_first_message", "canonical_memory_blocked_phone_repetition"
    if "first_hidden_video_call" in unlocked and route == "messages" and beat == "offer_video":
        return "secret_meeting_plan", "midnight_return", "canonical_memory_blocked_first_video_repetition"
    return route, beat, ""


def _focused_compass(compass: dict[str, Any]) -> dict[str, Any]:
    return {
        "human_state": compass.get("human_state"),
        "dramatic_center": compass.get("dramatic_center"),
        "route_goal": compass.get("route_goal"),
        "never": list(compass.get("never") or [])[:6],
        "story_reality": compass.get("story_reality", {}),
        "source_authority": (
            "O roteiro integral permanece no domínio. O modelo recebe somente o beat atual; "
            "a progressão vem de eventos do sistema e do next de beat_graph.py, nunca de frases casuais."
        ),
    }


def dirigir_turno(*, instance: dict[str, Any], messages: list[dict[str, Any]], story_state_value: Any = None) -> dict[str, Any]:
    scene = instance.get("scene_state")
    scene = deepcopy(scene) if isinstance(scene, dict) else {}

    legacy_route, legacy_beat = _legacy_position(instance)
    event_route, event_beat, event_reason = _advance_emitted_beat(scene, legacy_route, legacy_beat)

    synchronized = reconciliar_posicao_narrativa(
        messages=messages,
        legacy_route=event_route,
        legacy_beat=event_beat,
    )
    route = _text(synchronized.get("route") or event_route)
    beat = _text(synchronized.get("beat") or event_beat)

    memory = atualizar_memoria_canonica(instance.get("story_memory"), messages=messages, route=route, beat=beat)
    memory_prompt = memoria_canonica_para_prompt(memory)
    route, beat, memory_reason = _apply_memory_authority(route, beat, memory_prompt, messages)
    memory_reason = event_reason or memory_reason

    visual_state = _call_visual_state(messages, scene.get("confirmed_visual_state"))
    motel_execution: dict[str, Any] = {}

    if _motel_present(messages):
        motel_execution = observar_execucao_motel(messages, scene.get("screenplay_execution"))
        beat = proximo_beat_motel(motel_execution)
        route = _text((obter_beat(beat) or {}).get("route")) or "secret_meeting"
        memory_reason = "locked_screenplay_executor_overrode_cursor"
    elif beat == "motel_preparation":
        route = "secret_meeting"
    elif visual_state.get("first_call_ended") and route in {"hidden_call", "secret_meeting_plan"}:
        route = "secret_meeting_plan"
        beat = _resolve_meeting_plan_beat(messages, beat)
        if beat == "motel_preparation":
            route = "secret_meeting"
        memory_reason = memory_reason or "first_call_ended_opens_meeting_plan"
    elif route == "hidden_call" or visual_state.get("video_call_established"):
        route = "hidden_call"
        beat = _resolve_hidden_call_beat(messages, visual_state, beat)

    beat_data = obter_beat(beat) or {}
    resolved_route = _text(beat_data.get("route")) or route
    story_state = observar_estado_narrativo(story_state_value, messages=messages, route=resolved_route, beat_id=beat)
    raw_compass = montar_contexto_interpretativo(route=resolved_route, current_beat=beat, story_state_value=story_state)
    screenplay_lock = construir_trava_de_roteiro(beat)

    scene["confirmed_visual_state"] = visual_state
    if motel_execution:
        scene["screenplay_execution"] = motel_execution
    scene["current_route"] = resolved_route
    scene["current_beat"] = beat
    scene["directed_beat"] = beat
    scene.pop("script_runtime", None)
    instance["scene_state"] = scene
    instance["current_route"] = resolved_route
    instance["current_beat"] = beat
    instance["story_memory"] = memory

    return {
        "version": STORY_DIRECTOR_VERSION,
        "route": resolved_route,
        "beat": beat,
        "objective": _text(beat_data.get("objective")),
        "gate": _text(beat_data.get("gate")),
        "avoid": list(beat_data.get("avoid") or [])[:5],
        "screenplay_lock": screenplay_lock,
        "route_compass": _focused_compass(raw_compass),
        "canonical_story_memory": memory_prompt,
        "confirmed_visual_state": visual_state,
        "screenplay_execution": motel_execution or {
            "completed_beats": list(scene.get("completed_script_beats") or []),
            "progression_source": "beat_graph_events",
        },
        "story_state": story_state,
        "resolution": {
            "legacy_route": legacy_route,
            "legacy_beat": legacy_beat,
            "synchronized": synchronized,
            "memory_override_reason": memory_reason,
            "authority": (
                "A sequência vem de eventos de execução e do next de beat_graph.py. "
                "Texto casual do usuário nunca escolhe a próxima etapa."
            ),
        },
    }


__all__ = ["STORY_DIRECTOR_VERSION", "dirigir_turno"]
