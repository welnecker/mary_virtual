from scenarios.stories.casada_frustrada.story_structure import build_story_compass


def test_story_compass_does_not_expose_full_task_queue() -> None:
    compass = build_story_compass("phone_exchange", "exchange_numbers")

    assert "full_route_arc" not in compass
    assert "current_index" not in compass
    assert "possible_movements" in compass
    assert compass["diagnostic_beat_reference"] == "exchange_numbers"


def test_story_compass_blocks_repeated_phone_exchange() -> None:
    compass = build_story_compass("phone_exchange", "exchange_numbers")

    assert any(
        "pedir ou oferecer número" in rule
        for rule in compass["never"]
    )
    assert any(
        "realidade confirmada" in rule.lower()
        for rule in compass["interpretation_rules"]
    )


def test_messages_route_treats_existing_channel_as_fact() -> None:
    compass = build_story_compass("messages", "home_first_message")

    assert any(
        "voltar a pedir telefone" in rule
        for rule in compass["never"]
    )
    assert "fila de tarefas" in " ".join(compass["interpretation_rules"])
