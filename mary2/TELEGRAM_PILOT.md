# Mary Core 2 — integração de sub-roteiros Telegram pelo roteiro mãe

Branch experimental: agent/telegram-mary-pilot.
Código principal: mary2/app.py e mary2/telegram_pilot.py.
Não modifica as abas ou os textos autorais da planilha.

## Contrato do roteiro mãe

A coluna TELEGRAM de MINHA_SUGESTAO seleciona somente o sub-roteiro:

- Celular1, Celular2, ... → aba MARY_CELULAR, roteiros Celular1, Celular2, ...
- celular_rec1, celular_rec2, ... → aba MARY_CELULAR_RECEBIDO,
  roteiros Recebido1, Recebido2, ...

A numeração não representa ordem universal: é a ORDEM da linha
executada em MINHA_SUGESTAO que decide qual chamada ocorre em seguida.

A cena mãe define o interlocutor explicitamente quando Mary pega/atende o
celular. O adaptador extrai o nome da FALA-GUIA e da fala efetivamente
publicada, com fallback para DESCRIÇÃO-GUIA e PENSAMENTO-GUIA.
Se não identificar o personagem, sinaliza erro e mantém a linha bloqueada;
não presume Donisete nem qualquer outro.

A missão dramática da conversa, o sentimento, o contexto, as memórias, as
regras de orgulho ferido, os limites e a despedida são descritos pelo
roteiro secundário. A próxima linha de MINHA_SUGESTAO já contém a
continuidade autoral da história, e não deve ser inventada pelo Telegram.

## Mary ligando — CelularN

1. Mary publica sua linha mãe (AUTOMÁTICO ou BLOQUEADO).
2. O app resolve CelularN e envia a fala da linha 1 no Telegram.
3. A cena mãe fica travada; respostas seguintes alimentam linhas 2, 3 ...
4. O mesmo estado de progressão usado por direct_script marca cada linha.
5. Na última linha, se a FALA-GUIA tem ACEITE e RECUO, o classificador
   avalia a missão conforme a conversa inteira. RECUO bloqueia; ACEITE
   libera. Sem essas condições, a conclusão normal libera.
6. Depois da liberação, a cena mãe avança para sua próxima linha.

## Mary recebendo — celular_recN

1. Mary publica a cena que identifica o personagem que a está chamando.
2. O app resolve RecebidoN, valida sua existência e entra em WAITING,
   sem enviar fala ao Telegram nem chamar LLM.
3. Só uma mensagem NOVA do TELEGRAM_CHAT_ID autorizado, recebida depois
   desse gatilho, ativa a linha 1 de RecebidoN. Não precisa /mary.
4. Cada mensagem seguinte avança a linha secundária, sem modificar a mãe.
5. Depois da despedida e conclusão da última linha, o motor libera a mãe.
   ACEITE/RECUO seleciona apenas a fala condicional da última linha
   recebida; o retorno à mãe segue o acontecimento previamente escrito.
6. Em LOOP emocional esgotado, o retorno fica bloqueado. O painel permite
   reiniciar a chamada vigente, sem saltar a mãe.

## Garantias e restrições

- As chamadas não podem começar em qualquer momento; o estado idle não
  consulta Telegram e nem aceita /mary como gatilho espontâneo.
- Uma chamada por vez; as consecutivas têm estado, histórico, roteiro
  e identidade próprios. Nenhum sub-roteiro se inicia por ordem numérica
  implícita.
- A identidade de personagem é narrativa, definida pela linha mãe.
  TELEGRAM_CHAT_ID ainda autoriza apenas uma conta Telegram real.
- Nenhum modelo é chamado durante polling vazio (a cada 3 segundos)
  em WAITING/ACTIVE; as chamadas LLM são feitas ao processar mensagens.
- O app usa componentes compartilhados com o motor direto: carregamento
  de linhas, cursor, compreensão do usuário, Redator e Diretor Semântico.
  A avaliação emocional possui um adaptador Telegram próprio; ainda
  deve ser comparada com a implementação monolítica do Streamlit.
- Apenas texto. Monitor funciona enquanto a página Streamlit permanecer
  aberta e conectada. O estado está em st.session_state, sem transação
  persistente, recuperação garantida após restart ou isolamento
  multiusuário. Não é implantação permanente 24h.

## Testes

Regressões sem requisições reais: mary2/test_telegram_pilot.py.

Executar a partir da pasta mary2, com dependências instaladas:

    python -m unittest test_telegram_pilot -v

Verificações manuais recomendadas:

1. Cruzeiro Caribe4, linha 2 com Celular1: deve continuar iniciando a
   mensagem de Donisete, travar a cena e retornar apenas no desfecho.
2. Adicionar a um roteiro de teste do principal uma linha autoral com
   personagem explicitamente nomeado e TELEGRAM = celular_rec1:
   o app deve ficar em WAITING, sem enviar mensagem.
3. Após esse gatilho, escrever uma mensagem natural no Telegram:
   Recebido1 deve começar e responder ao personagem da linha mãe.
4. A última resposta de Recebido1 deve liberar a continuação autoral
   de MINHA_SUGESTAO, sem reiniciar o celular nem exigir /mary.
5. Testar Celular2 e celular_rec2 quando os respectivos sub-roteiros
   estiverem preenchidos; confirmar que nunca executam Celular1/Recebido1.
6. Enviar mensagem no Telegram fora de chamada ativa/pendente:
   não deve gerar resposta nem tokens.
7. Testar ORGULHO FERIDO, LOOP esgotado e reinício de tentativa.

Não criar linhas ou sub-roteiros fictícios automaticamente.
A alteração só produz resposta quando existem scripts autorais na planilha.
