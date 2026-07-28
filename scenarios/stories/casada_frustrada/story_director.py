from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from .beat_graph import INITIAL_BEAT, obter_beat, proximo_beat_padrao
from .canonical_memory import atualizar_memoria_canonica, memoria_canonica_para_prompt
from .canonical_screenplay import linhas_canonicas_do_beat
from .prompt_context import montar_contexto_interpretativo
from .screenplay_executor import construir_trava_de_roteiro
from .story_observer import observar_estado_narrativo


STORY_DIRECTOR_VERSION = "casada-frustrada-story-director-v6-single-cursor"

_GATE_MARKERS: dict[str, tuple[str, ...]] = {
    "accept_help_car": ("espero", "ajudo", "vou ajudar", "pode deixar", "claro"),
    "phone_acceptance": ("numero", "número", "anota", "salva", "pode anotar"),
    "video_acceptance": ("pode chamar", "chama", "liga", "aceito", "vamos"),
    "shirt_acceptance": ("tirei", "sem camisa", "pronto", "mostrei"),
    "pants_acceptance": ("tirei", "sem calca", "sem calça", "de cueca", "pronto"),
    "bra_request": ("tira", "quero ver", "por favor", "mostra"),
    "underwear_acceptance": ("tirei", "sem cueca", "nu", "pelado", "pronto"),
    "mutual_acceptance": ("topo", "vamos", "me tocando", "comecei"),
    "user_climax": ("gozei", "gozando", "vou gozar"),
    "meeting_interest": ("topo", "aceito", "pode ser", "vamos", "motel"),
    "meeting_acceptance": ("combinado", "fechado", "estarei la", "estarei lá", "meio dia", "meio-dia"),
    "arrival": ("cheguei", "chegando", "portaria", "estou aqui", "to aqui"),
    "erection_confirmed": ("duro", "erecao", "ereção", "pronto de novo"),
    "penetration_acceptance": ("entra", "pode", "vai", "mete", "dentro"),
    "mary_orgasm_allowed": ("continua", "nao para", "não para", "vai", "goza"),
    "farewell": ("tchau", "boa noite", "ate", "até", "beijo"),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _latest_exchange(messages: list[dict[str, Any]]) -> tuple[str, str] | None:
    user_index = -1
    user_text = ""
    for index in range(len(messages) - 1, -1, -1):
        item = messages[index]
        if isinstance(item, dict) and _text(item.get("role")) == "user":
            user_index = index
            user_text = _text(item.get("content"))
            break
    if user_index < 0:
        return None

    for index in range(user_index - 1, -1, -1):
        item = messages[index]
        if isinstance(item, dict) and _text(item.get("role")) == "assistant":
            assistant_text = _text(item.get("content"))
            if assistant_text:
                return assistant_text, user_text
    return None


def _canonical_was_emitted(beat_id: str, assistant_text: str) -> bool:
    response = _normalize(assistant_text)
    canonical = [_normalize(line) for line in linhas_canonicas_do_beat(beat_id)]
    canonical = [line for line in canonical if line]
    return bool(canonical) and any(line in response for line in canonical)


def _gate_satisfied(gate: str, user_text: str) -> bool:
    normalized = _normalize(user_text)
    if not normalized:
        return False
    markers = _GATE_MARKERS.get(gate, ())
    return any(_normalize(marker) in normalized for marker in markers)


def _single_cursor(instance: dict[str, Any]) -> tuple[dict[str, Any], str]:
    scene_value = instance.get("scene_state")
    scene = deepcopy(scene_value) if isinstance(scene_value, dict) else {}

    beat = _text(scene.get("current_beat"))
    if not obter_beat(beat):
        legacy = _text(instance.get("current_beat"))
        beat = legacy if obter_beat(legacy) else INITIAL_BEAT

    scene["current_beat"] = beat
    return scene, beat


def _advance_once(scene: dict[str, Any], beat_id: str, messages: list[dict[str, Any]]) -> tuple[str, str]:
    exchange = _latest_exchange(messages)
    if exchange is None:
        return beat_id, "cursor_unchanged_no_exchange"

    assistant_text, user_text = exchange
    if not _canonical_was_emitted(beat_id, assistant_text):
        return beat_id, "cursor_unchanged_current_beat_not_emitted"

    beat = obter_beat(beat_id) or {}
    gate = _text(beat.get("gate"))
    if gate and not _gate_satisfied(gate, user_text):
        scene["pending_gate"] = gate
        return beat_id, "cursor_held_by_gate"

    next_beat = proximo_beat_padrao(beat_id)
    if not next_beat:
        return beat_id, "cursor_at_terminal_beat"

    completed = list(scene.get("completed_beats") or [])
    if beat_id not in completed:
        completed.append(beat_id)
    scene["completed_beats"] = completed
    scene.pop("pending_gate", None)
    scene["current_beat"] = next_beat
    return next_beat, "cursor_advanced_by_screenplay_next"


def _focused_compass(compass: dict[str, Any]) -> dict[str, Any]:
    return {
        "human_state": compass.get("human_state"),
        "dramatic_center": compass.get("dramatic_center"),
        "route_goal": compass.get("route_goal"),
        "never": list(compass.get("never") or [])[:6],
        "story_reality": compass.get("story_reality", {}),
        "source_authority": (
            "immersive_screenplay.py é a única fonte textual. "
            "scene_state.current_beat é o único cursor da história."
        ),
    }


def dirigir_turno(*, instance: dict[str, Any], messages: list[dict[str, Any]], story_state_value: Any = None) -> dict[str, Any]:
    scene, beat_before = _single_cursor(instance)
    beat, progression_reason = _advance_once(scene, beat_before, messages)

    beat_data = obter_beat(beat) or obter_beat(INITIAL_BEAT) or {}
    beat = _text(beat_data.get("id")) or INITIAL_BEAT
    route = _text(beat_data.get("route"))
    scene["current_beat"] = beat
    scene["current_route"] = route

    memory = atualizar_memoria_canonica(
        instance.get("story_memory"),
        messages=messages,
        route=route,
        beat=beat,
    )
    memory_prompt = memoria_canonica_para_prompt(memory)

    story_state = observar_estado_narrativo(
        story_state_value,
        messages=messages,
        route=route,
        beat_id=beat,
    )
    compass = montar_contexto_interpretativo(
        route=route,
        current_beat=beat,
        story_state_value=story_state,
    )
    screenplay_lock = construir_trava_de_roteiro(beat)

    instance["scene_state"] = scene
    instance["story_memory"] = memory

    # Espelhos temporários para compatibilidade externa. Nunca são lidos como
    # autoridade quando scene_state.current_beat é válido.
    instance["current_beat"] = beat
    instance["current_route"] = route

    return {
        "version": STORY_DIRECTOR_VERSION,
        "route": route,
        "beat": beat,
        "objective": "Interpretar as falas canônicas do beat atual.",
        "gate": _text(beat_data.get("gate")),
        "avoid": [],
        "screenplay_lock": screenplay_lock,
        "route_compass": _focused_compass(compass),
        "canonical_story_memory": memory_prompt,
        "confirmed_visual_state": deepcopy(scene.get("confirmed_visual_state") or {}),
        "screenplay_execution": {
            "completed_beats": list(scene.get("completed_beats") or []),
            "progression_source": "single_scene_cursor",
        },
        "story_state": story_state,
        "resolution": {
            "beat_before": beat_before,
            "beat_after": beat,
            "progression_reason": progression_reason,
            "authority": "scene_state.current_beat é o único cursor narrativo.",
        },
    }


__all__ = ["STORY_DIRECTOR_VERSION", "dirigir_turno"]
