# Taxonomia e gravidade das ocorrências

Como a base da Guarda Municipal vira a tabela `data/processed/ocorrencias_gm_por_bairro.csv`: o que entra, o que sai e quanto pesa cada ocorrência.

Código: `ingestion/sigesguarda.py` (classificação) e `features/gravidade.py` (pesos). Execução: `python scripts/fase2_ocorrencias.py`.

---

## O que a tabela mede, e o que não mede

**Mede ocorrências registradas pela Guarda Municipal**, ponderadas por gravidade, por bairro. **Não mede risco.**

A diferença é a mesma que separou `transito_tranquilo` de criminalidade. A Guarda protege patrimônio municipal e registra onde está: no recorte de interesse, **22,6%** das ocorrências acontecem em equipamento urbano (estação-tubo, terminal, unidade de saúde), contra 9% da base inteira. Um bairro com terminal de ônibus tende a aparecer mais perigoso porque a Guarda está lá. A coluna `pct_em_equipamento_urbano` acompanha cada bairro para que esse viés fique visível, não escondido.

**A unidade é o bairro porque a base não tem coordenada.** Só 0,6% dos logradouros trazem algum número. Ver ADR 0004 para a base legal do uso.

---

## Do registro bruto à tabela

| Etapa | Registros |
|---|---:|
| Lidos | 236.897 |
| No período (1/1/2023 a 1/10/2026) | 234.701 |
| De interesse | **6.454** |
| De interesse com bairro de Curitiba | 6.443 |

**2022 fica fora**: a base só tem novembro e dezembro daquele ano.

**11 ocorrências ficam sem bairro** porque o nome registrado não é bairro de Curitiba: Campo Pequeno (7), Casa (2), Higienópolis (1) e Bairro Novo (1, que é regional, não bairro).

---

## Regras de inclusão

Uma ocorrência entra quando **atinge uma pessoa, ou o que ela carrega, no espaço público**. É a pergunta do projeto: o risco de quem está na rua, correndo.

1. **Quando a subcategoria identifica o alvo, só a de pessoa na rua entra.** Furto de patrimônio público, roubo a estabelecimento e violência doméstica saem.
2. **Disparo feito pela própria Guarda sai.** 201 dos 228 disparos registrados são da Guarda, com munição letal, menos letal ou dispositivo elétrico. Contá-los transformaria a presença da Guarda em risco.
3. **Tentativa de alvo indeterminado sai.** Tentativa de roubo e de furto podem ser contra comércio; pela coerência da regra 1, não entram.
4. **Tipo ambíguo vira o tipo menos grave compatível.** "Agressão física/verbal" pode ser lesão corporal ou injúria; entra como vias de fato. Na dúvida, não se inflaciona o risco.
5. **Só a natureza principal conta.** As naturezas 2 a 5 estão preenchidas em 0,2% dos registros.

| Natureza na base | Subcategoria | Tipo do projeto | Ocorrências |
|---|---|---|---:|
| Roubo | Transeunte | `roubo` | 1.040 |
| Furto | Transeunte | `furto` | 827 |
| Agressão física/verbal | Agressão | `vias_de_fato` | |
| Vias de Fato | — | `vias_de_fato` | 1.789 (as duas) |
| Ameaça | — | `ameaca` | 1.657 |
| Atos obscenos/libidinosos; Importunação ofensiva ao pudor | — | `ato_obsceno` | 505 |
| Importunação sexual | — | `importunacao_sexual` | 336 |
| Lesão Corporal | — | `lesao_corporal` | 153 |
| Tentativa | Tentativa de agressão | `tentativa_lesao_corporal` | 64 |
| Disparo de arma | Por terceiro; sem vítima; com vítima | `disparo_arma_fogo` | 27 |
| Tentativa de homicídio; Tentativa › Tentativa de homicídio | — | `tentativa_homicidio` | 19 |
| Estupro | — | `estupro` | 19 |
| Tentativa | Tentativa de sequestro | `tentativa_sequestro` | 11 |
| Homicídio | — | `homicidio` | 7 |

**O que sai, e quanto:** metade da base é trânsito; das 2.905 ocorrências de furto, 1.011 são de patrimônio público e só 844 de transeunte; das 2.933 agressões, 2.021 são violência doméstica. "Importunação ofensiva ao pudor" era contravenção (art. 61 da LCP), revogada pela Lei 13.718/2018 — a conduta hoje é ato obsceno ou importunação sexual, e entra como o menos grave dos dois.

---

## Os pesos

### Método

A decisão está registrada no [ADR 0005](adr/0005-peso-de-gravidade-pela-pena-minima.md), com as alternativas rejeitadas.

**Os pesos não são opinião: são derivados da pena mínima do Código Penal.** É o método do *Cambridge Crime Harm Index* (Sherman, Neyroud e Neyroud, 2016), que pondera cada crime pela pena que a lei atribui a ele, adaptado à legislação brasileira.

A vantagem sobre uma escala inventada é que o critério é externo, público e reprodutível. Quem discordar de um peso está discordando do legislador, e pode trocar a regra em um lugar só sem tocar no resto do pipeline. Os pesos são **calculados** a partir da tabela de penas, nunca digitados.

1. **Pena de referência** = pena mínima do caput, na redação vigente.
2. **Tentativa** = metade da pena do consumado. O art. 14, parágrafo único, reduz de 1/3 a 2/3; metade é o ponto médio.
3. **Tentativa de contravenção não existe** (art. 4º da LCP). Por isso "tentativa de agressão" é tentativa de **lesão corporal**, o tipo menos grave que admite tentativa.
4. **Normalização**: divide-se pela maior pena de referência. O mais grave vale 1.

### Tabela

| Tipo | Base legal | Pena mínima | Peso |
|---|---|---:|---:|
| Homicídio | art. 121, CP | 6 anos | **1,000** |
| Estupro | art. 213, CP | 6 anos | **1,000** |
| Roubo a transeunte | art. 157, CP (Lei 15.397/2026) | 6 anos | **1,000** |
| Tentativa de homicídio | art. 121 c/c art. 14, CP | 3 anos | 0,500 |
| Disparo de arma de fogo | art. 15, Lei 10.826/2003 | 2 anos | 0,333 |
| Furto a transeunte | art. 155, CP | 1 ano | 0,167 |
| Importunação sexual | art. 215-A, CP | 1 ano | 0,167 |
| Tentativa de sequestro | art. 148 c/c art. 14, CP | 6 meses | 0,083 |
| Lesão corporal | art. 129, CP | 3 meses | 0,041 |
| Ato obsceno | art. 233, CP | 3 meses | 0,041 |
| Tentativa de agressão (lesão corporal) | art. 129 c/c art. 14, CP | 45 dias | 0,021 |
| Ameaça | art. 147, CP | 1 mês | 0,014 |
| Vias de fato | art. 21, LCP | 15 dias | 0,007 |

### Três consequências que precisam estar à vista

**1. Roubo, estupro e homicídio empatam em 1.** A Lei nº 15.397, de 30 de abril de 2026, elevou a pena mínima do roubo simples para 6 anos, a mesma do homicídio simples e do estupro. A tabela segue a lei vigente. Mas quase todo o período da base (2023 a abril de 2026) correu sob a pena anterior, de 4 anos — com ela, o roubo valeria 0,667. É uma escolha documentada: o peso representa a avaliação atual do legislador, não a da data do fato.

**2. O índice é, na prática, roubo a transeunte.** Com a pena mínima, o roubo responde por **77,4%** da gravidade total, e o furto por 10,3%. Não é defeito: a pena de um roubo é seis vezes a de um furto, e o roubo é o tipo grave mais frequente. Mas quem lê o mapa precisa saber que está vendo, sobretudo, onde se rouba gente na rua.

**3. Contagem e gravidade contam histórias diferentes.** Ameaça e vias de fato são **53,4%** das ocorrências e só **2,6%** da gravidade. São justamente os dois tipos sem subcategoria, em que violência doméstica pode estar misturada — e o peso baixo limita o estrago. **Por isso a medida a usar é `gravidade_anual`, não `n_ocorrencias`.**

### Sensibilidade

`gravidade.pesos("media")` usa o ponto médio entre pena mínima e máxima, que dá mais peso ao furto (0,269) e separa o homicídio do resto (estupro e roubo caem para 0,615).

| Comparação | Resultado |
|---|---:|
| ρ de Spearman do ranking de bairros, mínima × média | **0,993** |
| Bairros na mesma classe alto/baixo nas duas versões | **94,7%** |
| Participação do roubo na gravidade (mínima / média) | 77,4% / 60,0% |
| ρ entre gravidade e contagem simples | 0,918 |

O ranking quase não depende da regra de pena escolhida. A classificação alto/baixo — que é a unidade de comunicação do projeto (ADR 0003) — muda para 4 dos 75 bairros.

---

## As colunas da tabela

| Coluna | O que é |
|---|---|
| `bairro` | Nome oficial — os 75 bairros, inclusive os sem ocorrência |
| `n_ocorrencias` | Ocorrências de interesse no período |
| `gravidade` | Σ peso das ocorrências |
| `gravidade_anual` | `gravidade` ÷ anos cobertos (3,75). **É a medida a usar** |
| `pct_em_equipamento_urbano` | % das ocorrências em equipamento municipal — indicador do viés de presença da Guarda |
| `baixa_contagem` | Menos de 5 ocorrências: taxa instável, e célula a suprimir em publicação (ADR 0004) |
| `n_<tipo>` | Contagem por tipo |

---

## Limitações

1. **Viés de presença da Guarda.** Já descrito acima. O tratamento definitivo depende da SESP-PR (pedido via LAI em andamento).
2. **Ainda não é taxa.** `gravidade_anual` é total, não por habitante. O Centro aparece com 120,6 — quatro vezes o segundo colocado — em boa parte porque concentra gente, comércio e Guarda. A divisão pela população do Censo por bairro é o passo seguinte.
3. **Violência doméstica residual** em ameaça e vias de fato, que não têm subcategoria. Contida pelo peso baixo, não eliminada.
4. **A regra do tipo menos grave subestima** onde a ambiguidade esconde casos graves. É a direção conservadora: o projeto prefere não inventar risco.
5. **Lei nova no meio do período** (Lei 15.397/2026), discutida acima.
6. **Bairro é grande demais para quem corre.** A CIC tem uma nota só para uma área enorme e heterogênea.
