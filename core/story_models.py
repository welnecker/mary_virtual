from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class GateDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class Beat:
    id: str
    mary_lines: tuple[str, ...]
    next_beat: str | None
    gate: str = ""
    route: str = ""
    completes: tuple[str, ...] = ()
    instructions: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Beat sem id.")
        if not self.mary_lines:
            raise ValueError(f"Beat {self.id!r} sem fala ou movimento canônico.")
        if any(not str(line).strip() for line in self.mary_lines):
            raise ValueError(f"Beat {self.id!r} contém linha vazia.")


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    opening_message: str
    first_beat: str
    beats: Mapping[str, Beat]
    ending_message: str = ""

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Capítulo sem id.")
        if self.first_beat not in self.beats:
            raise ValueError(f"Beat inicial inexistente: {self.first_beat!r}.")
        for beat_id, beat in self.beats.items():
            beat.validate()
            if beat.id != beat_id:
                raise ValueError(f"Chave {beat_id!r} difere do id {beat.id!r}.")
            if beat.next_beat and beat.next_beat not in self.beats:
                raise ValueError(
                    f"Beat {beat.id!r} aponta para sucessor inexistente {beat.next_beat!r}."
                )


@dataclass(frozen=True)
class MaryProfile:
    physical: Mapping[str, Any]
    psychological: Mapping[str, Any]
    voice: Mapping[str, Any]
    boundaries: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryManifest:
    id: str
    title: str
    description: str
    price_cents: int
    currency: str
    chapter_ids: tuple[str, ...]
    card_image: str = ""
    adult_only: bool = True
    active: bool = True

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("História sem id.")
        if self.price_cents < 0:
            raise ValueError("Preço não pode ser negativo.")
        if not self.chapter_ids:
            raise ValueError(f"História {self.id!r} sem capítulos.")


@dataclass
class StorySession:
    access_id: str
    story_id: str
    chapter_id: str
    current_beat: str
    status: str = "active"
    current_beat_emitted: bool = False
    completed_beats: list[str] = field(default_factory=list)
    completed_facts: list[str] = field(default_factory=list)
    turn_count: int = 0
    ending_reason: str = ""

    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class TurnPlan:
    mode: str
    beat_id: str
    mary_lines: tuple[str, ...]
    route: str
    gate: str
    instructions: tuple[str, ...]
    story_finished: bool = False


__all__ = [
    "Beat",
    "Chapter",
    "GateDecision",
    "MaryProfile",
    "StoryManifest",
    "StorySession",
    "TurnPlan",
]
