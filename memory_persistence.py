from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from config import MEMORY_EXPLICIT_CAPTURE_ENABLED, MEMORY_PROMPT_LIMIT
from google_sheets_repository import GoogleSheetsRepositoryError
from memory_store import (
    carregar_memorias_usuario,
    gerar_memory_key,
    normalizar_para_busca,
    normalizar_texto,
    obter_memorias_para_turno,
    registrar_memoria_usuario,
)
from repositories.memory_repository import (
    listar_memorias_usuario,
    salvar_ou_atualizar_memoria,
)


MEMORY_PERSISTENCE_VERSION = "memory-persistence-v3-configured-api-aligned"

_LOADED_USERS: set[str] = set()
_FAILED_LOAD_USERS: set[str] = set()

_EXPLICIT_MEMORY_PATTERNS = (
    re.compile(
        r"\b(?:lembre|lembra|não esqueça|nao esqueca|guarde|anote)\s+"
        r"(?:de\s+)?que\s+(.+)",
        re.I,
    ),
    re.compile(
        r"\bquero que (?:você|voce|mary) (?:lembre|guarde|saiba)\s+"
        r"(?:de\s+)?que\s+(.+)",
        re.I,
    ),
    re.compile(r"\buma coisa importante sobre mim(?: é| e)\s+(.+)", re.I),
)


def _resolver_user_id(user_profile: dict[str, Any] | None) -> str:
    if not isinstance(user_profile, dict):
        return ""
    return normalizar_texto(
        user_profile.get("profile_id")
        or user_profile.get("user_id")
        or user_profile.get("id")
    )


def _resolver_user_message(
    *,
    user_message: str,
    relationship_state: dict[str, Any] | None,
) -> str:
    explicit = normalizar_texto(user_message)
    if explicit:
        return explicit
    if not isinstance(relationship_state, dict):
        return ""
    for field in ("active_turn", "current_turn"):
        turn = relationship_state.get(field)
        if isinstance(turn, dict):
            text = normalizar_texto(turn.get("user_text"))
            if text:
                return text
    return ""


def _resolver_scenario_id(relationship_state: dict[str, Any] | None) -> str:
    if not isinstance(relationship_state, dict):
        return ""
    context = relationship_state.get("scenario_context")
    if not isinstance(context, dict):
        return ""
    return normalizar_texto(context.get("scenario_id"))


def garantir_memorias_carregadas(user_id: str) -> list[dict[str, Any]]:
    uid = normalizar_texto(user_id)
    if not uid or uid in _LOADED_USERS or uid in _FAILED_LOAD_USERS:
        return []

    try:
        memories = listar_memorias_usuario(uid, active_only=False)
    except GoogleSheetsRepositoryError:
        _FAILED_LOAD_USERS.add(uid)
        carregar_memorias_usuario(uid, [], replace=False)
        return []

    carregar_memorias_usuario(uid, memories, replace=True)
    _LOADED_USERS.add(uid)
    return memories


def extrair_memorias_explicitas(
    *,
    user_id: str,
    user_message: str,
    source_interaction_id: str = "",
    scenario_id: str = "",
) -> list[dict[str, Any]]:
    if not MEMORY_EXPLICIT_CAPTURE_ENABLED:
        return []

    uid = normalizar_texto(user_id)
    message = normalizar_texto(user_message)
    if not uid or not message:
        return []

    extracted: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pattern in _EXPLICIT_MEMORY_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue

        content = normalizar_texto(match.group(1)).strip(" .!?;:")
        if len(content) < 4 or len(content) > 500:
            continue

        normalized_content = normalizar_para_busca(content)
        if not normalized_content or normalized_content in seen:
            continue
        seen.add(normalized_content)

        memory_type = "preference"
        if any(
            term in normalized_content
            for term in ("nao quero", "limite", "nunca", "pare")
        ):
            memory_type = "boundary"
        elif any(
            term in normalized_content
            for term in ("sou ", "meu nome", "minha idade", "moro ")
        ):
            memory_type = "identity"
        elif any(
            term in normalized_content
            for term in ("prometi", "promessa", "vamos ")
        ):
            memory_type = "promise"

        memory_key = gerar_memory_key(
            user_id=uid,
            memory_text=content,
            memory_type=memory_type,
            subject="explicit_user_memory",
        )
        extracted.append(
            {
                "memory_id": memory_key,
                "memory_key": memory_key,
                "user_id": uid,
                "memory_text": content,
                "memory_type": memory_type,
                "subject": "explicit_user_memory",
                "importance": 0.9,
                "confidence": 1.0,
                "confirmed": True,
                "active": True,
                "pinned": memory_type in {"boundary", "identity"},
                "source_interaction_id": normalizar_texto(source_interaction_id),
                "scenario_id": normalizar_texto(scenario_id),
                "tags": ["explicit", "user_confirmed"],
            }
        )

    return extracted


def registrar_memorias_explicitas_turno(
    *,
    user_id: str,
    user_message: str,
    source_interaction_id: str = "",
    scenario_id: str = "",
) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for memory in extrair_memorias_explicitas(
        user_id=user_id,
        user_message=user_message,
        source_interaction_id=source_interaction_id,
        scenario_id=scenario_id,
    ):
        local = registrar_memoria_usuario(user_id, memory)
        try:
            persisted = salvar_ou_atualizar_memoria(local or memory)
        except GoogleSheetsRepositoryError:
            persisted = local or memory
        if persisted:
            registrar_memoria_usuario(user_id, persisted)
            saved.append(persisted)
    return saved


def resolver_memorias_para_prompt(
    *,
    user_profile: dict[str, Any] | None,
    relationship_state: dict[str, Any] | None,
    user_message: str = "",
    provided_memories: list[dict[str, Any]] | None = None,
    limit: int = MEMORY_PROMPT_LIMIT,
) -> list[dict[str, Any]]:
    resolved_limit = max(1, int(limit or MEMORY_PROMPT_LIMIT))
    uid = _resolver_user_id(user_profile)
    if not uid:
        return deepcopy(provided_memories or [])[:resolved_limit]

    garantir_memorias_carregadas(uid)
    message = _resolver_user_message(
        user_message=user_message,
        relationship_state=relationship_state,
    )
    scenario_id = _resolver_scenario_id(relationship_state)

    active_turn = (
        relationship_state.get("active_turn")
        if isinstance(relationship_state, dict)
        else {}
    )
    source_interaction_id = (
        normalizar_texto(active_turn.get("interaction_id"))
        if isinstance(active_turn, dict)
        else ""
    )

    if message and MEMORY_EXPLICIT_CAPTURE_ENABLED:
        registrar_memorias_explicitas_turno(
            user_id=uid,
            user_message=message,
            source_interaction_id=source_interaction_id,
            scenario_id=scenario_id,
        )

    selected = obter_memorias_para_turno(
        uid,
        query=message,
        limit=resolved_limit,
        active_scenario_id=scenario_id,
        preferred_types=(
            "boundary",
            "identity",
            "relationship",
            "preference",
            "promise",
        ),
    )

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for memory in [*(provided_memories or []), *selected]:
        if not isinstance(memory, dict):
            continue
        key = normalizar_texto(memory.get("memory_key") or memory.get("memory_id"))
        if not key:
            key = normalizar_para_busca(
                memory.get("memory_text") or memory.get("content")
            )
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(deepcopy(memory))
        if len(merged) >= resolved_limit:
            break
    return merged


def invalidar_cache_memorias(user_id: str = "") -> None:
    uid = normalizar_texto(user_id)
    if uid:
        _LOADED_USERS.discard(uid)
        _FAILED_LOAD_USERS.discard(uid)
    else:
        _LOADED_USERS.clear()
        _FAILED_LOAD_USERS.clear()


__all__ = [
    "MEMORY_PERSISTENCE_VERSION",
    "garantir_memorias_carregadas",
    "extrair_memorias_explicitas",
    "registrar_memorias_explicitas_turno",
    "resolver_memorias_para_prompt",
    "invalidar_cache_memorias",
]
