from __future__ import annotations

from scenarios.engine.models import ChapterDefinition
from .beat_graph import BEATS

CHAPTER = ChapterDefinition(
    chapter_id="cap_02",
    title="Continuação",
    worksheet="MARY_FRUSTRADA_CAP_02",
    initial_route="chapter_02_opening",
    initial_beat="chapter_02_opening",
    beats=BEATS,
)
