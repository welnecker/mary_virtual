"""§SOM§ cues remain independent from the reserved FALA GRAVADA transcript."""
from mary2.direct_script import DIRECT_HEADERS, inline_sounds_from_guide, build_direct_writer_prompt
from mary2.output_filter import parse_mary_components


def _prompt(guide, recorded_speech=""):
    return build_direct_writer_prompt(
        row={"order": 4, "speech_guide": guide, "recorded_speech": recorded_speech},
        user_text="Olá!", recent_messages=[],
    )


def test_inline_sounds_follow_authored_order_without_duplicate():
    guide = "Interpretar: Mary se assusta §GASP!!!§, depois ri §HA! HA!§."
    assert inline_sounds_from_guide(guide) == ["GASP!!!", "HA! HA!"]
    prompt = _prompt(guide, recorded_speech="Uma fala gravada que não deve entrar no prompt.")
    assert "SONS AUTORAIS INLINE" in prompt
    assert "Onomatopeia contextual:" not in prompt
    assert prompt.index("§GASP!!!§") < prompt.index("§HA! HA!§")


def test_recorded_speech_header_is_reserved_not_sent_to_writer():
    assert DIRECT_HEADERS["fala gravada"] == "recorded_speech"
    assert "onomatopeia" not in DIRECT_HEADERS
    prompt = _prompt("Interpretar: Mary ri de surpresa.", recorded_speech="Uma fala gravada reservada.")
    assert "Uma fala gravada reservada." not in prompt
    assert "SONS AUTORAIS INLINE" not in prompt


def test_parentheses_are_not_sounds_and_unclosed_marker_is_ignored():
    assert inline_sounds_from_guide("Interpretar: ela sorri (sem malícia).") == []
    assert inline_sounds_from_guide("Interpretar: ela sorri §HA!") == []
    assert inline_sounds_from_guide("Interpretar: §GASP!!!§ e §gasp!!!§") == ["GASP!!!"]


def test_editorial_delimiters_are_removed_in_all_channels():
    parts = parse_mary_components(
        "[AÇÃO] Mary derruba o livro.\n[FALA] Mary: §GASP!!!§ Que susto!"
    )
    assert parts["action"] == "Mary derruba o livro."
    assert parts["speech"] == "Mary: GASP!!! Que susto!"
