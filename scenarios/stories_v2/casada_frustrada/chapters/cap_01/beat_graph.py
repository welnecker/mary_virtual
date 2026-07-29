from __future__ import annotations

from scenarios.engine.models import BeatDefinition


BEATS = {
    "injury_check": BeatDefinition(
        beat_id="injury_check",
        route="supermarket_encounter",
        next_beat="recognize_plaza",
    ),
    "recognize_plaza": BeatDefinition(
        beat_id="recognize_plaza",
        route="supermarket_encounter",
        next_beat="first_farewell",
    ),
    "first_farewell": BeatDefinition(
        beat_id="first_farewell",
        route="supermarket_encounter",
        next_beat="second_encounter",
    ),
    "second_encounter": BeatDefinition(
        beat_id="second_encounter",
        route="aisle_flirtation",
        next_beat=None,
    ),
}
