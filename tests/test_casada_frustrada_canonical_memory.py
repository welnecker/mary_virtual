from scenarios.stories.casada_frustrada.canonical_memory import (
    atualizar_memoria_canonica,
    memoria_canonica_para_prompt,
)


def test_supermarket_and_phone_memories_unlock_without_future_events() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "Desculpa pelo carrinho, ainda bem que foi só um susto no mercado.",
        },
        {
            "role": "assistant",
            "content": "Você mora no Plaza? Eu moro no bloco A.",
        },
        {
            "role": "user",
            "content": "Meu número é 999711721.",
        },
        {
            "role": "assistant",
            "content": "Anotado. A gente se fala depois.",
        },
    ]

    memory = atualizar_memoria_canonica(
        None,
        messages=messages,
        route="phone_exchange",
        beat="car_farewell",
    )

    assert "met_at_supermarket" in memory["unlocked"]
    assert "neighbors_at_plaza" in memory["unlocked"]
    assert "helped_with_groceries" in memory["unlocked"]
    assert "exchanged_phone_numbers" in memory["unlocked"]
    assert "first_hidden_video_call" not in memory["unlocked"]
    assert "first_secret_meeting" not in memory["unlocked"]


def test_route_progress_unlocks_completed_shared_past() -> None:
    memory = atualizar_memoria_canonica(
        None,
        messages=[],
        route="secret_meeting_plan",
        beat="name_motel",
    )

    assert "met_at_supermarket" in memory["unlocked"]
    assert "helped_with_groceries" in memory["unlocked"]
    assert "exchanged_phone_numbers" in memory["unlocked"]
    assert "first_private_messages" in memory["unlocked"]
    assert "first_hidden_video_call" in memory["unlocked"]
    assert "secret_meeting_planned" in memory["unlocked"]
    assert "first_secret_meeting" not in memory["unlocked"]


def test_existing_memories_survive_reopening_and_prompt_marks_them_as_past() -> None:
    previous = {
        "unlocked": ["met_at_supermarket", "exchanged_phone_numbers"],
        "facts": {
            "met_at_supermarket": {
                "id": "met_at_supermarket",
                "category": "shared_origin",
                "text": "Mary conheceu o usuário no supermercado.",
            },
            "exchanged_phone_numbers": {
                "id": "exchanged_phone_numbers",
                "category": "intimacy_milestone",
                "text": "Mary conseguiu o número do usuário.",
            },
        },
    }

    memory = atualizar_memoria_canonica(
        previous,
        messages=[],
        route="messages",
        beat="home_first_message",
    )
    payload = memoria_canonica_para_prompt(memory)

    assert "met_at_supermarket" in payload["unlocked_ids"]
    assert "exchanged_phone_numbers" in payload["unlocked_ids"]
    assert "first_private_messages" in payload["unlocked_ids"]
    assert "passado compartilhado" in payload["authority"]
    assert "não repetir ações" in payload["authority"]
