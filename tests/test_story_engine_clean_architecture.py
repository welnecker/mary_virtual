from scenarios.engine.registry import StoryRegistry
from scenarios.engine.screenplay_repository import ScreenplayRepository
from scenarios.engine.session_engine import StorySessionEngine
from scenarios.stories_v2.casada_frustrada.story import STORY


def test_story_engine_starts_and_filters_current_beat() -> None:
    registry = StoryRegistry()
    registry.register(STORY)
    engine = StorySessionEngine(registry)
    session = engine.start("casada_frustrada")

    lines = ScreenplayRepository.from_records(
        [
            {
                "ordem": 10,
                "cena": "PRIMEIRO CONTATO",
                "rota": "supermarket_encounter",
                "beat": "injury_check",
                "tipo": "fala",
                "conteudo": "Tem certeza que está tudo bem?",
                "ativo": "SIM",
            },
            {
                "ordem": 20,
                "cena": "PRIMEIRO CONTATO",
                "rota": "supermarket_encounter",
                "beat": "recognize_plaza",
                "tipo": "fala",
                "conteudo": "Você mora no Plaza?",
                "ativo": "SIM",
            },
        ]
    )

    prompt = engine.build_prompt(session, lines)

    assert session.current_route == "supermarket_encounter"
    assert session.current_beat == "injury_check"
    assert "Tem certeza que está tudo bem?" in prompt
    assert "Você mora no Plaza?" not in prompt


def test_story_engine_advances_to_next_beat() -> None:
    registry = StoryRegistry()
    registry.register(STORY)
    engine = StorySessionEngine(registry)
    session = engine.start("casada_frustrada")

    engine.advance(session)

    assert session.current_beat == "recognize_plaza"
    assert "injury_check" in session.completed_beats
