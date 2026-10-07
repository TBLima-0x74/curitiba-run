# Estratégia de obtenção de dados de atividade física

**Status:** ✅ decidido — a Strava saiu do caminho crítico do projeto
**Desfecho:** o projeto foi reformulado em torno de um **Índice de Adequação à Corrida** construído de dados abertos (OSM, IPPUC, IBGE), eliminando a dependência da Strava. Ver o [README](../README.md) para o desenho vigente.
**Valor deste documento:** registro da análise que levou à decisão, e das opções descartadas com seus motivos. As fontes Strava permanecem relevantes apenas como **extensão opcional** de validação (§13 do README).

---

## 1. O problema mudou de natureza

O R1 foi registrado como um **risco técnico**: o endpoint `/segments/explore` passaria a exigir aprovação no *Extended Access Tier*. A leitura da política de API vigente mostra que o obstáculo real não é de acesso técnico, e sim **contratual** — e ele não é contornado por nenhuma aprovação de tier.

A cláusula 5.4 da [API Policy](https://www.strava.com/legal/api_policy) diz:

> *"You may not process or disclose Strava Data — even publicly viewable Strava Data — including in an aggregated, de-identified, or anonymized manner, for the purposes of analytics, analyses, customer insight generation, or product or service improvements."*

E a cláusula 2.3:

> *"Strava Data provided by a specific Strava user may be displayed ... only to that user. You may not display or disclose Strava Data related to other users."*

Lidas em conjunto, elas descrevem exatamente o que este projeto pretendia fazer: **processar dados da Strava de forma agregada e anonimizada para fins analíticos, e publicar o resultado**. Não há exceção redigida para pesquisa acadêmica, uso não comercial ou dados publicamente visíveis.

> ⚠️ **Consequência prática:** o Plano A (varredura de segmentos via API) e o Plano B originalmente previsto (painel de atletas via OAuth) são **inviáveis por licença**, não apenas por limite técnico. Subir de tier não resolve, porque a política de API se aplica igualmente a todos os tiers.
>
> *Esta é uma leitura de engenharia sobre um documento jurídico, não aconselhamento legal. Antes de qualquer publicação, a interpretação deve ser confirmada — idealmente por escrito, via `developers@strava.com`.*

---

## 2. O Plano A já era metodologicamente frágil

Independentemente da licença, vale registrar: a métrica `effort_count × distance` tinha um defeito grave que o planejamento inicial não capturou.

**`effort_count` é cumulativo desde a criação do segmento.** Não existe janela temporal. Um segmento criado há oito anos e um criado no ano passado não são comparáveis, e nenhum dos dois é comparável com uma base de ocorrências criminais de um período definido. A variável de exposição e a variável de desfecho estariam medidas em escalas temporais incompatíveis.

Somam-se a isso:

- **Segmentos são um recorte curado.** Existem onde alguém decidiu criar um, o que concentra em rotas populares e subestima corrida difusa em bairros periféricos — exatamente o gradiente que o projeto quer medir.
- **Sobreposição.** Trechos populares são cobertos por vários segmentos, e a soma ingênua superestima o volume (já registrado como R5).

Ou seja: **o R1 materializando é menos uma perda do que a eliminação forçada de um atalho ruim.** A reação correta não é procurar um substituto técnico para `/segments/explore`, e sim voltar ao requisito real.

---

## 3. O requisito real

O projeto não precisa de segmentos. Precisa de:

| # | Requisito | Por quê |
|---|-----------|---------|
| **RQ1** | Medida de exposição à corrida **espacialmente resolvida** e cobrindo todo o município | A variável explicativa da análise |
| **RQ2** | **Janela temporal definida e compatível** com a base de ocorrências | Sem isso não há comparação válida |
| **RQ3** | Volume suficiente para não ser dominado por ruído em células de baixa densidade | Estabilidade das estimativas (R9) |
| **RQ4** | **Direito de agregar, analisar e publicar** o resultado | Sem isso o projeto não pode existir publicamente |

RQ4 é o filtro eliminatório. Qualquer opção que falhe aqui está fora, por melhor que seja tecnicamente.

---

## 4. Opções avaliadas

### A. Strava Metro — Programa Acadêmico ⭐ recomendada

Dados de mobilidade ativa **agregados, desidentificados e mapeados sobre a malha viária do OpenStreetMap**, com recorte temporal. É o produto que a Strava construiu precisamente para análise urbana — e é regido por um **acordo separado**, não pela API Policy que veda analytics.

- **RQ4: atende.** É o único caminho que torna o uso de dados Strava legítimo para este projeto.
- Gratuito, com acesso de um ano à plataforma.
- Elegibilidade: pesquisadores e **estudantes** vinculados a instituição acadêmica — o vínculo com o IME qualifica.
- Candidaturas do terceiro ciclo abrem no **início de setembro**, com acesso no ciclo seguinte.

**Limitações a assumir:**

- A corrida pode vir agregada como **"pedestrian"**, junto com caminhada. Isso muda a variável de "km corridos" para "km de deslocamento a pé registrado", e a interpretação precisa acompanhar essa mudança.
- Processo **competitivo** — aprovação não é garantida.
- Restrições de redistribuição: o dado bruto não pode ir para o repositório público, apenas resultados agregados.
- Acesso por tempo limitado, o que reforça a necessidade de pipeline reprodutível e resultados intermediários salvos.

### B. Strava Metro — parceria institucional

Metro é gratuito para *"urban and trail planners, outdoor recreation teams, city governments and safe-infrastructure advocates"*. O **IPPUC** é exatamente esse perfil de organização.

Uma parceria — ou mesmo uma carta de apoio do IPPUC ou da Prefeitura anexada à candidatura acadêmica — abre uma segunda porta e **aumenta a probabilidade conjunta de sucesso**. Como efeito colateral, aproxima o projeto de quem controla as camadas de contexto e as bases de segurança, melhorando também o outro lado da análise.

Custo: tempo e articulação institucional. Sem custo financeiro e sem risco.

### C. Extended Access Tier

Voltado a *"larger partner applications and official integrations"* — o material da própria Strava cita Garmin e Apple como exemplos. Um projeto de pesquisa individual não é o público-alvo.

**E, decisivamente: mesmo se aprovado, a cláusula 5.4 continua valendo.** O tier concede limites maiores e acesso a endpoints, não licença para analytics.

**Veredito:** não resolve o problema. Baixo custo para tentar, mas não deve ser tratado como mitigação de R1.

### D. Painel de atletas via OAuth (Strava)

Recrutar corredores de Curitiba que autorizem o aplicativo.

- Tier Standard limita a **10 atletas** e passou a exigir assinatura Strava ativa do desenvolvedor.
- Dez atletas não cobrem um município de ~435 km². A cobertura seria de um punhado de rotas.
- A cláusula 2.3 impede exibir dados de outros usuários — publicar um mapa derivado das corridas dos voluntários é problemático mesmo com consentimento explícito deles.

**Veredito:** inviável como fonte primária.

### E. Garmin Connect Developer Program

*(resposta direta à pergunta sobre a Garmin — ver seção 5)*

### F. Agregadores multi-plataforma (Terra, ROOK, Open Wearables)

Uma integração única que cobre Garmin, Polar, Coros, Suunto, Fitbit, Wahoo e a própria Strava. Resolvem **custo de engenharia** de integrar várias plataformas.

**Não resolvem o problema central:** continuam sendo acesso por consentimento individual, sem nenhuma camada agregada ou de descoberta espacial. E são SaaS pago.

**Veredito:** só fazem sentido se o projeto virar um estudo de painel (seção 7), e mesmo aí são otimização, não viabilização.

### G. Fontes abertas alternativas

| Fonte | Avaliação |
|-------|-----------|
| **Strava Global Heatmap** | Tentador e explicitamente vedado. Raspar tiles viola os termos, e o dado não tem escala numérica nem janela temporal. **Uso admissível: nenhum além de conferência visual qualitativa.** |
| **Wikiloc / Komoot / AllTrails** | Repositórios de rotas com forte viés de trilha e turismo; cobertura urbana de corrida cotidiana é baixa. Termos de uso igualmente restritivos. |
| **OpenStreetMap** | Não tem volume de uso, mas é essencial como **infraestrutura**: vias, calçadas, parques, pistas. Já previsto como camada de contexto. |

### H. Proxies não digitais de exposição à corrida

Se nenhuma fonte de trajeto for obtida, ainda existe caminho — com outra variável:

- **Inscrições em provas de rua** por bairro de residência (organizadoras e federações).
- **Contagens de fluxo em parques** e equipamentos esportivos municipais.
- **Localização de assessorias esportivas, clubes de corrida e academias.**
- **Survey próprio** com corredores sobre rotas e percepção de segurança — mais trabalhoso, mas gera dado primário sem restrição de licença e permite perguntar diretamente sobre a variável de interesse.

Menos preciso espacialmente, porém **livre de qualquer trava contratual** — e, no caso do survey, capaz de medir percepção, que nenhuma das outras fontes captura.

---

## 5. A Garmin resolve o R1?

**Não. Ela resolve um problema diferente.**

O [Garmin Connect Developer Program](https://developer.garmin.com/gc-developer-program/) é arquitetural e comercialmente distinto da Strava:

| Aspecto | Situação |
|---------|----------|
| **Modelo de acesso** | Exclusivamente **enterprise/B2B**. Exige organização, candidatura, *integration call* e contrato. A FAQ é explícita: *"for business use"*; pesquisa acadêmica não aparece como caso previsto |
| **Custo** | Sem taxa de licenciamento ou manutenção, mas alguns dados exigem licença ou volume mínimo de dispositivos para uso comercial |
| **Prazo** | Análise da candidatura em até dois dias úteis; integração entre uma e quatro semanas |
| **Dados** | Activity API entrega arquivos `.FIT`, `.GPX`, `.TCX` completos, com GPS ponto a ponto — **qualidade superior à da Strava** |
| **Arquitetura** | Ping/Pull ou Push, mediante **consentimento de cada usuário** que conecta a conta ao seu aplicativo |
| **Descoberta espacial** | **Não existe.** Sem segmentos, sem *bounding box*, sem heatmap |
| **Dados agregados de terceiros** | **Não existe.** A Garmin não tem nenhum equivalente ao Strava Metro |

O ponto essencial: **a Garmin nunca oferece dados de quem não autorizou o seu aplicativo especificamente.** Ela é uma API de *integração de usuário*, não de *inteligência urbana*. Para cobrir Curitiba pela Garmin seria preciso recrutar, individualmente, milhares de corredores.

**Onde a Garmin de fato ajuda:** ela é uma versão melhor da opção D. Se o projeto migrar para desenho de painel (seção 7), Garmin — sozinha ou via agregador — entrega dados mais ricos, sem o teto de 10 atletas e sem a cláusula 5.4 da Strava. Mas ela **habilita um outro estudo**, não este.

**Analogia útil:** Strava Metro é um censo agregado da cidade; Garmin é um caderno de campo detalhado de quem você conseguir entrevistar. O projeto, como está desenhado, precisa de um censo.

---

## 6. Matriz de decisão

| Opção | RQ1 cobertura | RQ2 janela temporal | RQ3 volume | RQ4 licença | Custo | Prioridade |
|-------|:---:|:---:|:---:|:---:|-------|:---:|
| **A. Metro Acadêmico** | ✅ | ✅ | ✅ | ✅ | Candidatura + prazo | **1** |
| **B. Metro via IPPUC** | ✅ | ✅ | ✅ | ✅ | Articulação institucional | **2** |
| C. Extended Access Tier | ⚠️ | ❌ | ⚠️ | ❌ | Baixo | 5 |
| D. Painel OAuth Strava | ❌ | ✅ | ❌ | ❌ | Recrutamento | — |
| E. Garmin Connect | ❌ | ✅ | ❌ | ⚠️ | Contrato B2B | 4 |
| F. Agregadores | ❌ | ✅ | ❌ | ⚠️ | SaaS pago | — |
| G. Heatmap / repositórios | ⚠️ | ❌ | ⚠️ | ❌ | Baixo | — |
| **H. Proxies e survey** | ⚠️ | ✅ | ⚠️ | ✅ | Trabalho de campo | **3** |

---

## 7. Estratégia recomendada

### Trilhas em paralelo, não em sequência

Nenhuma das opções viáveis tem aprovação garantida, e todas têm prazo longo. Rodá-las em série desperdiça o recurso mais escasso do projeto, que é tempo de espera por terceiros.

**Trilha 1 — Metro Acadêmico (prioridade máxima, sensível a prazo).**
Preparar a candidatura: proposta de pesquisa, justificativa de relevância para mobilidade ativa e segurança viária, vínculo institucional e orientação. A janela do próximo ciclo abre no início de setembro.

**Trilha 2 — articulação com IPPUC / Prefeitura.**
Apresentar o projeto, buscar carta de apoio e explorar parceria Metro institucional. Ganho colateral relevante no acesso às bases de segurança e contexto.

**Trilha 3 — desenho de contingência com proxies.**
Levantar em paralelo a disponibilidade de inscrições em provas de rua e contagens municipais, e desenhar o instrumento de survey. Se as trilhas 1 e 2 falharem, o projeto continua com outra variável de exposição.

**Trilha 4 — Extended Access Tier.**
Solicitar, junto com uma consulta escrita a `developers@strava.com` sobre uso acadêmico. Custo quase nulo; serve principalmente para obter uma resposta formal por escrito.

### Portões de decisão

- **G1 — antes de investir em pipeline de ingestão:** ao menos uma trilha entre 1, 2 e 3 precisa ter resultado positivo. Sem isso, não se escreve código de coleta.
- **G2 — se 1 e 2 falharem:** decidir entre a contingência com proxies (trilha 3) ou o pivô de desenho descrito abaixo.

---

## 8. Mitigação de engenharia: desacoplar análise e fonte

A lição estrutural do R1 é que **o projeto amarrou o desenho analítico a uma fonte específica**. A correção é uma camada de adaptadores.

Definir um **esquema canônico de exposição**, independente da origem:

```
exposure_edge
├── geometry        # LineString ou célula H3
├── period_start    # janela temporal explícita
├── period_end
├── modality        # run | walk | pedestrian | ride
├── trip_count      # contagem de passagens
├── distance_km     # extensão do trecho
└── source          # metro | segments | gpx | proxy
```

E escrever adaptadores independentes:

```
src/ingestion/adapters/
├── base.py            # contrato comum
├── metro_adapter.py   # Strava Metro (edges OSM)
├── gpx_adapter.py     # arquivos de painel (Garmin, Strava export)
└── proxy_adapter.py   # inscrições, contagens, survey
```

Toda a análise das Fases 3 a 6 consome apenas `exposure_edge`. **Trocar a fonte de dados vira trocar um adaptador, não refazer o projeto.** Se o Metro sair, o adaptador de proxy assume; se o Metro chegar depois, os dois resultados são comparáveis pelo mesmo esquema.

Essa é a mitigação que realmente reduz o risco — as demais apenas aumentam a chance de obter uma fonte específica.

---

## 9. Plano de contingência: pivô de desenho

Se nenhuma fonte agregada for obtida, a resposta correta é **mudar a pergunta**, não forçar dados ruins em uma pergunta que eles não sustentam.

**Pergunta alternativa:** *corredores de Curitiba evitam áreas com maior incidência de ocorrências ao escolher suas rotas?*

Isso transforma o estudo:

| | Desenho atual | Pivô |
|---|---|---|
| Unidade de análise | Célula da cidade | Decisão de rota |
| Dado necessário | Censo espacial da corrida | Trajetos de uma amostra consentida |
| Tamanho de amostra | Cobertura municipal | Dezenas de corredores bastam |
| Método | Regressão espacial, GWR | Modelos de escolha discreta |
| Fonte viável | Metro | **Garmin, painel Strava, GPX exportado** |

É aqui que a Garmin entra com força: um painel de corredores voluntários, recrutados em clubes e assessorias, exportando seus trajetos com consentimento informado. A pergunta é mais estreita, mas **defensável, original e totalmente sob controle do projeto** — e responde diretamente à intuição que motivou a ideia original.

---

## 10. Ações imediatas

1. [ ] Verificar a abertura da janela do Metro Acadêmico e reunir os requisitos de candidatura
2. [ ] Redigir a proposta de pesquisa de uma página, com ênfase em mobilidade ativa e segurança
3. [ ] Contatar o IPPUC apresentando o projeto e solicitando carta de apoio
4. [ ] Enviar consulta escrita a `developers@strava.com` sobre uso acadêmico e a cláusula 5.4
5. [ ] Mapear disponibilidade de proxies: inscrições em provas de rua e contagens municipais
6. [ ] Implementar o esquema `exposure_edge` e o contrato de adaptadores antes de qualquer coletor
7. [ ] Atualizar o README: R1 reclassificado de risco técnico para **bloqueador de licença**

---

## Fontes

- [Strava API Policy](https://www.strava.com/legal/api_policy) — cláusulas 2.3, 5.3, 5.4 e 5.10
- [Strava — An Update To Our Developer Program](https://communityhub.strava.com/insider-journal-9/an-update-to-our-developer-program-13428)
- [Strava V3 API Changelog](https://developers.strava.com/docs/changelog/)
- [Strava Metro](https://metro.strava.com/)
- [Strava Metro for Academic Researchers](https://metro.strava.com/academics)
- [Garmin Connect Developer Program](https://developer.garmin.com/gc-developer-program/)
- [Garmin Connect Developer Program — FAQ](https://developer.garmin.com/gc-developer-program/program-faq/)
- [Garmin Activity API](https://developer.garmin.com/gc-developer-program/activity-api/)
- [Terra API — integrações de wearables](https://tryterra.co/integrations)
