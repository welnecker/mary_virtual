from __future__ import annotations

from scenarios.engine.models import ChapterDefinition
from .beat_graph import BEATS


CHAPTER = ChapterDefinition(
    chapter_id="cap_01",
    title="Primeiro encontro",
    spreadsheet_id="1ldFgUbxaEgi13ltNgx991INXTAm3e4nuhB8bjnYSyZM",
    worksheet="MARY_FRUSTRADA_CAP_01",
    initial_route="supermarket_encounter",
    initial_beat="injury_check",
    beats=BEATS,
)
