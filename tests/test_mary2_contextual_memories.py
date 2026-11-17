from unittest.mock import MagicMock, patch

from mary2.direct_script import (
    build_direct_writer_prompt,
    load_direct_info_boards,
    resolve_contextual_memories,
)


def test_board_loader_reads_both_columns_in_one_request():
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = [
        ["ROTEIRO", "QUADRO INICIAL", "MEMORIAS"],
        ["DeckPiscina1", "Boas-vindas", "Primeiro encontro\nLigação afetiva"],
        ["Cruzeiro Caribe2", "Cabine", ""],
    ]
    with patch("mary2.direct_script.gspread.service_account_from_dict") as service:
        service.return_value.open_by_key.return_value.worksheet.return_value = worksheet
        boards = load_direct_info_boards(service_account_info={"test": True}, spreadsheet_id="abc")
    assert boards["deckpiscina1"]["memorias"] == "Primeiro encontro\nLigação afetiva"
    assert boards["cruzeiro caribe2"]["memorias"] == ""
    worksheet.get_all_values.assert_called_once()


def test_multiple_memories_and_missing_references_do_not_break_style():
    boards = {
        "deckpiscina1": {"memorias": "Conheceu Donisete."},
        "cruzeiro caribe2": {"memorias": "Uma conversa\nna cabine."},
    }
    style, memory = resolve_contextual_memories(
        'Afetuosa — consulte "MEMORIAS-DeckPiscina1, Cruzeiro Caribe2, Desconhecido"', boards
    )
    assert style == "Afetuosa"
    assert memory.count("MEMÓRIA CANÔNICA") == 2
    assert "Uma conversa\nna cabine." in memory
    assert "Desconhecido" not in memory


def test_no_marker_means_no_memory_and_identical_style():
    assert resolve_contextual_memories("Nostálgica, divertida", {}) == ("Nostálgica, divertida", "")


def test_writer_receives_memory_as_past_not_current_mission():
    prompt = build_direct_writer_prompt(
        row={"order": 26, "speech_guide": "Comentar primeiro encontro", "style": "Nostálgica"},
        user_text="Lembra daquele dia?",
        contextual_memories="MEMÓRIA CANÔNICA DE DeckPiscina1\nDonisete ofereceu almoço.",
    )
    assert "Donisete ofereceu almoço." in prompt
    assert "A linha ativa e a memória instantânea governam o presente" in prompt
    assert "Estilo/atitude: Nostálgica" in prompt
    assert "consulte" not in prompt
