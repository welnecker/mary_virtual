from scenarios.stories.casada_frustrada import (
    montar_contexto_interpretativo,
    obter_trecho_roteiro,
)
from scenarios.stories.casada_frustrada.immersive_screenplay import (
    HIDDEN_CALL_DIALOGUE,
    IMMERSIVE_SCREENPLAY_VERSION,
    MESSAGES_DIALOGUE,
    SECRET_MEETING_DIALOGUE,
    SECRET_MEETING_PLAN_DIALOGUE,
    SUPERMARKET_DIALOGUE,
)


def test_each_route_uses_official_screenplay_source() -> None:
    expected_sources = {
        "supermarket_encounter": SUPERMARKET_DIALOGUE,
        "aisle_flirtation": SUPERMARKET_DIALOGUE,
        "phone_exchange": SUPERMARKET_DIALOGUE,
        "messages": MESSAGES_DIALOGUE,
        "hidden_call": HIDDEN_CALL_DIALOGUE,
        "secret_meeting_plan": SECRET_MEETING_PLAN_DIALOGUE,
        "secret_meeting": SECRET_MEETING_DIALOGUE,
        "growing_tension": SECRET_MEETING_DIALOGUE,
        "intimacy": SECRET_MEETING_DIALOGUE,
        "climax": SECRET_MEETING_DIALOGUE,
        "aftercare": SECRET_MEETING_DIALOGUE,
        "future_secret": SECRET_MEETING_DIALOGUE,
    }

    for route, source in expected_sources.items():
        context = obter_trecho_roteiro(route)
        assert context["source_version"] == IMMERSIVE_SCREENPLAY_VERSION
        assert context["excerpt"]
        assert context["excerpt"] in source


def test_supermarket_routes_receive_distinct_relevant_excerpts() -> None:
    first_contact = obter_trecho_roteiro("supermarket_encounter")["excerpt"]
    aisle = obter_trecho_roteiro("aisle_flirtation")["excerpt"]
    phone = obter_trecho_roteiro("phone_exchange")["excerpt"]

    assert "Tem certeza que tá tudo bem?" in first_contact
    assert "Tô olhando pro seu carrinho" in aisle
    assert "Queria seu número" in phone
    assert first_contact != aisle != phone


def test_interpretive_context_contains_one_official_screenplay_block() -> None:
    context = montar_contexto_interpretativo(
        route="aisle_flirtation",
        current_beat="second_encounter",
        story_state_value=None,
    )

    screenplay = context["official_screenplay"]
    assert screenplay["route"] == "aisle_flirtation"
    assert screenplay["block"] == "reencontro e aproximação no supermercado"
    assert screenplay["excerpt"]
    assert "fonte dramática principal" in context["source_authority"]
    assert "current_milestone" not in context
