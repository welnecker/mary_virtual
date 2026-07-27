from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from .beat_graph import BEAT_ORDER, obter_beat
from .canonical_memory import atualizar_memoria_canonica, memoria_canonica_para_prompt
from .prompt_context import montar_contexto_interpretativo
from .story_observer import observar_estado_narrativo
from .story_sync import reconciliar_posicao_narrativa


STORY_DIRECTOR_VERSION = "casada-frustrada-story-director-v2-call-boundaries"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _history(messages: list[dict[str, Any]], role: str = "") -> str:
    parts: list[str] = []
    for item in messages[-100:]:
        if not isinstance(item, dict):
            continue
        item_role = _text(item.get("role"))
        if item_role not in {"user", "assistant"} or (role and item_role != role):
            continue
        content = _text(item.get("content"))
        if content:
            parts.append(_normalize(content))
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
    route = _text(beat_data.get("route")) or route
    return route, beat


def _call_visual_state(messages: list[dict[str, Any]], previous: Any) -> dict[str, bool]:
    state = deepcopy(previous) if isinstance(previous, dict) else {}
    history = _history(messages)
    assistant = _history(messages, "assistant")
    user = _history(messages, "user")

    checks = {
        "video_call_established": _contains(history, "ta me vendo", "esta me vendo", "camera ligada", "chamada de video", "celular aqui na bancada"),
        "user_shirt_removed": _contains(user, "tirei a camisa", "sem camisa", "agora da pra ver", "agora consegue ver", "mostrei o peito", "mostrei o peitoral"),
        "user_pants_removed": _contains(user, "tirei a calca", "sem calca", "fiquei de cueca", "so de cueca"),
        "mary_dress_removed": _contains(assistant, "vou tirar o vestido", "tirei o vestido", "fiquei de calcinha e sutia", "so de calcinha e sutia"),
        "mary_bra_removed": _contains(assistant, "tirei o sutia", "vou tirar o sutia", "sem sutia", "meus seios", "meus peitos"),
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
    latest_assistant = _latest(messages, "assistant")

    if visual.get("user_climax_confirmed"):
        return "react_user_climax"
    if visual.get("mutual_masturbation_started"):
        return "urge_user_climax"
    if visual.get("mary_panties_removed"):
        return "propose_mutual_masturbation"
    if visual.get("user_underwear_removed"):
        if _contains(assistant, "entre meus seios", "colocar ela aqui"):
            return "mary_remove_panties"
        if _contains(assistant, "que rola", "voce e muito gostoso", "voce e gostoso"):
            return "breast_fantasy"
        return "react_nudity"
    if visual.get("mary_bra_removed"):
        return "ask_remove_underwear"
    if visual.get("mary_dress_removed"):
        return "invite_bra_request"
    if visual.get("user_pants_removed"):
        if _contains(assistant, "olha esse volume", "volume na cueca"):
            return "mary_remove_dress"
        return "react_underwear"
    if visual.get("user_shirt_removed"):
        if _contains(assistant, "voce e gostoso", "que peitoral", "to vermelha", "estou vermelha"):
            return "ask_remove_pants"
        return "react_torso"
    if visual.get("video_call_established"):
        if _contains(assistant, "voce e lindo", "voce e muito lindo", "posso te pedir uma coisa"):
            return "ask_remove_shirt"
        return "admire_video"
    return fallback if fallback in BEAT_ORDER and (obter_beat(fallback) or {}).get("route") == "hidden_call" else "camera_setup"


def _resolve_meeting_plan_beat(messages: list[dict[str, Any]], fallback: str) -> str:
    assistant = _history(messages, "assistant")
    latest_user = _latest(messages, "user")
    latest_assistant = _latest(messages, "assistant")

    user_awake = _contains(latest_user, "acordei", "to acordado", "estou acordado", "to ouvindo", "estou ouvindo", "oi mary")
    user_accepts = _contains(latest_user, "sim", "claro", "pode ser", "vamos", "topo", "aceito", "combinado", "fechado")

    if _contains(assistant, "boa noite", "sonha comigo"):
        return "good_night"
    if _contains(assistant, "nao vai me dar bolo", "nao me da bolo", "voce ta me devendo"):
        return "good_night"
    if _contains(assistant, "motel status", "amanha ao meio dia", "amanha meio dia"):
        return "demand_no_show" if user_accepts else "name_motel"
    if _contains(assistant, "o que acha de um motel", "quero marcar um lugar", "vamos nos encontrar", "quero te encontrar"):
        return "name_motel" if user_accepts else "propose_motel"
    if user_awake or _contains(latest_assistant, "ta acordado", "esta acordado"):
        return "propose_motel"
    return fallback if fallback in {"midnight_return", "propose_motel", "name_motel", "demand_no_show", "good_night"} else "midnight_return"


def _apply_memory_authority(route: str, beat: str, memory_prompt: dict[str, Any], messages: list[dict[str, Any]]) -> tuple[str, str, str]:
    unlocked = set(memory_prompt.get("unlocked_ids") or [])
    history = _history(messages)

    if "first_private_messages" in unlocked and route in {"supermarket_encounter", "aisle_flirtation", "phone_exchange"}:
        route = "messages"
        if _contains(history, "posso te chamar por video", "te chamar por video"):
            beat = "offer_video"
        elif _contains(history, "te achei muito atraente", "voce me atrai", "estou atraida"):
            beat = "offer_video"
        elif _contains(history, "banheiro", "falar com voce em paz", "mais a vontade"):
            beat = "admit_neediness"
        else:
            beat = "home_first_message"
        return route, beat, "canonical_memory_forced_messages"

    if "exchanged_phone_numbers" in unlocked and beat in {"request_phone", "exchange_numbers"}:
        if _contains(history, "cheguei", "tela do celular", "mensagem", "trancada no quarto", "sozinho em casa", "sozinha em casa"):
            return "messages", "home_first_message", "canonical_memory_blocked_phone_repetition"
        return "phone_exchange", "car_farewell", "canonical_memory_blocked_phone_repetition"

    if "first_hidden_video_call" in unlocked and route == "messages" and beat == "offer_video":
        return "secret_meeting_plan", "midnight_return", "canonical_memory_blocked_first_video_repetition"

    return route, beat, ""


def dirigir_turno(
    *,
    instance: dict[str, Any],
    messages: list[dict[str, Any]],
    story_state_value: Any = None,
) -> dict[str, Any]:
    legacy_route, legacy_beat = _legacy_position(instance)
    synchronized = reconciliar_posicao_narrativa(
        messages=messages,
        legacy_route=legacy_route,
        legacy_beat=legacy_beat,
    )
    route = _text(synchronized.get("route") or legacy_route)
    beat = _text(synchronized.get("beat") or legacy_beat)

    previous_memory = instance.get("story_memory")
    memory = atualizar_memoria_canonica(
        previous_memory,
        messages=messages,
        route=route,
        beat=beat,
    )
    memory_prompt = memoria_canonica_para_prompt(memory)
    route, beat, memory_reason = _apply_memory_authority(route, beat, memory_prompt, messages)

    scene = instance.get("scene_state")
    scene = deepcopy(scene) if isinstance(scene, dict) else {}
    visual_state = _call_visual_state(messages, scene.get("confirmed_visual_state"))

    if visual_state.get("first_call_ended"):
        route = "secret_meeting_plan"
        beat = _resolve_meeting_plan_beat(messages, beat)
        memory_reason = memory_reason or "first_call_ended_opens_meeting_plan"
    elif route == "hidden_call" or visual_state.get("video_call_established"):
        route = "hidden_call"
        beat = _resolve_hidden_call_beat(messages, visual_state, beat)

    beat_data = obter_beat(beat) or {}
    resolved_route = _text(beat_data.get("route")) or route

    story_state = observar_estado_narrativo(
        story_state_value,
        messages=messages,
        route=resolved_route,
        beat_id=beat,
    )
    compass = montar_contexto_interpretativo(
        route=resolved_route,
        current_beat=beat,
        story_state_value=story_state,
    )

    scene["confirmed_visual_state"] = visual_state
    scene["current_route"] = resolved_route
    scene["current_beat"] = beat
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
        "screenplay": compass.get("official_screenplay", {}),
        "route_compass": compass,
        "canonical_story_memory": memory_prompt,
        "confirmed_visual_state": visual_state,
        "story_state": story_state,
        "resolution": {
            "legacy_route": legacy_route,
            "legacy_beat": legacy_beat,
            "synchronized": synchronized,
            "memory_override_reason": memory_reason,
            "authority": (
                "Esta é a única direção narrativa do turno. Foi resolvida a partir do passado "
                "canônico, dos fatos visuais e da conversa. O runtime não possui milestone próprio."
            ),
        },
    }


__all__ = ["STORY_DIRECTOR_VERSION", "dirigir_turno"]