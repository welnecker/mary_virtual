from relationship import (
    criar_estado_relacao_padrao,
    detectar_sinais_relacao,
    montar_resumo_estado_relacao,
    planejar_direcao_turno,
    planejar_iniciativa_mary,
)


state = criar_estado_relacao_padrao()

signals = detectar_sinais_relacao(
    user_text="Oi, cheguei.",
    mary_response="",
    interaction_count=0,
    has_image=False,
)

state, intent = planejar_iniciativa_mary(
    state,
    signals=signals,
)

state, direction = planejar_direcao_turno(
    state,
    signals=signals,
    turn_intent=intent,
)

print("SINAIS")
print(signals)

print("\nINTENÇÃO")
print(intent)

print("\nDIREÇÃO")
print(direction)

print("\nESTADO")
print(
    montar_resumo_estado_relacao(
        state
    )
)
