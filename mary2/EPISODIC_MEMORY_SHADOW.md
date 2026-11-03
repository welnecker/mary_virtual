# Etapa 1 — Memória episódica em observação (shadow mode)

Branch: `agent/episodic-memory-shadow-pilot`. Base: `0907863`.

## Implementado
- A aba `EPISODIC_MEMORY_AUDIT` na planilha MARY_CORE_PERSISTENCE registra observações por turno.
- Depois de `save_turn` concluir um turno `direct_sheet`, `app.py` seleciona evidências literais de interações passadas já presentes em `st.session_state.turn_records` e chama `save_episodic_memory_audit`.
- Não há alteração de prompt, de fala, de validação, da memória permanente ou de regras de avanço; falhas de auditoria são capturadas e não interrompem a resposta.
- A leitura acontece sobre o histórico já carregado na sessão: sem outra leitura de planilha, sem LLM adicional.
- Filtragem por `run_id`, `chapter_instance_id`, `branch_id`, sequência anterior e exclusão dos dois turnos recentes. Não consulta roteiro futuro.
- Resultado `NO_MATCH` é legítimo. Status `CANDIDATES` inclui somente trechos originais, não inferências.

## Como validar
1. Verificar que a implantação Streamlit está usando esta branch (não basta criar a branch no GitHub).
2. Executar um capítulo `direct_sheet` com algumas interações e retomar algum assunto antigo.
3. Consultar `EPISODIC_MEMORY_AUDIT`: linhas devem aparecer após cada turno salvo, mesmo com `NO_MATCH`.
4. Confirmar que as respostas de Mary permanecem idênticas em arquitetura e que não houve alteração em `MINHA_SUGESTAO` / `INTERACTIONS` além do fluxo normal.
5. Conferir `candidate_evidence_json` contra `INTERACTIONS`, usando `run_id`, `seq`, `chapter_instance_id` e `branch_id`.

## Testes locais
```bash
python -m unittest discover -s tests -p test_episodic_memory_shadow.py
python -m py_compile mary2/episodic_memory_shadow.py mary2/persistence.py mary2/app.py
```

**Validação pendente:** testes automatizados não executados neste ambiente (sem acesso de rede à clonagem GitHub). Nenhuma execução do app foi observada ainda.

## Limites
Este é um filtro lexical conservador, não um recuperador semântico. Trechos selecionados ainda não são entregues ao Redator e não há métrica real de economia de tokens. A promoção à etapa 2 exige revisão humana da precisão e do comportamento de não-recuperação.
