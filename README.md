# Mary Virtual

MVP em Streamlit para conversa multimodal com Mary usando texto e fotografias pelo OpenRouter.

## Recursos atuais

- Chat em Streamlit
- Upload de JPG, PNG e WebP
- Envio multimodal ao `google/gemini-3-flash-preview`
- Resposta somente em primeira pessoa, sem narração
- Histórico mantido durante a sessão
- Senha opcional do aplicativo

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Crie `.streamlit/secrets.toml` a partir do exemplo:

```toml
OPENROUTER_API_KEY = "sua-chave-openrouter"
MARY_APP_PASSWORD = "senha-opcional"
```

Execute:

```bash
streamlit run app.py
```

## Próximas etapas

1. Persistência no Google Sheets
2. Cânone da Mary
3. Memória relacional
4. Estado emocional e sexual persistente
5. Resumo estruturado das fotografias
