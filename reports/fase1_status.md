# Fase 1 — situação

**Concluída.** O IAC está calculado para Curitiba com dados reais, as cinco dimensões passam no diagnóstico de redundância, e a inspeção visual que o critério de saída exigia foi feita: **25 de 25 células, 17 `confere`, 8 `parcial`, nenhum `não confere`** — com os dez IAC baixos conferindo todos, que é o extremo de que a hipótese H1 depende. Detalhe em [`validacao_iac.md`](validacao_iac.md).

As três correções pendentes — `lit` desligada, `tertiary` e `busway` reclassificados, e `seguranca_viaria` renomeada para `transito_tranquilo` — **já estão nos números**: recalculado em 7/10 e verificado contra a rodada anterior. A tabela de verificação está em [`docs/indice_adequacao.md`](../docs/indice_adequacao.md).

> **Para recalcular, `python scripts/fase1.py` basta.** A etapa 5 passou a reaplicar a classificação viária a cada execução, em vez de lê-la do `arestas.parquet` — sem isso, a reclassificação de `tertiary` e `busway` não chegaria ao número, porque a etapa 4 pula o download que já existe. Ver desafio 18.

---

## O que está pronto

### Malha analítica

| Resolução | Células | Área média | Lacuna de cobertura |
|-----------|--------:|-----------:|--------------------:|
| H3 r8 | 690 | 0,706 km² | 0,0000% |
| H3 r9 (primária) | 4.508 | 0,101 km² | 0,0000% |
| H3 r10 | 30.743 | 0,014 km² | 0,0000% |

Limite municipal com 435,4 km², contra ~435 km² da referência oficial.

O preenchimento padrão do H3 descartava 4,1 km² de borda — quase 1% do território, todo periférico. Corrigido com contenção por sobreposição, e `grid.verificar_cobertura` falha alto se a lacuna passar de 0,1%.

### Dados ingeridos

| Fonte | Conteúdo | Volume |
|-------|----------|-------:|
| OSM | Rede caminhável | 185.386 arestas, 65.920 nós |
| OSM | Espaços dedicados | 2.161 polígonos |
| GeoCuritiba | Postes | 179.401, dos quais 154.851 de iluminação |
| GeoCuritiba | MDT 2019 a 0,5 m, reamostrado a 10 m | declividade derivada |
| GeoCuritiba | Unidades de conservação | 134, das quais 59 públicas |

### O índice

5 dimensões, 4.030 células com valor de 4.508, média 0,423, mediana 0,426, máximo 0,881.

Diagnóstico: **VIF entre 1,00 e 1,19** — nenhuma dimensão tem mais de 17% da variação explicada pelas outras. Pior correlação entre pares: **0,398**, contra 0,95 na primeira rodada, e hoje esse par não envolve nenhuma dimensão corrigida.

As duas dimensões mais mexidas são agora as mais independentes: `iluminacao` com VIF 1,01 e `transito_tranquilo` com 1,03.

Detalhe completo de fórmulas, filtros e diagnósticos em [`docs/indice_adequacao.md`](../docs/indice_adequacao.md).

### Código

**74 testes passando.** A lógica posterior ao download é verificada contra uma cidade sintética de medidas conhecidas, com asserções de igualdade exata — a soma dos comprimentos por célula bate com o comprimento da linha original, a soma das áreas bate com a área do parque mesmo quando ele aparece duplicado nas camadas.

---

## O que foi corrigido desde a primeira rodada

| Defeito | Correção | Efeito medido |
|---------|----------|---------------|
| `superficie_caminhavel` e `continuidade` correlacionavam 0,95 e somavam 40% do peso | Fundidas em `densidade_malha`, peso 0,20 | Pior correlação 0,95 → 0,81 |
| `conforto` correlacionava −0,09 com o índice: sem MDT, media ausência de urbanização | Virou `declividade`, do MDT do IPPUC | Passou a +0,495 com o IAC |
| 523 postes do OSM colapsavam a normalização, injetando 0,25 fixo em toda célula | Postes oficiais; `normalizar` passou a avisar quando vira constante | 154.851 postes, dimensão viva |
| Postes por km² media densidade de rua | Normalizado por **km de via** | `malha` × `iluminacao` 0,81 → 0,31 |
| 24.550 postes de rede elétrica contados como iluminação | Filtro por `tipoposte` | Só os que iluminam |
| RPPNM privadas e 197 km² de APA entravam como espaço público | Filtro por camada do FeatureServer | 219,8 km² → 11,53 km² |
| `lit` do OSM, ausente em 66% das células, valia metade da iluminação | Componente desligada (`usar_lit=False`) | Mediana da iluminação 0,259 → 0,461; abaixo de 0,3 de 58,3% → 21,0% |
| `tertiary` (coletora de bairro) contava como rodovia; `busway` do BRT como ambígua | Reclassificadas | Mediana 0,802 → 0,864; células em 0 de 30 → 10 |
| `seguranca_viaria` sugeria criminalidade, que ela não mede | Renomeada para `transito_tranquilo` | — |
| A classificação viária era gravada no download e a etapa 4 pulava o que existia | Reaplicada na etapa 5 a cada execução | 17.718 arestas e 1.406 km que não teriam mudado |
| `densidade_malha` penalizava parque em 3× na extensão e 9× nas interseções | Peso de 0,20 para 0,15, excedente para `espaco_dedicado` | Barigui segue no percentil 89; ranking muda pouco (ρ 0,991) |

---

## Um resultado que parece ruim e não é

**A estabilidade entre cenários de peso caiu de 0,863 para 0,697, e depois para 0,624.**

É consequência direta da correção, não regressão. Dimensões redundantes produzem estabilidade espúria: se todas medem a mesma coisa, mudar o peso não altera o ranking. Ao eliminar a redundância, o peso passou a importar de verdade.

Mudar os pesos não resolve — testado com três conjuntos diferentes, o piso fica inalterado, porque o par mais divergente não envolve o cenário base. A discussão completa está em [`docs/indice_adequacao.md`](../docs/indice_adequacao.md).

O piso é puxado pelo par `infraestrutura` × `percepção`, que discorda justamente em `transito_tranquilo` (0,15 contra 0,35) e em `iluminacao` (0,05 contra 0,30) — as duas dimensões que acabaram de ficar independentes. Quanto menos redundante a dimensão, mais o peso dela importa.

Na prática, **70,4%** das células recebem a mesma classificação alto/baixo em todos os cenários, e **14,9%** se movem dois quartis ou mais.

**Decidido:** o IAC é comunicado como `alto` / `baixo`, nunca como ranking contínuo, sempre acompanhado da contagem de cenários que concordam — [ADR 0003](../docs/adr/0003-alto-baixo-como-unidade-de-comunicacao.md). O contínuo segue no arquivo como insumo; o que muda é o que se afirma em público.

| Concordância entre os 4 cenários | Células | % |
|---|---:|---:|
| `baixo` em todos | 1.424 | 35,3% |
| alternam conforme o peso | 1.191 | 29,6% |
| `alto` em todos | 1.415 | 35,1% |

**2.839 células (70,4%) são conclusão firme.** O limiar também foi testado: entre o percentil 40 e o 60, a fração de estáveis fica entre 70,0% e 72,6%.

E o argumento de que as correções foram necessárias — apesar de cada uma ter derrubado a estabilidade — está escrito em [`docs/indice_adequacao.md`](../docs/indice_adequacao.md), seção "As correções foram necessárias". Em uma linha: a estabilidade mede quanto o resultado depende dos pesos, não se as dimensões medem o que dizem medir, e redundância produz estabilidade espúria.

---

## A inspeção achou um defeito antes mesmo de começar

A observação de que o Parque Barigui — um dos melhores lugares para correr da cidade — ficava no percentil 26 da `densidade_malha` veio de conhecer a cidade, não de teste. Levou à redução de peso acima, e está documentada em [`docs/desafios.md`](../docs/desafios.md), desafio 13.

É o argumento a favor do critério de saída: nenhuma checagem interna acusaria, porque a dimensão estava coerente consigo mesma.

---

## O R1 segue aberto, mas agora é mensurável

478 células (10,6% do município) não têm nenhuma via caminhável no OSM, e **não são células de borda**: 264 estão inteiramente dentro de Curitiba, concentradas na periferia sul e oeste.

Um primeiro teste de completude, comparando as unidades de conservação oficiais com os polígonos do OSM, deu resultado tranquilizador: nos 60 parques e bosques públicos, a **cobertura mediana do OSM é de 93%**, com 52 bem mapeados. Oito não estão — entre eles o BCBU Tatuquara, em bairro de baixa renda.

Com n=8 isso não conclui nada. O teste que importa é a completude por decil de renda, e ele depende dos setores censitários — Fase 3.

> **Ressalva de método.** A primeira versão desse teste deu "4,3% de cobertura", número que teria sugerido catástrofe. Era artefato: a camada inclui duas APAs somando 197 km², que são zoneamento e não parque. Separar por categoria antes de medir mudou a conclusão por completo.

---

## O que a inspeção visual encontrou

Oito `parcial` em 25, nenhum `não confere`, e as causas se repetem num padrão curto:

| Causa | Células | Desfecho |
|---|--:|---|
| `surface` não medido (rua de terra com IAC alto) | 3 | Limitação 11 — a etiqueta está ausente em 62,1% da rede e não pode ser usada |
| Pista de atletismo invisível para o índice | 1 | Limitação 10 — forma funcional errada, dimensão nova no backlog |
| Célula heterogênea de 0,1 km² | 2 | Risco R4, já documentado |
| Lacuna na camada **oficial** de postes | 1 | Novo: a camada do GeoCuritiba era tratada como completa |
| Confusão entre segurança viária e criminalidade | 1 | Dimensão renomeada para `transito_tranquilo` |

Os dois casos que eu havia marcado como "olhar com atenção redobrada" — Marechal Floriano Peixoto e Manoel Ribas — conferiram os dois. **O índice estava certo e minha leitura da cidade estava errada nos dois.**

---

## Pendente para fechar a fase

- [x] `reports/validacao_iac.md` — inspeção visual de amostra estratificada, com os oito `parcial` explicados um a um. **Critério de saída cumprido.**
- [ ] Recalcular com as duas correções pendentes (`lit` desligada; `tertiary` e `busway` reclassificados) e reconferir os diagnósticos
- [x] Mapa de robustez: `robustez_da_classificacao` grava `classe`, `n_alto` e `estavel` no parquet da Fase 1 — gravadas e conferidas em 7/10, coerentes com o IAC em todas as 4.508 células
- [ ] Decidir se a declividade passa a ser medida ao longo das vias, em vez de média do terreno da célula

### Fora da Fase 1

- [ ] Ciclovias oficiais do GeoCuritiba, que ainda não entraram no `espaco_dedicado`
- [ ] Setores censitários com renda — já localizados no GeoCuritiba, insumo da Fase 3
- [ ] Dimensão de **proximidade a equipamento esportivo**, que é o que falta para o índice ver uma pista de atletismo — arrasta a decisão sobre acesso público (limitação 10)
- [ ] Conferir a completude da camada oficial de postes: uma célula da inspeção tem 6,34 km de via e iluminação no chão da distribuição
