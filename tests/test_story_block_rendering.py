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


def test_preserva_pensamento_antes_da_fala_que_ele_prepara():
    text = (
        "Pensamento de Mary: Eu quero prolongar isso, mas preciso parecer casual.\n\n"
        "O mercado está bem cheio hoje, né?"
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks == [
        ("thought", "Eu quero prolongar isso, mas preciso parecer casual."),
        ("speech", "O mercado está bem cheio hoje, né?"),
    ]
    assert speech == "O mercado está bem cheio hoje, né?"


def test_preserva_pensamento_entre_duas_falas_na_ordem_logica():
    text = (
        "Pode responder o que for mais fácil, vai.\n\n"
        "Pensamento de Mary: Eu me adiantei e perguntei duas coisas de uma vez.\n\n"
        "Mas confesso que fiquei mais curiosa com o seu carrinho."
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks == [
        ("speech", "Pode responder o que for mais fácil, vai."),
        ("thought", "Eu me adiantei e perguntei duas coisas de uma vez."),
        ("speech", "Mas confesso que fiquei mais curiosa com o seu carrinho."),
    ]
    assert speech == (
        "Pode responder o que for mais fácil, vai. "
        "Mas confesso que fiquei mais curiosa com o seu carrinho."
    )


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
