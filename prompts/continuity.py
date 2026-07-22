from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Iterable


CONTINUITY_PROMPT_VERSION = "continuity-v1-compact-grounded"


SCENE_FIELDS: tuple[str, ...] = (
    "location",
    "current_location",
    "time_context",
    "current_phase",
    "scenario_phase",
    "scene_phase",
    "current_position",
    "current_activity",
    "current_pace",
    "characters_present",
    "speaker",
    "direct_listener",
    "recommended_focus",
    "last_action_choice",
)

PENDING_FIELDS: tuple[str, ...] = (
    "open_elements",
    "open_threads",
    "pending_elements",
    "unresolved_elements",
    "promises",
    "unfinished_actions",
)

RESOLVED_FIELDS: tuple[str, ...] = (
    "resolved_elements",
    "completed_elements",
    "closed_threads",
)


# ==========================================================
# NORMALIZAÇÃO
# ==========================================================


def normalizar_texto(value: Any) -> str:
    return str(value or "").strip()


def normalizar_dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def normalizar_lista(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return list(deepcopy(value))
    return []


def limitar_texto(value: Any, *, max_chars: int) -> str:
    text = normalizar_texto(value)
    if not text:
        return ""
    limit = max(1, int(max_chars))
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def serializar_compacto(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def remover_vazios(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        if isinstance(value, (list, tuple, dict)) and not value:
            continue
        result[key] = value
    return result


# ==========================================================
# CENA ATIVA
# ==========================================================


def extrair_estado_cenario(
    relationship_state: dict[str, Any] | None,
    scene_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retorna o estado de cena mais específico disponível.

    O argumento explícito vence. Caso não exista, procura os envelopes usados
    atualmente pelo projeto. Nenhum valor é inventado.
    """

    if isinstance(scene_state, dict) and scene_state:
        return deepcopy(scene_state)

    relationship = normalizar_dict(relationship_state)
    for key in (
        "active_scenario",
        "scenario_state",
        "scene_state",
        "current_scenario",
        "scenario_context",
    ):
        candidate = relationship.get(key)
        if not isinstance(candidate, dict):
            continue
        nested = candidate.get("scene_state")
        if isinstance(nested, dict):
            candidate = nested
        if candidate:
            return deepcopy(candidate)

    return {}


def montar_snapshot_cena(
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = normalizar_dict(scene_state)
    snapshot: dict[str, Any] = {}

    for field in SCENE_FIELDS:
        value = state.get(field)
        if value in (None, "", [], {}):
            continue
        snapshot[field] = deepcopy(value)

    sexual = state.get("sexual_state")
    if isinstance(sexual, dict):
        sexual_snapshot = remover_vazios(
            {
                "phase": sexual.get("scene_phase"),
                "activity": sexual.get("current_activity"),
                "position": sexual.get("current_position"),
                "pace": sexual.get("current_pace"),
                "mary_pre_orgasm_announced": sexual.get(
                    "mary_pre_orgasm_announced"
                ),
                "mary_orgasm_done": sexual.get("mary_orgasm_done"),
                "user_orgasm_warning": sexual.get("user_orgasm_warning"),
                "user_orgasm_done": sexual.get("user_orgasm_done"),
                "aftercare_required": sexual.get("aftercare_required"),
            }
        )
        if sexual_snapshot:
            snapshot["sexual_continuity"] = sexual_snapshot

    return remover_vazios(snapshot)


# ==========================================================
# PENDÊNCIAS E FATOS
# ==========================================================


def _normalizar_item_continuidade(value: Any) -> str:
    if isinstance(value, dict):
        for key in (
            "summary",
            "text",
            "content",
            "fact",
            "description",
            "title",
            "topic",
        ):
            text = limitar_texto(value.get(key), max_chars=240)
            if text:
                return text
        return ""
    return limitar_texto(value, max_chars=240)


def _coletar_itens(
    source: dict[str, Any],
    fields: Iterable[str],
    *,
    limit: int,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for field in fields:
        raw = source.get(field)
        values = raw if isinstance(raw, (list, tuple)) else [raw]
        for value in values:
            text = _normalizar_item_continuidade(value)
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            result.append(text)
            if len(result) >= limit:
                return result

    return result


def extrair_pendencias(
    scene_state: dict[str, Any] | None,
    relationship_state: dict[str, Any] | None = None,
    *,
    limit: int = 6,
) -> list[str]:
    state = normalizar_dict(scene_state)
    relationship = normalizar_dict(relationship_state)

    result = _coletar_itens(state, PENDING_FIELDS, limit=limit)
    if len(result) < limit:
        extra = _coletar_itens(
            relationship,
            PENDING_FIELDS,
            limit=limit - len(result),
        )
        seen = {item.casefold() for item in result}
        result.extend(item for item in extra if item.casefold() not in seen)

    return result[:limit]


def extrair_resolvidos(
    scene_state: dict[str, Any] | None,
    *,
    limit: int = 6,
) -> list[str]:
    return _coletar_itens(
        normalizar_dict(scene_state),
        RESOLVED_FIELDS,
        limit=limit,
    )


def selecionar_memorias_continuidade(
    memories: list[dict[str, Any]] | None,
    *,
    max_items: int = 6,
) -> list[str]:
    """Seleciona fatos já registrados sem inferir importância inexistente.

    Respeita a ordem recebida, remove duplicatas e ignora memórias marcadas como
    apagadas, inativas ou não confirmadas.
    """

    result: list[str] = []
    seen: set[str] = set()

    for memory in memories or []:
        if not isinstance(memory, dict):
            continue
        if memory.get("deleted") or memory.get("active") is False:
            continue
        if memory.get("confirmed") is False:
            continue

        text = ""
        for key in (
            "summary",
            "memory_text",
            "content",
            "fact",
            "text",
            "description",
        ):
            text = limitar_texto(memory.get(key), max_chars=280)
            if text:
                break

        normalized = text.casefold()
        if not text or normalized in seen:
            continue

        seen.add(normalized)
        result.append(text)
        if len(result) >= max(0, int(max_items)):
            break

    return result


# ==========================================================
# BLOCO DE PROMPT
# ==========================================================


def montar_contexto_continuidade(
    *,
    relationship_state: dict[str, Any] | None = None,
    scene_state: dict[str, Any] | None = None,
    memories: list[dict[str, Any]] | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
    last_mary_response: str = "",
    max_memories: int = 6,
    max_recent_messages: int = 4,
) -> str:
    active_scene = extrair_estado_cenario(relationship_state, scene_state)
    snapshot = montar_snapshot_cena(active_scene)
    pending = extrair_pendencias(
        active_scene,
        relationship_state,
        limit=6,
    )
    resolved = extrair_resolvidos(active_scene, limit=5)
    selected_memories = selecionar_memorias_continuidade(
        memories,
        max_items=max_memories,
    )

    recent: list[dict[str, str]] = []
    for message in (recent_messages or [])[-max(0, int(max_recent_messages)) :]:
        if not isinstance(message, dict):
            continue
        role = normalizar_texto(message.get("role"))
        content = limitar_texto(message.get("content"), max_chars=420)
        if role and content:
            recent.append({"role": role, "content": content})

    payload = remover_vazios(
        {
            "scene": snapshot,
            "pending": pending,
            "resolved": resolved,
            "confirmed_memories": selected_memories,
            "recent": recent,
            "last_mary_response": limitar_texto(
                last_mary_response,
                max_chars=500,
            ),
        }
    )

    if not payload:
        return ""

    return (
        "[CONTINUIDADE — FATOS E ESTADO ATUAL]\n"
        + serializar_compacto(payload)
        + "\nREGRAS: preserve fatos confirmados e posições já estabelecidas; "
        "não repita a última fala nem reencene ação concluída; retome no ponto "
        "exato; pendências são oportunidades, não obrigações; não invente ação, "
        "pensamento, sensação ou orgasmo do usuário; se houver contradição, o "
        "turno mais recente e o estado corporal explícito prevalecem."
    )


def montar_diagnostico_continuidade(
    *,
    relationship_state: dict[str, Any] | None = None,
    scene_state: dict[str, Any] | None = None,
    memories: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active_scene = extrair_estado_cenario(relationship_state, scene_state)
    snapshot = montar_snapshot_cena(active_scene)
    pending = extrair_pendencias(active_scene, relationship_state)
    selected_memories = selecionar_memorias_continuidade(memories)

    return {
        "version": CONTINUITY_PROMPT_VERSION,
        "has_scene": bool(snapshot),
        "scene_fields": sorted(snapshot.keys()),
        "pending_count": len(pending),
        "memory_count": len(selected_memories),
        "sexual_phase": normalizar_dict(
            snapshot.get("sexual_continuity")
        ).get("phase", ""),
    }


__all__ = [
    "CONTINUITY_PROMPT_VERSION",
    "SCENE_FIELDS",
    "PENDING_FIELDS",
    "RESOLVED_FIELDS",
    "normalizar_texto",
    "normalizar_dict",
    "normalizar_lista",
    "limitar_texto",
    "serializar_compacto",
    "remover_vazios",
    "extrair_estado_cenario",
    "montar_snapshot_cena",
    "extrair_pendencias",
    "extrair_resolvidos",
    "selecionar_memorias_continuidade",
    "montar_contexto_continuidade",
    "montar_diagnostico_continuidade",
]
