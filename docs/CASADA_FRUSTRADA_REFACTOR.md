# Casada Frustrada — plano de refatoração orientado pelo roteiro

## Objetivo

Tornar `immersive_screenplay.py` a linha mestra da história, com progressão previsível, sem repetição, retrocesso ou salto de etapas.

A reconstrução será feita somente nesta branch. A branch `main` permanece congelada na base estável `b9123881059a9dc7f3e1194bcca4a9c327806f3b` até que o fluxo completo seja testado.

## Princípio central

Mary não cria a sequência da história. Mary interpreta o trecho atual do roteiro.

O motor precisa responder somente a quatro perguntas:

1. Qual trecho do roteiro está ativo?
2. Mary já interpretou esse trecho?
3. A resposta do usuário satisfaz a condição necessária?
4. Qual é o próximo trecho definido pelo próprio roteiro?

## Fonte única de verdade

### Conteúdo narrativo

`immersive_screenplay.py`

Responsável por:

- texto canônico;
- ordem das falas e ações;
- identificação de cada trecho;
- condição de conclusão quando necessária;
- referência ao próximo trecho.

Nenhum outro arquivo pode conter uma segunda versão das falas, objetivos narrativos ou sequência.

### Cursor único

`instance["scene_state"]["current_beat"]`

Responsável exclusivamente por indicar o trecho pendente.

`instance["current_beat"]` será removido ou transformado em valor derivado, nunca em segunda fonte persistida.

## Responsabilidade dos arquivos

| Arquivo ou estado | Decisão | Responsabilidade final |
|---|---|---|
| `immersive_screenplay.py` | Manter e ampliar | Roteiro executável completo e fonte textual única |
| `canonical_screenplay.py` | Absorver ou remover | Não deve duplicar falas; pode desaparecer se o roteiro já expuser os beats diretamente |
| `beat_graph.py` | Absorver ou remover | Não deve duplicar ordem já registrada no roteiro |
| `story_director.py` | Substituir | Classificar somente a resposta atual e decidir manter/avançar/encerrar |
| `progression_guard.py` | Remover | Monkeypatch e segundo mecanismo de progressão |
| `story_sync.py` | Retirar do fluxo normal | Apenas ferramenta opcional de migração de sessões antigas |
| `screenplay_executor.py` | Reduzir ou remover | Não terá motor especial para motel; somente validação contratual, caso necessária |
| `canonical_memory.py` | Manter como auxiliar | Guardar fatos permanentes; nunca escolher rota ou beat |
| `visual_state` | Manter como auxiliar | Guardar continuidade física; nunca escolher rota ou beat |
| `scene_state` | Manter | Contexto da sessão e cursor único |
| `instance.current_beat` | Eliminar como fonte | Compatibilidade temporária ou propriedade derivada |
| runtime do cenário | Simplificar | Persistir atomicamente o cursor antes/depois de cada resposta |

## Fluxo pretendido

```text
mensagem inicial do app
    ↓
scene_state.current_beat aponta o próximo trecho ainda não interpretado
    ↓
usuário responde
    ↓
story_director classifica somente a resposta atual
    ↓
roteiro decide manter ou avançar
    ↓
modelo recebe somente o trecho ativo
    ↓
runtime valida e persiste o cursor
```

## Estados mínimos do turno

Cada trecho pode estar em apenas um destes estados:

- `pending_mary`: Mary ainda precisa interpretar o trecho;
- `awaiting_user`: Mary interpretou e aguarda resposta ou ação;
- `completed`: trecho concluído;
- `recovery`: uma única tentativa de recondução;
- `ended`: história encerrada.

Esses estados pertencem ao mesmo cursor. Não haverá listas ou cursores concorrentes decidindo a posição.

## Regras de progressão

### Trecho concluído pela fala de Mary

Depois que a resposta validada contém integralmente o trecho canônico, o cursor avança para o próximo trecho antes do turno seguinte.

### Trecho que aguarda o usuário

Depois que Mary interpreta o trecho, o cursor permanece em `awaiting_user`.

A resposta atual do usuário pode produzir somente:

- `accepted`: avançar para o próximo trecho;
- `compatible_improvisation`: responder brevemente e manter a condição pendente;
- `hesitation`: uma recuperação controlada;
- `refusal`: encerrar conforme o roteiro;
- `unrelated`: reconhecer brevemente e voltar ao mesmo ponto.

O texto do usuário nunca escolhe livremente outro beat.

## Garantias obrigatórias

- Um beat concluído nunca pode voltar a ser atual.
- O cursor nunca pode saltar mais de um sucessor, salvo transição explicitamente definida no roteiro.
- A memória não pode mover o cursor.
- O estado visual não pode mover o cursor.
- O histórico completo não será usado para reconstruir a posição em turnos normais.
- O motel seguirá exatamente o mesmo motor das demais cenas.
- A introdução exibida pelo app deve ser marcada como já interpretada.
- O modelo receberá somente o trecho atual, nunca o roteiro integral como cardápio.

## Estratégia de implementação

1. Criar uma representação executável dos beats dentro de `immersive_screenplay.py`, sem alterar o texto canônico.
2. Criar testes de integridade do roteiro: IDs únicos, sucessores válidos e alcance do início ao fim.
3. Criar o cursor mínimo e os estados do turno.
4. Substituir `story_director.py` por uma função pura, sem monkeypatch e sem leitura reconstrutiva do histórico.
5. Simplificar o runtime para persistência atômica.
6. Remover progressivamente os mecanismos antigos somente depois de cada teste equivalente passar.
7. Simular o roteiro completo, da abertura ao encerramento.
8. Integrar à `main` apenas depois da aprovação dos testes e de uma sessão manual completa.

## Testes obrigatórios antes da integração

### Integridade estrutural

- todos os beats possuem ID único;
- todo `next` aponta para beat existente;
- existe um único beat inicial;
- existe um caminho completo até o encerramento;
- nenhum ciclo involuntário.

### Progressão funcional

- abertura não é repetida;
- confirmação do acidente avança uma única vez;
- reconhecimento do Plaza não se repete;
- despedida abre o reencontro;
- reencontro não retorna ao acidente;
- gates não avançam com resposta irrelevante;
- gates avançam com cooperação;
- recusa segue a política do roteiro;
- chamada e motel usam o mesmo motor;
- nenhum beat concluído reaparece.

### Teste integral

Simular a história completa e registrar, a cada turno:

- beat anterior;
- linha canônica enviada;
- classificação da resposta;
- beat posterior;
- motivo da transição.

A integração será bloqueada se houver repetição, retrocesso, salto ou divergência entre cursor persistido e prompt enviado.

## Regra de segurança do desenvolvimento

Nenhuma alteração estrutural será feita diretamente na `main`.

A branch `backup/refatoracao-cursor-unico-2026-07-28` preserva a tentativa anterior para consulta, mas não será usada como base da reconstrução.
