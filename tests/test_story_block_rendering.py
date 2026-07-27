from ui.sidebar_rollback_and_thought_style import _separar_resposta_mary


def test_separa_fala_ponte_e_fala_sem_misturar_voz():
    text = (
        "Pois é, até que deu sorte. O mercado tá bem cheio hoje.\n\n"
        "Enquanto você começa a colocar suas coisas na esteira, eu fico ali do lado, "
        "esperando a minha vez, mas sem pressa de sair.\n\n"
        "Você me espera? Acho que vou precisar de uma ajudinha até o carro."
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks == [
        ("speech", "Pois é, até que deu sorte. O mercado tá bem cheio hoje."),
        (
            "bridge",
            "Enquanto você começa a colocar suas coisas na esteira, eu fico ali do lado, "
            "esperando a minha vez, mas sem pressa de sair.",
        ),
        ("speech", "Você me espera? Acho que vou precisar de uma ajudinha até o carro."),
    ]
    assert "Enquanto você começa" not in speech
    assert "Pois é, até que deu sorte" in speech
    assert "Você me espera?" in speech


def test_rotulos_explicitos_separam_ponte_e_pensamento():
    text = (
        "Ponte de cena: Alguns minutos depois, Mary chega ao carro.\n"
        "Pensamento de Mary: Tomara que ele tenha percebido meu interesse.\n"
        "Chegamos... vou abrir o porta-malas."
    )

    blocks, speech = _separar_resposta_mary(text)

    assert blocks[0] == ("bridge", "Alguns minutos depois, Mary chega ao carro.")
    assert blocks[1] == (
        "thought",
        "Tomara que ele tenha percebido meu interesse.",
    )
    assert blocks[2] == ("speech", "Chegamos... vou abrir o porta-malas.")
    assert speech == "Chegamos... vou abrir o porta-malas."
