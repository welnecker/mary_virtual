# Mary Core 2 — sub-roteiro Telegram (Streamlit Cloud)

Implementação experimental na branch \`agent/telegram-mary-pilot\`, sem Render,
worker, webhook, banco adicional ou alteração da branch principal.

## Disparo pelo roteiro autoral

- A aba \`MINHA_SUGESTAO\` possui a coluna **TELEGRAM**.
- Exemplo confirmado na planilha: \`Cruzeiro Caribe4\`, ORDEM 2, **TELEGRAM = Celular1**.
- Depois da publicação e aprovação semântica da ORDEM 2 (automática),
  o Streamlit inicia uma única vez o roteiro \`Celular1\` da aba \`MARY_CELULAR\`.
- O cursor do roteiro principal não avança e sua entrada fica suspensa.
  O painel lateral mantém um fragmento Streamlit ativo, que consulta as mensagens
  automaticamente a cada 3 segundos enquanto a página estiver conectada.
  Há também um botão **Verificar agora**.
- Mary envia somente a fala aprovada pelo diretor. As próximas linhas do celular
  só avançam após a chegada de mensagens do \`TELEGRAM_CHAT_ID\` autorizado.
- A linha final classifica a última resposta do destinatário:
  **ACEITE** somente se houver concordância explícita com o encontro;
  **RECUO** em caso de negativa, hesitação ou ambiguidade. O prompt e a validação
  semântica recebem apenas a missão do ramo correspondente.
- **ACEITE:** conversa é concluída; o roteiro principal avança automaticamente
  para a ORDEM 3 de \`Cruzeiro Caribe4\`.
- **RECUO:** conversa termina; o roteiro principal fica bloqueado;
  o botão **Reiniciar Celular** inicia nova tentativa na linha 1.
- As memórias autorais continuam vindo das colunas de \`MARY_CELULAR\`,
  e o histórico da tentativa permanece somente em memória de sessão.
  Nenhuma memória narrativa nova ou resumo gerado é acrescentado à história.

## Preparação

1. Em \`@marycore2_bot\`, enviar \`/start\`; identificar o ID privado do chat.
2. Implantar o Streamlit Cloud a partir da branch \`agent/telegram-mary-pilot\`
   usando \`mary2/app.py\` como arquivo inicial.
3. Nos Secrets privados, manter as credenciais habituais e acrescentar
   \`TELEGRAM_BOT_TOKEN\` e \`TELEGRAM_CHAT_ID\`; não publicar o token.
4. Abrir \`Cruzeiro Caribe4\`; executar suas linhas automáticas 1 e 2.
   Depois da linha 2, o primeiro envio deve surgir no Telegram.
5. Responder no Telegram e clicar **Verificar respostas** no menu lateral
   a cada nova interação até a linha 5.
6. Testar separadamente ACEITE e RECUO em execuções reiniciadas.

## Limitações deste piloto

- O recebimento automático depende de a sessão Streamlit permanecer aberta
  e conectada ao servidor; não há serviço independente ou entrega garantida
  quando o navegador é fechado.
- \`getUpdates\` não deve ser consumido por outro processo do mesmo bot;
  não pode coexistir com webhook configurado.
- O cursor do Telegram, o histórico e o bloqueio da chamada ficam no
  \`st.session_state\`. **Um reinício do processo, outra sessão do navegador
  ou uma restauração incompleta podem perder a trava.** Não há recuperação
  transacional após reinício. Não considerar pronto para produção.
- A identificação da aprovação usa uma chamada adicional ao modelo
  classificador; classificação não reconhecida retém o avanço.
- O classificador aceita somente consentimento explícito; não garante
  uma avaliação perfeita de linguagem natural. Auditar o resultado nos testes.
- A falha de rede durante \`sendMessage\` é ambígua: a mensagem pode ter
  sido entregue sem confirmação ao aplicativo. A tela mantém o estado de erro
  e não dispara automaticamente de novo.
- O gatilho está integrado às linhas automáticas do roteiro direto.
  Outros modos de interação precisarão de integração específica.
- O piloto pressupõe uma sessão privada e um destinatário autorizado.
  Não é seguro como bot multiusuário sem persistência e isolamento.
