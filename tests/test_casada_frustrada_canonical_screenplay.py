from scenarios.stories.casada_frustrada.canonical_screenplay import linhas_canonicas_do_beat
from scenarios.stories.casada_frustrada.screenplay_executor import construir_trava_de_roteiro
from scenarios.stories.casada_frustrada.story_sync import reconciliar_posicao_narrativa


def test_screenplay_lock_uses_exact_lines_from_immersive_screenplay() -> None:
    lock = construir_trava_de_roteiro("ask_touch_butt")

    assert lock["canonical_lines"] == [
        "Aperta minha bunda. Abre minhas nádegas e me amassa."
    ]
    assert lock["canonical_lines"] == linhas_canonicas_do_beat("ask_touch_butt")
    assert lock["canonical_text_must_be_preserved"] is True


def test_user_improvisation_cannot_replace_valid_beat_graph_position() -> None:
    result = reconciliar_posicao_narrativa(
        messages=[
            {"role": "user", "content": "Vamos falar de futebol e esquecer isso."},
            {"role": "assistant", "content": "Você quer mudar de assunto?"},
        ],
        legacy_route="growing_tension",
        legacy_beat="ask_remove_bra",
    )

    assert result["route"] == "growing_tension"
    assert result["beat"] == "ask_remove_bra"
    assert result["legacy_cursor_overridden"] is False
    assert result["reason"] == "beat_graph_position_preserved"


def test_invalid_state_recovers_to_initial_beat_without_reading_dialogue() -> None:
    result = reconciliar_posicao_narrativa(
        messages=[{"role": "user", "content": "Cheguei no motel."}],
        legacy_route="unknown",
        legacy_beat="missing-beat",
    )

    assert result["beat"] == "injury_check"
    assert result["legacy_cursor_overridden"] is True
