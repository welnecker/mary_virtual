# Piloto: memória episódica contextual (shadow mode)

Base: `agent/emotional-voice-integration-pilot` @ `0907863`.

Este piloto **não altera os prompts, o estado, a persistência nem os logs da aplicação**. O módulo
`mary2/episodic_memory_shadow.py` recebe registros já armazenados em `INTERACTIONS` e
retorna até três evidências literais para inspeção offline.

## Limites de segurança
- Filtra `run_id`, `chapter_instance_id`, `branch_id` e `seq < before_seq`.
- Descarta por padrão as duas interações mais recentes, pois já estão no contexto imediato.
- Só considera pares usuário/Mary completos e palavras presentes na fala atual.
- Não lê linhas futuras do roteiro; não reinterpreta as falas; não consolida fatos.
- Não faz chamadas de LLM nem adiciona tokens ao Redator enquanto estiver desativado.
- Pode retornar zero candidatos, o que é deliberado.

## Teste
```bash
python -m unittest discover -s tests -p test_episodic_memory_shadow.py
```

## Próximo passo (não implementado)
Comparar candidatos contra o contexto já enviado ao Redator e contra os eventos
`direct_conversation_state`. Somente após medir precisão, duplicação e tokens,
considerar um toggle opt-in e registrar auditoria em aba própria. Este piloto
lexical não equivale a recuperação semântica e não deve ser habilitado em produção.
