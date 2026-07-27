from scenarios.stories.casada_frustrada.prompt_context import (
    aplicar_estado_narrativo_ao_compasso,
)
from scenarios.stories.casada_frustrada.story_structure import (
    build_story_compass,
)


def test_completed_contact_removes_phone_movements() -> None:
    compass = build_story_compass("phone_exchange", "exchange_numbers")
    state = {
        "confirmed_facts": [
            "o canal de comunicação por mensagens já está estabelecido",
        ],
        "completed_functions": ["establish_contact_channel"],
        "blocked_movements": [
            "ask_phone_number",
            "offer_phone_number_again",
        ],
    }

    result = aplicar_estado_narrativo_ao_compasso(compass, state)

    assert all(
        "telefone" not in movement.casefold()
        and "número" not in movement.casefold()
        and "numero" not in movement.casefold()
        and "contato" not in movement.casefold()
        for movement in result["possible_movements"]
    )
    assert (
        "establish_contact_channel"
        in result["story_reality"]["completed_functions"]
    )
    assert any(
        "não pedir nem oferecer telefone novamente" in rule
        for rule in result["interpretation_rules"]
    )


def test_story_reality_is_authoritative() -> None:
    result = aplicar_estado_narrativo_ao_compasso(
        build_story_compass("messages", "admit_attraction"),
        {
            "confirmed_facts": ["Mary e o usuário já conversam diretamente"],
            "active_tensions": ["o usuário pediu que Mary desacelerasse"],
        },
    )

    reality = result["story_reality"]
    assert reality["confirmed_facts"] == [
        "Mary e o usuário já conversam diretamente",
    ]
    assert reality["active_tensions"] == [
        "o usuário pediu que Mary desacelerasse",
    ]
    assert "prioridade" in reality["authority"]
