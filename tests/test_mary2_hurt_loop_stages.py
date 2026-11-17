from mary2.direct_script import (
    hurt_loop_max_interactions,
    hurt_loop_turn_direction,
    should_activate_hurt_loop,
)


def test_only_explicit_line_violation_starts_hurt_loop():
    loop_row = {"speech_guide": "MISSÃO INTERATIVA ESPECIAL — ORGULHO FERIDO"}
    negative_rule = "Rejeição de desculpas, convite sexual ou humilhação pública."
    assert not should_activate_hurt_loop(
        {"violation": False, "frustration": True, "rejected": True}, negative_rule, loop_row
    )
    assert should_activate_hurt_loop(
        {"violation": True, "frustration": False}, negative_rule, loop_row
    )
    assert not should_activate_hurt_loop({"violation": True}, "", loop_row)
    assert not should_activate_hurt_loop({"violation": True}, negative_rule, {})


def test_loop_has_three_distinct_stages_and_final_exit():
    loop_row = {"speech_guide": "Após três interações sem reconciliação, encerrar."}
    maximum = hurt_loop_max_interactions(loop_row)
    assert maximum == 3
    first = hurt_loop_turn_direction(1, maximum)
    second = hurt_loop_turn_direction(2, maximum)
    third = hurt_loop_turn_direction(3, maximum)
    assert "PRIMEIRA" in first
    assert "intermediária" in second
    assert "ÚLTIMA" in third
    assert "encerramento do roteiro" in third
    assert "última etapa" in second


def test_one_attempt_loop_goes_straight_to_last_stage():
    assert "ÚLTIMA" in hurt_loop_turn_direction(1, 1)
