from __future__ import annotations

import hashlib
import re
import unicodedata
from copy import deepcopy
from typing import Any, Callable

from .beat_graph import obter_beat, proximo_beat_padrao
from .canonical_screenplay import linhas_canonicas_do_beat


PROGRESSION_GUARD_VERSION = "casada-frustrada-progression-guard-v1-emission-seal"

_ACCEPTANCE_MARKERS = (
    "sim", "claro", "pode", "pode ser", "topo", "aceito", "combinado",
    "fechado", "vamos", "pronto", "tirei", "fiz", "estou fazendo",
    "to fazendo", "cheguei", "estou aqui", "to aqui", "acordei",
    "estou vendo", "to vendo", "consigo ver", "anotei", "salvei",
)

_ACTION_MARKERS_BY_GATE: dict[str, tuple[str, ...]] = {
    "accept_help_car": ("espero", "ajudo", "vou ajudar", "vamos", "claro", "pode deixar"),
    "phone_acceptance": ("meu numero", "meu número", "anota", "salva", "pode anotar"),
    "video_acceptance": ("pode chamar", "chama", "liga", "aceito", "vamos por video", "vamos por vídeo"),
    "shirt_acceptance": ("tirei", "sem camisa", "pronto", "mostrei"),
    "pants_acceptance": ("tirei", "sem calca", "sem calça", "de cueca", "pronto"),
    "bra_request": ("tira", "quero ver", "por favor", "mostra"),
    "underwear_acceptance": ("tirei", "sem cueca", "nu", "pelado", "pronto"),
    "mutual_acceptance": ("topo", "vamos", "estou me tocando", "to me tocando", "comecei"),
    "user_climax": ("gozei", "to gozando", "estou gozando", "vou gozar"),
    "meeting_interest": ("topo", "aceito", "pode ser", "vamos", "motel"),
    "meeting_acceptance": ("combinado", "fechado", "estarei la", "estarei lá", "meio dia", "meio-dia"),
    "arrival": ("cheguei", "estou chegando", "to chegando", "portaria", "estou aqui", "to aqui"),
    "erection_confirmed": ("duro", "erecao", "ereção", "pronto de novo"),
    "penetration_acceptance": ("entra", "pode", "vai", "mete", "estou dentro", "to dentro"),
    "mary_orgasm_allowed": ("continua", "nao para", "não para", "vai", "goza"),
    "farewell": ("tchau", "boa noite", "ate", "até", "beijo"),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _last_exchange(messages: list[dict[str, Any]]) -> tuple[str, str] | None:
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


def _canonical_emitted(beat_id: str, assistant_text: str) -> bool:
    canonical = linhas_canonicas_do_beat(beat_id)
    if not canonical:
        return False
    normalized_response = _normalize(assistant_text)
    return any(_normalize(line) in normalized_response for line in canonical if _normalize(line))


def _gate_satisfied(gate: str, user_text: str) -> bool:
    normalized = _normalize(user_text)
    if not normalized:
        return False
    markers = _ACTION_MARKERS_BY_GATE.get(gate, ())
    if markers:
        return any(_normalize(marker) in normalized for marker in markers)
    return any(_normalize(marker) in normalized for marker in _ACCEPTANCE_MARKERS)


def preparar_progressao_canonica(
    instance: dict[str, Any],
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Consume one emitted canonical beat and move only through beat_graph.next.

    The user's wording may be creative, but it never selects a route or arbitrary
    beat. It can only satisfy the current gate. The graph chooses the successor.
    """
    scene_value = instance.get("scene_state")
    scene = deepcopy(scene_value) if isinstance(scene_value, dict) else {}
    beat_id = _text(scene.get("current_beat") or instance.get("current_beat"))
    beat = obter_beat(beat_id) or {}
    if not beat:
        return instance

    exchange = _last_exchange(messages)
    if exchange is None:
        return instance
    assistant_text, user_text = exchange
    if not _canonical_emitted(beat_id, assistant_text):
        return instance

    signature_source = f"{beat_id}\n{assistant_text}\n{user_text}"
    signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()[:20]
    if _text(scene.get("consumed_emission_signature")) == signature:
        return instance

    gate = _text(beat.get("gate"))
    if gate and not _gate_satisfied(gate, user_text):
        scene["pending_gate"] = gate
        scene["pending_gate_beat"] = beat_id
        instance["scene_state"] = scene
        return instance

    next_beat = proximo_beat_padrao(beat_id)
    if not next_beat:
        return instance
    next_data = obter_beat(next_beat) or {}

    completed = list(scene.get("completed_script_beats") or [])
    if beat_id not in completed:
        completed.append(beat_id)

    scene["completed_script_beats"] = completed
    scene["consumed_emission_signature"] = signature
    scene["emitted_beat"] = beat_id
    scene["advanced_from_beat"] = beat_id
    scene["current_beat"] = next_beat
    scene["current_route"] = _text(next_data.get("route"))
    scene.pop("pending_gate", None)
    scene.pop("pending_gate_beat", None)
    scene.pop("directed_beat", None)

    instance["scene_state"] = scene
    instance["current_beat"] = next_beat
    instance["current_route"] = _text(next_data.get("route"))
    return instance


def instalar_guarda_de_progressao(story_director_module: Any) -> None:
    original = getattr(story_director_module, "dirigir_turno", None)
    if not callable(original) or getattr(original, "_canonical_progression_guard", False):
        return

    def guarded_dirigir_turno(*, instance: dict[str, Any], messages: list[dict[str, Any]], story_state_value: Any = None) -> dict[str, Any]:
        preparar_progressao_canonica(instance, messages)
        result = original(
            instance=instance,
            messages=messages,
            story_state_value=story_state_value,
        )
        if isinstance(result, dict):
            resolution = result.setdefault("resolution", {})
            if isinstance(resolution, dict):
                resolution["progression_guard"] = PROGRESSION_GUARD_VERSION
        return result

    guarded_dirigir_turno._canonical_progression_guard = True  # type: ignore[attr-defined]
    setattr(story_director_module, "dirigir_turno", guarded_dirigir_turno)


__all__ = [
    "PROGRESSION_GUARD_VERSION",
    "preparar_progressao_canonica",
    "instalar_guarda_de_progressao",
]
