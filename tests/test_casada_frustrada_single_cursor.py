from scenarios.stories.casada_frustrada.story_director import dirigir_turno


def _instance(beat: str, route: str = "supermarket_encounter") -> dict:
    return {
        "scenario_id": "casada_frustrada",
        "scene_state": {
            "current_route": route,
            "current_beat": beat,
            "completed_beats": [],
        },
        "story_memory": {},
    }


def test_opening_reply_stays_on_second_script_line() -> None:
    instance = _instance("injury_check")
    messages = [
        {"role": "assistant", "content": "Eita, caralho... desculpa!"},
        {"role": "user", "content": "Não foi nada, só um susto."},
    ]

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["beat"] == "injury_check"
    assert direction["screenplay_lock"]["canonical_lines"] == ["Tem certeza que tá tudo bem?"]


def test_confirmation_advances_to_plaza_recognition() -> None:
    instance = _instance("injury_check")
    messages = [
        {"role": "assistant", "content": "Tem certeza que tá tudo bem?"},
        {"role": "user", "content": "Tá sim, foi só um susto."},
    ]

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["beat"] == "recognize_plaza"
    assert instance["scene_state"]["current_beat"] == "recognize_plaza"
    assert "injury_check" in instance["scene_state"]["completed_beats"]


def test_reencounter_never_returns_to_accident() -> None:
    instance = _instance("second_encounter", "aisle_flirtation")
    messages = [
        {"role": "assistant", "content": "Oi... tá recuperado do susto? rsrsrs"},
        {"role": "user", "content": "Tô sim. E você, atropelou mais alguém? rsrsrs"},
    ]

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["beat"] == "market_crowded"
    assert direction["route"] == "aisle_flirtation"
    assert direction["beat"] not in {"injury_check", "recognize_plaza", "first_farewell"}


def test_gate_holds_cursor_on_unrelated_reply() -> None:
    instance = _instance("ask_wait_help_car", "aisle_flirtation")
    messages = [
        {"role": "assistant", "content": "Você me espera? Acho que preciso de ajuda até o carro."},
        {"role": "user", "content": "Esse mercado está cheio hoje."},
    ]

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["beat"] == "ask_wait_help_car"
    assert instance["scene_state"]["pending_gate"] == "accept_help_car"


def test_gate_advances_only_to_graph_successor() -> None:
    instance = _instance("ask_wait_help_car", "aisle_flirtation")
    messages = [
        {"role": "assistant", "content": "Você me espera? Acho que preciso de ajuda até o carro."},
        {"role": "user", "content": "Claro, eu espero e ajudo você."},
    ]

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["beat"] == "open_trunk"
    assert direction["route"] == "phone_exchange"
