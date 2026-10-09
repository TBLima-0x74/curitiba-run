# ADR 0005 — O peso de gravidade de cada ocorrência vem da pena mínima do Código Penal

**Status:** aceito

## Contexto

A camada de risco da Fase 2 soma ocorrências por bairro, e uma soma simples trata um estupro e um furto como equivalentes. Era preciso um peso de 0 a 1 por tipo, em que o mais grave pese mais.

O problema de qualquer peso é o mesmo dos pesos do IAC (ADR 0003): ele é uma escolha. A diferença é que, aqui, existe uma referência externa pronta — **a lei já gradua a gravidade de cada crime, pela pena**.

## Decisão

**O peso de cada tipo é a pena mínima do caput, na redação vigente, dividida pela maior pena mínima da tabela.** O tipo mais grave vale 1.

É o método do *Cambridge Crime Harm Index* (Sherman, Neyroud e Neyroud, 2016), que pondera cada crime pela pena que a legislação atribui a ele, adaptado ao Código Penal brasileiro.

Quatro regras completam o método, todas implementadas em `features/gravidade.py`:

1. **Tentativa** vale metade do consumado. O art. 14, parágrafo único, do CP reduz a pena de 1/3 a 2/3; metade é o ponto médio da faixa legal.
2. **Tentativa de contravenção não existe** (art. 4º da LCP). "Tentativa de agressão" entra como tentativa de lesão corporal, o tipo menos grave que admite tentativa.
3. **Tipo ambíguo** vira o tipo menos grave compatível com o registro. "Agressão física/verbal" pode ser lesão corporal ou injúria; entra como vias de fato. Na dúvida, o projeto não inflaciona o risco.
4. **Os pesos são calculados, nunca digitados.** A tabela guarda a pena e a base legal de cada tipo; o peso sai dela. Mudar uma pena muda o peso, sem número solto para esquecer.

| Tipo | Base legal | Pena mínima | Peso |
|---|---|---:|---:|
| Homicídio | art. 121, CP | 6 anos | 1,000 |
| Estupro | art. 213, CP | 6 anos | 1,000 |
| Roubo a transeunte | art. 157, CP (Lei 15.397/2026) | 6 anos | 1,000 |
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

A medida por bairro é `gravidade_anual` = Σ peso das ocorrências ÷ anos cobertos.

## Justificativa

**Critério externo, público e reprodutível.** Uma escala inventada pelo autor ("estupro 0,9, furto 0,2") seria impossível de defender ponto a ponto. Com a pena como critério, quem discorda de um peso está discordando do legislador — e pode trocar a regra num lugar só, sem tocar no resto do pipeline.

**Pena mínima, e não máxima.** A mínima é a pena do caso típico, sem agravantes; a máxima é o teto do pior caso. O *Crime Harm Index* usa o ponto de partida da pena para um réu primário pela mesma razão: ele descreve o crime comum, que é o que a base registra.

**O resultado é robusto à escolha da regra.** Trocando a pena mínima pelo ponto médio entre mínima e máxima (`gravidade.pesos("media")`):

| Comparação | Resultado |
|---|---:|
| ρ de Spearman do ranking dos 75 bairros | **0,993** |
| Bairros na mesma classe alto/baixo | **94,7%** (71 de 75) |

Como a comunicação do projeto é por classe alto/baixo (ADR 0003), a escolha entre as duas regras muda a conclusão de 4 bairros.

## Alternativas rejeitadas

**Contagem simples, sem peso.** Trata estupro e furto como iguais, que foi exatamente o que motivou a decisão. E seria dominada por ameaça e vias de fato, que são 53,4% das ocorrências — justamente os tipos sem subcategoria, em que violência doméstica pode estar misturada.

**Escala definida pelo autor.** Arbitrária e indefensável item a item.

**Pena máxima.** Descreve o pior caso, não o típico, e comprime as diferenças: furto (6 anos) passaria a valer 60% do estupro (10 anos), contra 17% pela pena mínima.

**Escala logarítmica da pena.** Atenuaria a distância de 146 vezes entre homicídio e vias de fato (6 anos contra 15 dias). Fica como possibilidade de sensibilidade, não como padrão: transformar a pena é uma segunda escolha do autor em cima da do legislador.

## Consequências

- **Roubo empata com estupro e homicídio.** A Lei nº 15.397, de 30 de abril de 2026, elevou a pena mínima do roubo simples para 6 anos. A tabela segue a lei vigente. Quase todo o período da base (2023 a abril de 2026) correu sob a pena anterior, de 4 anos, com a qual o roubo valeria 0,667. **O peso representa a avaliação atual do legislador, não a da data do fato** — escolha registrada, não acidente.
- **Na prática, a camada mostra roubo a transeunte.** Ele responde por 77,4% da gravidade total (60,0% com o ponto médio). Quem lê o mapa precisa saber disso.
- **`gravidade_anual` é a medida; `n_ocorrencias` não.** Ameaça e vias de fato são 53,4% das ocorrências e 2,6% da gravidade.
- **A regra do tipo menos grave subestima** onde a ambiguidade esconde casos graves. É a direção conservadora, e é deliberada.
- **Nova lei penal exige revisar a tabela.** Os pesos dependem da redação vigente; uma mudança de pena muda o peso no próximo cálculo.

As regras de inclusão de cada tipo e a contagem de ocorrências estão em [`../taxonomia_ocorrencias.md`](../taxonomia_ocorrencias.md).

## Fontes

- Sherman, L.; Neyroud, P. W.; Neyroud, E. (2016). *The Cambridge Crime Harm Index: Measuring Total Harm from Crime Based on Sentencing Guidelines*. Policing, 10(3), 171–183.
- Decreto-Lei nº 2.848/1940 (Código Penal) e Decreto-Lei nº 3.688/1941 (Lei das Contravenções Penais), redação vigente.
- [Lei nº 15.397, de 30 de abril de 2026](https://www2.camara.leg.br/legin/fed/lei/2026/lei-15397-30-abril-2026-799020-norma-pl.html)
- Lei nº 10.826/2003 (Estatuto do Desarmamento), art. 15.
