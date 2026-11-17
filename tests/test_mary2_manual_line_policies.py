from unittest.mock import MagicMock, patch

from mary2.direct_script import load_direct_script_rows


def test_emotional_rules_are_per_line_and_suggestion_is_loaded():
    sheet = MagicMock()
    sheet.get_all_values.return_value = [
        ["ORDEM", "ROTEIRO", "FALA-GUIA", "PROMPT NEGATIVO", "ORGULHO FERIDO", "SUGESTAO", "PROSSEGUIR"],
        ["1", "Cruzeiro Caribe5", "Mary pergunta", "Não admitir deboche", "Mary se afasta", "Conte sobre Miami", ""],
        ["2", "Cruzeiro Caribe5", "Mary muda de assunto", "", "", "Sugestão local", ""],
        ["3", "Cruzeiro Caribe5", "Mary prossegue", "Regra da linha 3", "Reação 3", "Não exibir no automático", "automatico"],
        ["LOOP", "Cruzeiro Caribe5", "Mary pede respeito", "Limite LOOP", "Postura LOOP", "", ""],
    ]
    with patch("mary2.direct_script.gspread.service_account_from_dict") as service:
        service.return_value.open_by_key.return_value.worksheet.return_value = sheet
        rows = load_direct_script_rows(
            service_account_info={"test": True}, spreadsheet_id="sheet", worksheet_name="MINHA_SUGESTAO",
            script_name="Cruzeiro Caribe5",
        )

    assert len(rows) == 3
    assert rows[0]["negative_prompt"] == "Não admitir deboche"
    assert rows[0]["hurt_style"] == "Mary se afasta"
    assert rows[0]["user_suggestion"] == "Conte sobre Miami"
    assert rows[1]["negative_prompt"] == ""
    assert rows[1]["hurt_style"] == ""
    assert rows[1]["user_suggestion"] == "Sugestão local"
    assert rows[2]["negative_prompt"] == "Regra da linha 3"
    assert rows[2]["_emotional_loop_row"]["negative_prompt"] == "Limite LOOP"


def test_unaccented_and_accented_suggestion_headers_are_compatible():
    for header in ("SUGESTAO", "SUGESTÃO"):
        sheet = MagicMock()
        sheet.get_all_values.return_value = [
            ["ORDEM", "ROTEIRO", "FALA-GUIA", header],
            ["1", "Teste1", "Olá", "Pergunte sobre a viagem."],
        ]
        with patch("mary2.direct_script.gspread.service_account_from_dict") as service:
            service.return_value.open_by_key.return_value.worksheet.return_value = sheet
            rows = load_direct_script_rows(
                service_account_info={"test": True}, spreadsheet_id="sheet", worksheet_name="MINHA_SUGESTAO",
                script_name="Teste1",
            )
        assert rows[0]["user_suggestion"] == "Pergunte sobre a viagem."
