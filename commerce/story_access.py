from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StoryAccess:
    id: str
    user_id: str
    story_id: str
    chapter_id: str
    payment_id: str
    status: str = "available"
    session_id: str = ""
    consumed_reason: str = ""

    @property
    def can_start(self) -> bool:
        return self.status == "available" and not self.session_id


def bind_access_to_session(access: StoryAccess, *, session_id: str) -> StoryAccess:
    if not access.can_start:
        raise ValueError("Este acesso já foi usado ou não está disponível.")
    if not str(session_id or "").strip():
        raise ValueError("session_id obrigatório.")
    access.status = "in_use"
    access.session_id = session_id.strip()
    return access


def consume_access(access: StoryAccess, *, reason: str) -> StoryAccess:
    if access.status == "consumed":
        return access
    if not access.session_id:
        raise ValueError("Não é possível consumir um acesso que nunca iniciou sessão.")
    access.status = "consumed"
    access.consumed_reason = str(reason or "story_closed").strip()
    return access


__all__ = ["StoryAccess", "bind_access_to_session", "consume_access"]
