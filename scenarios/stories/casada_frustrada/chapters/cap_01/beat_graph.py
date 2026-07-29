from __future__ import annotations

from scenarios.engine.models import BeatDefinition

_SEQUENCE = [
    ("injury_check", "supermarket_encounter"), ("recognize_plaza", "supermarket_encounter"),
    ("first_farewell", "supermarket_encounter"), ("second_encounter", "aisle_flirtation"),
    ("market_crowded", "aisle_flirtation"), ("cart_single_guess", "aisle_flirtation"),
    ("home_weekend_routine", "aisle_flirtation"), ("checkout_turn", "aisle_flirtation"),
    ("ask_wait_help_car", "aisle_flirtation"), ("open_trunk", "phone_exchange"),
    ("liked_meeting", "phone_exchange"), ("request_phone", "phone_exchange"),
    ("exchange_numbers", "phone_exchange"), ("car_farewell", "phone_exchange"),
    ("home_first_message", "messages"), ("seek_bathroom_privacy", "messages"),
    ("admit_neediness", "messages"), ("admit_attraction", "messages"), ("offer_video", "messages"),
    ("camera_setup", "hidden_call"), ("admire_video", "hidden_call"),
    ("ask_remove_shirt", "hidden_call"), ("react_torso", "hidden_call"),
    ("ask_remove_pants", "hidden_call"), ("react_underwear", "hidden_call"),
    ("mary_remove_dress", "hidden_call"), ("invite_bra_request", "hidden_call"),
    ("reveal_breasts", "hidden_call"), ("ask_remove_underwear", "hidden_call"),
    ("react_nudity", "hidden_call"), ("breast_fantasy", "hidden_call"),
    ("mary_remove_panties", "hidden_call"), ("propose_mutual_masturbation", "hidden_call"),
    ("guide_mutual_masturbation", "hidden_call"), ("urge_user_climax", "hidden_call"),
    ("react_user_climax", "hidden_call"), ("end_first_call", "hidden_call"),
    ("midnight_return", "secret_meeting_plan"), ("propose_motel", "secret_meeting_plan"),
    ("name_motel", "secret_meeting_plan"), ("demand_no_show", "secret_meeting_plan"),
    ("good_night", "secret_meeting_plan"), ("motel_preparation", "secret_meeting_plan"),
    ("motel_reunion", "secret_meeting"), ("ask_touch_butt", "secret_meeting"),
    ("ask_touch_breasts", "growing_tension"), ("ask_remove_bra", "growing_tension"),
    ("heels_and_panties", "intimacy"), ("offer_oral", "intimacy"),
    ("oral_admiration", "intimacy"), ("oral_climax_request", "intimacy"),
    ("oral_after_climax", "intimacy"), ("request_her_pleasure", "intimacy"),
    ("invite_cunnilingus", "intimacy"), ("guide_cunnilingus", "intimacy"),
    ("request_doggy", "intimacy"), ("ask_spank", "intimacy"),
    ("ask_lubricate", "intimacy"), ("penetration_start", "intimacy"),
    ("penetration_rhythm", "intimacy"), ("ask_anal_finger", "intimacy"),
    ("first_orgasm_build", "climax"), ("first_orgasm", "climax"),
    ("second_orgasm_build", "climax"), ("request_internal_climax", "climax"),
    ("shared_climax", "climax"), ("post_oral_tease", "aftercare"),
    ("praise_lover", "aftercare"), ("post_penetration", "aftercare"),
    ("clean_with_mouth", "aftercare"), ("final_departure", "future_secret"),
]

BEATS = {
    beat_id: BeatDefinition(
        beat_id=beat_id,
        route=route,
        next_beat=_SEQUENCE[index + 1][0] if index + 1 < len(_SEQUENCE) else None,
    )
    for index, (beat_id, route) in enumerate(_SEQUENCE)
}

__all__ = ["BEATS"]
