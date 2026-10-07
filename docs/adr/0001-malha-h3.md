# ADR 0001 — Malha hexagonal H3 como unidade de análise

**Status:** aceito

## Contexto

A análise precisa de uma unidade espacial para agregar infraestrutura, ocorrências e população. As candidatas eram os 75 bairros, os setores censitários do IBGE, uma grade quadrada regular e a malha hexagonal H3.

## Decisão

Malha **H3 na resolução 9** (~0,1 km² por célula) como unidade primária, com agregação secundária por bairro e regional apenas para comunicação.

## Justificativa

- **Vizinhança uniforme.** Hexágonos têm seis vizinhos equidistantes; células quadradas têm vizinhos de aresta e de vértice a distâncias diferentes, o que distorce matrizes de peso espacial e estatísticas de autocorrelação.
- **Independência de fronteiras administrativas.** Bairros têm tamanhos muito desiguais em Curitiba e suas fronteiras foram traçadas por critérios alheios ao fenômeno estudado.
- **Sensibilidade testável.** A hierarquia do H3 permite repetir toda a análise nas resoluções 8 e 10 com uma linha de código, o que torna a análise de MAUP barata em vez de teórica.
- **Interoperabilidade.** Índices H3 são chaves textuais estáveis, o que simplifica joins e persistência em Parquet.

## Consequências

- Setores censitários precisam ser interpolados para a malha por área ponderada, assumindo distribuição homogênea interna — aproximação registrada nas limitações.
- Células de borda ficam parcialmente fora do município; a coluna `fracao_no_municipio` permite ponderar ou excluir.
- Resultados por bairro passam a ser derivados, não primários.
