from scenarios.stories.casada_frustrada.progression_guard import preparar_progressao_canonica


def _instance(beat: str, route: str = "supermarket_encounter") -> dict:
    return {
        "scenario_id": "casada_frustrada",
        "current_route": route,
        "current_beat": beat,
        "scene_state": {
            "current_route": route,
            "current_beat": beat,
        },
    }


def test_injury_check_advances_after_canonical_emission_and_user_reply() -> None:
    instance = _instance("injury_check")
    messages = [
        {"role": "assistant", "content": "Eita, caralho... desculpa! Tem certeza que tá tudo bem?"},
        {"role": "user", "content": "Tudo certo. Não machucou."},
    ]

    preparar_progressao_canonica(instance, messages)

    assert instance["current_beat"] == "recognize_plaza"
    assert instance["scene_state"]["advanced_from_beat"] == "injury_check"
    assert "injury_check" in instance["scene_state"]["completed_script_beats"]


def test_same_emission_is_consumed_only_once() -> None:
    instance = _instance("injury_check")
    messages = [
        {"role": "assistant", "content": "Eita, caralho... desculpa! Tem certeza que tá tudo bem?"},
        {"role": "user", "content": "Tudo certo."},
    ]

    preparar_progressao_canonica(instance, messages)
    first_beat = instance["current_beat"]
    preparar_progressao_canonica(instance, messages)

    assert first_beat == "recognize_plaza"
    assert instance["current_beat"] == "recognize_plaza"


def test_action_gate_does_not_advance_on_unrelated_reply() -> None:
    instance = _instance("ask_wait_help_car", "aisle_flirtation")
    messages = [
        {"role": "assistant", "content": "Você me espera? Acho que preciso de ajuda até o carro."},
        {"role": "user", "content": "Esse mercado está muito cheio hoje."},
    ]

    preparar_progressao_canonica(instance, messages)

    assert instance["current_beat"] == "ask_wait_help_car"
    assert instance["scene_state"]["pending_gate"] == "accept_help_car"


def test_action_gate_advances_when_user_cooperates() -> None:
    instance = _instance("ask_wait_help_car", "aisle_flirtation")
    messages = [
        {"role": "assistant", "content": "Você me espera? Acho que preciso de ajuda até o carro."},
        {"role": "user", "content": "Claro, eu espero e ajudo você."},
    ]

    preparar_progressao_canonica(instance, messages)

    assert instance["current_beat"] == "open_trunk"
    assert instance["current_route"] == "phone_exchange"
