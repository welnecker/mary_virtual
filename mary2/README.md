# Mary Core 2

Protótipo enxuto de novela interativa com Mary, Janio e Ricardo.

## Arquitetura

- `story_bible.py` — relações e enredo-base.
- `director.py` — tempo, lugar, presença e progressão de cena.
- `input_router.py` — separa direção de cena de fala do personagem.
- `prompts.py` — personalidade e voz da Mary.
- `memory_engine.py` — consolida memória canônica.
- `persistence.py` — salva e retoma runs no Google Sheets.
- `state.py` — estado relacional e impulso de redenção.
- `openrouter_client.py` — acesso ao OpenRouter.
- `app.py` — interface Streamlit.

## Persistência

A persistência usa uma planilha Google com duas abas:

### STORY_RUNS

Guarda o snapshot atual de cada história:

- `run_id`
- `player_id`
- `status`
- `created_at`
- `updated_at`
- `last_seq`
- `active_user_role`
- `canonical_memory`
- `scene_json`
- `story_state_json`

### INTERACTIONS

Guarda o histórico dos turnos:

- `run_id`
- `seq`
- `created_at`
- `user_role`
- `scene_direction`
- `scene_caption`
- `user_text`
- `mary_text`

Ao abrir o app, a última run ativa do jogador é restaurada automaticamente.
São reidratados o estado da cena, a memória canônica e as últimas 30 interações.

O botão **Nova história** arquiva a run ativa anterior e cria outra.

## Google Sheets

O app pode criar automaticamente a planilha `MARY_CORE_PERSISTENCE`.
Não é obrigatório informar um spreadsheet ID.

No Streamlit Secrets:

```toml
MARY_SHEETS_ID = ""
MARY_SHEETS_TITLE = "MARY_CORE_PERSISTENCE"
MARY_PLAYER_ID = "janio"
MARY_SHEETS_OWNER_EMAIL = ""

[GOOGLE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "seu-projeto"
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
"""
client_email = "conta@seu-projeto.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Se `MARY_SHEETS_OWNER_EMAIL` for informado, o app tenta compartilhar a planilha criada com esse e-mail como editor.

Nunca versionar a credencial real.

## OpenRouter

```toml
OPENROUTER_API_KEY = "sua-chave"
MARY_DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
MARY_FALLBACK_MODEL = ""
MARY_MEMORY_MODEL = ""
MARY_DIRECTOR_MODEL = ""
MARY_INPUT_MODEL = ""
```

## Rodar localmente

```powershell
cd mary2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Direção livre

O usuário pode falar ou dirigir a cena em linguagem natural.

Exemplos:

```text
No dia seguinte, Mary acorda primeiro, vendo Janio dormir.
```

```text
No estacionamento do trabalho, já no fim da tarde, Janio entra no carro.
"Mary... você pode falar agora?"
```

O sistema separa direção de cena e diálogo antes de gerar a reação da Mary.

### Reinício de capítulo e cota de leitura

O reinício restaura o checkpoint de entrada e grava uma nova instância do capítulo,
sem apagar as interações anteriores. A conexão, os cabeçalhos validados e os
checkpoints carregados são reutilizados no processo, separados por credenciais e
planilha. A lista de checkpoints tem atualização de 30 segundos e conserva a
última leitura válida quando o Sheets retorna 429; checkpoints conhecidos são
imutáveis e podem ser restaurados diretamente da cópia carregada.

STORY_RUNS e STORY_CHECKPOINTS devem permanecer como registros de acréscimo:
não ordenar nem remover fisicamente suas linhas durante a execução do app.
Após manutenção estrutural manual, reinicie o processo para renovar os índices.
O cache não substitui o armazenamento: após um reinício do servidor, a primeira
leitura depende do Sheets. Falhas de leitura sem cópia válida e falhas de escrita
continuam sendo informadas. A conversa local só é substituída após a confirmação
da gravação do novo snapshot; created_at e last_seq não são regravados no restart.

Validação: `python -m pytest -q tests/test_mary2_restart_persistence.py`.


### Carona para Camburi — v39

A escolha **Dar carona para Mary** abre quatro fases de quatro turnos:
carro e rota, sábado e convite, trânsito e chegada, combinação e despedida.
Após 16 turnos, o fechamento ainda depende de chegada, carro parado e despedida
concretamente estabelecidos; caso contrário, a convergência continua.

A apresentação do personal é preservada por falas-fonte da lanchonete em
`current_status.personal_conversation_reference`. Não há nome fixo, extração
por expressão regular nem chamada extra ao modelo. Essa referência entra no
contexto do Diretor e de Mary por STATUS ATUAL e sobrevive à persistência.
As falas são fontes atribuídas, não fatos inventados ou metas do capítulo antigo.
Ao reabrir uma decisão anterior à v39, a referência é reconstruída das interações
da instância original, até a sequência do checkpoint; outras rotas não entram.

O capítulo termina na entrada **Mary em seu apartamento**, ainda sem roteiro
próprio. O contexto preserva a apresentação e os pares de oferta/resposta da
carona. Não grava aceitação da balada ou horário como fato fixo. O horário das
20 horas é uma proposta ficcional para o mesmo sábado, antes desse horário.

Validação: `python -m pytest -q tests/test_mary2_carona.py tests/test_mary2_restart_persistence.py`.
