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

## Taxa por habitante e normalização de 0 a 1

A gravidade total diz onde há mais ocorrências, não onde é mais arriscado estar: bairro populoso acumula mais por ter mais gente. A segunda etapa divide pela população.

**Denominador:** população residente do **Censo 2022**, arquivo "básico" dos Agregados por Bairros do IBGE, variável `V0001` (total de pessoas). O carregamento falha alto se algum dos 75 bairros oficiais faltar, se algum nome do IBGE não casar com a lista oficial, ou se alguma população vier sigilosa — os três casos produziriam taxa errada sem aviso.

**Taxa:**

```
taxa_gravidade = gravidade_anual ÷ população × 100.000
```

**Normalização em escala logarítmica.** Primeiro `log(1 + taxa)`, depois a mesma normalização do IAC — corte nos percentis 2 e 98 e escala para [0, 1].

O logaritmo veio depois da primeira execução. A taxa tem cauda pesada: quatro bairros — São Francisco, Taboão, Centro e Jardim Botânico — ficam muito acima dos outros 71. Na escala linear, a mediana dos bairros era **0,026** e 60 dos 75 ficavam abaixo de 0,1: num mapa, quase todos teriam a mesma cor. O corte nos percentis protege contra um extremo isolado, não contra um grupo.

| | Linear | Logarítmica |
|---|---:|---:|
| Mediana | 0,026 | **0,390** |
| Quartis | 0,01 · 0,03 · 0,06 | **0,24 · 0,39 · 0,53** |
| Bairros abaixo de 0,1 | 60 | **8** |
| Classe alto/baixo | — | **idêntica nas duas** |

O logaritmo não muda a ordem, então a classificação alto/baixo pela mediana sai a mesma. O que muda é a leitura das distâncias: na escala log, um passo de 0,1 é uma razão constante entre taxas, não uma diferença constante. `taxa_por_habitante(..., escala="linear")` continua disponível.

O corte só protege contra um outlier isolado quando há **pelo menos 51 unidades** — abaixo disso, o percentil 98 interpolado já inclui o extremo. Curitiba tem 75 bairros; um teste fixa esse caso.

**Duas ressalvas que acompanham a taxa:**

1. **Residente não é quem circula.** O denominador é quem dorme no bairro; as ocorrências acontecem com quem passa por ele. Os números confirmam: três dos quatro bairros com maior taxa — São Francisco (centro histórico), Centro e Jardim Botânico (rodoferroviária) — têm pouca gente morando e muita gente passando. **O erro não pode ser medido diretamente**, porque não há dado público de população flutuante por bairro. **Decisão: fica como limitação declarada, sem correção.** A taxa de São Francisco, Centro e Jardim Botânico deve ser lida como teto: o risco de quem passa por esses bairros é menor do que o número sugere, porque o número divide ocorrências de muitos visitantes por poucos moradores. A análise que mediria o efeito disso nas conclusões — recalcular a taxa por km de via caminhável e por área, e marcar os bairros cuja classe alto/baixo muda — fica registrada como extensão futura, não como pendência da fase.
2. **Bairro pequeno tem taxa instável.** Tratado pela suavização bayesiana empírica — ver a seção dela. Na prática, mudou pouco: o que instabiliza uma taxa é ter poucas ocorrências, e quase todos os bairros pequenos têm ocorrências suficientes.

Saída: `data/processed/taxa_ocorrencias_gm_por_bairro.csv`, com as colunas abaixo mais `populacao`, `taxa_gravidade` (observada), `taxa_gravidade_eb` (suavizada), `peso_proprio`, `taxa_gravidade_norm`, `classe_risco`, `taxa_ocorrencias` (ocorrências por ano por 100 mil) e `populacao_pequena`.

**O nome é deliberado.** A coluna se chama `taxa_gravidade_norm`, e não `risco`: enquanto a única fonte for a Guarda Municipal, ela mede ocorrências registradas pela Guarda, não risco.

---

## Suavização bayesiana empírica

Taxa de bairro pequeno oscila com poucas ocorrências. A correção padrão é o Bayes empírico global (Marshall, 1991): cada bairro é puxado em direção à média da cidade na medida em que seu próprio dado é pouco. É de `taxa_gravidade_eb` que saem a normalização de 0 a 1 e a classe alto/baixo; `taxa_gravidade` continua sendo a taxa observada.

**Adaptação a gravidade ponderada.** O método foi feito para contagens. Aqui o numerador é uma soma de pesos, e a variância de amostragem de uma soma de pesos é **κ vezes a média**, com κ = E[w²]/E[w] calculado sobre todas as ocorrências. Em Curitiba, **κ = 0,825**: uma nota feita de poucos roubos (peso 1) oscila mais do que uma feita de muitas ameaças (peso 0,014). A exposição é pessoa-ano — população × 3,75 anos.

**Resultado: quase não muda nada, e é o resultado correto.**

| | |
|---|---:|
| Peso do próprio bairro — mínimo · mediana · máximo | 0,74 · 0,99 · 1,00 |
| ρ entre taxa observada e suavizada | 0,986 |
| Bairros que mudam de classe | **0** |

O motivo é que **o ruído estava superestimado**. O que torna uma taxa instável é o número de ocorrências, não o tamanho da população. O Taboão, segundo colocado, tem 3.470 moradores mas **63 ocorrências**: o coeficiente de variação da sua nota é de cerca de 13%. A taxa dele é alta de verdade — o problema do Taboão é o denominador residente, não o ruído. Só os bairros com zero ou quase zero ocorrências mexem: Riviera vai de 0 a 5,2 e Lamenha Pequena de 0 a 2,4, e continuam em baixo.

**Ressalva de método.** O estimador de Marshall não é robusto a cauda pesada. A variância entre bairros é dominada pelos quatro extremos (São Francisco, Taboão, Centro, Jardim Botânico), e por isso o encolhimento sai pequeno para todos. Recalculando a variância sem eles, o peso próprio cai a 0,20 na Riviera e 0,66 no Taboão — mas aí aparece o problema oposto: a média da cidade (20,1) está muito acima da mediana (8,9), porque a distribuição é assimétrica, e bairros **sem nenhuma ocorrência** passariam para a classe alta. Puxar para uma média inflada pela cauda inventa risco onde não há registro. O estimador clássico foi mantido; um Bayes empírico **local**, que puxa cada bairro para a média dos vizinhos em vez da cidade, é a alternativa que trataria as duas coisas, e fica como extensão.

A marcação `populacao_pequena` continua na tabela, mas como sinal de cautela, não de ruído: para ruído, a coluna certa é `baixa_contagem`.

---

## Classe alto/baixo de risco

Como o IAC (ADR 0003), a camada de risco é comunicada em duas classes: `classe_risco` é `alto` quando a taxa do bairro está na mediana dos 75 bairros ou acima dela, e `baixo` abaixo. A mediana é de **8,81 por 100 mil habitantes por ano**; ficam **38 bairros alto e 37 baixo**.

**O corte é pela mediana dos bairros, não das células.** Cada bairro conta uma vez, qualquer que seja o tamanho. A mediana das células daria à CIC, com 451 hexágonos, o peso de dezenas de bairros pequenos. A diferença não é detalhe: os dois cortes classificam de forma diferente **751 células**.

**Consequência que precisa estar à vista:** como os bairros grandes da periferia têm taxa baixa, a classe alta cobre só **1.328 das 4.508 células (29%)**, e **36% da população** mora em bairro de risco alto. Metade dos bairros não é metade do território, nem metade das pessoas.

**A fronteira é estreita.** Augusta (8,40) fica em baixo e Santa Felicidade (8,81) em alto; Tarumã (9,19), com 13 ocorrências em 7 mil habitantes, também em alto. Seis dos nove bairros com menos de 5.000 habitantes caem em alto, que é o efeito da taxa instável — a suavização bayesiana empírica, pendente, deve mexer exatamente aí.

---

## Do bairro ao hexágono

Para cruzar com o IAC, cada hexágono H3 r9 **herda a nota do bairro que ocupa a maior parte dele**.

- **Limites de bairro:** os serviços públicos do GeoCuritiba **não têm camada de bairros** — a primeira execução procurou entre as cerca de 120 camadas e não achou. Têm os **setores censitários de 2022**, e no Censo 2022 cada setor pertence a um único bairro: unir os setores pelo nome do bairro reconstrói os limites. O resultado vai para `data/raw/ippuc/bairros.parquet`. A busca tenta primeiro uma camada de bairros, caso o IPPUC publique uma, e o id nunca é fixado no código — o servidor reorganiza camadas entre versões, e um id errado baixaria outra coisa sem aviso. Qualquer outra malha de bairros serve, se salva na mesma pasta; uma malha nacional, como a do IBGE, é filtrada para Curitiba antes de unir os polígonos.
- **Bairro dominante:** calculado pela área de interseção, sobre a parte da célula coberta por algum bairro. Assim uma célula na divisa do município não parece dividida só porque metade dela está fora de Curitiba.
- **`celula_dividida`:** marca as células em que o bairro dominante cobre menos da metade. Nelas, a nota herdada representa menos da metade do território.
- **Bairro sem célula:** um bairro pequeno pode não ser dominante em nenhum hexágono. O pipeline avisa, porque a nota dele não chega ao mapa.
- **Célula de borda sem bairro:** a malha H3 foi recortada pelo limite municipal do **IBGE**, que é generalizado; os bairros seguem o limite **oficial** do IPPUC. Os dois contornos divergem em média 80 m, e **37 células** da borda não tocam nenhum bairro. Recebem o bairro mais próximo — estão a no máximo 177 m — e saem marcadas em `bairro_por_proximidade`. Além de 500 m o pipeline para, porque aí a divergência já não seria de contorno.

Saída: `data/processed/risco_gm_h3_r9.parquet`, com `h3`, `bairro`, `fracao_bairro`, `bairro_por_proximidade`, `celula_dividida`, `populacao`, `taxa_gravidade`, `taxa_gravidade_eb`, `peso_proprio`, `taxa_gravidade_norm`, `classe_risco` e `populacao_pequena`.

**A nota é constante dentro do bairro.** Duas células vizinhas do mesmo bairro recebem o mesmo valor, e duas células vizinhas separadas pela divisa podem receber valores muito diferentes. É a consequência direta de a base não ter coordenada, e já estava entre as limitações.

---

## Segunda fonte: SESP-PR

A SESP-PR entra pelas **mesmas regras** deste documento — mesmos tipos, mesmos pesos (ADR 0005), mesma taxa, mesma suavização, mesma classe —, para que as duas fontes difiram só no que registram. O que muda é a classificação da natureza, porque o vocabulário da polícia não é o da Guarda e só será conhecido quando a resposta chegar:

- **Padrões, não lista fechada.** `CLASSIFICACAO`, em `ingestion/sesp.py`, é uma lista ordenada de expressões regulares: a primeira que casar define o tipo. A ordem importa — tentativa de homicídio vem antes de homicídio; latrocínio e feminicídio contam como homicídio.
- **Natureza não reconhecida não entra calada.** Sai no relatório, com a contagem, para ser decidida uma a uma.
- **Roubo e furto genéricos** só entram quando o tipo de local indica via pública; roubo a residência ou a comércio não é risco para quem corre. Sem coluna de local, ficam de fora — a regra do tipo menos grave aplicada ao lugar.
- **Violência doméstica** é excluída pela natureza (doméstica, Maria da Penha, familiar), como na Guarda.
- **Período:** a partir de 2023, como a Guarda; o fim é a última data da base (o fim do último mês, se vier só ano e mês), para que os anos cobertos — e portanto a gravidade anual — sejam os da própria SESP.

A comparação entre as duas fontes e o roteiro de chegada estão em [`fase2_status.md`](../reports/status/fase2_status.md#quando-a-resposta-chegar).

---

## As colunas da tabela

| Coluna | O que é |
|---|---|
| `bairro` | Nome oficial — os 75 bairros, inclusive os sem ocorrência |
| `n_ocorrencias` | Ocorrências de interesse no período |
| `gravidade` | Σ peso das ocorrências |
| `gravidade_anual` | `gravidade` ÷ anos cobertos (3,75). **É a medida a usar** |
| `pct_em_equipamento_urbano` | % das ocorrências em equipamento municipal — indicador do viés de presença da Guarda |
| `baixa_contagem` | Menos de 5 ocorrências: taxa instável, e bairro suprimido na publicação ([ADR 0007](adr/0007-supressao-de-baixa-contagem.md)) |
| `n_<tipo>` | Contagem por tipo |

---

## Limitações

1. **Viés de presença da Guarda.** Já descrito acima. O tratamento definitivo depende da SESP-PR (pedido via LAI em andamento); o código que mede o viés, comparando as duas fontes, já está pronto.
2. **Denominador residente.** A taxa divide pela população que mora no bairro, não pela que circula — ver a seção sobre a taxa.
3. **Violência doméstica residual** em ameaça e vias de fato, que não têm subcategoria. Contida pelo peso baixo, não eliminada.
4. **A regra do tipo menos grave subestima** onde a ambiguidade esconde casos graves. É a direção conservadora: o projeto prefere não inventar risco.
5. **Lei nova no meio do período** (Lei 15.397/2026), discutida acima.
6. **Bairro é grande demais para quem corre.** A CIC tem uma nota só para uma área enorme e heterogênea.
