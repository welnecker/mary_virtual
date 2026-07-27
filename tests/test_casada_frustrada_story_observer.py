from scenarios.stories.casada_frustrada.story_observer import (
    ASK_PHONE_MOVEMENT,
    CONTACT_FUNCTION,
    OFFER_PHONE_MOVEMENT,
    observar_estado_narrativo,
)


def test_contact_channel_is_completed_when_messages_already_exist() -> None:
    messages = [
        {
            "role": "user",
            "content": "Caramba, Mary, a gente já está conversando por mensagens.",
        },
        {
            "role": "assistant",
            "content": "Você tem razão. Vamos continuar por aqui.",
        },
    ]

    state = observar_estado_narrativo(
        None,
        messages=messages,
        route="phone_exchange",
        beat_id="exchange_numbers",
    )

    assert CONTACT_FUNCTION in state["completed_functions"]
    assert ASK_PHONE_MOVEMENT in state["blocked_movements"]
    assert OFFER_PHONE_MOVEMENT in state["blocked_movements"]
    assert "o canal de comunicação por mensagens já está estabelecido" in state["confirmed_facts"]


def test_messages_route_implies_established_contact() -> None:
    state = observar_estado_narrativo(
        {},
        messages=[],
        route="messages",
        beat_id="home_first_message",
    )

    assert CONTACT_FUNCTION in state["completed_functions"]
    assert OFFER_PHONE_MOVEMENT in state["blocked_movements"]


def test_user_concern_becomes_active_tension() -> None:
    state = observar_estado_narrativo(
        {},
        messages=[
            {
                "role": "user",
                "content": "Calma, Mary. Isso pode fugir do controle.",
            }
        ],
        route="messages",
        beat_id="admit_attraction",
    )

    assert any("fuja do controle" in tension for tension in state["active_tensions"])
