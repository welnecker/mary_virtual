# Capítulos modulares — piloto

## Objetivo

O Mary Core usa um prompt-base permanente para a personalidade de Mary e injeta
somente o prompt do capítulo atualmente ativo.

A sequência enviada ao modelo é:

1. `MARY_CORE` — personalidade e regras permanentes;
2. `STORY_BIBLE` — fatos estruturais do universo;
3. `chapter_prompt(chapter_id)` — contexto exclusivo do capítulo atual;
4. estado estrutural compacto;
5. memória canônica resumida;
6. cena atual;
7. últimas interações do capítulo.

Ao trocar de capítulo, o histórico anterior continua na planilha, porém deixa de ser
usado como contexto recente. O modelo recebe o novo capítulo, a memória consolidada
e a nova cena.

## Onde ficam os capítulos

Arquivo:

`mary2/chapters.py`

Cada item de `CHAPTERS` contém:

- `title`: nome mostrado na tela;
- `prompt`: instruções exclusivas daquele capítulo;
- `decision_after_turns`: mínimo de interações antes de liberar decisões;
- `choices`: botões disponíveis;
- `opening_caption`: abertura narrativa mostrada na tela;
- `opening_mary`: primeira fala de Mary;
- `initial_scene`: estado inicial da nova cena.

## Piloto

### confissao_inicial — A Confissão

Depois de 3 interações, libera:

- **Romper** → `pos_rompimento`
- **Tentar reconciliar** → `pos_reconciliacao`

O valor 3 é propositalmente curto para teste. Em produção pode ser aumentado.

### pos_rompimento — O dia seguinte

A tela abre já com Mary sozinha no apartamento e ligando para Silvia.
Silvia é criada como `PERSONAGEM_DA_CENA`, permitindo ao usuário assumir seu papel.

### pos_reconciliacao — A manhã da reconciliação

A tela abre na manhã seguinte à decisão do casal permanecer junto.
O prompt deixa de tratar a confissão como assunto obrigatório e passa a privilegiar
vida conjugal, confiança, desejo, rotina, humor, conflitos e novas situações.

## Como criar uma nova decisão

Dentro do capítulo de origem:

```python
"choices": [
    {
        "id": "aceitar_encontro",
        "label": "Aceitar encontro",
        "next_chapter": "primeiro_encontro",
    },
    {
        "id": "recusar_encontro",
        "label": "Recusar",
        "next_chapter": "seguir_rotina",
    },
]
```

Depois, basta criar os capítulos `primeiro_encontro` e `seguir_rotina` no mesmo
arquivo.

O app cria os botões automaticamente. Não é necessário alterar a interface para
cada nova escolha.

## Princípio

O roteiro determina **em qual fase da vida Mary está**.
O LLM determina **como Mary vive e fala dentro dessa fase**.
O usuário determina **os rumos importantes pelos botões e pelas interações livres**.
