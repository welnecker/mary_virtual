# Piloto Mary Core 2 — Telegram (manual, sem Render)

Esta branch preserva o motor da aplicação e acrescenta `mary2/telegram_pilot.py`, acionado no sidebar em `mary2/app.py`.

## Pré-requisitos

- Criar e iniciar o bot do Telegram `@marycore2_bot` com `/start` (já feito no Telegram).
- Implantar **um novo app Streamlit Community Cloud** a partir desta branch, com o mesmo arquivo principal `mary2/app.py` e demais Secrets já usados pelo Mary Core 2.
- Adicionar `TELEGRAM_BOT_TOKEN` aos **Secrets do novo app**, nunca ao GitHub, chat, planilha ou logs.
- Após abrir o app, usar **Identificar chat Telegram**. Se necessário, enviar uma nova mensagem ao bot e clicar novamente. Registrar somente o ID privado do usuário autorizado em `TELEGRAM_CHAT_ID` nos Secrets. Reiniciar o novo app para carregar a alteração.
- A conta de serviço Google já usada deve ter permissão de leitura da planilha `MARY_CORE_PERSISTENCE`, cuja aba `MARY_CELULAR` contém `ROTEIRO=Celular1`.

Exemplo de Secrets a ACRESCENTAR ao piloto (substitua os valores apenas no painel privado do Streamlit):

```toml
TELEGRAM_BOT_TOKEN = "token_obtido_no_botfather"
TELEGRAM_CHAT_ID = "id_telegram_do_seu_chat"
```

As demais configurações, como `OPENROUTER_API_KEY`, `MARY_SHEETS_ID`, `GOOGLE_CREDS_JSON` e `MARY_ACCESS_PASSWORD`, continuam necessárias.

## Funcionamento do piloto

1. Clique em **Telegram — Chamar**: motor interpreta a linha 1 e envia a fala após validação semântica.
2. Responda pelo Telegram.
3. Clique em **Verificar respostas** no Streamlit: motor usa a linha seguinte e envia a nova fala.
4. Repita para a terceira linha. Depois, encerra-se o roteiro.
5. **Reiniciar piloto Telegram** limpa somente o estado local do piloto, sem remover mensagens entregues nem reiniciar a história principal.

## Limitações conhecidas

- Não há mensagens espontâneas, recepção automática em background, ping nem webhook.
- O estado `index/history/offset` fica na sessão Streamlit do navegador e **não é persistente**. Refresh, desconexão, troca de sessão ou reinício da instância podem perder o progresso.
- Os dados não são isolados por usuário em armazenamento persistente; use somente em implantação de acesso restrito e com `TELEGRAM_CHAT_ID` do destinatário pretendido.
- O recebimento via `getUpdates` pressupõe que não exista webhook instalado para o bot e que nenhum outro processo consuma os mesmos updates.
- Ao ocorrer falha do diretor, não envia a mensagem; mensagens não aprovadas não devem avançar a linha.
- Não execute esse piloto como um sistema multiusuário ou um bot sempre ativo.
- O piloto emite **somente falas**. Pensamento e ação são internos.
- Se houver edições autorais na aba, os novos valores serão lidos na próxima interação.
- Não foi validado o envio real até que o token e o chat ID sejam configurados no Streamlit Cloud.

## Contrato da planilha

Aba `MARY_CELULAR`, colunas idênticas à `MINHA_SUGESTAO`; usa o leitor `load_direct_script_rows` com roteiro `Celular1`. Memórias globais e memória física da linha 1 propagam-se às linhas seguintes pelo leitor existente. A memória instantânea é local da linha.

## Segurança

Nunca cole o token do BotFather em conversas, planilhas, arquivos commitados ou tickets. Se ele vazar, regenere-o pelo BotFather antes de usar o piloto.
