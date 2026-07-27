from ui.sidebar_rollback_and_thought_style import _separar_resposta_mary


def test_mantem_apenas_fala_e_pensamento_em_primeira_pessoa():
    text = (
        "Vou cobrar essa promessa, hein?\n\n"
        "Pensamento de Mary: Eu não queria entrar no carro e ir embora agora.\n\n"
        "Olha, seria bom ter seu contato."
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks == [
        ("speech", "Vou cobrar essa promessa, hein?"),
        ("thought", "Eu não queria entrar no carro e ir embora agora."),
        ("speech", "Olha, seria bom ter seu contato."),
    ]
    assert speech == "Vou cobrar essa promessa, hein? Olha, seria bom ter seu contato."


def test_descarta_ponte_de_cena_da_tela_e_da_voz():
    text = (
        "Chegamos ao carro.\n"
        "Ponte de cena: Mary encosta suavemente no carro e olha para você.\n"
        "Foi muito bom te conhecer."
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks == [
        ("speech", "Chegamos ao carro."),
        ("speech", "Foi muito bom te conhecer."),
    ]
    assert "Mary encosta" not in speech


def test_descarta_narracao_explicita_em_terceira_pessoa():
    text = (
        "Eu gostei da sua companhia.\n"
        "Mary mexe distraidamente na alça da bolsa e olha para o chão.\n"
        "Queria continuar falando com você."
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks == [
        ("speech", "Eu gostei da sua companhia."),
        ("speech", "Queria continuar falando com você."),
    ]
    assert "Mary mexe" not in speech
