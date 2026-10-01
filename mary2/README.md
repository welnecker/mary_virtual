# Mary Core 2

Protótipo novo e enxuto para reconstruir Mary como personagem persistente,
sem árvores de decisão e sem o excesso de regras dos projetos anteriores.

## Princípios

- O usuário interpreta o marido.
- Mary mantém vontade própria.
- Amor, culpa, desejo, orgulho e medo podem coexistir.
- Segredos são revelados progressivamente.
- O LLM interpreta tensões psicológicas; o código não escolhe emoções por `if/else`.
- Memória recente e estado relacional são separados.
- O modelo pode ser trocado no laboratório sem alterar a personalidade-base.

## Rodar localmente

```powershell
cd mary2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Secret do OpenRouter

Crie localmente:

`.streamlit/secrets.toml`

com:

```toml
OPENROUTER_API_KEY = "sua-chave"
MARY_DEFAULT_MODEL = "openai/gpt-4.1-mini"
MARY_FALLBACK_MODEL = ""
```

Não versionar o arquivo real.

No Streamlit Community Cloud, cadastre as mesmas chaves em **App settings > Secrets**.

## Estrutura

- `app.py` — interface de laboratório.
- `prompts.py` — Mary Core, deliberadamente compacto.
- `state.py` — casamento, estado interno, verdades e segredos.
- `memory.py` — memória recente.
- `openrouter_client.py` — acesso isolado ao OpenRouter.

## Próximos passos naturais

1. Avaliar Mary por 30–50 turnos sem alterar o prompt no meio do teste.
2. Comparar modelos usando a mesma cena inicial.
3. Criar um extrator de fatos para promover acontecimentos importantes à memória longa.
4. Criar um mecanismo de revelação de segredos baseado em evidência e coerência, não em palavras-chave.
5. Persistir runs somente depois de a personalidade-base estar aprovada.
