from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ScreenplayLine:
    order: int
    scene: str
    route: str
    beat: str
    kind: str
    content: str
    condition: str = ""
    dramatic_function: str = ""
    next_route: str = ""
    active: bool = True


@dataclass(frozen=True, slots=True)
class BeatDefinition:
    beat_id: str
    route: str
    next_beat: str | None = None
    gate: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChapterDefinition:
    chapter_id: str
    title: str
    worksheet: str
    initial_route: str
    initial_beat: str
    beats: Mapping[str, BeatDefinition]
    spreadsheet_id: str | None = None


@dataclass(frozen=True, slots=True)
class StoryDefinition:
    story_id: str
    title: str
    character_id: str
    initial_chapter_id: str
    chapters: Mapping[str, ChapterDefinition]
    description: str = ""


@dataclass(slots=True)
class StorySession:
    story_id: str
    chapter_id: str
    current_route: str
    current_beat: str
    completed_beats: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
