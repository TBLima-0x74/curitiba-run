# Onde dá para correr em Curitiba?

**Infraestrutura de corrida, risco de segurança e desigualdade de acesso ao espaço público**

Projeto de análise geoespacial que investiga como se distribuem, no território de Curitiba, as duas condições necessárias para correr na rua: **infraestrutura adequada** e **segurança**.

> **A infraestrutura adequada para corrida em Curitiba está distribuída de forma desigual em relação ao risco de segurança?**
> **Quem tem acesso a espaço seguro para correr?**

O projeto constrói um **Índice de Adequação à Corrida (IAC)** a partir de dados abertos de infraestrutura urbana, cruza com a densidade de ocorrências de segurança pública, e analisa a distribuição resultante em relação a renda e população.

**Todas as fontes são públicas, re-baixáveis e redistribuíveis.** O repositório é autossuficiente: clonar, rodar `make all` e obter os resultados do zero.

---

## Sumário

- [1. Motivação](#1-motivação)
- [2. Perguntas e hipóteses](#2-perguntas-e-hipóteses)
- [3. Escopo](#3-escopo)
- [4. Fontes de dados](#4-fontes-de-dados)
- [5. Desenho metodológico](#5-desenho-metodológico)
- [6. Fases do projeto](#6-fases-do-projeto)
- [7. Estrutura do repositório](#7-estrutura-do-repositório)
- [Como executar](#como-executar)
- [Desafios](#desafios)
- [8. Stack técnica](#8-stack-técnica)
- [9. Riscos e ameaças à validade](#9-riscos-e-ameaças-à-validade)
- [10. Ética e comunicação responsável](#10-ética-e-comunicação-responsável)
- [11. Critérios de sucesso](#11-critérios-de-sucesso)
- [12. Convenções de trabalho](#12-convenções-de-trabalho)
- [13. Extensões futuras](#13-extensões-futuras)

---

## 1. Motivação

Correr na rua é a atividade física mais acessível que existe: não custa mensalidade, não exige equipamento e não depende de horário marcado. Essa acessibilidade, porém, é **condicional ao território**. Correr exige superfície caminhável, continuidade de percurso, iluminação e uma sensação razoável de segurança.

Essas condições não estão distribuídas por igual em nenhuma cidade brasileira. E quando infraestrutura precária e risco elevado coincidem no mesmo lugar, o efeito não é aditivo — é uma **dupla penalização** que retira da população local o acesso a uma prática de saúde pública gratuita.

Curitiba é um caso favorável para medir isso. A cidade tem uma infraestrutura de dados abertos incomum no país: a Guarda Municipal publica sua base de ocorrências, o IPPUC mantém um acervo geoespacial maduro, e o OpenStreetMap tem boa cobertura urbana. É possível construir a análise inteira sem pedir permissão a ninguém.

### Uma nota sobre a origem deste projeto

A ideia inicial era cruzar quilômetros corridos registrados no Strava com dados de criminalidade. Duas descobertas mudaram o desenho: a política de API da Strava veda expressamente o uso analítico agregado de seus dados, e — mais importante — a pergunta original tinha um problema de identificação que dado nenhum resolveria.

A pergunta atual é **descritiva por natureza**, e descritivo é exatamente o que os dados sustentam. A análise mede desigualdade de acesso, não efeito causal, e por isso não precisa de uma estratégia de identificação que ela não teria como oferecer. O histórico completo dessa decisão está em [`docs/estrategia_dados_atividade.md`](docs/estrategia_dados_atividade.md).

---

## 2. Perguntas e hipóteses

### Perguntas

| # | Pergunta |
|---|----------|
| **P1** | Como se distribui espacialmente a adequação à corrida em Curitiba? |
| **P2** | Adequação à corrida e risco de segurança são espacialmente associados? Em que direção? |
| **P3** | Que parcela da população, por faixa de renda, vive a distância caminhável de espaço adequado **e** de baixo risco? |
| **P4** | Existem áreas de **dupla penalização** — baixa adequação e alto risco simultâneos? Onde? |
| **P5** | A desigualdade no acesso a espaço *seguro* para correr é maior que a desigualdade na infraestrutura isolada? |

### Hipóteses

| # | Hipótese | Direção esperada |
|---|----------|------------------|
| H1 | A adequação à corrida é positivamente associada à renda do entorno | Positiva |
| H2 | A densidade de ocorrências é negativamente associada à renda | Negativa |
| H3 | Como consequência de H1 e H2, as áreas de dupla penalização concentram-se na periferia | Concentração |
| H4 | Indicadores agregados de "área verde por habitante" **mascaram** a desigualdade, porque medem oferta e não acesso | Divergência entre métricas |
| **H5** | **A desigualdade de acesso a espaço seguro é maior que a desigualdade de infraestrutura isolada**, porque os dois gradientes se compõem em vez de se compensarem | Composição |

H5 é a hipótese central e a mais informativa: se confirmada, significa que analisar infraestrutura sem considerar segurança **subestima sistematicamente** a desigualdade real de acesso à atividade física.

---

## 3. Escopo

### Dentro do escopo

- Perímetro do município de Curitiba — 75 bairros, 10 regionais.
- Construção de um índice composto de adequação à corrida a partir de dados abertos.
- Cruzamento com densidade de ocorrências de segurança pública georreferenciadas.
- Análise de acessibilidade **em rede** (distância caminhável real, não euclidiana).
- Análise de equidade por faixa de renda e por regional.
- Entregáveis reprodutíveis: pipeline versionado, mapa interativo e relatório.

### Fora do escopo

- **Inferência causal.** A análise é descritiva e de equidade. Nenhuma alegação sobre efeito de infraestrutura em criminalidade, ou o inverso.
- **Comportamento observado de corredores.** O projeto mede condições disponíveis, não uso efetivo — ver [extensões](#13-extensões-futuras).
- **Previsão de criminalidade.** Descartado explicitamente por razões éticas.
- Região Metropolitana de Curitiba.
- Análise temporal fina — a estrutura de dados a comporta, a v1 não a executa.

---

## 4. Fontes de dados

Todas gratuitas, públicas e re-baixáveis por qualquer pessoa que clone o repositório.

### 4.1 Infraestrutura urbana — insumo do IAC

| Fonte | Conteúdo | Uso |
|-------|----------|-----|
| [OpenStreetMap](https://www.openstreetmap.org) (via `osmnx` / Overpass) | Malha viária, calçadas (`footway`, `sidewalk`), vias de pedestres, hierarquia viária, `lit=yes`, uso do solo | Espinha dorsal do índice |
| [IPPUC — GeoDownloads](https://ippuc.org.br/geodownloads/geo.html) e [GeoCuritiba](https://geocuritiba.ippuc.org.br/) | Limites de bairros e regionais, parques e praças, ciclovias e ciclofaixas, equipamentos esportivos, eixos viários oficiais | Camadas oficiais e validação do OSM |
| [Dados Abertos de Curitiba](https://dadosabertos.curitiba.pr.gov.br/) | Iluminação pública, equipamentos urbanos, arborização | Dimensões complementares do índice |
| Modelo digital de elevação (Copernicus DEM / SRTM) | Altimetria | Declividade — conforto e viabilidade de percurso |

### 4.2 Segurança pública

| Fonte | Conteúdo | Granularidade |
|-------|----------|---------------|
| [**SiGesGuarda**](https://dadosabertos.curitiba.pr.gov.br/conjuntodado/detalhe?chave=b16ead9d-835e-41e8-a4d7-dcc4f2b4b627) — Guarda Municipal | Ocorrências atendidas: natureza, subcategoria, bairro, rua, data e hora | **Bairro** — sem coordenada, e a rua vem sem número |
| SESP-PR | Ocorrências policiais do estado | Solicitada via LAI, por bairro e mês; portal fora do ar |

A base da Guarda mede **onde a Guarda atua**, não onde há risco: ela protege patrimônio municipal e registra onde está. Por isso a camada que sai dela se chama "ocorrências registradas pela GM" até que a SESP-PR permita corrigir o viés. Uso autorizado pelo [ADR 0004](docs/adr/0004-base-legal-dados-de-ocorrencias.md).

### 4.3 População e renda

| Fonte | Uso |
|-------|-----|
| IBGE — Censo Demográfico, setores censitários | População residente, densidade, renda domiciliar per capita, composição etária |

---

## 5. Desenho metodológico

### 5.1 Unidade de análise

**Malha hexagonal H3, resolução 9** (~0,1 km² por célula) como unidade primária; agregação secundária por **bairro** e por **regional** para comunicação.

Hexágonos evitam a arbitrariedade dos limites administrativos, têm vizinhança uniforme e permitem testar a sensibilidade dos resultados à escala — mitigação direta do **Problema da Unidade de Área Modificável (MAUP)**.

### 5.2 O Índice de Adequação à Corrida (IAC)

Índice composto, normalizado de 0 a 1 por célula, agregando seis dimensões:

| Dimensão | Indicador | Fonte principal |
|----------|-----------|-----------------|
| **Superfície caminhável** | Densidade de calçadas e vias de pedestres (km/km²) | OSM |
| **Espaço dedicado** | Área de parque, praça e pista dentro da célula e adjacências | IPPUC + OSM |
| **Trânsito tranquilo** (`transito_tranquilo`) | Proporção da via mapeada que é de baixo tráfego — trânsito, não criminalidade. A classe da via é proxy fraco: ver limitação 8 em [`docs/indice_adequacao.md`](docs/indice_adequacao.md) | OSM |
| **Continuidade** | Conectividade da malha, densidade de interseções, tamanho do maior componente conectado | OSM (análise de rede) |
| **Conforto** | Declividade média; cobertura arbórea | DEM, IPPUC |
| **Iluminação** | Densidade de pontos de iluminação pública | Dados Abertos Curitiba, OSM `lit` |

Cada dimensão é normalizada, e o índice é a média ponderada delas. **A escolha dos pesos é arbitrária por natureza** — por isso a análise de sensibilidade aos pesos (§5.5) não é opcional, é parte do resultado.

### 5.3 A superfície de risco

Gravidade das ocorrências **por bairro**, em taxa por habitante. Cada ocorrência pesa a pena mínima do seu tipo no Código Penal, normalizada de 0 a 1 ([ADR 0005](docs/adr/0005-peso-de-gravidade-pela-pena-minima.md)). Como a base não tem coordenada, cada hexágono H3 herda a nota do bairro que ocupa a maior parte dele. O detalhe está em [`docs/taxonomia_ocorrencias.md`](docs/taxonomia_ocorrencias.md).

### 5.4 Combinação: acesso a espaço seguro

Duas leituras complementares:

**a) Tipologia de quadrantes** — cada célula classificada pelo cruzamento de IAC e risco, ambos dicotomizados pela mediana. O IAC entra aqui já como classe `alto`/`baixo`: a posição exata no ranking contínuo depende dos pesos, que são arbitrários, e por isso **não é o que o projeto afirma** — ver [ADR 0003](docs/adr/0003-alto-baixo-como-unidade-de-comunicacao.md). A classe binária se mantém em 70,4% das células entre os quatro cenários de peso, contra 41,4% do quartil, e cada célula vai acompanhada de em quantos cenários a classe se sustenta.

| | Baixo risco | Alto risco |
|---|---|---|
| **Alto IAC** | 🟢 **Privilegiado** | 🟡 **Subutilizado** — infraestrutura existe, o risco inibe o uso |
| **Baixo IAC** | 🔵 **Latente** — seguro, mas sem infraestrutura; o mais barato de corrigir | 🔴 **Duplamente penalizado** |

O quadrante **Latente** é o achado de maior valor prático: são as áreas onde investimento em infraestrutura teria retorno imediato, sem depender de política de segurança.

**b) Acessibilidade em rede** — para cada célula habitada, a distância **caminhável pela malha real** até o espaço adequado e de baixo risco mais próximo. Reporta-se a parcela da população a 5, 10 e 15 minutos de caminhada, estratificada por decil de renda.

Essa segunda leitura é o que responde P3 de forma direta e comunicável.

### 5.5 Estratégia analítica

1. **Descritiva** — distribuição do IAC e do risco; mapas coropléticos; perfis por regional.
2. **Autocorrelação espacial** — I de Moran global e local (LISA) para IAC e risco; mapas de cluster.
3. **Associação bivariada** — Moran bivariado entre IAC e risco, com envelope de significância por permutação; mapa da tipologia de quadrantes.
4. **Equidade** — curvas de Lorenz e índices de concentração do IAC e do acesso seguro por decil de renda; razão entre decil superior e inferior. **Teste direto de H5:** comparar a concentração da infraestrutura isolada com a do acesso seguro.
5. **Modelagem** — regressão do IAC e do acesso seguro sobre renda, densidade e distância ao centro, com termo espacial (SAR ou SEM conforme diagnóstico por multiplicadores de Lagrange).
6. **Sensibilidade** — repetição em H3 resoluções 8 e 10 e no nível de bairro (MAUP); **e variação dos pesos do índice**, incluindo pesos iguais, análise de componentes principais e cenários extremos, reportando a estabilidade do ranking de células.

> **Escopo deliberadamente contido.** GWR, MGWR e modelos espaço-temporais ficam como extensão. Para os objetivos deste projeto, um pipeline completo e reprodutível com seis etapas bem executadas vale mais que um catálogo de modelos inacabado.

---

## 6. Fases do projeto

> Fases são sequenciais em **dependência**, não em calendário. As Fases 1 e 2 são independentes entre si e podem correr em paralelo. Cada fase define objetivo, atividades, entregáveis e um **critério de saída** verificável.

### Fase 0 — Fundação

**Objetivo:** repositório de pé e viabilidade das fontes confirmada.

**Atividades**

- Inicializar repositório, licença, `.gitignore`, ambiente reprodutível e estrutura de pastas.
- Baixar amostras de cada fonte e inspecionar: colunas, cobertura, projeção, qualidade.
- **Avaliar a completude do OSM em Curitiba** contra as camadas oficiais do IPPUC — ver risco R1, que é a principal ameaça à validade do projeto.
- Definir a taxonomia preliminar de naturezas de ocorrência.
- Registrar as decisões iniciais em ADRs.

**Entregáveis**

- Repositório inicializado, ambiente reprodutível (`pyproject.toml`), `Makefile` esqueleto
- `docs/viabilidade.md` com a avaliação de cada fonte
- `docs/adr/0001-malha-h3.md` e demais decisões iniciais

**Critério de saída:** todas as fontes baixadas programaticamente ao menos uma vez, com script versionado e qualidade documentada.

---

### Fase 1 — Índice de Adequação à Corrida

**Objetivo:** produzir o IAC por célula, defensável e auditável.

**Atividades**

- Extrair a malha viária e de pedestres do OSM com `osmnx`; construir o grafo caminhável.
- Calcular métricas de rede por célula: densidade de calçadas, interseções, conectividade, componente conectado dominante.
- Incorporar parques, praças, pistas e ciclovias do IPPUC, resolvendo sobreposição com o OSM.
- Derivar declividade do DEM e agregar por célula.
- Incorporar iluminação pública e arborização.
- Normalizar cada dimensão e compor o índice; **documentar os pesos e sua justificativa**.
- **Validar contra o mundo real:** inspeção visual de imagens de satélite e Street View numa amostra estratificada de células, verificando se IAC alto e IAC baixo correspondem ao que se vê.

**Entregáveis**

- `src/features/suitability_index.py`
- `data/processed/iac_h3_r9.parquet`
- `docs/indice_adequacao.md` — dimensões, fórmula, pesos e limitações
- `reports/validacoes/validacao_iac.md` — a inspeção da amostra, com imagens

**Critério de saída:** índice calculado para todas as células habitadas, com validação visual documentada e desacordos explicados.

---

### Fase 2 — Dados de segurança pública

**Objetivo:** uma camada de risco por bairro, comparável com o IAC. *(Independente da Fase 1.)* Situação atual em [`reports/status/fase2_status.md`](reports/status/fase2_status.md).

**Atividades**

- Padronizar a base da Guarda Municipal — nomes de bairro, categorias, esquema — com testes de contrato.
- Filtrar as ocorrências que atingem uma pessoa na rua e pesá-las pela gravidade.
- Dividir pela população do Censo por bairro, e classificar cada bairro em alto/baixo.
- Medir quanto da nota de cada bairro é presença da Guarda.
- Obter os dados da SESP-PR via LAI e usá-los para corrigir esse viés.

**Entregáveis**

- `src/curitiba_run/ingestion/sigesguarda.py`, `features/gravidade.py` e `scripts/fase2_ocorrencias.py`
- `data/processed/ocorrencias_gm_por_bairro.csv`
- `docs/taxonomia_ocorrencias.md` e ADRs 0004 e 0005
- `reports/validacoes/qualidade_dados_seguranca.md` com o teste do viés de presença da Guarda

**Critério de saída:** camada de risco por bairro, por habitante, com classe alto/baixo e com o viés de presença da Guarda medido — corrigido pela SESP-PR se a resposta vier, ou declarado como limitação se não vier.

---

### Fase 3 — Malha espacial e integração

**Objetivo:** uma tabela analítica, uma linha por célula.

**Atividades**

- Construir a malha H3 recortada pelo limite municipal — resolução 9 primária, 8 e 10 para sensibilidade.
- Agregar ocorrências por célula, total e por classe; aplicar suavização onde a exposição for baixa.
- Interpolar população e renda dos setores censitários para a malha, por área ponderada.
- **Calcular a acessibilidade em rede:** distância caminhável de cada célula habitada ao espaço adequado e de baixo risco mais próximo.
- Construir as matrizes de vizinhança espacial.
- Manter `data` e `hora` das ocorrências preservados, para a extensão temporal futura.

**Entregáveis**

- `data/processed/malha_h3_r9.parquet` — tabela analítica principal
- `src/processing/grid.py`, `accessibility.py`, `spatial_join.py`
- Matrizes de vizinhança serializadas

**Critério de saída:** tabela analítica única e validada por somas de controle — total de ocorrências e de população alocados batem com a origem.

---

### Fase 4 — Análise exploratória e tipologia

**Objetivo:** entender os padrões antes de modelar.

**Atividades**

- Estatísticas descritivas e distribuições de todas as variáveis.
- Mapas coropléticos de IAC, risco e acessibilidade.
- I de Moran global e LISA para IAC e risco; mapas de cluster.
- Moran bivariado entre IAC e risco.
- **Construção e mapeamento da tipologia de quadrantes**, com perfil de população e renda de cada quadrante.
- Inspeção qualitativa de casos notáveis, sobretudo no quadrante Latente.

**Entregáveis**

- `notebooks/01_eda_espacial.ipynb`
- `reports/figures/` — mapas e gráficos
- `reports/achados_exploratorios.md`

**Critério de saída:** tipologia construída, clusters identificados e as quatro classes caracterizadas por população, renda e localização.

---

### Fase 5 — Equidade e modelagem

**Objetivo:** quantificar a desigualdade de acesso e testar H5.

**Atividades**

- Curvas de Lorenz e índices de concentração do IAC por decil de renda.
- Mesmas métricas para o **acesso seguro**; comparação direta entre as duas — o teste de H5.
- Parcela da população a 5, 10 e 15 minutos de espaço adequado e seguro, por decil.
- Regressão do IAC e do acesso seguro sobre renda, densidade e distância ao centro.
- Diagnóstico de dependência espacial residual; modelo SAR ou SEM conforme o teste.
- **Análise de sensibilidade completa:** três resoluções espaciais e ao menos quatro esquemas de pesos do índice.

**Entregáveis**

- `notebooks/02_equidade.ipynb`, `03_modelagem.ipynb`
- `src/analysis/equity.py`, `models.py`
- `reports/resultados.md`
- `reports/validacoes/sensibilidade.md`

**Critério de saída:** H5 testada com resultado explícito, e conclusões estáveis entre esquemas de peso e escalas — ou a instabilidade documentada como achado.

---

### Fase 6 — Visualização e comunicação

**Objetivo:** tornar o resultado legível para quem não vai abrir o código.

**Atividades**

- Mapa interativo com camadas alternáveis: IAC, risco, tipologia, acessibilidade.
- Figuras estáticas em qualidade de publicação.
- Relatório final: pergunta, método, achados, limitações e o que **não** se pode concluir.
- Resumo executivo de uma página com os três achados principais.

**Entregáveis**

- `reports/mapa_interativo.html`
- `reports/relatorio_final.md`
- `reports/figures/` finalizado

**Critério de saída:** um leitor externo entende achados e limitações sem abrir um notebook.

---

### Fase 7 — Reprodutibilidade e publicação

**Objetivo:** garantir que o projeto roda do zero na máquina de outra pessoa.

**Atividades**

- Pipeline ponta a ponta orquestrado por `make all`, partindo de um clone limpo.
- Testes automatizados das transformações críticas — malha, agregação, acessibilidade, composição do índice.
- CI executando testes e *lint* a cada push.
- README final com instalação e execução; instruções verificadas em ambiente limpo.
- Licença de código e de dados; verificação do que pode ser publicado.

**Entregáveis**

- `Makefile` completo, `tests/`, `.github/workflows/ci.yml`
- README de instalação verificado

**Critério de saída:** clone limpo em máquina sem estado prévio reproduz todos os resultados finais.

---

## 7. Estrutura do repositório

Itens marcados como *planejado* ainda não existem: estão no desenho das fases seguintes.

```
curitiba-run/
├── README.md
├── LICENSE
├── pyproject.toml
├── Makefile                          # atalhos opcionais — make help
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml          # lint e testes a cada push
│
├── scripts/                          # pontos de entrada, um por etapa
│   ├── fase1.py                      # limite → malhas H3 → GeoCuritiba → OSM → IAC
│   └── fase2_ocorrencias.py          # ocorrências da Guarda → tabela por bairro
│
├── src/curitiba_run/                 # o pacote: toda a lógica, testável
│   ├── config.py                     # caminhos, pesos do IAC, os 75 bairros oficiais
│   ├── ingestion/
│   │   ├── osm.py                    # rede caminhável e espaços dedicados (osmnx)
│   │   ├── geocuritiba.py            # postes, MDT e áreas verdes do IPPUC
│   │   ├── ippuc.py                  # limite municipal
│   │   ├── sigesguarda.py            # ocorrências da Guarda Municipal
│   │   ├── sesp.py                   # bloqueado até o ADR da SESP-PR (pedido via LAI)
│   │   ├── ibge.py
│   │   └── dem.py
│   ├── processing/
│   │   ├── grid.py                   # malha H3 com verificação de cobertura
│   │   ├── accessibility.py          # distância em rede
│   │   ├── geocoding.py              # sem uso por ora: a base da Guarda não tem número
│   │   └── spatial_join.py
│   ├── features/
│   │   ├── dimensions.py             # as cinco dimensões do IAC
│   │   ├── suitability_index.py      # normalização, composição e robustez alto/baixo
│   │   ├── gravidade.py              # peso de cada ocorrência pela pena mínima
│   │   ├── risk_surface.py
│   │   └── typology.py               # quadrantes IAC × risco
│   ├── analysis/                     # Moran/LISA, equidade, modelos
│   └── viz/                          # mapas e gráficos
│
├── tests/                            # verificados contra uma cidade sintética
│   ├── fixtures/cidade_sintetica.py
│   ├── test_grid.py
│   ├── test_osm.py
│   ├── test_geocuritiba.py
│   ├── test_dimensions.py
│   ├── test_suitability_index.py
│   ├── test_typology.py
│   ├── test_equity.py
│   ├── test_gravidade.py
│   └── test_sigesguarda.py
│
├── data/                             # nada aqui vai para o Git
│   ├── raw/                          # como baixado, nunca editado à mão
│   │   ├── osm/
│   │   ├── ippuc/
│   │   ├── sigesguarda/
│   │   ├── sesp/
│   │   ├── ibge/
│   │   └── dem/
│   ├── interim/                      # cache do osmnx e arquivos temporários
│   └── processed/                    # malhas H3, IAC, ocorrências por bairro
│
├── docs/
│   ├── indice_adequacao.md           # método da Fase 1: o IAC
│   ├── taxonomia_ocorrencias.md      # método da Fase 2: ocorrências e pesos
│   ├── desafios.md                   # onde o projeto quase deu errado
│   ├── estrategia_dados_atividade.md # histórico da saída da Strava
│   └── adr/                          # uma decisão por arquivo
│       ├── 0001-malha-h3.md
│       ├── 0002-sem-dependencia-strava.md
│       ├── 0003-alto-baixo-como-unidade-de-comunicacao.md
│       ├── 0004-base-legal-dados-de-ocorrencias.md
│       └── 0005-peso-de-gravidade-pela-pena-minima.md
│
├── reports/
│   ├── status/                       # situação de cada fase e backlog
│   │   ├── fase1_status.md
│   │   └── fase2_status.md
│   ├── validacoes/                   # evidência de que o cálculo mede o que diz
│   │   ├── validacao_iac.md
│   │   ├── qualidade_dados_seguranca.md   # planejado
│   │   └── sensibilidade.md               # planejado
│   ├── figures/
│   ├── resultados.md                 # planejado
│   ├── relatorio_final.md            # planejado
│   └── mapa_interativo.html          # planejado
│
└── notebooks/                        # exploração, a partir da Fase 4
```

### Como a documentação se organiza

- **`README.md`** — o que é o projeto, e o mapa para o resto.
- **`docs/` com um documento de método por fase** — como cada coisa é calculada hoje. Muda junto com o código.
- **`docs/adr/`** — uma decisão por arquivo, com as alternativas rejeitadas. Não se reescreve: decisão nova vira ADR novo.
- **`docs/desafios.md`** — os problemas que quase passaram, e o que cada um ensinou.
- **`reports/status/`** — onde cada fase está e o que falta. **`reports/validacoes/`** — as evidências que fecham cada critério de saída.

### Política de dados

- `data/raw/`, `data/interim/` e `data/processed/` não vão para o Git. Os scripts recriam tudo a partir das fontes públicas.
- **Dado de ocorrência nunca é publicado bruto** — só agregado, e com supressão de contagens baixas ([ADR 0004](docs/adr/0004-base-legal-dados-de-ocorrencias.md)).
- O material de inspeção manual (`reports/validacoes/*.html`) é privado e fica só na máquina local.
- **Nenhum dado do projeto depende de acesso privilegiado** — com a exceção declarada da SESP-PR, solicitada via LAI.

---

## Desafios

O registro dos obstáculos que mudaram o projeto está em [`docs/desafios.md`](docs/desafios.md) — dezenove deles, com o que cada um ensinou.

Vale a leitura por um motivo específico: **nenhum desses defeitos se manifestou como erro.** A licença da Strava não gerou exceção; a métrica sem janela temporal teria somado normalmente; três dimensões quebradas do índice devolveram 4.508 valores bem-comportados; a malha que perdia 1% do município fechava todas as contas. Só a serialização do Parquet realmente quebrou — e foi o mais fácil de corrigir.

O que encontrou os outros dezoito foi ler a licença, checar a correlação entre dimensões, conferir somas de controle e perguntar em que direção cada erro empurraria o resultado. Nada disso aparece num pipeline verde.

---

## Como executar

O projeto roda sem `make` — ele é conveniência, não requisito. **Windows não traz `make`**, então o caminho principal é o script.

### Um comando

```bash
python scripts/fase1.py
```

Executa a Fase 1 inteira: limite municipal → malhas H3 nas três resoluções → camadas do OpenStreetMap → dimensões → IAC. Cada etapa pula o que já existe em disco, então uma queda no meio não obriga a recomeçar; `--refazer` força tudo de novo.

As respostas do Overpass ficam em cache local, e a rede caminhável de Curitiba é uma consulta pesada — a primeira execução leva alguns minutos, as seguintes são rápidas.

```bash
python scripts/fase1.py --so-malha   # só as malhas, dispensa internet
```

### Fase 2 — ocorrências

```bash
python scripts/fase2_ocorrencias.py
```

Lê a base da Guarda Municipal salva em `data/raw/sigesguarda/` (baixada do [Portal de Dados Abertos](https://dadosabertos.curitiba.pr.gov.br/)), mantém só as ocorrências de interesse, aplica o peso de gravidade e grava `data/processed/ocorrencias_gm_por_bairro.csv`. Não precisa de internet.

### Preparando o ambiente

Com [uv](https://docs.astral.sh/uv/) (recomendado — instala o próprio Python):

```bash
uv sync --extra dev
uv run python scripts/fase1.py
```

Com pip, em Python 3.11+:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  no Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/fase1.py
```

### Requisitos de rede

A ingestão precisa alcançar `overpass-api.de`, `nominatim.openstreetmap.org`, `ippuc.org.br`, `geocuritiba.ippuc.org.br`, `dadosabertos.curitiba.pr.gov.br` e `servicodados.ibge.gov.br`. Atrás de proxy corporativo ou VPN restritiva o download falha — o script detecta isso e diz exatamente quais hosts faltam, em vez de despejar um *traceback*.

### Se você tiver `make`

```bash
make help      # lista os alvos
make fase1     # equivalente ao script
make malhas    # só as malhas
make test      # testes
```

No Windows, `make` existe via WSL, Git Bash com make instalado, ou `choco install make`. Nada disso é necessário.

### Testes

```bash
pytest              # com o pacote instalado
PYTHONPATH=src pytest   # sem instalar
```

Os testes que dependem de `geopandas` são pulados automaticamente se a biblioteca não estiver instalada, então a suíte roda mesmo num ambiente mínimo.

---

## 8. Stack técnica

| Camada | Ferramentas |
|--------|-------------|
| Linguagem | Python 3.11+ |
| Dados tabulares | `pandas`, `pyarrow` |
| Geoespacial | `geopandas`, `shapely`, `h3`, `pyproj`, `rasterio` |
| Redes e OSM | `osmnx`, `networkx` |
| Estatística espacial | `esda`, `libpysal`, `spreg` (ecossistema PySAL) |
| Modelagem | `statsmodels` |
| Visualização | `matplotlib`, `folium`, `contextily` |
| Orquestração | `make` |
| Qualidade | `pytest`, `ruff`, `pre-commit`, `nbstripout` |
| Ambiente | `uv` |

**Sistema de referência:** EPSG:4326 na ingestão; **EPSG:31982 (SIRGAS 2000 / UTM 22S)** para todo cálculo métrico de distância e área.

---

## 9. Riscos e ameaças à validade

As duas primeiras são **ameaças à validade**, não riscos de execução: são erros de medida correlacionados com a própria variável de interesse. Merecem tratamento explícito no relatório, não apenas mitigação.

| # | Ameaça | Impacto | Tratamento |
|---|--------|---------|------------|
| **R1** | **A completude do OSM é correlacionada com renda.** Bairros centrais e ricos são mais mapeados. Se calçadas existem na periferia mas não estão no OSM, o IAC subestima a infraestrutura lá — **e isso enviesa o resultado exatamente na direção da hipótese H1.** | **Crítico** | Validar o OSM contra as camadas oficiais do IPPUC; **reportar a completude por decil de renda** como resultado próprio; inspeção visual estratificada por satélite; usar preferencialmente camadas oficiais onde existirem |
| **R2** | **A subnotificação e a falha de geocodificação também variam por região.** A propensão a acionar a Guarda e a qualidade dos endereços não são uniformes. | **Alto** | Testar viés espacial da geocodificação (Fase 2); usar naturezas de menor subnotificação; validar contra SESP |
| R3 | Arbitrariedade dos pesos do índice composto | Alto | Análise de sensibilidade obrigatória com ao menos quatro esquemas; reportar estabilidade do ranking |
| R4 | MAUP — resultados dependem da malha | Médio | Sensibilidade em três resoluções e no nível de bairro |
| R5 | Células com pouca população geram estimativas instáveis | Médio | Filtro de população mínima; suavização bayesiana empírica |
| R6 | Interpretação causal indevida por terceiros | Médio | Linguagem descritiva em todo o texto; seção de limitações em destaque |
| R7 | Estigmatização territorial a partir dos mapas | Médio | Ver §10 |
| **R8** | **Escopo excessivo impede a conclusão** | **Alto** | Escopo de modelagem deliberadamente cortado (§5.5); GWR e temporal como extensões; a v1 precisa fechar |

---

## 10. Ética e comunicação responsável

1. **Nenhum dado individualizado.** Só entram agregados espaciais com contagem mínima suficiente para impedir reidentificação.
2. **Uso vedado.** O projeto não se destina a policiamento preditivo, precificação de seguros ou avaliação imobiliária. Consta da licença de uso dos resultados.
3. **Sem ranking de "bairros perigosos".** Mapas de criminalidade têm efeito social real. A comunicação enfatiza **acesso e desigualdade**, não periculosidade, e reporta incerteza junto com estimativa.
4. **O enquadramento é de direito, não de risco.** A pergunta é quem tem acesso a espaço público adequado — não quais áreas evitar. A diferença entre essas duas narrativas, com os mesmos dados, é uma escolha consciente do projeto.
5. **Limitações com o mesmo destaque dos achados.** As ameaças R1 e R2 vão no corpo do relatório, não em nota de rodapé.

---

## 11. Critérios de sucesso

- [ ] Um clone limpo do repositório roda `make all` e reproduz todos os resultados, sem acesso privilegiado a nada.
- [ ] O IAC está construído, documentado e validado contra observação do mundo real.
- [ ] A completude do OSM por decil de renda foi medida e reportada (R1).
- [ ] O viés espacial da geocodificação foi testado e reportado (R2).
- [ ] A tipologia de quadrantes está mapeada e caracterizada.
- [ ] H5 foi testada com resultado explícito.
- [ ] As conclusões foram testadas em três escalas espaciais e quatro esquemas de peso.
- [ ] Existe um mapa interativo e um relatório que um leitor não técnico entende.
- [ ] As limitações estão escritas com o mesmo cuidado dos achados.

---

## 12. Convenções de trabalho

### Branches

```
main                    # sempre reproduzível
feat/<descricao>        # nova funcionalidade
fix/<descricao>         # correção
data/<descricao>        # nova fonte ou atualização de base
docs/<descricao>        # documentação
exp/<descricao>         # experimento analítico
```

### Commits — Conventional Commits

```
feat(features): compõe o índice de adequação com seis dimensões
fix(processing): corrige projeção no cálculo de declividade
data(sigesguarda): atualiza base de ocorrências
docs(readme): detalha a tipologia de quadrantes
test(accessibility): cobre distância em rede com grafo sintético
chore(ci): configura workflow de lint
```

### Notebooks

Notebooks servem para exploração e narrativa; **lógica reutilizável mora em `src/`**. Todo notebook commitado é executável de cima a baixo, com saídas limpas via `nbstripout` no `pre-commit`.

---

## 13. Extensões futuras

Fora da v1, mas contempladas pela arquitetura.

**Uso observado versus condições disponíveis.** O IAC mede onde *dá* para correr. Comparar com onde de fato se corre fecharia o argumento. Duas rotas possíveis:

- **Strava Metro** — dados agregados e desidentificados de mobilidade ativa, licenciados para análise urbana. O programa acadêmico é gratuito para pesquisadores e estudantes. Os dados **não podem ser redistribuídos**, então entrariam como camada de validação, não como parte do repositório público.
- **Assessorias esportivas** — pontos de encontro e percursos padrão, frequentemente públicos. A concentração espacial dessa amostra é enviesada, mas nesse uso **o viés é o achado**: se a corrida organizada se concentra numa cunha rica da cidade, isso valida diretamente a tese de desigualdade de acesso.

**Extensão temporal.** Distribuição horária das ocorrências, cruzada com iluminação e com o horário em que as pessoas efetivamente correm. Estrutura de dados já preservada na Fase 3.

**Outras direções**

- Percepção de segurança via survey — a única forma de medir a barreira subjetiva, que nenhuma fonte objetiva captura.
- Extensão a outras capitais com dados abertos equivalentes, transformando o IAC em índice comparável.
- Inclusão de caminhada e ciclismo, ampliando de corrida para mobilidade ativa.
- GWR / MGWR para heterogeneidade espacial dos coeficientes.

---

## Fontes

- [OpenStreetMap](https://www.openstreetmap.org) · [`osmnx`](https://osmnx.readthedocs.io/)
- [IPPUC — Downloads de dados geográficos](https://ippuc.org.br/geodownloads/geo.html) · [GeoCuritiba](https://geocuritiba.ippuc.org.br/)
- [Portal de Dados Abertos da Prefeitura de Curitiba](https://dadosabertos.curitiba.pr.gov.br/)
- [SiGesGuarda — ocorrências da Guarda Municipal](https://dadosabertos.curitiba.pr.gov.br/conjuntodado/detalhe?chave=b16ead9d-835e-41e8-a4d7-dcc4f2b4b627)
- [SESP-PR / CAPE — Estatísticas de criminalidade](https://www.seguranca.pr.gov.br/CAPE/Estatisticas)
- [Prefeitura de Curitiba — Dados geográficos](https://servicos.curitiba.pr.gov.br/dados-geograficos-de-curitiba/92)
- [Strava Metro](https://metro.strava.com/) e [Metro for Academic Researchers](https://metro.strava.com/academics) — apenas para a extensão
