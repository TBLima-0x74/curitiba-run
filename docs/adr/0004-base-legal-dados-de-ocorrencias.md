# ADR 0004 — Base legal para usar dados de ocorrências do portal municipal

**Status:** aceito

## Contexto

A Fase 2 constrói a superfície de risco a partir de registros de ocorrências. Antes de escrever a ingestão, era preciso saber se o uso pretendido é permitido — a lição do [ADR 0002](0002-sem-dependencia-strava.md), em que a cláusula 5.4 da API Policy da Strava vedava exatamente a análise agregada que o projeto queria fazer.

O uso pretendido: baixar as bases, filtrar as ocorrências relevantes para quem corre na rua, agregá-las na malha H3 e publicar a análise e o código em repositório público.

## O que dizem as regras

**Regras de Utilização do Portal de Dados Abertos de Curitiba**, na resposta oficial à pergunta *"Posso utilizar as bases de dados para qualquer finalidade?"*:

> Sim, desde que seja para atividades legais. Conforme estabelecido nas Regras de Utilização, o uso das bases fornecidas "é livre para qualquer finalidade ou atividade, no limite das restrições legais e respectiva regulamentação".

**Política de Dados Abertos do Município**, regulamentada pelo Decreto nº 1023/2014:

- dados abertos são *"livremente disponíveis para todos utilizarem e redistribuírem como desejarem"*;
- princípio "livres de licenças": *"Os dados não estão sujeitos a regulações de direitos autorais, marcas, patentes ou segredo industrial"*;
- admite *"restrições razoáveis de privacidade, segurança e controle de acesso"*, na forma da legislação aplicável.

Não há exigência formal de citar a fonte. O projeto cita mesmo assim.

## Decisão

**O uso das bases do Portal de Dados Abertos de Curitiba na Fase 2 está autorizado, sob três condições que o projeto adota como regra.**

1. **Só entram bases publicadas pelo portal municipal.** O Decreto nº 1023/2014 cobre a Administração Direta, Indireta e Autarquias de Curitiba — a Guarda Municipal (SIGESGUARDA) está dentro. **Os dados da SESP-PR não estão**: são do governo estadual e têm termos próprios. Nenhuma base estadual entra no projeto antes de um ADR próprio com a base legal dela.
2. **O dado bruto não é publicado.** Registro de ocorrência com endereço é dado pessoal em potencial, e a Lei Geral de Proteção de Dados (Lei nº 13.709/2018) é justamente uma das "restrições legais" a que as Regras de Utilização remetem — e é posterior ao decreto. O repositório publica apenas agregados por célula H3. O `.gitignore` já exclui `data/raw/`.
3. **Células com contagem muito baixa são suprimidas ou suavizadas antes de publicar.** "Uma ocorrência neste hexágono, neste mês" pode identificar uma vítima. O limiar de supressão é decidido e documentado na própria Fase 2, antes do primeiro mapa.

## Justificativa

A situação é o oposto da Strava. Lá a licença proibia a análise; aqui a análise é o propósito declarado da política — que lista entre seus objetivos o desenvolvimento de novos usos dos dados abertos. Não há cláusula a contornar.

O que há são obrigações que valem para qualquer dado sobre pessoas, e é por isso que as condições 2 e 3 não são opcionais: o "livre para qualquer finalidade" do portal termina, nas palavras dele, no limite das restrições legais.

Registrar isto antes da primeira linha de ingestão segue a regra que o desafio 1 deixou: **verificar a licença é parte do levantamento de viabilidade, não etapa burocrática posterior.**

## Consequências

- `ingestion/sigesguarda.py` pode ser implementado. `ingestion/sesp.py` fica bloqueado até um ADR com a base legal estadual.
- Os arquivos de ocorrências ficam em `data/raw/sigesguarda/` e nunca são versionados.
- A superfície de risco publicada é sempre agregada e passa por supressão de células de baixa contagem.
- Isto é leitura técnica dos termos, não parecer jurídico. Se o projeto sair do portfólio para uso institucional, a confirmação vai pelo Canal de Dúvidas do portal.

## Acesso aos dados

O portal disponibiliza as bases também pelo espelho do C3SL/UFPR, por rsync:

```
rsync -av rsync://dadosabertos.c3sl.ufpr.br/dadosabertos/curitiba/<Base>/ ./data/raw/<pasta>/
```

## Fontes

- [Portal de Dados Abertos de Curitiba](https://dadosabertos.curitiba.pr.gov.br/), Regras de Utilização e resposta "Posso utilizar as bases de dados para qualquer finalidade?"
- [Decreto nº 1023/2014 — Regulamento de Política de Dados Abertos do Município de Curitiba](https://dadosabertos.curitiba.pr.gov.br/conteudo/decreto-n-10232014---regulamento-de-politica-de-dados-abertos-do-municipio-de-curitiba/31)
- [Política de Dados Abertos — Prefeitura de Curitiba (PDF, 2014)](https://mid.curitiba.pr.gov.br/2014/00147194.pdf)
- [Lei nº 13.709/2018 — Lei Geral de Proteção de Dados Pessoais](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
