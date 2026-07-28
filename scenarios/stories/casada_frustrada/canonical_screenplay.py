from __future__ import annotations

from typing import Any

from .immersive_screenplay import (
    HIDDEN_CALL_DIALOGUE,
    MESSAGES_DIALOGUE,
    SECRET_MEETING_DIALOGUE,
    SECRET_MEETING_PLAN_DIALOGUE,
    SUPERMARKET_DIALOGUE,
)


CANONICAL_SCREENPLAY_VERSION = "casada-frustrada-canonical-screenplay-v1"


def _spoken_lines(block: str) -> list[str]:
    return [
        line[2:].strip()
        for raw in str(block or "").splitlines()
        if (line := raw.strip()).startswith("— ")
    ]


def _take(lines: list[str], *indexes: int) -> list[str]:
    return [lines[index] for index in indexes if 0 <= index < len(lines)]


_SUPERMARKET = _spoken_lines(SUPERMARKET_DIALOGUE)
_MESSAGES = _spoken_lines(MESSAGES_DIALOGUE)
_CALL = _spoken_lines(HIDDEN_CALL_DIALOGUE)
_PLAN = _spoken_lines(SECRET_MEETING_PLAN_DIALOGUE)
_MEETING = _spoken_lines(SECRET_MEETING_DIALOGUE)

# As frases vêm diretamente de immersive_screenplay.py. Este arquivo apenas liga
# cada beat às linhas já escritas; não contém paráfrases nem texto substituto.
CANONICAL_LINES_BY_BEAT: dict[str, list[str]] = {
    "injury_check": _take(_SUPERMARKET, 0, 1),
    "recognize_plaza": _take(_SUPERMARKET, 2),
    "first_farewell": _take(_SUPERMARKET, 3),
    "second_encounter": _take(_SUPERMARKET, 6),
    "market_crowded": _take(_SUPERMARKET, 7),
    "cart_single_guess": _take(_SUPERMARKET, 8),
    "home_weekend_routine": _take(_SUPERMARKET, 9),
    "checkout_turn": _take(_SUPERMARKET, 10),
    "ask_wait_help_car": _take(_SUPERMARKET, 11),
    "open_trunk": _take(_SUPERMARKET, 12),
    "liked_meeting": _take(_SUPERMARKET, 13),
    "request_phone": _take(_SUPERMARKET, 14),
    "exchange_numbers": _take(_SUPERMARKET, 15),
    "car_farewell": _take(_SUPERMARKET, 16),
    "home_first_message": _take(_MESSAGES, 2),
    "seek_bathroom_privacy": _take(_MESSAGES, 3),
    "admit_neediness": _take(_MESSAGES, 4),
    "admit_attraction": _take(_MESSAGES, 5),
    "offer_video": _take(_MESSAGES, 6, 7),
    "camera_setup": _take(_CALL, 0, 1),
    "admire_video": _take(_CALL, 2, 3),
    "ask_remove_shirt": _take(_CALL, 4),
    "react_torso": _take(_CALL, 5),
    "ask_remove_pants": _take(_CALL, 6),
    "react_underwear": _take(_CALL, 7),
    "mary_remove_dress": _take(_CALL, 8, 9),
    "invite_bra_request": _take(_CALL, 10),
    "reveal_breasts": _take(_CALL, 11),
    "ask_remove_underwear": _take(_CALL, 12),
    "react_nudity": _take(_CALL, 13),
    "breast_fantasy": _take(_CALL, 14),
    "mary_remove_panties": _take(_CALL, 15),
    "propose_mutual_masturbation": _take(_CALL, 16, 17),
    "guide_mutual_masturbation": _take(_CALL, 18),
    "urge_user_climax": _take(_CALL, 19),
    "react_user_climax": _take(_CALL, 20, 21),
    "end_first_call": _take(_CALL, 22),
    "midnight_return": _take(_PLAN, 1),
    "propose_motel": _take(_PLAN, 2, 3),
    "name_motel": _take(_PLAN, 4, 5),
    "demand_no_show": _take(_PLAN, 6),
    "good_night": _take(_PLAN, 7),
    "motel_preparation": _take(_PLAN, 8, 9, 10, 11),
    "motel_reunion": _take(_MEETING, 0, 1),
    "ask_touch_butt": _take(_MEETING, 2),
    "ask_touch_breasts": _take(_MEETING, 3),
    "ask_remove_bra": _take(_MEETING, 4),
    "heels_and_panties": _take(_MEETING, 5),
    "offer_oral": _take(_MEETING, 6, 7),
    "oral_admiration": _take(_MEETING, 8),
    "oral_climax_request": _take(_MEETING, 9),
    "oral_after_climax": _take(_MEETING, 10),
    "request_her_pleasure": _take(_MEETING, 11, 12, 13),
    "invite_cunnilingus": _take(_MEETING, 14),
    "guide_cunnilingus": _take(_MEETING, 15),
    "first_orgasm_build": _take(_MEETING, 16),
    "first_orgasm": _take(_MEETING, 17),
    "post_oral_tease": _take(_MEETING, 18, 19),
    "praise_lover": _take(_MEETING, 20),
    "request_doggy": _take(_MEETING, 21, 22),
    "ask_spank": _take(_MEETING, 23),
    "ask_lubricate": _take(_MEETING, 24),
    "penetration_start": _take(_MEETING, 25),
    "penetration_rhythm": _take(_MEETING, 26),
    "ask_anal_finger": _take(_MEETING, 27),
    "second_orgasm_build": _take(_MEETING, 28),
    "request_internal_climax": _take(_MEETING, 29),
    "shared_climax": _take(_MEETING, 30, 31),
    "post_penetration": _take(_MEETING, 32),
    "clean_with_mouth": _take(_MEETING, 33),
    "final_departure": _take(_MEETING, 34, 35, 36),
}


def linhas_canonicas_do_beat(beat_id: Any) -> list[str]:
    return list(CANONICAL_LINES_BY_BEAT.get(str(beat_id or "").strip(), []))


__all__ = [
    "CANONICAL_SCREENPLAY_VERSION",
    "CANONICAL_LINES_BY_BEAT",
    "linhas_canonicas_do_beat",
]
