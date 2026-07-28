from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.story_models import Chapter, MaryProfile, StoryManifest


@dataclass(frozen=True)
class StoryPackage:
    manifest: StoryManifest
    profile: MaryProfile
    chapters: dict[str, Chapter]

    def validate(self) -> None:
        self.manifest.validate()
        missing = [
            chapter_id
            for chapter_id in self.manifest.chapter_ids
            if chapter_id not in self.chapters
        ]
        if missing:
            raise ValueError(
                f"História {self.manifest.id!r} referencia capítulos ausentes: {missing}."
            )
        for chapter in self.chapters.values():
            chapter.validate()

    def get_chapter(self, chapter_id: str) -> Chapter:
        try:
            return self.chapters[chapter_id]
        except KeyError as exc:
            raise KeyError(
                f"Capítulo {chapter_id!r} não existe na história {self.manifest.id!r}."
            ) from exc


_REGISTRY: dict[str, StoryPackage] = {}


def register_story(package: StoryPackage, *, replace: bool = False) -> None:
    package.validate()
    story_id = package.manifest.id
    if story_id in _REGISTRY and not replace:
        raise ValueError(f"História já registrada: {story_id!r}.")
    _REGISTRY[story_id] = package


def get_story(story_id: str) -> StoryPackage:
    try:
        return _REGISTRY[story_id]
    except KeyError as exc:
        raise KeyError(f"História não registrada: {story_id!r}.") from exc


def list_stories(*, active_only: bool = True) -> list[StoryPackage]:
    packages: Iterable[StoryPackage] = _REGISTRY.values()
    if active_only:
        packages = (package for package in packages if package.manifest.active)
    return sorted(packages, key=lambda item: item.manifest.title.casefold())


def clear_registry() -> None:
    _REGISTRY.clear()


__all__ = [
    "StoryPackage",
    "clear_registry",
    "get_story",
    "list_stories",
    "register_story",
]
