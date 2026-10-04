from sheet_script import build_line_prompt, line_for_interaction, script_line
from chapters import get_chapter


def test_carona_uses_sheet_line_runtime_only():
    chapter = get_chapter("carona_camburi")
    assert chapter["script_mode"] == "sheet_line_runtime"
    assert chapter["script_name"] == "Carona"
    assert not chapter.get("dramatic_phases")
    prompt = chapter.get("prompt", "")
    assert "Clube Náutico" not in prompt
    assert "balada eletrônica" not in prompt


def test_carona_opening_consumes_first_authored_line():
    assert line_for_interaction(chapter_turn=1, opening_consumes_line_one=True) == 2
    assert line_for_interaction(chapter_turn=12, opening_consumes_line_one=True) == 13


def test_only_selected_line_is_exposed_to_prompt():
    rows = [
        {"order": 2, "speech_guide": "trânsito", "writer_limits": "não falar da balada"},
        {"order": 6, "speech_guide": "Clube Náutico", "released_fact": "balada eletrônica"},
    ]
    current = script_line(rows, 2)
    prompt = build_line_prompt(current, line_order=2)
    assert "trânsito" in prompt
    assert "Clube Náutico" not in prompt
    assert "balada eletrônica" not in prompt


def test_interpreted_line_preserves_semantic_core():
    row = {
        "order": 6,
        "type": "INTERPRETADA",
        "speech_guide": "já ouviu falar do Clube Náutico?",
        "semantic_core": (
            "Mary CONHECE o Clube Náutico; Mary SABE da balada; "
            "não está descobrindo o lugar."
        ),
        "writer_limits": "Não transformar conhecimento em dúvida.",
    }
    prompt = build_line_prompt(row, line_order=6)
    assert "FALA-GUIA é direção dramática, não texto literal" in prompt
    assert "Mary CONHECE o Clube Náutico" in prompt
    assert "Não transformar conhecimento em dúvida" in prompt
