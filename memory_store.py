from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any, Iterable


MEMORY_STORE_VERSION = "memory-store-v1-fast-relevant"
DEFAULT_MAX_MEMORIES_PER_USER = 120
DEFAULT_PROMPT_LIMIT = 8

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


# ==========================================================
# NORMALIZAÇÃO
# ==========================================================


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


def limitar_float(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, safe_float(value, minimum)))


def normalizar_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = normalizar_para_busca(value)
    if text in {"true", "1", "yes", "sim", "s", "verdadeiro"}:
        return True
    if text in {"false", "0", "no", "nao", "n", "falso", ""}:
        return False
    return default


def normalizar_lista(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return list(deepcopy(value))
    if value in (None, ""):
        return []
    return [deepcopy(value)]


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
    for field in TEXT_FIELDS:
        text = limitar_texto(memory.get(field))
        if text:
            return text
    return ""


def gerar_memory_key(
    *,
    user_id: str,
    text: str,
    memory_type: str = "general",
    subject: str = "",
) -> str:
    basis = "|".join(
        (
            normalizar_para_busca(user_id),
            normalizar_para_busca(memory_type),
            normalizar_para_busca(subject),
            normalizar_para_busca(text),
        )
    )
    return sha1(basis.encode("utf-8")).hexdigest()[:20]


def normalizar_memoria(
    memory: Any,
    *,
    user_id: str = "",
) -> dict[str, Any]:
    raw = deepcopy(memory) if isinstance(memory, dict) else {}
    text = extrair_texto_memoria(memory)
    if not text:
        return {}

    resolved_user_id = normalizar_texto(raw.get("user_id") or user_id)
    memory_type = normalizar_para_busca(
        raw.get("memory_type") or raw.get("type") or raw.get("category")
    ) or "general"
    if memory_type not in MEMORY_TYPES:
        memory_type = "general"

    subject = limitar_texto(raw.get("subject") or raw.get("topic"), max_chars=120)
    importance = limitar_float(
        raw.get("importance", raw.get("priority", TYPE_WEIGHTS[memory_type])),
        0.0,
        1.0,
    )
    confidence = limitar_float(raw.get("confidence", 1.0), 0.0, 1.0)
    active = not normalizar_bool(raw.get("deleted"), default=False)
    active = active and normalizar_bool(raw.get("active"), default=True)
    confirmed = normalizar_bool(raw.get("confirmed"), default=True)

    key = normalizar_texto(raw.get("memory_key") or raw.get("memory_id"))
    if not key:
        key = gerar_memory_key(
            user_id=resolved_user_id,
            text=text,
            memory_type=memory_type,
            subject=subject,
        )

    created_at = normalizar_texto(raw.get("created_at") or raw.get("timestamp"))
    updated_at = normalizar_texto(raw.get("updated_at"))

    tags = []
    seen_tags: set[str] = set()
    for tag in normalizar_lista(raw.get("tags")):
        normalized = normalizar_para_busca(tag)
        if normalized and normalized not in seen_tags:
            seen_tags.add(normalized)
            tags.append(normalized)

    result = deepcopy(raw)
    result.update(
        {
            "memory_key": key,
            "user_id": resolved_user_id,
            "memory_text": text,
            "memory_type": memory_type,
            "subject": subject,
            "importance": importance,
            "confidence": confidence,
            "active": active,
            "confirmed": confirmed,
            "tags": tags,
            "created_at": created_at or utc_now_iso(),
            "updated_at": updated_at or created_at or utc_now_iso(),
        }
    )
    result["_search_text"] = normalizar_para_busca(
        " ".join((text, subject, memory_type, " ".join(tags)))
    )
    result["_tokens"] = sorted(tokenizar(result["_search_text"]))
    return result


# ==========================================================
# PONTUAÇÃO E SELEÇÃO
# ==========================================================


def calcular_relevancia_memoria(
    memory: dict[str, Any],
    *,
    query: str = "",
    active_scenario_id: str = "",
    preferred_types: Iterable[str] | None = None,
) -> float:
    if not memory.get("active", True) or not memory.get("confirmed", True):
        return -1.0

    score = (
        0.42 * limitar_float(memory.get("importance"), 0.0, 1.0)
        + 0.18 * limitar_float(memory.get("confidence"), 0.0, 1.0)
        + 0.18 * TYPE_WEIGHTS.get(str(memory.get("memory_type")), 0.60)
    )

    query_tokens = tokenizar(query)
    memory_tokens = set(memory.get("_tokens") or tokenizar(memory.get("_search_text")))
    if query_tokens:
        overlap = len(query_tokens & memory_tokens) / max(1, len(query_tokens))
        score += 0.42 * overlap

    normalized_query = normalizar_para_busca(query)
    normalized_text = normalizar_para_busca(memory.get("memory_text"))
    if normalized_query and normalized_query in normalized_text:
        score += 0.20

    preferred = {
        normalizar_para_busca(item)
        for item in (preferred_types or [])
        if normalizar_para_busca(item)
    }
    if memory.get("memory_type") in preferred:
        score += 0.16

    scenario_id = normalizar_texto(
        memory.get("scenario_id") or memory.get("scenario_session_id")
    )
    if active_scenario_id and scenario_id == normalizar_texto(active_scenario_id):
        score += 0.24

    if normalizar_bool(memory.get("pinned"), default=False):
        score += 0.30

    return score


def selecionar_memorias_relevantes(
    memories: Iterable[dict[str, Any]],
    *,
    query: str = "",
    limit: int = DEFAULT_PROMPT_LIMIT,
    active_scenario_id: str = "",
    preferred_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, str, dict[str, Any]]] = []
    seen: set[str] = set()

    for memory in memories:
        normalized = normalizar_memoria(memory)
        if not normalized:
            continue
        key = normalized["memory_key"]
        if key in seen:
            continue
        seen.add(key)

        score = calcular_relevancia_memoria(
            normalized,
            query=query,
            active_scenario_id=active_scenario_id,
            preferred_types=preferred_types,
        )
        if score < 0:
            continue
        scored.append((score, normalized.get("updated_at", ""), normalized))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected: list[dict[str, Any]] = []
    for score, _, memory in scored[: max(0, int(limit))]:
        clean = {
            key: deepcopy(value)
            for key, value in memory.items()
            if not key.startswith("_")
        }
        clean["relevance_score"] = round(score, 4)
        selected.append(clean)
    return selected


# ==========================================================
# ARMAZENAMENTO EM MEMÓRIA DA SESSÃO
# ==========================================================


@dataclass
class MemoryStore:
    max_memories_per_user: int = DEFAULT_MAX_MEMORIES_PER_USER
    _by_user: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def clear(self, user_id: str | None = None) -> None:
        if user_id is None:
            self._by_user.clear()
            return
        self._by_user.pop(normalizar_texto(user_id), None)

    def load(
        self,
        user_id: str,
        memories: Iterable[dict[str, Any] | str],
        *,
        replace: bool = True,
    ) -> list[dict[str, Any]]:
        uid = normalizar_texto(user_id)
        if replace or uid not in self._by_user:
            self._by_user[uid] = {}

        for memory in memories:
            normalized = normalizar_memoria(memory, user_id=uid)
            if normalized:
                self._by_user[uid][normalized["memory_key"]] = normalized

        self._trim(uid)
        return self.list(uid)

    def upsert(
        self,
        user_id: str,
        memory: dict[str, Any] | str,
    ) -> dict[str, Any]:
        uid = normalizar_texto(user_id)
        normalized = normalizar_memoria(memory, user_id=uid)
        if not normalized:
            return {}

        bucket = self._by_user.setdefault(uid, {})
        current = bucket.get(normalized["memory_key"])
        if current:
            merged = deepcopy(current)
            merged.update(normalized)
            merged["created_at"] = current.get("created_at") or normalized["created_at"]
            merged["updated_at"] = utc_now_iso()
            normalized = normalizar_memoria(merged, user_id=uid)

        bucket[normalized["memory_key"]] = normalized
        self._trim(uid)
        return self.get(uid, normalized["memory_key"])

    def remove(self, user_id: str, memory_key: str) -> bool:
        uid = normalizar_texto(user_id)
        bucket = self._by_user.get(uid, {})
        return bucket.pop(normalizar_texto(memory_key), None) is not None

    def deactivate(self, user_id: str, memory_key: str) -> dict[str, Any]:
        uid = normalizar_texto(user_id)
        bucket = self._by_user.get(uid, {})
        memory = bucket.get(normalizar_texto(memory_key))
        if not memory:
            return {}
        memory["active"] = False
        memory["updated_at"] = utc_now_iso()
        return self.get(uid, memory_key)

    def get(self, user_id: str, memory_key: str) -> dict[str, Any]:
        memory = self._by_user.get(normalizar_texto(user_id), {}).get(
            normalizar_texto(memory_key)
        )
        return self._clean(memory) if memory else {}

    def list(
        self,
        user_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        memories = list(self._by_user.get(normalizar_texto(user_id), {}).values())
        if active_only:
            memories = [
                memory
                for memory in memories
                if memory.get("active", True) and memory.get("confirmed", True)
            ]
        memories.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return [self._clean(memory) for memory in memories]

    def select(
        self,
        user_id: str,
        *,
        query: str = "",
        limit: int = DEFAULT_PROMPT_LIMIT,
        active_scenario_id: str = "",
        preferred_types: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        return selecionar_memorias_relevantes(
            self._by_user.get(normalizar_texto(user_id), {}).values(),
            query=query,
            limit=limit,
            active_scenario_id=active_scenario_id,
            preferred_types=preferred_types,
        )

    def stats(self, user_id: str) -> dict[str, Any]:
        memories = list(self._by_user.get(normalizar_texto(user_id), {}).values())
        by_type: dict[str, int] = {}
        active = 0
        for memory in memories:
            memory_type = str(memory.get("memory_type") or "general")
            by_type[memory_type] = by_type.get(memory_type, 0) + 1
            if memory.get("active", True) and memory.get("confirmed", True):
                active += 1
        return {
            "version": MEMORY_STORE_VERSION,
            "total": len(memories),
            "active": active,
            "inactive": len(memories) - active,
            "by_type": by_type,
        }

    def _trim(self, user_id: str) -> None:
        bucket = self._by_user.get(user_id, {})
        limit = max(1, int(self.max_memories_per_user))
        if len(bucket) <= limit:
            return

        ranked = sorted(
            bucket.values(),
            key=lambda item: (
                normalizar_bool(item.get("pinned"), default=False),
                limitar_float(item.get("importance")),
                item.get("updated_at", ""),
            ),
            reverse=True,
        )
        self._by_user[user_id] = {
            item["memory_key"]: item
            for item in ranked[:limit]
        }

    @staticmethod
    def _clean(memory: dict[str, Any] | None) -> dict[str, Any]:
        if not memory:
            return {}
        return {
            key: deepcopy(value)
            for key, value in memory.items()
            if not key.startswith("_")
        }


DEFAULT_MEMORY_STORE = MemoryStore()


def carregar_memorias_usuario(
    user_id: str,
    memories: Iterable[dict[str, Any] | str],
    *,
    replace: bool = True,
) -> list[dict[str, Any]]:
    return DEFAULT_MEMORY_STORE.load(user_id, memories, replace=replace)


def registrar_memoria_usuario(
    user_id: str,
    memory: dict[str, Any] | str,
) -> dict[str, Any]:
    return DEFAULT_MEMORY_STORE.upsert(user_id, memory)


def obter_memorias_para_turno(
    user_id: str,
    *,
    user_message: str = "",
    limit: int = DEFAULT_PROMPT_LIMIT,
    active_scenario_id: str = "",
    preferred_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    return DEFAULT_MEMORY_STORE.select(
        user_id,
        query=user_message,
        limit=limit,
        active_scenario_id=active_scenario_id,
        preferred_types=preferred_types,
    )


def limpar_memorias_usuario(user_id: str | None = None) -> None:
    DEFAULT_MEMORY_STORE.clear(user_id)


__all__ = [
    "MEMORY_STORE_VERSION",
    "DEFAULT_MAX_MEMORIES_PER_USER",
    "DEFAULT_PROMPT_LIMIT",
    "MEMORY_TYPES",
    "TYPE_WEIGHTS",
    "utc_now_iso",
    "normalizar_texto",
    "normalizar_para_busca",
    "limitar_texto",
    "normalizar_bool",
    "tokenizar",
    "extrair_texto_memoria",
    "gerar_memory_key",
    "normalizar_memoria",
    "calcular_relevancia_memoria",
    "selecionar_memorias_relevantes",
    "MemoryStore",
    "DEFAULT_MEMORY_STORE",
    "carregar_memorias_usuario",
    "registrar_memoria_usuario",
    "obter_memorias_para_turno",
    "limpar_memorias_usuario",
]
