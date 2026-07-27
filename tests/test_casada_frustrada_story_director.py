from scenarios.stories.casada_frustrada.canonical_memory import (
    atualizar_memoria_canonica,
)
from scenarios.stories.casada_frustrada.story_director import dirigir_turno


def _instance(route: str, beat: str, *, memory=None):
    return {
        "scenario_id": "casada_frustrada",
        "current_route": route,
        "current_beat": beat,
        "scene_state": {
            "current_route": route,
            "current_beat": beat,
            "script_runtime": {"current_beat": beat},
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


def test_director_exposes_one_authoritative_function() -> None:
    messages = [
        {"role": "assistant", "content": "Oi, está me vendo? Vou colocar o celular na bancada."},
        {"role": "user", "content": "Estou vendo sim."},
    ]
    instance = _instance("hidden_call", "camera_setup")

    direction = dirigir_turno(instance=instance, messages=messages)

    assert direction["resolution"]["authority"].startswith(
        "Esta é a única direção narrativa"
    )
    assert direction["objective"]
    assert direction["screenplay"]["route"] == direction["route"]
