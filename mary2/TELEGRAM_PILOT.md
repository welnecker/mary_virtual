# Mary Core 2 — roteiro celular, iniciador e recebido (piloto)

Branch isolada: agent/telegram-mary-pilot. Apenas Streamlit Cloud,
sem Render, webhook, Supabase ou alteração da branch principal.

## Planilhas verificadas

Planilha MARY_CORE_PERSISTENCE:

- MINHA_SUGESTAO: coluna TELEGRAM = Celular1 em Cruzeiro Caribe4, linha 2.
- MARY_CELULAR: roteiro Celular1, ORDEM 1–5 + LOOP.
- MARY_CELULAR_RECEBIDO: roteiro Recebido1, ORDEM 1–5 + LOOP.

Os dois roteiros Telegram têm os mesmos 17 cabeçalhos de controle:
FALA-GUIA, PENSAMENTO-GUIA, PROSSEGUIR, PROMPT NEGATIVO, ORGULHO FERIDO,
memórias e a linha especial LOOP. Não são modificados pelo adaptador.

## Fluxo A — Mary chama Donisete

1. Executar Cruzeiro Caribe4, linhas 1 e 2 no Streamlit.
2. Depois da linha 2 aprovada, o gatilho TELEGRAM ativa Celular1.
3. Streamlit suspende a progressão do roteiro principal.
4. Mary envia a primeira mensagem, interpreta as respostas seguintes,
   e avança usando o estado do roteiro direto.
5. Na última linha, ACEITE confirma encontro e libera a linha 3;
   RECUO encerra a tentativa, mantendo a cena suspensa.
6. Depois que o roteiro principal avança com sucesso, o bot volta
   a ficar disponível para uma nova chamada recebida.

## Fluxo B — Donisete chama Mary

1. Deixar o Streamlit aberto com o Telegram em estado disponível
   (sem Celular1 ou Recebido1 ativos).
2. Enviar mensagem comum como "Oi, Mary!" ou comando /mary ao bot.
3. O monitor identifica a mensagem do TELEGRAM_CHAT_ID autorizado.
4. A aba MARY_CELULAR_RECEBIDO, roteiro Recebido1, é carregada;
   a mensagem original é entregue à linha 1 com memórias autorais.
5. Cada nova mensagem de Donisete alimenta a próxima linha, sem
   alterar a ORDEM de MINHA_SUGESTAO.
6. A última linha de Recebido1 encerra a sessão do Telegram.
   Mensagens tardias são consumidas sem resposta, para impedir reinício em loop.
   Somente o comando /mary inicia outra chamada após o encerramento.
7. Se entrar no LOOP, as tentativas seguem a orientação da linha
   especial e o estado normal fica suspenso até reparação ou exaustão.

## Compartilhamento de contratos com o motor original

Reutilizados: load_direct_script_rows, ensure_direct_state,
register_direct_user_reply, current_direct_row, mark_direct_line_emitted,
build_direct_writer_prompt, hurt_loop_max_interactions,
analyze_user_understanding, validate_direct_semantic_turn e filtros de fala.

Os critérios autorais de ORGULHO FERIDO e LOOP são avaliados no
adaptador Telegram. A classificação emocional do piloto ainda não
compartilha literalmente a mesma função interna monolítica de app.py.
O resultado precisa de auditoria comparativa em casos reais antes de
ser considerado semanticamente idêntico ao motor Streamlit.
Nenhuma memória narrativa nova é adicionada à história principal.

## Testes

Arquivo de testes com mocks: mary2/test_telegram_pilot.py.

Com dependências instaladas, executar da pasta mary2:

    python -m unittest test_telegram_pilot -v

No aplicativo Streamlit Cloud:

- Teste A1: clique Prosseguir em Caribe4 até a linha 2; Mary
  deve enviar linha 1 no Telegram automaticamente.
- Teste A2: responda quatro vezes, confirmando o encontro na última;
  a linha 3 de Caribe4 deve ser liberada.
- Teste A3: reinicie o roteiro e recuse na última resposta; a
  linha 3 não deve ser liberada.
- Teste B1: depois da liberação, envie "Oi, Mary!" ao bot; Recebido1
  deve começar pela linha 1 e continuar até a despedida.
- Teste B2: em uma nova tentativa, envie uma mensagem que contrarie
  explicitamente PROMPT NEGATIVO; confira a entrada no LOOP e a
  eventual reparação ou encerramento após o limite autoral.
- Teste B3: confira que Recebido1 não avançou MINHA_SUGESTAO.

## Limitações

- Somente mensagens de texto e apenas TELEGRAM_CHAT_ID autorizado.
- O monitor usa st.fragment a cada 3 segundos enquanto Streamlit
  estiver aberto e conectado; não é um daemon independente.
- No início de uma nova sessão, mensagens anteriores ao offset de
  inicialização são desconsideradas, para não acionar chamadas antigas.
- A sessão é mantida em st.session_state, sem persistência transacional.
  Reiniciar o Streamlit pode perder estados de chamada e bloqueio.
  Não indicado para multiusuário ou para produção sem serviço receptor.
- O mesmo bot não deve ter outro consumidor de getUpdates nem webhook.
- Erros de rede durante sendMessage podem ser ambíguos. Verificar
  a conversa no Telegram antes de repetir manualmente.
- A classificação de ACEITE/RECUO e a emoção dependem de LLM; testar
  respostas ambíguas, reparações e limites explícitos por linha.
- A linha LOOP não altera o roteiro principal em chamadas recebidas.
