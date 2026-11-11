# Piloto de fala gravada (branch agent/pre-recorded-voice-pilot)

A coluna `FALA GRAVADA` da aba `MINHA_SUGESTAO` contém a fala literal
de Mary. O MP3 correspondente fica em `mary2/assets/audios/`.

Exemplo para ROTEIRO=`Cruzeiro Caribe2` e ORDEM=`1`:

- FALA GRAVADA: `Sil, olha essa foto! A gente ficou linda demais!`
- Arquivo: `mary2/assets/audios/Cruzeiro Caribe2_001.mp3`

## Contrato do piloto

- Sem transcrição e sem MP3: execução livre anterior, inalterada.
- Com transcrição e MP3: o Gemini gera apenas a atuação e pensamento opcional;
  a aplicação usa a transcrição literalmente em exibição, validação e histórico.
- Apenas uma das duas partes: falha explícita, sem publicar uma resposta nova.
- Se o Diretor não aprovar a atuação + transcrição, a resposta não é publicada.
  A transcrição nunca é reescrita por uma correção do modelo.
- O áudio é manual (`st.audio(..., autoplay=False)`). Reruns não iniciam
  nova reprodução automaticamente.
- LOOP de orgulho ferido não usa a gravação da linha original.
- A persistência acrescenta uma coluna no fim de INTERACTIONS:
  `audio_filename`. Ela é lida durante retomadas.
- As imagens por ORDEM continuam independentes do áudio.
- Nenhum provedor TTS ou agente adicional é acionado.

## Testes

No diretório `mary2`, execute:

```bash
python -m unittest discover -s tests -p 'test_scene_audios.py'
```

Também testar manualmente no ambiente piloto:

1. Linha sem MP3 e sem transcrição.
2. Linha com MP3 e transcrição correspondentes.
3. Linha com somente transcrição e somente MP3.
4. Linha gravada automática reprovada pelo Diretor (sem avanço).
5. Reiniciar ou retomar após persistir a linha gravada.
6. Clicar Prosseguir sem gerar uma nova reprodução ou duplicar a fala.
7. Verificar `TOKEN_USAGE_AUDIT` e `INTERACTIONS`.

O diretório `assets/audios` precisa existir na implantação e conter os
arquivos MP3. Não armazenar caminhos absolutos da máquina do autor.
