from __future__ import annotations

from scenarios.engine.models import StoryDefinition
from scenarios.stories.casada_frustrada.chapters.cap_01.config import CHAPTER as CAP_01
from scenarios.stories.casada_frustrada.chapters.cap_02.config import CHAPTER as CAP_02


STORY = StoryDefinition(
    story_id="casada_frustrada",
    title="Casada frustrada",
    description="Uma história interativa em capítulos independentes e contínuos.",
    character_id="mary",
    initial_chapter_id="cap_01",
    chapters={
        CAP_01.chapter_id: CAP_01,
        CAP_02.chapter_id: CAP_02,
    },
)
