# Arquitetura modular por capítulos — piloto

## Princípio

Cada capítulo é um contexto independente.

Ao encerrar um capítulo:
- o prompt daquele capítulo deixa de existir;
- a cena anterior deixa de existir;
- as interações recentes anteriores deixam de ser enviadas ao LLM;
- somente fatos estruturais escolhidos pelo roteiro passam ao `story_ledger`;
- o `current_status` é atualizado deterministicamente;
- o próximo capítulo começa com prompt e cena próprios.

Não existe memória emocional automática entre capítulos neste piloto.

## Prompt enviado à Mary

A montagem atual é:

1. `PHYSICAL_CANON`
2. `story_ledger`
3. `current_status`
4. prompt do capítulo atual
5. cena atual
6. interações recentes somente do capítulo atual

### Canon físico

Arquivo: `mary2/story_bible.py`

Contém somente características físicas permanentes de Mary.
Não contém casamento, traição, culpa, amor, reconciliação, estado civil ou objetivos.

### Story ledger

Fica em `story_state["story_ledger"]`.

É uma lista acumulativa de fatos estruturais de capítulos encerrados.
No piloto, somente escolhas por botão escrevem no ledger.

Exemplo após escolher reconciliação:

- Mary confessou a Janio que o traiu com Ricardo.
- Após a confissão, Mary e Janio decidiram tentar permanecer juntos.

### Current status

Fica em `story_state["current_status"]`.

Representa somente a situação estrutural válida agora, por exemplo:

```json
{
  "relationship_status": "casada com Janio",
  "living_situation": "vive com Janio",
  "relationship_with_janio": "reconciliação em curso"
}
```

Ao contrário do ledger, o status pode ser substituído por escolhas futuras.

## Capítulos

Arquivo: `mary2/chapters.py`

Cada capítulo define:

- `title`
- `allowed_roles`
- `prompt`
- `decision_after_turns`
- `choices`
- `opening_caption`
- `opening_mary`
- `initial_scene`

Cada escolha pode definir:

- `next_chapter`
- `ledger_entries`
- `status_updates`

O app cria os botões automaticamente.

## Piloto atual

### A Confissão

Após 3 interações:

- **Romper**
- **Tentar reconciliar**

### Romper → O dia seguinte

A escolha grava no ledger que houve a confissão e a separação.
O status passa para separada.
O prompt anterior é descartado.
O usuário assume Silvia no novo capítulo.

### Tentar reconciliar → A manhã da reconciliação

A escolha grava no ledger a confissão e a decisão de permanecer juntos.
O status passa para reconciliação em curso.
O prompt anterior é descartado.
O usuário continua como Janio.

## Memória automática

`memory_engine.py` não participa do fluxo normal deste piloto.

Isso é proposital. Primeiro validamos isolamento real entre capítulos.
Depois, se necessário, uma memória livre poderá ser reintroduzida para registrar
somente fatos emergentes que o roteiro não conhecia, sem controlar estado emocional
ou objetivos do capítulo.
