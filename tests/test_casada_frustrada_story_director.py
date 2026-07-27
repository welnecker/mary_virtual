from scenarios.stories.casada_frustrada.canonical_memory import atualizar_memoria_canonica
from scenarios.stories.casada_frustrada.story_director import dirigir_turno


def _instance(route: str, beat: str, *, memory=None, visual=None, execution=None):
    return {
        "scenario_id": "casada_frustrada",
        "current_route": route,
        "current_beat": beat,
        "scene_state": {
            "current_route": route,
            "current_beat": beat,
            "script_runtime": {"current_beat": beat},
            "confirmed_visual_state": visual or {},
            "screenplay_execution": execution or {},
        },
        "story_memory": memory or {},
    }


def test_memory_prevents_phone_exchange_from_commanding_messages() -> None:
    prior_messages = [
        {"role": "assistant", "content": "Me passa seu número."},
        {"role": "user", "content": "999711721, Janio."},
        {"role": "assistant", "content": "Anotado. A gente se fala."},
        {"role": "assistant", "content": "Cheguei em casa e estou falando com você pelo celular."},
    ]
    memory = atualizar_memoria_canonica(
        {}, messages=prior_messages, route="messages", beat="home_first_message"
    )
    messages = [
        *prior_messages,
        {"role": "assistant", "content": "Estou sorrindo sozinha para a tela do celular."},
        {"role": "user", "content": "Você é muito agradável."},
    ]
    instance = _instance("phone_exchange", "exchange_numbers", memory=memory)

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["route"] == "messages"
    assert direction["beat"] not in {"request_phone", "exchange_numbers"}
    assert instance["current_route"] == "messages"
    assert "script_runtime" not in instance["scene_state"]


def test_confirmed_shirt_removal_opens_reaction_not_repeat_request() -> None:
    messages = [
        {"role": "assistant", "content": "Oi, está me vendo? Vou colocar o celular na bancada."},
        {"role": "assistant", "content": "Você é lindo. Tira sua camisa para eu ver seu peitoral?"},
        {"role": "user", "content": "Pronto, tirei a camisa. Agora consegue ver melhor?"},
    ]
    instance = _instance("hidden_call", "ask_remove_shirt")

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["route"] == "hidden_call"
    assert direction["beat"] == "react_torso"
    assert direction["confirmed_visual_state"]["user_shirt_removed"] is True


def test_second_call_after_user_wakes_opens_motel_proposal() -> None:
    messages = [
        {"role": "assistant", "content": "Preciso desligar. Te ligo quando meu marido estiver dormindo. Me espera."},
        {"role": "user", "content": "Tá bom. Vou deixar o celular alto."},
        {"role": "assistant", "content": "Psiu, Jânio? Tá acordado?"},
        {"role": "user", "content": "Oi? Acordei..."},
    ]
    instance = _instance(
        "secret_meeting_plan",
        "midnight_return",
        visual={"video_call_established": True, "first_call_ended": True},
    )

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["route"] == "secret_meeting_plan"
    assert direction["beat"] == "propose_motel"
    assert direction["screenplay_lock"]["current_route"] == "secret_meeting_plan"
    assert "motel" in direction["objective"].lower()


def test_ended_first_call_is_not_reopened_by_old_video_state() -> None:
    messages = [
        {"role": "assistant", "content": "Preciso desligar agora. Daqui a pouco eu te chamo."},
        {"role": "user", "content": "Me liga depois."},
    ]
    instance = _instance(
        "hidden_call",
        "react_user_climax",
        visual={"video_call_established": True, "first_call_ended": True},
    )

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["route"] == "secret_meeting_plan"
    assert direction["beat"] == "midnight_return"
    assert direction["screenplay_lock"]["current_route"] == "secret_meeting_plan"


def test_physical_motel_reality_overrides_stale_good_night_cursor() -> None:
    messages = [
        {"role": "assistant", "content": "Boa noite. Amanhã te espero no Motel Status ao meio-dia."},
        {"role": "assistant", "content": "Cheguei no Motel Status. Estou na suíte 14."},
        {"role": "user", "content": "Cheguei. Estou entrando na portaria."},
        {"role": "assistant", "content": "Entra e tranca a porta. Me pega logo. Me beija."},
        {"role": "user", "content": "Estou sentindo seu abraço. Que delícia."},
        {"role": "assistant", "content": "Não me solta. Aperta mais."},
        {"role": "user", "content": "Fala o que você quer."},
    ]
    instance = _instance(
        "secret_meeting_plan",
        "good_night",
        visual={"first_call_ended": True, "video_call_established": True},
    )

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["route"] == "growing_tension"
    assert direction["beat"] == "ask_touch_butt"
    assert direction["screenplay_lock"]["current_beat"] == "ask_touch_butt"
    assert direction["screenplay_lock"]["next_beat_locked"] == "ask_touch_breasts"
    assert direction["resolution"]["memory_override_reason"] == "locked_screenplay_executor_overrode_cursor"


def test_bra_removed_and_heels_panties_completed_opens_oral_not_panties_removal() -> None:
    messages = [
        {"role": "assistant", "content": "Cheguei no Motel Status. Estou na suíte."},
        {"role": "user", "content": "Cheguei. Estou entrando."},
        {"role": "assistant", "content": "Me pega logo. Me beija."},
        {"role": "assistant", "content": "Aperta minha bunda. Abre minhas nádegas."},
        {"role": "user", "content": "Plaf! Gostosa!"},
        {"role": "assistant", "content": "Aperta meus seios. Sente como são firmes."},
        {"role": "user", "content": "Estou apertando e chupando."},
        {"role": "assistant", "content": "Desprende o meu sutiã. Liberta eles."},
        {"role": "user", "content": "Tirei. Pronto. Põe na minha boca. Chup!"},
        {"role": "assistant", "content": "Vou ficar aqui só de calcinha e salto alto para você."},
        {"role": "user", "content": "Estou muito excitado."},
    ]
    instance = _instance("growing_tension", "ask_remove_bra")

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["route"] == "intimacy"
    assert direction["beat"] == "offer_oral"
    assert direction["screenplay_lock"]["mandatory_objective"].startswith(
        "Mary anuncia que quer dar prazer oral"
    )
    assert direction["screenplay_lock"]["next_beat_locked"] == "oral_admiration"
    assert "invite_cunnilingus" not in direction["screenplay_execution"]["completed_beats"]


def test_full_screenplay_is_not_exposed_as_future_action_menu() -> None:
    messages = [
        {"role": "assistant", "content": "Cheguei no Motel Status. Estou na suíte."},
        {"role": "user", "content": "Cheguei. Estou entrando."},
    ]
    direction = dirigir_turno(
        instance=_instance("secret_meeting_plan", "good_night"),
        messages=messages,
    )

    assert "screenplay" not in direction
    assert "official_screenplay" not in direction["route_compass"]
    assert direction["screenplay_lock"]["current_beat"] == direction["beat"]
    assert direction["screenplay_lock"]["next_beat_locked"] != direction["beat"]


def test_director_exposes_one_authoritative_function() -> None:
    messages = [
        {"role": "assistant", "content": "Oi, está me vendo? Vou colocar o celular na bancada."},
        {"role": "user", "content": "Estou vendo sim."},
    ]
    direction = dirigir_turno(
        instance=_instance("hidden_call", "camera_setup"),
        messages=messages,
    )

    assert "A sequência do roteiro é obrigatória" in direction["resolution"]["authority"]
    assert direction["objective"]
    assert direction["screenplay_lock"]["current_route"] == direction["route"]
