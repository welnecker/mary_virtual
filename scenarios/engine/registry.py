from __future__ import annotations

from .models import ChapterDefinition, StoryDefinition


class StoryRegistry:
    def __init__(self) -> None:
        self._stories: dict[str, StoryDefinition] = {}

    def register(self, story: StoryDefinition) -> None:
        if story.story_id in self._stories:
            raise ValueError(f"História já registrada: {story.story_id}")
        self._stories[story.story_id] = story

    def get_story(self, story_id: str) -> StoryDefinition:
        try:
            return self._stories[story_id]
        except KeyError as exc:
            raise KeyError(f"História não registrada: {story_id}") from exc

    def get_chapter(self, story_id: str, chapter_id: str) -> ChapterDefinition:
        story = self.get_story(story_id)
        try:
            return story.chapters[chapter_id]
        except KeyError as exc:
            raise KeyError(
                f"Capítulo não registrado: {story_id}/{chapter_id}"
            ) from exc

    def list_stories(self) -> tuple[StoryDefinition, ...]:
        return tuple(self._stories.values())


story_registry = StoryRegistry()
