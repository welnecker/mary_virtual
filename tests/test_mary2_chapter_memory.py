from mary2.chapter_memory import build_recent_memory_prompt, parse_recent_memory, recent_memory_text
from mary2.state import migrate_state


def test_recent_memory_prompt_uses_completed_chapter_dialogue_without_raw_protocol():
    prompt = build_recent_memory_prompt(
        source_chapter_id="academia_suco_aceito",
        records=[
            {"user_text": "Me chamo Rafael.", "mary_text": "Prazer, Rafael."},
            {"user_text": "Gosto de liberdade.", "mary_text": "Isso combina com você."},
        ],
        structural_facts=["Mary está separada de Janio."],
    )
    assert "Me chamo Rafael." in prompt
    assert "Gosto de liberdade." in prompt
    assert "Mary está separada de Janio." in prompt
    assert "ROTEIRO_STATUS" not in prompt


def test_recent_memory_parser_keeps_only_known_groups_and_lists():
    memory = parse_recent_memory(
        '{"facts":["Mary conheceu Rafael."],'
        '"about_user_character":["Rafael valoriza liberdade."],'
        '"mary_perceptions":["Mary gostou da franqueza dele."],'
        '"references":[],'
        '"open_items":["Ainda nao combinaram a noite."],'
        '"do_not_assume":["Nao assumir reciprocidade."],'
        '"extra":["ignorar"]}'
    )
    assert memory["facts"] == ["Mary conheceu Rafael."]
    assert "extra" not in memory
    assert memory["do_not_assume"] == ["Nao assumir reciprocidade."]


def test_recent_memory_text_is_summary_not_dialogue_replay():
    text = recent_memory_text({
        "facts": ["Mary conheceu Rafael na academia."],
        "about_user_character": ["Rafael valoriza liberdade."],
        "mary_perceptions": [],
        "references": [],
        "open_items": [],
        "do_not_assume": [],
    })
    assert "MEMORIA RECENTE DA EXECUCAO" in text
    assert "Mary conheceu Rafael na academia." in text
    assert "USUARIO:" not in text
    assert "MARY:" not in text


def test_recent_memory_survives_state_migration_reload():
    state = {
        "narrative": {
            "chapter_id": "carona_camburi",
            "recent_memory_source_chapter": "academia_suco_aceito",
            "recent_memory": {
                "facts": ["Mary conheceu Rafael na academia."],
                "about_user_character": [],
                "mary_perceptions": [],
                "references": [],
                "open_items": [],
                "do_not_assume": [],
            },
        },
        "current_status": {},
        "story_ledger": [],
    }
    restored = migrate_state(state)
    assert restored["narrative"]["recent_memory_source_chapter"] == "academia_suco_aceito"
    assert restored["narrative"]["recent_memory"]["facts"] == [
        "Mary conheceu Rafael na academia."
    ]
