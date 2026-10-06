from mary2.block_script import (
    apply_block_turn,
    build_block_prompt,
    current_block_row,
    ensure_block_state,
)


ROWS = [
    {
        "order": 1,
        "block_id": "bloco_01",
        "scene_id": "bloco_01",
        "objective": "Reagir ao carro e entrar como passageira.",
        "free_territory": "Humor sobre treino e lanchonete.",
        "convergence": "Preparar o trajeto e o trânsito.",
        "tone": "leve",
        "atmosphere": "descontraída",
        "permanent_memory": "Use o perfil permanente de Mary.",
        "authorial_recent_memory": "Mary saiu da academia e conversou na lanchonete.",
        "dynamic_requirement": "Nenhuma neste bloco.",
        "physical_action": "Pode entrar e se acomodar.",
        "specific_limits": "Não controlar o usuário.",
        "target_min": 2,
        "target_max": 3,
        "min_turns": 2,
        "ideal_turns": 3,
        "max_turns": 5,
        "depends_on_user": False,
        "next_block_id": "bloco_02",
    },
    {
        "order": 2,
        "block_id": "bloco_02",
        "scene_id": "bloco_02",
        "objective": "Descobrir onde o personal mora.",
        "free_territory": "Curiosidade leve.",
        "convergence": "Preparar uma conversa mais pessoal.",
        "tone": "curiosa",
        "atmosphere": "próxima",
        "permanent_memory": "Use o perfil permanente de Mary.",
        "authorial_recent_memory": "A carona já começou.",
        "dynamic_requirement": "Onde o personal mora e se Camburi fica no caminho.",
        "physical_action": "",
        "specific_limits": "Não inventar resposta.",
        "target_min": 1,
        "target_max": 2,
        "min_turns": 1,
        "ideal_turns": 2,
        "max_turns": 5,
        "depends_on_user": True,
        "next_block_id": "",
    },
]


def scene():
    return {
        "physical_state": {
            "location_type": "inside_vehicle",
            "vehicle_motion": "parked",
            "mary_position": "passenger_seat",
            "arrival_state": "en_route",
        }
    }


def test_prompt_uses_authorial_recent_memory():
    state = ensure_block_state({}, ROWS)
    prompt = build_block_prompt(
        facts_prompt="Fatos fixos.",
        row=ROWS[0],
        state=state,
        scene=scene(),
    )

    assert "MEMÓRIA RECENTE AUTORAL" in prompt
    assert "Mary saiu da academia e conversou na lanchonete." in prompt
    assert "Preparar o trajeto e o trânsito." in prompt


def test_non_dependent_block_advances_at_target_max():
    state = ensure_block_state({}, ROWS)

    for _ in range(2):
        progress = apply_block_turn(
            rows=ROWS,
            state=state,
            row=ROWS[0],
            dependency={"satisfied": True},
            scene=scene(),
        )
        assert progress["advanced"] is False

    progress = apply_block_turn(
        rows=ROWS,
        state=state,
        row=ROWS[0],
        dependency={"satisfied": True},
        scene=scene(),
    )

    assert progress["advanced"] is True
    assert progress["advanced_to"] == "bloco_02"
    assert state["block_turn"] == 0
    assert current_block_row(ROWS, state)["block_id"] == "bloco_02"


def test_dependent_block_waits_for_user_answer():
    state = ensure_block_state({}, ROWS)
    state["block_index"] = 1
    state["block_id"] = "bloco_02"

    progress = apply_block_turn(
        rows=ROWS,
        state=state,
        row=ROWS[1],
        dependency={"satisfied": False, "summary": ""},
        scene=scene(),
    )

    assert progress["advanced"] is False
    assert state["block_id"] == "bloco_02"


def test_dependent_block_accepts_confirmed_answer_but_holds_without_next_row():
    state = ensure_block_state({}, ROWS)
    state["block_index"] = 1
    state["block_id"] = "bloco_02"

    progress = apply_block_turn(
        rows=ROWS,
        state=state,
        row=ROWS[1],
        dependency={
            "satisfied": True,
            "refused": False,
            "summary": "O personal mora em Jardim Camburi e Camburi fica no caminho.",
            "source_quote": "moro em Jardim Camburi, é caminho",
        },
        scene=scene(),
    )

    assert progress["advanced"] is False
    assert progress["holding_for_next_block"] is True
    assert state["dynamic_memory"][0]["summary"].startswith("O personal mora")


def test_last_pilot_block_never_invents_next_block():
    one_row = [dict(ROWS[0], next_block_id="")]
    state = ensure_block_state({}, one_row)

    for _ in range(3):
        progress = apply_block_turn(
            rows=one_row,
            state=state,
            row=one_row[0],
            dependency={"satisfied": True},
            scene=scene(),
        )

    assert progress["advanced"] is False
    assert progress["holding_for_next_block"] is True
    assert state["block_id"] == "bloco_01"
