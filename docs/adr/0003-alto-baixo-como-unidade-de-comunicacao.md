# ADR 0003 — Alto/Baixo é a unidade de comunicação do IAC

**Status:** aceito

## Contexto

O IAC é um número contínuo de 0 a 1 por célula, e a tentação natural é comunicá-lo como ranking: "esta célula é a 312ª melhor de Curitiba". A análise de sensibilidade a pesos mostra que essa afirmação não se sustenta.

Os pesos do índice são escolha do autor, não resultado de estimação. Sob os quatro esquemas testados — `base`, `iguais`, `infraestrutura` e `percepção` — a posição de cada célula se move:

| Recorte | Concordância entre os 4 cenários |
|---|---:|
| Mesmo quartil | 41,4% das células |
| Varia 1 quartil | 43,7% |
| Varia 2 ou mais | 14,9% |
| **Mesma classificação alto/baixo** | **70,4%** |

O piso de estabilidade de ranking (Spearman) é de **0,624**, entre `infraestrutura` e `percepção`. Esses dois cenários existem para ser opostos: um afirma que adequação é provisão física, o outro que é segurança percebida. São posições que pessoas reais defendem, e a divergência entre elas é informação sobre o problema, não ruído a ser suprimido.

## Decisão

**O IAC é comunicado como classificação binária `alto` / `baixo`, com corte na mediana do município, acompanhada obrigatoriamente da contagem de cenários que concordam.**

Implementado em `features/suitability_index.py`:

- `classificar_alto_baixo(iac, corte=None)` — a classe, cortada na mediana por padrão.
- `robustez_da_classificacao(cenarios, quantil=0.5)` — por célula, a classe em cada cenário, `n_alto`, e `estavel`.
- `resumo_da_robustez(robustez)` — a tabela de concordância para o relatório.

A Fase 1 grava `classe`, `n_alto` e `estavel` no `iac_h3_r9.parquet`, ao lado do valor contínuo. O contínuo não sai do arquivo: ele continua sendo o insumo de toda a análise. O que muda é **o que se afirma em público**.

Distribuição medida em Curitiba, 4.030 células:

| Concordância | Células | % |
|---|---:|---:|
| `baixo` em todos os 4 cenários | 1.424 | 35,3% |
| alto em 1 de 4 | 449 | 11,1% |
| alto em 2 de 4 | 275 | 6,8% |
| alto em 3 de 4 | 467 | 11,6% |
| `alto` em todos os 4 cenários | 1.415 | 35,1% |

**2.839 células (70,4%) são estáveis** — são as conclusões firmes. As 1.191 restantes são o índice dizendo "depende do que você valoriza", e dizer isso é parte do resultado.

## Justificativa

**Reportar alto/baixo não é perder resolução — é parar de afirmar uma precisão que o índice não tem.** 70,4% contra 41,4% não é uma escolha de conveniência: é a diferença entre uma afirmação que sobrevive à arbitrariedade dos pesos e uma que não sobrevive.

**O limiar também é arbitrário, e também foi testado.** Variando o corte entre o percentil 40 e o 60, a fração de células estáveis fica entre **70,0% e 72,6%**. A classificação é robusta ao limiar, não só aos pesos.

**O corte é por cenário, não absoluto.** Cada esquema de pesos produz sua própria escala, e `alto` significa "na metade superior *daquele* ranking". Um corte absoluto comum confundiria nível com posição: somar uma constante a um cenário não altera o ranking dele, mas mudaria a classe de centenas de células. Medido — o número de estáveis cairia de 70,4% para 36,2%, instabilidade inteiramente fabricada. A primeira versão desta função tinha esse defeito e foi corrigida; dois testes agora o travam.

**A tipologia de quadrantes da Fase 4 já depende disso.** `features/typology.py` cruza alto/baixo de IAC com alto/baixo de risco. Adotar a classe binária como unidade de comunicação torna o pipeline coerente de ponta a ponta, em vez de binarizar só no último passo.

## Alternativas rejeitadas

**Ajustar os pesos até a estabilidade subir.** Testado e descartado por ser inócuo e desonesto: três conjuntos alternativos de pesos para o cenário `base` deixam o piso inalterado em 0,624, porque o par mais divergente não envolve o `base`. A única forma de elevar o número seria aproximar os cenários entre si — isto é, testar menos para obter um resultado mais tranquilizador.

**Reportar o ranking contínuo com intervalo de incerteza.** Mais informativo em princípio, mas a incerteza aqui não é amostral e não tem distribuição: vem de uma escolha de valores. Um intervalo sugeriria uma interpretação probabilística que não existe.

**Tercis ou quartis em vez de binário.** Mantêm parte do problema — 41,4% de concordância de quartil — sem ganho de interpretação. Binário é o recorte mais grosso e, por isso, o único que resiste.

## Consequências

- Mapas e tabelas de resultado usam duas classes, e as células instáveis aparecem marcadas, não omitidas.
- O mapa de robustez sai do backlog e passa a ser camada de resultado.
- Peso só muda por razão substantiva — literatura ou pergunta de pesquisa. Nunca para melhorar a métrica de estabilidade; aí o número vira decoração.
- Comparações finas entre células ("A é melhor que B") ficam fora do que o projeto afirma, a menos que A e B estejam em classes estáveis diferentes.
