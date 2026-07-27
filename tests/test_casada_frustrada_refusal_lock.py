from scenarios.stories.casada_frustrada.refusal_lock import detectar_trava_psicologica


def _messages(user_text: str):
    return [
        {"role": "assistant", "content": "Mary faz uma iniciativa decisiva."},
        {"role": "user", "content": user_text},
    ]


def test_refusing_phone_triggers_definitive_ending() -> None:
    lock = detectar_trava_psicologica(
        messages=_messages("Não vou te passar meu número."),
        open_beat="request_phone",
    )

    assert lock is not None
    assert lock["trigger"] == "refusal"
    assert lock["category"] == "phone"
    assert lock["input_locked_after_response"] is True
    assert lock["requires_new_paid_cycle"] is True
    assert "número" in lock["final_direction"]


def test_postponing_motel_ends_meeting_route() -> None:
    lock = detectar_trava_psicologica(
        messages=_messages("Agora não, preciso pensar. Quem sabe outro dia."),
        open_beat="propose_motel",
    )

    assert lock is not None
    assert lock["trigger"] == "postpone"
    assert lock["category"] == "meeting"
    assert lock["ending_type"] == "psychological_refusal_lock"


def test_refusing_grocery_help_uses_route_specific_reaction() -> None:
    lock = detectar_trava_psicologica(
        messages=_messages("Não vou ajudar a levar essas compras."),
        open_beat="ask_wait_help_car",
    )

    assert lock is not None
    assert lock["category"] == "groceries_help"
    assert "cavalheiros" in lock["final_direction"]


def test_not_stop_is_not_misread_as_refusal() -> None:
    lock = detectar_trava_psicologica(
        messages=_messages("Não para, continua assim!"),
        open_beat="urge_user_climax",
    )

    assert lock is None


def test_neutral_delay_outside_guarded_beat_does_not_end() -> None:
    lock = detectar_trava_psicologica(
        messages=_messages("Vou pensar nisso depois."),
        open_beat="react_torso",
    )

    assert lock is None
