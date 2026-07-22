from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any, Iterable

from config import MEMORY_MAX_PER_USER, MEMORY_PROMPT_LIMIT


MEMORY_STORE_VERSION = "memory-store-v2-centralized-config"
DEFAULT_MAX_MEMORIES_PER_USER = MEMORY_MAX_PER_USER
DEFAULT_PROMPT_LIMIT = MEMORY_PROMPT_LIMIT

MEMORY_TYPES = {
    "identity",
    "preference",
    "relationship",
    "event",
    "promise",
    "boundary",
    "visual",
    "sexual",
    "scenario",
    "general",
}

TYPE_WEIGHTS = {
    "boundary": 1.00,
    "identity": 0.95,
    "promise": 0.90,
    "relationship": 0.88,
    "preference": 0.84,
    "scenario": 0.82,
    "sexual": 0.80,
    "visual": 0.78,
    "event": 0.72,
    "general": 0.60,
}

TEXT_FIELDS = (
    "memory_text",
    "text",
    "content",
    "summary",
    "fact",
    "description",
    "memory",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalizar_texto(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalizar_para_busca(value: Any) -> str:
    text = normalizar_texto(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def limitar_texto(value: Any, *, max_chars: int = 600) -> str:
    text = normalizar_texto(value)
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 1)].rstrip() + "…"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def limitar_float(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, safe_float(value, minimum)))


def normalizar_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "sim", "s", "verdadeiro"}:
        return True
    if text in {"false", "0", "no", "nao", "não", "n", "falso", ""}:
        return False
    return default


def normalizar_lista(value: Any) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[,;|]", value)
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = normalizar_texto(item)
        key = normalizar_para_busca(text)
        if text and key and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def tokenizar(value: Any) -> set[str]:
    return {
        token
        for token in normalizar_para_busca(value).split()
        if len(token) >= 3
    }


def extrair_texto_memoria(memory: Any) -> str:
    if isinstance(memory, str):
        return limitar_texto(memory)
    if not isinstance(memory, dict):
        return ""
    for field_name in TEXT_FIELDS:
        text = limitar_texto(memory.get(field_name))
        if text:
            return text
    return ""


def gerar_memory_key(
    *,
    user_id: str,
    memory_text: str,
    memory_type: str = "general",
    subject: str = "",
) -> str:
    canonical = "|".join(
        (
            normalizar_para_busca(user_id),
            normalizar_para_busca(memory_type or "general"),
            normalizar_para_busca(subject),
            normalizar_para_busca(memory_text),
        )
    )
    return sha1(canonical.encode("utf-8")).hexdigest()[:20]


def normalizar_memoria(
    memory: Any,
    *,
    user_id: str = "",
) -> dict[str, Any]:
    source = dict(memory) if isinstance(memory, dict) else {"memory_text": memory}
    text = extrair_texto_memoria(source)
    if not text:
        return {}

    uid = normalizar_texto(source.get("user_id") or user_id)
    memory_type = normalizar_para_busca(
        source.get("memory_type") or source.get("type") or source.get("category")
    ) or "general"
    if memory_type not in MEMORY_TYPES:
        memory_type = "general"

    subject = normalizar_texto(source.get("subject"))
    key = normalizar_texto(source.get("memory_key") or source.get("memory_id"))
    if not key:
        key = gerar_memory_key(
            user_id=uid,
            memory_text=text,
            memory_type=memory_type,
            subject=subject,
        )

    now = utc_now_iso()
    normalized = dict(source)
    normalized.update(
        {
            "memory_key": key,
            "user_id": uid,
            "memory_text": text,
            "memory_type": memory_type,
            "subject": subject,
            "importance": limitar_float(source.get("importance", 0.5)),
            "confidence": limitar_float(source.get("confidence", 0.8)),
            "active": normalizar_bool(source.get("active"), default=True),
            "confirmed": normalizar_bool(source.get("confirmed"), default=True),
            "pinned": normalizar_bool(source.get("pinned"), default=False),
            "tags": normalizar_lista(source.get("tags")),
            "created_at": normalizar_texto(source.get("created_at")) or now,
            "updated_at": normalizar_texto(source.get("updated_at")) or now,
        }
    )
    normalized["_search_text"] = normalizar_para_busca(
        " ".join((text, subject, " ".join(normalized["tags"])))
    )
    normalized["_tokens"] = tokenizar(normalized["_search_text"])
    return normalized


def _public_memory(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in memory.items()
        if not key.startswith("_")
    }


def calcular_relevancia_memoria(
    memory: dict[str, Any],
    *,
    query: str = "",
    preferred_types: Iterable[str] | None = None,
    active_scenario_id: str = "",
) -> float:
    if not memory.get("active", True) or not memory.get("confirmed", True):
        return -1.0

    memory_type = str(memory.get("memory_type") or "general")
    score = TYPE_WEIGHTS.get(memory_type, TYPE_WEIGHTS["general"])
    score += limitar_float(memory.get("importance", 0.5)) * 0.50
    score += limitar_float(memory.get("confidence", 0.8)) * 0.20
    if memory.get("pinned"):
        score += 0.75

    preferred = {
        normalizar_para_busca(item)
        for item in (preferred_types or [])
        if normalizar_para_busca(item)
    }
    if memory_type in preferred:
        score += 0.35

    scenario_id = normalizar_texto(memory.get("scenario_id"))
    if scenario_id:
        if active_scenario_id and scenario_id == active_scenario_id:
            score += 0.35
        elif active_scenario_id and scenario_id != active_scenario_id:
            return -1.0

    query_normalized = normalizar_para_busca(query)
    if query_normalized:
        query_tokens = tokenizar(query_normalized)
        memory_tokens = set(memory.get("_tokens") or ())
        overlap = query_tokens & memory_tokens
        if query_tokens:
            score += (len(overlap) / len(query_tokens)) * 1.20
        search_text = str(memory.get("_search_text") or "")
        if query_normalized in search_text or search_text in query_normalized:
            score += 0.80

    return round(score, 6)


def selecionar_memorias_relevantes(
    memories: Iterable[Any],
    *,
    user_id: str = "",
    query: str = "",
    limit: int = DEFAULT_PROMPT_LIMIT,
    preferred_types: Iterable[str] | None = None,
    active_scenario_id: str = "",
) -> list[dict[str, Any]]:
    best_by_key: dict[str, tuple[float, dict[str, Any]]] = {}
    for memory in memories:
        normalized = normalizar_memoria(memory, user_id=user_id)
        if not normalized:
            continue
        score = calcular_relevancia_memoria(
            normalized,
            query=query,
            preferred_types=preferred_types,
            active_scenario_id=active_scenario_id,
        )
        if score < 0:
            continue
        key = normalized["memory_key"]
        current = best_by_key.get(key)
        if current is None or score > current[0]:
            best_by_key[key] = (score, normalized)

    ranked = sorted(
        best_by_key.values(),
        key=lambda item: (item[0], str(item[1].get("updated_at") or "")),
        reverse=True,
    )
    result: list[dict[str, Any]] = []
    for score, memory in ranked[: max(0, int(limit))]:
        public = _public_memory(memory)
        public["relevance_score"] = score
        result.append(public)
    return result


@dataclass
class MemoryStore:
    max_memories_per_user: int = DEFAULT_MAX_MEMORIES_PER_USER
    _by_user: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def clear(self, user_id: str = "") -> None:
        uid = normalizar_texto(user_id)
        if uid:
            self._by_user.pop(uid, None)
        else:
            self._by_user.clear()

    def load(
        self,
        user_id: str,
        memories: Iterable[Any],
        *,
        replace: bool = True,
    ) -> list[dict[str, Any]]:
        uid = normalizar_texto(user_id)
        if not uid:
            return []
        if replace:
            self._by_user[uid] = {}
        bucket = self._by_user.setdefault(uid, {})
        for memory in memories:
            normalized = normalizar_memoria(memory, user_id=uid)
            if normalized:
                bucket[normalized["memory_key"]] = normalized
        self._trim(uid)
        return self.list(uid)

    def upsert(self, user_id: str, memory: Any) -> dict[str, Any]:
        uid = normalizar_texto(user_id)
        normalized = normalizar_memoria(memory, user_id=uid)
        if not uid or not normalized:
            return {}
        bucket = self._by_user.setdefault(uid, {})
        current = bucket.get(normalized["memory_key"])
        if current:
            normalized["created_at"] = current.get("created_at") or normalized["created_at"]
            normalized["updated_at"] = utc_now_iso()
        bucket[normalized["memory_key"]] = normalized
        self._trim(uid)
        return _public_memory(normalized)

    def remove(self, user_id: str, memory_key: str) -> bool:
        uid = normalizar_texto(user_id)
        key = normalizar_texto(memory_key)
        return bool(self._by_user.get(uid, {}).pop(key, None))

    def deactivate(self, user_id: str, memory_key: str) -> bool:
        uid = normalizar_texto(user_id)
        memory = self._by_user.get(uid, {}).get(normalizar_texto(memory_key))
        if not memory:
            return False
        memory["active"] = False
        memory["updated_at"] = utc_now_iso()
        return True

    def get(self, user_id: str, memory_key: str) -> dict[str, Any] | None:
        memory = self._by_user.get(normalizar_texto(user_id), {}).get(
            normalizar_texto(memory_key)
        )
        return _public_memory(memory) if memory else None

    def list(self, user_id: str, *, active_only: bool = False) -> list[dict[str, Any]]:
        memories = self._by_user.get(normalizar_texto(user_id), {}).values()
        selected = [
            _public_memory(memory)
            for memory in memories
            if not active_only or memory.get("active", True)
        ]
        return sorted(
            selected,
            key=lambda item: str(item.get("updated_at") or ""),
            reverse=True,
        )

    def select(
        self,
        user_id: str,
        *,
        query: str = "",
        limit: int = DEFAULT_PROMPT_LIMIT,
        preferred_types: Iterable[str] | None = None,
        active_scenario_id: str = "",
    ) -> list[dict[str, Any]]:
        uid = normalizar_texto(user_id)
        return selecionar_memorias_relevantes(
            self._by_user.get(uid, {}).values(),
            user_id=uid,
            query=query,
            limit=limit,
            preferred_types=preferred_types,
            active_scenario_id=active_scenario_id,
        )

    def prompt_context(
        self,
        user_id: str,
        *,
        query: str = "",
        limit: int = DEFAULT_PROMPT_LIMIT,
        preferred_types: Iterable[str] | None = None,
        active_scenario_id: str = "",
    ) -> str:
        selected = self.select(
            user_id,
            query=query,
            limit=limit,
            preferred_types=preferred_types,
            active_scenario_id=active_scenario_id,
        )
        if not selected:
            return ""
        lines = ["[MEMÓRIAS RELEVANTES]"]
        for memory in selected:
            kind = memory.get("memory_type", "general")
            lines.append(f"- ({kind}) {memory.get('memory_text', '')}")
        return "\n".join(lines)

    def stats(self, user_id: str = "") -> dict[str, Any]:
        uid = normalizar_texto(user_id)
        if uid:
            memories = list(self._by_user.get(uid, {}).values())
            return {
                "user_id": uid,
                "total": len(memories),
                "active": sum(bool(item.get("active", True)) for item in memories),
            }
        return {
            "users": len(self._by_user),
            "total": sum(len(bucket) for bucket in self._by_user.values()),
        }

    def _trim(self, user_id: str) -> None:
        bucket = self._by_user.get(user_id, {})
        maximum = max(1, int(self.max_memories_per_user))
        if len(bucket) <= maximum:
            return
        ranked = sorted(
            bucket.values(),
            key=lambda item: (
                bool(item.get("pinned", False)),
                limitar_float(item.get("importance", 0.5)),
                str(item.get("updated_at") or ""),
            ),
            reverse=True,
        )
        self._by_user[user_id] = {
            memory["memory_key"]: memory
            for memory in ranked[:maximum]
        }


_GLOBAL_MEMORY_STORE = MemoryStore()


def carregar_memorias_usuario(
    user_id: str,
    memories: Iterable[Any],
    *,
    replace: bool = True,
) -> list[dict[str, Any]]:
    return _GLOBAL_MEMORY_STORE.load(user_id, memories, replace=replace)


def registrar_memoria_usuario(user_id: str, memory: Any) -> dict[str, Any]:
    return _GLOBAL_MEMORY_STORE.upsert(user_id, memory)


def remover_memoria_usuario(user_id: str, memory_key: str) -> bool:
    return _GLOBAL_MEMORY_STORE.remove(user_id, memory_key)


def desativar_memoria_usuario(user_id: str, memory_key: str) -> bool:
    return _GLOBAL_MEMORY_STORE.deactivate(user_id, memory_key)


def listar_memorias_cache_usuario(
    user_id: str,
    *,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    return _GLOBAL_MEMORY_STORE.list(user_id, active_only=active_only)


def obter_memorias_para_turno(
    user_id: str,
    *,
    query: str = "",
    limit: int = DEFAULT_PROMPT_LIMIT,
    preferred_types: Iterable[str] | None = None,
    active_scenario_id: str = "",
) -> list[dict[str, Any]]:
    return _GLOBAL_MEMORY_STORE.select(
        user_id,
        query=query,
        limit=limit,
        preferred_types=preferred_types,
        active_scenario_id=active_scenario_id,
    )


def limpar_memorias_usuario(user_id: str = "") -> None:
    _GLOBAL_MEMORY_STORE.clear(user_id)


def obter_estatisticas_memoria(user_id: str = "") -> dict[str, Any]:
    return _GLOBAL_MEMORY_STORE.stats(user_id)


__all__ = [
    "MEMORY_STORE_VERSION",
    "DEFAULT_MAX_MEMORIES_PER_USER",
    "DEFAULT_PROMPT_LIMIT",
    "MEMORY_TYPES",
    "TYPE_WEIGHTS",
    "MemoryStore",
    "normalizar_texto",
    "normalizar_para_busca",
    "extrair_texto_memoria",
    "gerar_memory_key",
    "normalizar_memoria",
    "calcular_relevancia_memoria",
    "selecionar_memorias_relevantes",
    "carregar_memorias_usuario",
    "registrar_memoria_usuario",
    "remover_memoria_usuario",
    "desativar_memoria_usuario",
    "listar_memorias_cache_usuario",
    "obter_memorias_para_turno",
    "limpar_memorias_usuario",
    "obter_estatisticas_memoria",
]
