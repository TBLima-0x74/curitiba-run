# Validação visual do IAC

Amostra estratificada de 25 células para conferência contra imagem de satélite e Street View. É o critério de saída da Fase 1: verificar se IAC alto e IAC baixo correspondem ao que se vê.

**Como usar:** abra os dois links de cada linha, olhe, e preencha a coluna *Confere?* com `sim`, `não` ou `parcial`. Quando não conferir, anote o porquê na seção de desacordos no fim — é essa explicação que fecha o critério, não a nota em si.

**Desenho da amostra.** Sorteadas entre as 3.896 células que têm IAC e estão pelo menos 90% dentro do município, com no máximo uma por célula-pai H3 de resolução 6 — isso impede que a amostra se amontoe num bairro só. Três estratos: os 10 maiores IAC, os 10 menores, e 5 casos onde as dimensões mais discordam entre si, que são os mais informativos.

**Valores conferidos contra `data/processed/iac_h3_r9.parquet` em 7/10, com o peso de `densidade_malha` já em 0,15.** As colunas são valores brutos, não normalizados — é o que permite julgar contra o que se vê.

| Coluna | O que é | Mediana do município |
|---|---|---:|
| `malha` | Densidade da malha caminhável, 0 a 1 | 0,27 |
| `espaço` | Fração da célula ocupada por parque ou praça | 0,01 |
| `segur` | Proporção da extensão em via de baixo tráfego | 0,80 |
| `decliv` | Declividade média, **em graus** | 4,0° |
| `ilum` | Iluminação: postes por km de via e cobertura `lit` | 0,26 |

O IAC não é a média dessas colunas: cada uma é normalizada contra a distribuição do município antes de entrar, e a declividade entra invertida. Uma célula pode ter valores brutos modestos e IAC alto se estiver acima da mediana em tudo.

---

## IAC alto — deve parecer bom para correr

Espere calçada contínua, quarteirão curto, pouco tráfego pesado, terreno plano.

| Rua de referência | IAC | malha | espaço | segur | decliv | ilum | Satélite | Street View | Confere? |
|---|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| Alameda Ecológica Burle Marx | **0,86** | 0,55 | 0,70 | 1,00 | 2,5° | 0,47 | [ver](https://www.google.com/maps/search/?api=1&query=-25.4291,-49.31444&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.4291,-49.31444) |  confere |
| Rua Dino Bertoldi | **0,84** | 0,89 | 0,68 | 0,97 | 1,8° | 0,08 | [ver](https://www.google.com/maps/search/?api=1&query=-25.42784,-49.22003&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.42784,-49.22003) |  **parcial** |
| Avenida Marechal Floriano Peixoto | **0,82** | 0,61 | 0,83 | 0,71 | 1,6° | 0,63 | [ver](https://www.google.com/maps/search/?api=1&query=-25.52609,-49.22342&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.52609,-49.22342) |  confere |
| Rua Manoel Ordones | **0,77** | 0,34 | 0,45 | 1,00 | 2,0° | 0,20 | [ver](https://www.google.com/maps/search/?api=1&query=-25.53462,-49.2298&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.53462,-49.2298) |  **parcial** |
| Rua Maria Cândida de Souza | **0,74** | 0,20 | 0,36 | 1,00 | 3,0° | 0,50 | [ver](https://www.google.com/maps/search/?api=1&query=-25.39246,-49.30404&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.39246,-49.30404) |  confere |
| Rua Alceu José Guadagnin | **0,73** | 0,36 | 0,37 | 1,00 | 2,2° | 0,22 | [ver](https://www.google.com/maps/search/?api=1&query=-25.44859,-49.19943&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.44859,-49.19943) |  confere |
| Rua Mateus Leme | **0,70** | 0,37 | 0,40 | 0,83 | 7,3° | 0,57 | [ver](https://www.google.com/maps/search/?api=1&query=-25.38294,-49.26719&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.38294,-49.26719) |  confere |
| _(sem via nomeada)_ | **0,69** | 1,00 | 0,07 | 1,00 | 3,3° | 0,60 | [ver](https://www.google.com/maps/search/?api=1&query=-25.44545,-49.36065&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.44545,-49.36065) |  **parcial** |
| Rua Buenos Aires | **0,68** | 1,00 | 0,13 | 0,93 | 2,8° | 0,48 | [ver](https://www.google.com/maps/search/?api=1&query=-25.44808,-49.27552&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.44808,-49.27552) |  confere |
| Rua Wacílio Zacachuka | **0,68** | 0,41 | 0,25 | 0,94 | 2,5° | 0,45 | [ver](https://www.google.com/maps/search/?api=1&query=-25.55755,-49.3341&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.55755,-49.3341) |  confere |

## IAC baixo — deve parecer ruim para correr

Espere rodovia sem calçada, via sem saída, terreno íngreme ou área não urbanizada.

| Rua de referência | IAC | malha | espaço | segur | decliv | ilum | Satélite | Street View | Confere? |
|---|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| Rodovia Vereador Admar Bertolli | **0,02** | 0,04 | 0,00 | 0,00 | 11,3° | 0,00 | [ver](https://www.google.com/maps/search/?api=1&query=-25.3837,-49.34634&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.3837,-49.34634) |  confere |
| Rua Massao Suguimoto | **0,09** | 0,07 | 0,00 | 0,18 | 6,4° | 0,00 | [ver](https://www.google.com/maps/search/?api=1&query=-25.51639,-49.34789&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.51639,-49.34789) |  confere |
| Rua Paulo Kulik | **0,09** | 0,05 | 0,00 | 0,06 | 9,6° | 0,25 | [ver](https://www.google.com/maps/search/?api=1&query=-25.35511,-49.2358&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.35511,-49.2358) |  confere |
| Estrada Delegado Bruno de Almeida | **0,10** | 0,06 | 0,00 | 0,15 | 8,2° | 0,20 | [ver](https://www.google.com/maps/search/?api=1&query=-25.63232,-49.35191&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.63232,-49.35191) |  confere |
| Rua Vereador Ângelo Burbello | **0,11** | 0,05 | 0,00 | 0,11 | 8,2° | 0,24 | [ver](https://www.google.com/maps/search/?api=1&query=-25.57483,-49.29817&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.57483,-49.29817) |  confere |
| Rua Leonardo Kubis | **0,11** | 0,05 | 0,00 | 0,50 | 13,8° | 0,02 | [ver](https://www.google.com/maps/search/?api=1&query=-25.41744,-49.37793&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.41744,-49.37793) |  confere |
| Rua Padre Paulo Canelles | **0,11** | 0,00 | 0,00 | 0,00 | 11,2° | 0,50 | [ver](https://www.google.com/maps/search/?api=1&query=-25.36068,-49.24208&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.36068,-49.24208) |  confere |
| Avenida Manoel Ribas | **0,11** | 0,16 | 0,00 | 0,15 | 8,8° | 0,23 | [ver](https://www.google.com/maps/search/?api=1&query=-25.41083,-49.31989&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.41083,-49.31989) |  confere |
| Rua João Chede | **0,12** | 0,07 | 0,00 | 0,05 | 5,5° | 0,08 | [ver](https://www.google.com/maps/search/?api=1&query=-25.52773,-49.31176&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.52773,-49.31176) |  confere |
| Estrada do Ganchinho | **0,14** | 0,05 | 0,01 | 0,07 | 6,3° | 0,23 | [ver](https://www.google.com/maps/search/?api=1&query=-25.57852,-49.26481&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.57852,-49.26481) |  confere |

## Dimensões em desacordo — os casos que mais ensinam

Células em que uma dimensão é alta e outra é baixa. Se o índice erra, é aqui que aparece primeiro.

| Rua de referência | IAC | malha | espaço | segur | decliv | ilum | Satélite | Street View | Confere? |
|---|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| _(sem via nomeada)_ | **0,70** | 0,01 | 0,87 | 1,00 | 1,1° | 0,00 | [ver](https://www.google.com/maps/search/?api=1&query=-25.54354,-49.23011&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.54354,-49.23011) |  **parcial** |
| _(sem via nomeada)_ | **0,68** | 0,13 | 0,51 | 1,00 | 3,8° | 0,00 | [ver](https://www.google.com/maps/search/?api=1&query=-25.51032,-49.21374&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.51032,-49.21374) |  **parcial** |
| _(sem via nomeada)_ | **0,64** | 0,14 | 0,70 | 1,00 | 7,0° | 0,00 | [ver](https://www.google.com/maps/search/?api=1&query=-25.61017,-49.32679&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.61017,-49.32679) |  **parcial** |
| Rua Konrad Adenauer | **0,62** | 0,29 | 0,49 | 0,13 | 2,6° | 0,83 | [ver](https://www.google.com/maps/search/?api=1&query=-25.4189,-49.21973&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.4189,-49.21973) |  **parcial** |
| Rua Lory Lunardon | **0,62** | 0,42 | 0,39 | 1,00 | 13,4° | 0,23 | [ver](https://www.google.com/maps/search/?api=1&query=-25.37747,-49.28222&basemap=satellite) | [ver](https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-25.37747,-49.28222) |  **parcial** |

---

## Dois casos que eu pedi para olhar com atenção redobrada

Os dois eram pontos em que meu conhecimento da cidade divergia do índice. **Nos dois o índice estava certo e eu errado** — registrado porque o erro foi meu, e porque é o tipo de divergência que a inspeção existe para resolver.

**Avenida Marechal Floriano Peixoto, entre os IAC mais altos: confere.** A célula pontua pelo miolo residencial em volta, como eu havia levantado como a hipótese favorável. A dimensão de segurança viária não estava diluindo tráfego pesado.

**Avenida Manoel Ribas, entre os IAC mais baixos: confere.** Eu esperava que IAC baixo ali fosse erro. A célula tem só **1,80 km** de via caminhável mapeada, `espaco_dedicado` de 0,001 e segurança viária de 0,148 — o ponto caiu num trecho em que a avenida domina e não há malha residencial em volta. O número está descrevendo a célula, não o bairro das Mercês.

---

## Desacordos encontrados

Nenhuma célula recebeu **não confere**. Os oito `parcial` estão abaixo, com a causa identificada em cada um. Nenhum deles é erro de cálculo: são todos limites do dado ou do construto, e **dois são achados novos** que foram incorporados à documentação.

| Rua | O que o índice diz | O que se vê | Causa provável |
|---|---|---|---|
| Rua Dino Bertoldi | `ilum` 0,08, no chão da distribuição, com IAC 0,84 | Rua residencial com iluminação aparentemente normal | **Lacuna na camada oficial de postes.** A célula tem 6,34 km de via mapeada; com tão poucos postes por km, ou o trecho falta na camada do GeoCuritiba, ou o denominador está inflado por via de serviço. O projeto tratava a camada oficial como completa — não é garantido |
| Rua Manoel Ordones | IAC 0,77, entre os melhores | Rua sem asfalto | **Pavimento não é medido.** `surface` está ausente em **100% dos 3,59 km** dessa célula, e em 62,1% da rede do município. Ver limitação 11 |
| _(sem via nomeada)_ — pista da Universidade Positivo | IAC 0,69 (percentil 98,7), `malha` 1,00, `espaço` 0,07 | Pista de atletismo, lugar excelente para correr | **A pista é invisível para o índice.** Acertou o resultado pelo motivo errado: pontuou pela malha densa do Ecoville em volta, não pela pista. Ver limitação 10 |
| Rua Konrad Adenauer | IAC 0,62, `segur` 0,13, `ilum` 0,83 | Rua movimentada, com risco de assalto percebido | **O índice não mede criminalidade** — `seguranca_viaria` é trânsito. A dimensão até acusou a via arterial corretamente (0,13). O que falta é a Fase 2 — e esta observação é o que motivou renomear a dimensão para `transito_tranquilo` |
| Rua Lory Lunardon | IAC 0,62 com `decliv` 13,4° | Trilha íngreme | **Célula heterogênea, e o teto de declividade.** 13,4° é quase o teto de 15°, então a dimensão saturou; as outras quatro compensaram |
| _(sem via nomeada)_, 0,70 | `malha` 0,01 e `espaço` 0,87 | Trilha — "não é ideal para correr, mas é possível" | Não é desacordo de verdade: o julgamento foi que **a nota é válida**. Fica registrado como caso em que a célula tem 0,12 km de via e o índice sobrevive de `espaco_dedicado` |
| _(sem via nomeada)_, 0,68 | `malha` 0,13, `espaço` 0,51, `ilum` 0,00 | "No meio do mato, mas tem uma pista nas proximidades" | **Transbordamento acertando por sorte.** A suavização com o anel vizinho puxou a célula para cima, e há mesmo pista por perto — mas o índice não sabe disso, só sabe que o vizinho tem área verde |
| _(sem via nomeada)_, 0,64 | IAC 0,64 | Estrada de terra | Mesma causa da Manoel Ordones: `surface` ausente em 100% dos 1,71 km da célula |

---

## Conclusão

- Células conferidas: **25 de 25**
- **Confere: 17 · Parcial: 8 · Não confere: 0**
- O índice é defensável para seguir à Fase 2? **Sim, com as limitações 10 e 11 registradas.**

O resultado mais importante não é a contagem, é **onde** os acertos caem.

**Os 10 IAC baixos conferiram todos.** É o que mais importa para a pergunta do projeto, porque a hipótese H1 é uma afirmação sobre o extremo inferior: se o índice inventasse carência onde não há, a conclusão inteira cairia. Rodovia sem calçada, estrada rural, terreno íngreme — o índice está vendo o que diz ver.

**Nenhum `não confere` em 25 células.** E os oito `parcial` se distribuem num padrão legível: três são o mesmo defeito (`surface` não medido), um é construto (a pista), um é lacuna de dado oficial (os postes), um é o nome da dimensão de segurança, e dois são células heterogêneas — o problema estrutural da resolução r9, já documentado como risco R4.

**O estrato de "dimensões em desacordo" produziu 5 de 5 `parcial`,** e nenhum `confere`. Era o desenho: é o estrato construído para quebrar o índice. Que ele produza divergência parcial e não erro grosseiro é o melhor resultado possível ali.

Duas ressalvas de método sobre esta própria validação:

1. **n = 25, e a inspeção é de quem construiu o índice.** Não é validação cega. Serve para detectar defeito grosseiro, que é o que se pretendia, e não para estimar acurácia.
2. **O julgamento é por imagem de satélite e Street View**, cuja data não coincide com a do OSM nem com a do MDT 2019.
