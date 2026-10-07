# ADR 0002 — O projeto não depende de dados da Strava

**Status:** aceito

## Contexto

O projeto nasceu com a intenção de cruzar quilômetros corridos registrados no Strava com dados de criminalidade. Duas descobertas mudaram o desenho.

**Licença.** A cláusula 5.4 da API Policy da Strava veda processar dados da plataforma *"even in an aggregated, de-identified, or anonymized manner, for the purposes of analytics"*. A cláusula 2.3 impede exibir dados de outros atletas. Não há exceção redigida para pesquisa acadêmica ou uso não comercial, e o obstáculo não é contornado por nenhum tier de acesso.

**Método.** Independentemente da licença, a métrica pretendida — `effort_count × distance` por segmento — é cumulativa desde a criação do segmento e não tem janela temporal, o que a torna incomparável com uma base de ocorrências de período definido.

A análise completa das alternativas avaliadas está em [`../estrategia_dados_atividade.md`](../estrategia_dados_atividade.md).

## Decisão

Substituir a medida de **corrida observada** por um **Índice de Adequação à Corrida** construído de dados abertos (OpenStreetMap, IPPUC, IBGE, DEM), e reformular a pergunta de pesquisa em torno de desigualdade de acesso.

Nenhuma etapa do pipeline depende de acesso privilegiado a dado algum.

## Justificativa

- Elimina a única dependência capaz de inviabilizar o projeto.
- Torna o repositório autossuficiente: `make all` reproduz tudo a partir de um clone limpo.
- A nova pergunta é **descritiva por natureza**, e descritivo é o que os dados sustentam — a pergunta original tinha um problema de identificação que fonte nenhuma resolveria.

## Consequências

- O projeto mede condições disponíveis, não uso observado. A distinção precisa estar explícita em todos os entregáveis.
- A camada de adaptadores de fonte, desenhada como mitigação enquanto a dependência existia, foi removida: manter andaime de uma dependência abandonada é complexidade sem contrapartida.
- Strava Metro e dados de assessorias esportivas permanecem como **extensões opcionais** de validação, fora do caminho crítico.
