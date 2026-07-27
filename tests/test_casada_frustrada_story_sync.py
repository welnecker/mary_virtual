from scenarios.stories.casada_frustrada.story_sync import (
    reconciliar_posicao_narrativa,
)


def test_private_messages_override_stale_supermarket_cursor() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "Oi, Janio... sou eu, a Mary. Salva meu número com discrição.",
        },
        {
            "role": "assistant",
            "content": "Estou aqui no banheiro para falar com você em paz.",
        },
    ]

    result = reconciliar_posicao_narrativa(
        messages=messages,
        legacy_route="aisle_flirtation",
        legacy_beat="ask_wait_help_car",
    )

    assert result["route"] == "messages"
    assert result["beat"] == "admit_neediness"
    assert result["legacy_cursor_overridden"] is True


def test_attraction_already_admitted_opens_video_offer() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "Estou aqui no banheiro para falar com você em paz.",
        },
        {
            "role": "assistant",
            "content": "Eu te achei muito atraente. É sério.",
        },
        {
            "role": "user",
            "content": "Uma loucura deliciosa, rsrsrs.",
        },
    ]

    result = reconciliar_posicao_narrativa(
        messages=messages,
        legacy_route="aisle_flirtation",
        legacy_beat="ask_wait_help_car",
    )

    assert result["route"] == "messages"
    assert result["beat"] == "offer_video"
    assert result["reason"] == "conversation_confirms_private_messages"


def test_video_acceptance_advances_both_sources_to_hidden_call() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "Posso te chamar por vídeo?",
        },
        {
            "role": "user",
            "content": "Pode me chamar por vídeo.",
        },
    ]

    result = reconciliar_posicao_narrativa(
        messages=messages,
        legacy_route="messages",
        legacy_beat="offer_video",
    )

    assert result["route"] == "hidden_call"
    assert result["beat"] == "camera_setup"
