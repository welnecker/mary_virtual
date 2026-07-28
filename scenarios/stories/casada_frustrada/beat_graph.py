from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical_screenplay import linhas_canonicas_do_beat


BEAT_GRAPH_VERSION = "casada-frustrada-beat-graph-v3-structure-only"


def _beat(
    beat_id: str,
    route: str,
    next_beat: str | None,
    *,
    gate: str = "",
    intensity: int = 0,
    sexual_phase: str = "idle",
    completes: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "id": beat_id,
        "route": route,
        "next": [next_beat] if next_beat else [],
        "gate": gate,
        "intensity": intensity,
        "sexual_phase": sexual_phase,
        "completes": list(completes),
        "question_limit": 1,
        "one_movement_only": True,
    }


# Este arquivo contém somente estrutura executável. Toda fala, pensamento e
# escrita dramática pertencem exclusivamente a immersive_screenplay.py.
_ORDERED = [
    _beat("injury_check", "supermarket_encounter", "recognize_plaza"),
    _beat("recognize_plaza", "supermarket_encounter", "first_farewell"),
    _beat("first_farewell", "supermarket_encounter", "second_encounter", completes=("first_contact_closed",)),
    _beat("second_encounter", "aisle_flirtation", "market_crowded", completes=("second_encounter_started",)),
    _beat("market_crowded", "aisle_flirtation", "cart_single_guess"),
    _beat("cart_single_guess", "aisle_flirtation", "home_weekend_routine", completes=("single_status_explored",)),
    _beat("home_weekend_routine", "aisle_flirtation", "checkout_turn"),
    _beat("checkout_turn", "aisle_flirtation", "ask_wait_help_car"),
    _beat("ask_wait_help_car", "aisle_flirtation", "open_trunk", gate="accept_help_car"),
    _beat("open_trunk", "phone_exchange", "liked_meeting", completes=("help_to_car_completed",)),
    _beat("liked_meeting", "phone_exchange", "request_phone"),
    _beat("request_phone", "phone_exchange", "exchange_numbers", gate="phone_acceptance"),
    _beat("exchange_numbers", "phone_exchange", "car_farewell", completes=("phone_numbers_exchanged",)),
    _beat("car_farewell", "phone_exchange", "home_first_message"),
    _beat("home_first_message", "messages", "seek_bathroom_privacy", completes=("first_private_message_sent",)),
    _beat("seek_bathroom_privacy", "messages", "admit_neediness", completes=("privacy_established",)),
    _beat("admit_neediness", "messages", "admit_attraction"),
    _beat("admit_attraction", "messages", "offer_video"),
    _beat("offer_video", "messages", "camera_setup", gate="video_acceptance", completes=("video_offered",)),
    _beat("camera_setup", "hidden_call", "admire_video", intensity=2, sexual_phase="tension", completes=("video_call_established", "camera_positioned")),
    _beat("admire_video", "hidden_call", "ask_remove_shirt", intensity=2, sexual_phase="tension"),
    _beat("ask_remove_shirt", "hidden_call", "react_torso", gate="shirt_acceptance", intensity=3, sexual_phase="active"),
    _beat("react_torso", "hidden_call", "ask_remove_pants", intensity=3, sexual_phase="active"),
    _beat("ask_remove_pants", "hidden_call", "react_underwear", gate="pants_acceptance", intensity=4, sexual_phase="active"),
    _beat("react_underwear", "hidden_call", "mary_remove_dress", intensity=4, sexual_phase="active"),
    _beat("mary_remove_dress", "hidden_call", "invite_bra_request", intensity=4, sexual_phase="active", completes=("mary_lingerie_revealed",)),
    _beat("invite_bra_request", "hidden_call", "reveal_breasts", gate="bra_request", intensity=4, sexual_phase="active"),
    _beat("reveal_breasts", "hidden_call", "ask_remove_underwear", intensity=5, sexual_phase="active"),
    _beat("ask_remove_underwear", "hidden_call", "react_nudity", gate="underwear_acceptance", intensity=5, sexual_phase="active"),
    _beat("react_nudity", "hidden_call", "breast_fantasy", intensity=5, sexual_phase="active"),
    _beat("breast_fantasy", "hidden_call", "mary_remove_panties", intensity=5, sexual_phase="active"),
    _beat("mary_remove_panties", "hidden_call", "propose_mutual_masturbation", intensity=5, sexual_phase="active"),
    _beat("propose_mutual_masturbation", "hidden_call", "guide_mutual_masturbation", gate="mutual_acceptance", intensity=5, sexual_phase="active"),
    _beat("guide_mutual_masturbation", "hidden_call", "urge_user_climax", intensity=5, sexual_phase="active"),
    _beat("urge_user_climax", "hidden_call", "react_user_climax", gate="user_climax", intensity=5, sexual_phase="climax"),
    _beat("react_user_climax", "hidden_call", "end_first_call", intensity=5, sexual_phase="climax"),
    _beat("end_first_call", "hidden_call", "midnight_return", intensity=3, sexual_phase="aftercare", completes=("first_call_ended",)),
    _beat("midnight_return", "secret_meeting_plan", "propose_motel"),
    _beat("propose_motel", "secret_meeting_plan", "name_motel", gate="meeting_interest"),
    _beat("name_motel", "secret_meeting_plan", "demand_no_show", gate="meeting_acceptance", completes=("secret_meeting_arranged",)),
    _beat("demand_no_show", "secret_meeting_plan", "good_night"),
    _beat("good_night", "secret_meeting_plan", "motel_preparation"),
    _beat("motel_preparation", "secret_meeting", "motel_reunion"),
    _beat("motel_reunion", "secret_meeting", "ask_touch_butt", gate="arrival", intensity=4, sexual_phase="tension"),
    _beat("ask_touch_butt", "growing_tension", "ask_touch_breasts", gate="touch_butt", intensity=5, sexual_phase="active"),
    _beat("ask_touch_breasts", "growing_tension", "ask_remove_bra", gate="touch_breasts", intensity=5, sexual_phase="active"),
    _beat("ask_remove_bra", "growing_tension", "heels_and_panties", gate="remove_bra", intensity=5, sexual_phase="active"),
    _beat("heels_and_panties", "intimacy", "offer_oral", intensity=5, sexual_phase="active"),
    _beat("offer_oral", "intimacy", "oral_admiration", gate="oral_acceptance", intensity=5, sexual_phase="active"),
    _beat("oral_admiration", "intimacy", "oral_climax_request", intensity=5, sexual_phase="active"),
    _beat("oral_climax_request", "intimacy", "oral_after_climax", gate="user_climax", intensity=5, sexual_phase="climax"),
    _beat("oral_after_climax", "intimacy", "request_her_pleasure", intensity=5, sexual_phase="aftercare"),
    _beat("request_her_pleasure", "intimacy", "invite_cunnilingus", intensity=5, sexual_phase="active"),
    _beat("invite_cunnilingus", "intimacy", "guide_cunnilingus", gate="cunnilingus_acceptance", intensity=5, sexual_phase="active"),
    _beat("guide_cunnilingus", "intimacy", "first_orgasm_build", gate="cunnilingus_execution", intensity=5, sexual_phase="active"),
    _beat("first_orgasm_build", "climax", "first_orgasm", intensity=5, sexual_phase="pre_orgasm"),
    _beat("first_orgasm", "climax", "post_oral_tease", gate="mary_orgasm_allowed", intensity=5, sexual_phase="climax", completes=("mary_first_orgasm_done",)),
    _beat("post_oral_tease", "aftercare", "praise_lover", intensity=4, sexual_phase="aftercare"),
    _beat("praise_lover", "aftercare", "request_doggy", intensity=4, sexual_phase="tension"),
    _beat("request_doggy", "intimacy", "ask_spank", gate="erection_confirmed", intensity=5, sexual_phase="active"),
    _beat("ask_spank", "intimacy", "ask_lubricate", gate="spank_execution", intensity=5, sexual_phase="active"),
    _beat("ask_lubricate", "intimacy", "penetration_start", gate="lubrication_execution", intensity=5, sexual_phase="active"),
    _beat("penetration_start", "intimacy", "penetration_rhythm", gate="penetration_acceptance", intensity=5, sexual_phase="active"),
    _beat("penetration_rhythm", "intimacy", "ask_anal_finger", gate="penetration_execution", intensity=5, sexual_phase="active"),
    _beat("ask_anal_finger", "intimacy", "second_orgasm_build", gate="anal_finger_execution", intensity=5, sexual_phase="active"),
    _beat("second_orgasm_build", "climax", "request_internal_climax", intensity=5, sexual_phase="pre_orgasm"),
    _beat("request_internal_climax", "climax", "shared_climax", gate="user_climax", intensity=5, sexual_phase="climax"),
    _beat("shared_climax", "climax", "post_penetration", gate="mary_orgasm_allowed", intensity=5, sexual_phase="climax", completes=("final_climax_done",)),
    _beat("post_penetration", "aftercare", "clean_with_mouth", intensity=3, sexual_phase="aftercare"),
    _beat("clean_with_mouth", "aftercare", "final_departure", intensity=3, sexual_phase="aftercare"),
    _beat("final_departure", "future_secret", None, intensity=2, sexual_phase="aftercare", completes=("story_completed",)),
]

BEATS: dict[str, dict[str, Any]] = {beat["id"]: beat for beat in _ORDERED}
BEAT_ORDER = [beat["id"] for beat in _ORDERED]
INITIAL_BEAT = "injury_check"


def obter_beat(beat_id: Any) -> dict[str, Any] | None:
    beat = BEATS.get(str(beat_id or "").strip())
    if not isinstance(beat, dict):
        return None
    result = deepcopy(beat)
    canonical_lines = linhas_canonicas_do_beat(result["id"])
    result["canonical_lines"] = canonical_lines
    result["examples"] = canonical_lines
    result["objective"] = f"Interpretar integralmente as falas canônicas do beat {result['id']}."
    result["avoid"] = []
    result["transition"] = ""
    result["thought"] = ""
    return result


def proximo_beat_padrao(beat_id: Any) -> str:
    beat = BEATS.get(str(beat_id or "").strip())
    if not isinstance(beat, dict):
        return ""
    next_beats = beat.get("next")
    if not isinstance(next_beats, list) or not next_beats:
        return ""
    return str(next_beats[0] or "").strip()


def indice_beat(beat_id: Any) -> int:
    try:
        return BEAT_ORDER.index(str(beat_id or "").strip())
    except ValueError:
        return -1


def beat_por_indice(index: int) -> dict[str, Any] | None:
    if index < 0 or index >= len(BEAT_ORDER):
        return None
    return obter_beat(BEAT_ORDER[index])


__all__ = [
    "BEAT_GRAPH_VERSION",
    "BEATS",
    "BEAT_ORDER",
    "INITIAL_BEAT",
    "obter_beat",
    "proximo_beat_padrao",
    "indice_beat",
    "beat_por_indice",
]
