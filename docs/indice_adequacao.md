# Índice de Adequação à Corrida (IAC)

Índice composto que mede, por célula da malha H3, **quão adequado é o território para correr na rua** — ignorando deliberadamente se as pessoas correm ali.

Cinco dimensões, média ponderada, escala 0 a 1.

```
IAC(c) = Σ  w(d) × x̃(d, c)        com  Σ w(d) = 1
```

---

## As cinco dimensões

| Dimensão | O que mede | Valor bruto | Unidade | Fonte |
|----------|------------|-------------|---------|-------|
| `densidade_malha` | Quanto percurso existe e quantas rotas são possíveis | Média de duas componentes normalizadas: km de via caminhável por km² e interseções por km² | 0–1 | OSM |
| `espaco_dedicado` | Espaço projetado para estar a pé | Área de parque, praça e pista na célula ÷ área, suavizada com a média dos vizinhos | fração | OSM + IPPUC |
| `transito_tranquilo` | Quanto da via mapeada é de baixo tráfego — **trânsito, não criminalidade** | Extensão em via de baixo tráfego ÷ extensão total | razão | OSM |
| `declividade` | Se dá para correr continuamente | Declividade média da célula | **graus** | MDT 2019 do IPPUC |
| `iluminacao` | Viabilidade fora da luz do dia | Postes **por km de via** combinados com a fração de via com `lit=yes` | 0–1 | GeoCuritiba + OSM |

### Decisões de medida que explicam resultados estranhos

**Densidade contra razão.** `densidade_malha` pergunta *quanto existe*; `transito_tranquilo` e `iluminacao` perguntam *qual a qualidade do que existe*. A distinção não é cosmética: uma célula cortada por via expressa tem muita extensão e péssima adequação, e misturar os dois tipos de medida esconderia justamente esse caso.

**Ausência de via não é via ruim.** Células sem nenhuma via caminhável recebem valor ausente em `transito_tranquilo` e em `iluminacao`, nunca zero. Como o índice exige as cinco dimensões, essas células ficam sem IAC — são **478, ou 10,6% do município**.

**Parque transborda.** `espaco_dedicado` mistura o valor da célula com a média do anel vizinho, meio a meio: um parque grande beneficia quem mora ao lado, não só quem está dentro do hexágono.

**Declividade guarda graus.** O valor bruto fica em graus, e a inversão (mais é pior) acontece na normalização, via `IAC_DIMENSOES_INVERTIDAS`. Assim o relatório pode dizer "média de 4,2°", que comunica, em vez de "0,71 normalizado", que não.

### O que a classe da via não mede

`transito_tranquilo` lê a etiqueta `highway` do OSM e nada mais. Vale dizer de saída o que isso implica, porque o nome promete mais do que a medida entrega.

**O nome, primeiro.** A dimensão chamava-se `seguranca_viaria` e foi renomeada para `transito_tranquilo`. Ela mede segurança **no trânsito** e não contém um único dado de criminalidade; como a Fase 2 cruza o índice com ocorrências policiais, duas colunas vizinhas com nomes parecidos enganavam na leitura — e enganaram, aqui dentro, na leitura do próprio resultado.

**O que a etiqueta descreve.** `highway` classifica a via pela função que ela cumpre **para o automóvel**: hierarquia de tráfego, não experiência de quem anda. A dimensão só serve de proxy para "agradável de correr" na medida em que as duas coisas andam juntas, e em Curitiba elas andam juntas apenas em parte:

| | km | % da rede |
|---|---:|---:|
| `footway`, `path`, `steps` — passeio ou trilha mapeada à parte | 1.106 | **9,3%** |
| Eixo de rua — o pedestre viaja no leito da via | — | **90,7%** |

Em 90,7% da rede a nota da célula é, literalmente, uma afirmação sobre carros. Uma avenida de calçada larga e arborizada e uma marginal sem passeio recebem a mesma classificação, porque o OSM as etiqueta igual. **O índice conta a via; não avalia o passeio.** Largura, pavimento, arborização, qualidade de travessia e ocupação por carro estacionado não entram — e não existem como dado para Curitiba na escala do município.

Isso é limite do dado disponível, não do cálculo. A correção honesta não é um coeficiente de ajuste: é não ler a dimensão como qualidade de percurso. O que ela sustenta é a afirmação mais estreita de que *a via mapeada aqui é predominantemente coletora/arterial*, ou não é.

### A composição da rede, e a reclassificação que ela motivou

A observação veio de olhar o resultado: células em 0 em lugares que não são perigosos. Um 0 significa **100% da extensão caminhável mapeada classificada como alto tráfego** — e são poucas: 30 células (0,7%), 85 abaixo de 0,2.

| Classe | km | % da rede | Classificação |
|---|---:|---:|---|
| `residential` | 6.382 | 48,6% | baixo |
| `service` | 1.940 | 14,8% | baixo |
| `tertiary` | 1.248 | 9,5% | **ambíguo** (era alto) |
| `secondary` | 1.110 | 8,4% | alto |
| `footway` | 1.106 | 8,4% | baixo |
| `primary` | 418 | 3,2% | alto |
| `living_street` | 196 | 1,5% | baixo |
| `trunk` | 163 | 1,2% | alto |
| `busway` | 158 | 1,2% | **alto** (era ambíguo) |
| `unclassified` | 149 | 1,1% | ambíguo |

Nas células zeradas, **73,5% da extensão é `tertiary`**, 15,2% `secondary` e 11,4% `trunk`. Quase todo o fenômeno vinha de uma classe só — e `tertiary` no OSM é **coletora de bairro**: comércio, faixa de pedestre, carro a 40. Agrupá-la com `motorway` e `trunk` era o erro. Forçá-la para baixo tráfego seria o erro oposto, então ela virou ambígua, com 0,5, junto de `unclassified`.

Na direção contrária, `busway` — a canaleta do BRT, via exclusiva de biarticulado — valia 0,5 por omissão, por não constar de nenhuma das listas. Passou a alto tráfego.

| | antes | depois |
|---|---:|---:|
| Mediana | 0,802 | **0,864** |
| Células em exatamente 0 | 30 | **10** |
| Células abaixo de 0,2 | 85 | **40** |
| Células em exatamente 1 | 1.180 | 1.180 |

ρ de Spearman de **0,970** entre as duas versões: a correção acerta a cauda, que é onde o defeito estava, sem remexer o corpo da distribuição. Os quatro valores da tabela foram medidos antes de recalcular e **confirmados exatamente** depois.

No IAC final, o efeito desta correção isolada seria pequeno — mediana de 0,415 para 0,418, ρ dos rankings de 0,970, 1.203 células trocando de quartil. O recálculo, porém, aplicou **as três correções de uma vez** (reclassificação, `lit` desligado e o rename), e o efeito conjunto é maior: mediana de **0,4146 para 0,4255**, ρ dos rankings de **0,9115** e **1.164 células** trocando de quartil. Quase todo o movimento vem da iluminação, não da hierarquia viária.

Para que um 0,5 por decisão não se confunda com um 0,5 por desconhecimento, `classificar_hierarquia_viaria` agora **avisa** quando encontra uma classe fora das três listas — o OSM cria etiquetas novas, e sem o aviso ela entraria como ambígua em silêncio.

---

---

## Os dois filtros de entrada

### Postes: só os que iluminam

A camada de postes do GeoCuritiba traz **179.401 feições** e um domínio codificado em `tipoposte`:

| Código | Significado | Quantidade | Entra? |
|--------|-------------|-----------:|:------:|
| 2 | Iluminação | 154.850 | ✅ |
| 4 | Rede elétrica | 24.550 | ❌ |
| 3 | Ornamental | 1 | ✅ |
| 0, 5, 99 | Desconhecido, sinalização, outros | 0 | ❌ |

Poste de rede elétrica é distribuição de energia e não ilumina nada. Contá-lo faria a dimensão premiar bairros com rede aérea, que não é o que se quer medir.

**Não há ponderação entre tipos, e isso foi verificado.** A pergunta natural é se um poste "vale" mais que outro, por área iluminada ou potência. Para esta camada, não:

- `tipoposte` é classificação **funcional**, não escala de intensidade — não há ordem entre as categorias.
- A camada **não traz** potência, luminária, lâmpada, carga nem altura. Sem fluxo luminoso e sem altura, a área iluminada por poste não é derivável.
- `matconstr` é material de construção (concreto, metal, madeira), sem relação estável com intensidade luminosa.

Qualquer peso entre tipos seria inventado. A decisão correta é binária: manter os que iluminam, descartar os que não iluminam. A justificativa vive em `ingestion.geocuritiba.equivalencia_entre_tipos_de_poste` e é coberta por teste.

### Áreas verdes: só espaço público aberto

O Sistema Municipal de Unidades de Conservação tem **134 unidades somando 219,8 km²** — mais de metade do município. Depois do filtro: **59 unidades, 11,53 km²**.

| Categoria | Unidades | Entra? | Por quê |
|-----------|---------:|:------:|---------|
| Parque Natural Municipal, Parque Linear | 34 | ✅ | Espaço público aberto |
| Bosque Municipal | 17 | ✅ | Espaço público aberto |
| Bosque de Conservação da Biodiversidade Urbana | 8 | ✅ | Espaço público aberto |
| **RPPNM** — Reserva Particular do Patrimônio Natural Municipal | 67 | ❌ | **Propriedade privada.** O município concede benefício fiscal em troca da preservação; não há acesso público |
| **APA** — Área de Proteção Ambiental | 2 | ❌ | **197 km² de zoneamento ambiental.** Incluir faria o índice declarar que meia Curitiba é parque |
| ESEC, RVS, ARIE, Específicas | 6 | ❌ | Acesso restrito ou categoria heterogênea |

O download é feito por camada do FeatureServer, que tem uma por categoria — mais limpo que filtrar por atributo depois.

---

## Normalização e pesos

### De bruto para 0–1

```
x̃ = ( clip(x, p2, p98) − p2 ) / ( p98 − p2 )
```

Truncar nos percentis 2 e 98 impede que uma célula extrema comprima toda a distribuição. Dimensões invertidas entram como `1 − x̃`.

**Quando a série é constante, a função avisa.** Se p2 e p98 coincidem, a fórmula dividiria por zero; a função devolve 0,5 para todas as células **e emite warning nomeando a dimensão**. Sem esse aviso, uma dimensão morta vira constante invisível — foi exatamente o que aconteceu com os 523 postes do OSM, que injetaram 0,25 fixo em toda célula sem uma linha de log.

### Os pesos

| Dimensão | base | iguais | infraestrutura | percepção |
|----------|-----:|-------:|---------------:|----------:|
| `densidade_malha` | **0,15** | 0,20 | 0,30 | 0,10 |
| `espaco_dedicado` | **0,30** | 0,20 | 0,40 | 0,15 |
| `transito_tranquilo` | 0,25 | 0,20 | 0,15 | 0,35 |
| `declividade` | 0,15 | 0,20 | 0,10 | 0,10 |
| `iluminacao` | 0,15 | 0,20 | 0,05 | 0,30 |

### Por que a etiqueta `lit` do OSM ficou de fora

A dimensão era metade postes oficiais, metade fração de via com `lit=yes`. A segunda metade saiu.

| | postes/km | `lit=yes` |
|---|---:|---:|
| Mediana bruta | 12,4 postes/km | **0,000** |
| Mediana normalizada | 0,461 | **0,000** |
| Células com valor zero | — | **65,9%** |

Valendo metade do peso, a componente rebaixava a dimensão por construção. Células com densidade de poste no quartil superior ficavam com nota mediana de 0,34, e um terço abaixo de 0,3.

**Ausência no OSM significa "ninguém mapeou", não "não há iluminação".** Além disso, quem mapeia `lit` mapeia avenida: a componente correlacionava −0,30 com `transito_tranquilo`, medindo em parte "tem via arterial".

| | Com `lit` (50/50) | Só postes |
|---|---:|---:|
| Mediana | 0,259 | **0,461** |
| Células abaixo de 0,3 | 58% | **21%** |
| Correlação com `densidade_malha` | 0,310 | **0,083** |
| Correlação com `transito_tranquilo` | −0,305 | **−0,073** |

O parâmetro `usar_lit` segue disponível em `dimensions.iluminacao`, desligado por padrão — o dado existe e pode melhorar; o que precisa ser explícito é a decisão de não usá-lo.

### Por que `densidade_malha` pesa 0,15, e não 0,20

A dimensão foi construída sobre literatura de **caminhabilidade**, onde densidade de interseções é virtude: quarteirão curto, rota direta, pedestre indo a algum lugar.

**Quem corre não vai a lugar nenhum.** Sai e volta ao mesmo ponto. Variedade de rota quase não importa, e interseção deixa de ser conectividade para virar interrupção — travessia, semáforo, parada.

A consequência é mensurável. Comparando células com mais de 50% de parque contra células urbanas com menos de 5%:

| | Parque | Urbano | Razão |
|---|---:|---:|---:|
| km de via por km² | 9,3 | 30,7 | **0,30×** |
| interseções por km² | 9,9 | 89,1 | **0,11×** |

O **Parque Barigui**, um dos melhores lugares para correr em Curitiba, fica no **percentil 26** da cidade nessa dimensão.

**Quatro reformulações foram testadas e nenhuma resolve:**

| Variante | Percentil do Barigui |
|---|---:|
| Atual: extensão + interseções | 26% |
| Só extensão de via | 29% |
| Extensão contígua sem carro, suavizada pela vizinhança | 38% |
| Extensão do componente conexo de vias sem carro | 65% |

A quarta parece resolver até se olhar o que ela mede: os maiores componentes têm 1.422 km, 1.017 km e 740 km — são malhas residenciais inteiras da cidade, não circuitos de parque. O Barigui subiu por estar ligado a um componente de 491 km, e o conjunto dos parques foi apenas de 24% para 34%.

**O diagnóstico é de construto, não de aritmética.** Densidade linear não distingue 3 km de rua interrompida de 1,6 km de pista contínua sem carro — que são os números reais de uma célula residencial e de uma célula do Barigui. Para correr, a segunda é melhor; a medida diz o contrário e nenhuma reformulação dela diz outra coisa.

Some-se o **risco R4**: o circuito do Barigui tem cerca de 6 km e a célula tem 0,1 km². O loop é grande demais para ser visto na resolução em que medimos.

**A correção foi de peso, não de fórmula.** O excedente de 0,05 foi para `espaco_dedicado`, que é a dimensão que de fato identifica esses lugares. A dimensão não foi removida porque densidade perto de zero é genuinamente ruim: é ela que separa rodovia e área não urbanizada do resto.

**Efeito medido:** o ranking quase não muda (ρ de Spearman de 0,991 entre os dois conjuntos de peso) e o percentil do Barigui continua em 89%. O IAC dele sobe de 0,753 para 0,793. A mudança está certa pela razão, não pelo efeito — o índice já classificava o Barigui corretamente, porque `espaco_dedicado` e `transito_tranquilo` o carregavam.

Os pesos são uma escolha, não um achado — nenhum procedimento os deriva dos dados. Por isso existem os quatro cenários, e por isso a seção de estabilidade abaixo não é opcional.

---

### A pista de atletismo, e por que a forma funcional é o problema

Observação vinda da inspeção visual: pista de atletismo é o melhor lugar que existe para correr, e o índice não tem como dizer isso.

Primeiro o que a medição **não** confirmou. A suspeita inicial era que pistas recebessem nota baixa em `densidade_malha` e em `espaco_dedicado` de forma sistemática. Não é o caso. Cruzando as **31 feições** `leisure=track` com `sport=athletics|running` do OSM contra a malha r9:

| | células com pista | município | percentil mediano da pista |
|---|---:|---:|---:|
| `densidade_malha` (bruto) | 0,425 | 0,274 | **78** |
| `espaco_dedicado` (bruto) | 0,067 | 0,008 | **84** |
| IAC | 0,502 | 0,415 | **85** |

As 18 células que contêm pista ficam, na mediana, no quartil superior da cidade. Nenhuma delas está abaixo da mediana em `espaco_dedicado`.

**O defeito é mais estreito e mais grave do que o enunciado geral.** O índice não pontua a pista: pontua a vizinhança dela. Quando a vizinhança é boa, o número sai certo pelo motivo errado; quando não é, o número sai errado.

- **2 das 18 células com pista estão no decil inferior do IAC.** Em −25,57659, −49,31649 há uma pista de 10.494 m² numa célula de IAC 0,224, percentil **3,5**. Em −25,53151, −49,29971, uma de 13.403 m² em célula de percentil **9,6**.
- No caso oposto, a pista da **Universidade Positivo** (−25,44545, −49,36065) está no percentil 98,7 — mas com `densidade_malha` de 0,999 e `espaco_dedicado` de 0,073. Ela pontua pela malha do Ecoville em volta. Tire a pista da célula e o IAC praticamente não se move.

A causa é **a forma funcional das duas dimensões, não o peso nem o dado**:

- `espaco_dedicado` é **fração de área**. Uma pista de 400 m com o miolo tem 1,0 a 1,5 ha; a célula r9 tem 10,1 ha. O teto estrutural é de ~15%, e o máximo observado em Curitiba é de 21,1%, com mediana de **6,6%**. Nenhuma pista, perfeitamente mapeada, consegue levar a dimensão perto de 1.
- `densidade_malha` é **densidade linear com interseções**. Um oval fechado tem extensão curta e praticamente nenhuma interseção — a mesma razão pela qual o Barigui fica no percentil 26 (ver a seção acima).

Ou seja: as duas dimensões que deveriam captar a pista a descrevem como "um pedaço pequeno de área verde sem conectividade". O construto certo para um equipamento pontual é **presença ou proximidade** — binário, ou decaimento por distância até a pista mais próxima — e não fração de área nem densidade. Isso é uma dimensão nova, não um ajuste, e está no backlog.

**Por que não foi corrigido agora.** Uma dimensão de proximidade a equipamento esportivo muda a pergunta do índice: hoje ele mede adequação da *rua*, e `leisure=track` no OSM inclui pista de kart, velódromo fechado e pista de patinação, além de equipamento em campus privado de acesso restrito — a pista da Positivo entre eles. Entrar nesse terreno exige decidir o que conta como acesso público, que é a mesma discussão do filtro de áreas verdes. Fica registrado como limitação, não disfarçado como peso.

---

## Diagnóstico de redundância

Calculado sobre as 4.030 células que têm IAC.

### VIF — fator de inflação da variância

| Dimensão | R² contra as outras quatro | VIF |
|----------|---------------------------:|----:|
| `densidade_malha` | 0,161 | 1,19 |
| `declividade` | 0,159 | 1,19 |
| `transito_tranquilo` | 0,029 | 1,03 |
| `iluminacao` | 0,005 | 1,01 |
| `espaco_dedicado` | 0,004 | 1,00 |

Regra prática: abaixo de 2,5 é excelente, abaixo de 5 aceitável, acima de 10 indica redundância real. **Nenhuma dimensão tem mais de 17% da sua variação explicada pelas demais.**

O desligamento do `lit` e a reclassificação viária melhoraram ainda este quadro: `iluminacao` saiu de VIF 1,21 para 1,01 e `transito_tranquilo` de 1,14 para 1,03. As duas dimensões que mais mudaram são hoje as mais independentes das demais.

### Correlação entre dimensões (Spearman)

| Par | ρ | Variância compartilhada |
|-----|---:|---:|
| `densidade_malha` × `declividade` | +0,398 | 15,8% |
| `densidade_malha` × `espaco_dedicado` | +0,264 | 7,0% |
| `densidade_malha` × `transito_tranquilo` | −0,233 | 5,4% |
| `espaco_dedicado` × `iluminacao` | +0,221 | 4,9% |
| `transito_tranquilo` × `declividade` | −0,157 | 2,5% |
| `espaco_dedicado` × `declividade` | +0,117 | 1,4% |
| `densidade_malha` × `iluminacao` | +0,083 | 0,7% |
| demais pares | < 0,05 | < 0,3% |

**Trajetória do pior par:** 0,95 → 0,81 → **0,398** — e o pior par hoje não envolve nenhuma dimensão corrigida.

Dois pares confirmam o diagnóstico do `lit`. `densidade_malha` × `iluminacao` caiu de **+0,310 para +0,083** e `transito_tranquilo` × `iluminacao` de **−0,299 para −0,043**: era a etiqueta medindo "tem via arterial mapeada", exatamente como previsto antes de desligá-la.

### Por que 0,398 não é problema e 0,95 era

A diferença é de **natureza**, não de grau.

Os casos corrigidos eram **artefatos de medida**. `superficie` e `continuidade` saíam da mesma malha do OSM medindo o mesmo construto (90% compartilhado). Postes por km² era mecanicamente um proxy de densidade de rua (66%). Nos dois, o índice contava a mesma coisa duas vezes.

`densidade_malha` × `declividade` compartilha 16%, e o que sobra é **geografia real**: cidade se adensa onde o terreno é plano. E a relação é heterogênea de um jeito que confirma isso:

| Quartil de declividade | ρ(malha, declividade) |
|------------------------|----------------------:|
| mais plano | +0,274 |
| 2 | +0,181 |
| 3 | +0,064 |
| mais íngreme | −0,070 |

Decai monotonicamente e some no terreno íngreme. Não é outlier: removendo 5% de cada extremo o valor mal se move (0,369).

**Forçar ortogonalidade custaria caro.** Residualizar daria "inclinação condicional à densidade", que não significa 4,2° nem nada interpretável. PCA produziria componentes sem nome, o que inviabiliza a análise de sensibilidade a pesos — não se varia o peso de algo que não tem significado. Em ambos os casos, removeria informação verdadeira sobre a cidade para melhorar um número que já está bom.

---

## Estabilidade entre cenários de peso

| | base | iguais | infraestrutura | percepção |
|---|---:|---:|---:|---:|
| **base** | 1,000 | 0,947 | 0,875 | 0,890 |
| **iguais** | | 1,000 | 0,885 | 0,826 |
| **infraestrutura** | | | 1,000 | **0,624** |

**Piso: 0,624**, entre `infraestrutura` e `percepção` — o mesmo par de sempre.

Trajetória: 0,757 com seis dimensões → 0,863 com cinco → 0,697 ao descorrelacionar a iluminação → **0,624** depois de desligar o `lit` e reclassificar a hierarquia viária.

**A queda continua sendo a mesma história, agora com uma evidência direta.** O piso é puxado pelo par que discorda mais em `transito_tranquilo` (0,15 contra 0,35) e em `iluminacao` (0,05 contra 0,30) — e são exatamente as duas dimensões que acabaram de ficar independentes das outras, com VIF de 1,03 e 1,01. Quanto menos uma dimensão é redundante, mais o peso dela importa; quanto mais o peso importa, mais os dois cenários extremos divergem. O número caiu porque a medida melhorou.

### A queda é consequência da correção, não regressão

Quando dimensões são redundantes, mudar os pesos quase não altera o ranking: todas medem a mesma coisa, então o resultado é o mesmo de qualquer jeito. **Parte da estabilidade anterior era espúria** — vinha da redundância que foi eliminada. Com dimensões independentes, o peso passa a importar de verdade, e a métrica reflete isso.

### Mudar os pesos não resolve

Testado de novo com os números atuais: três conjuntos alternativos de pesos para o `base` deixam o piso **inalterado em 0,624** (devolver `densidade_malha` a 0,20; reforçar `transito_tranquilo` a 0,30; achatar tudo para perto de 0,20). O motivo é estrutural — o par mais divergente é `infraestrutura` × `percepção`, que não envolve o `base`. Mexer no padrão muda as correlações dele com os outros e não toca no piso.

A única forma de elevar o número seria **aproximar os cenários entre si** — e eles existem para ser opostos. Um afirma que adequação é provisão física; o outro, que é segurança percebida. São duas posições que pessoas reais defendem. Subir a estabilidade estreitando o teste seria produzir um número tranquilizador testando menos.

### A decisão: alto/baixo, com a robustez ao lado

**0,624 é um achado reportável:** quem pondera provisão física e quem pondera segurança percebida ranqueiam Curitiba de formas diferentes, com 38,9% de variância de ranking em comum.

E o quadro melhora muito quando se olha o que de fato será comunicado:

| Recorte | Concordância entre os 4 cenários |
|---------|---------------------------------:|
| Mesmo quartil | 41,4% das células |
| Varia 1 quartil | 43,7% |
| Varia 2 ou mais | **14,9%** |
| **Mesma classificação alto/baixo** | **70,4%** |

**Decidido, e registrado em [ADR 0003](adr/0003-alto-baixo-como-unidade-de-comunicacao.md): o IAC é comunicado como `alto` / `baixo`, nunca como ranking contínuo, sempre com a contagem de cenários que concordam.** Reportar duas classes não é perder resolução — é parar de afirmar uma precisão que o índice não tem.

| Concordância entre os 4 cenários | Células | % |
|---|---:|---:|
| `baixo` em todos | 1.424 | 35,3% |
| alto em 1 de 4 | 449 | 11,1% |
| alto em 2 de 4 | 275 | 6,8% |
| alto em 3 de 4 | 467 | 11,6% |
| `alto` em todos | 1.415 | 35,1% |

**2.839 células (70,4%) são estáveis** e sustentam conclusão firme. As outras 1.191 são o índice dizendo "depende do que você valoriza", e isso vira camada de resultado em vez de nota de rodapé.

O limiar é a decisão arbitrária que sobra depois dessa escolha, e também foi testado: variando o corte entre o percentil 40 e o 60, a fração de estáveis fica entre **70,0% e 72,6%**. A classificação resiste ao limiar, não só aos pesos.

Na prática: `classificar_alto_baixo` e `robustez_da_classificacao` em `features/suitability_index.py`, e as colunas `classe`, `n_alto` e `estavel` gravadas no `iac_h3_r9.parquet` ao lado do valor contínuo — que não sai do arquivo, porque continua sendo o insumo de toda a análise. O que muda é o que se afirma em público.

E fica a regra: **peso só muda por razão substantiva.** Se a literatura ou a pergunta de pesquisa indicarem outro balanço, mude por isso. Nunca para melhorar a métrica de estabilidade — aí o número vira decoração.

---

## As correções foram necessárias, e a estabilidade caiu por causa delas

Vale deixar isto explícito, porque a sequência de números convida à conclusão oposta: o piso de estabilidade caiu de 0,863 para 0,697 e depois para **0,624**, sempre logo depois de uma correção. Alguém lendo o histórico de trás para frente concluiria que o índice foi piorando.

**Cada correção foi validada contra a realidade, não contra uma métrica.**

| Correção | Por que era defeito, e não preferência |
|---|---|
| `lit` desligada | Ausente em 66% das células, e ausência no OSM significa "ninguém mapeou". Pior: correlacionava **−0,30** com `transito_tranquilo` — media em parte "tem avenida mapeada", que para corrida é sinal **negativo**, entrando numa dimensão como se fosse positivo |
| `tertiary` reclassificada | Respondia por **73,5%** da extensão nas células zeradas. Detectada por inspeção visual: lugares em 0 que não têm nada de perigoso |
| `busway` reclassificada | Canaleta de biarticulado valendo 0,5 por não constar de nenhuma lista |
| `densidade_malha` de 0,20 para 0,15 | O Parque Barigui, um dos melhores lugares para correr da cidade, no percentil 26 da dimensão |

**A métrica que mediu redundância melhorou enquanto a de estabilidade piorava**, e as duas se movem em direções opostas por mecanismo, não por acidente:

| | antes | depois |
|---|---:|---:|
| VIF de `iluminacao` | 1,21 | **1,01** |
| VIF de `transito_tranquilo` | 1,14 | **1,03** |
| ρ(`densidade_malha`, `iluminacao`) | +0,310 | **+0,083** |
| ρ(`transito_tranquilo`, `iluminacao`) | −0,299 | **−0,043** |
| Piso de estabilidade entre cenários | 0,697 | **0,624** |

Dimensões redundantes produzem estabilidade espúria: se todas medem a mesma coisa, mudar o peso não altera o ranking, e a métrica acusa solidez onde há apenas repetição. As duas dimensões que mais mudaram são hoje as mais independentes de todas — e são exatamente as que o par `infraestrutura` × `percepção` pondera de forma mais oposta (0,05 contra 0,30 na iluminação; 0,15 contra 0,35 no trânsito). Quanto menos redundante a dimensão, mais o peso dela importa. **O piso caiu porque o teste passou a funcionar.**

**A distinção que fecha o argumento:** a estabilidade entre cenários mede *quanto o resultado depende dos pesos*. Ela não mede, e não pode medir, *se as dimensões medem o que dizem medir*. São duas propriedades diferentes, e otimizar a primeira à custa da segunda é escolher um número confortável em vez de um número verdadeiro. Um índice com cinco cópias da mesma variável teria estabilidade perto de 1,00 e não mediria nada.

**E há evidência independente de que a direção está certa.** A inspeção visual de 25 células foi feita depois de as correções estarem especificadas, contra imagem de satélite e Street View: **17 `confere`, 8 `parcial`, nenhum `não confere`**, com os dez IAC baixos conferindo todos os dez — o extremo de que a hipótese H1 depende. Nenhum dos oito `parcial` é erro de cálculo; são limites de dado e de construto, todos registrados nas limitações. Ver [`../reports/validacao_iac.md`](../reports/validacao_iac.md).



---

## Limitações

1. **Mede oferta, não uso nem percepção.** Uma via pode ser perfeita no índice e vazia na prática.
2. **A completude do OSM acompanha a renda** (risco R1). É a limitação mais séria e segue aberta.
3. **A normalização é relativa a Curitiba.** IAC de 0,8 significa "entre os melhores da cidade", não "bom em termos absolutos". Não é comparável entre municípios sem re-normalização conjunta.
4. **Pesos arbitrários** — ver acima.
5. **Escala fixa na declividade**: o teto de 15° é referência prática, não parâmetro estimado.
6. **`densidade_malha` mede oferta de infraestrutura linear, não qualidade de percurso.** Penaliza sistematicamente parque e pista fechada — ver a seção sobre o peso 0,15. Nenhuma reformulação testada resolve, e a limitação fica registrada em vez de disfarçada.
7. **Declividade é média do terreno da célula**, incluindo fundo de vale e encosta sem rua. O mais válido seria a declividade ao longo das vias caminháveis — pendente no backlog. Vale notar que isso provavelmente **aumentaria** a correlação com `densidade_malha`, por amarrar a medida à malha: é melhoria de validade, não de descorrelação.
8. **A classe da via é um proxy fraco de qualidade de percurso.** Só 9,3% da rede caminhável são passeio ou trilha mapeada à parte; nos outros 90,7% o eixo da rua carrega o pedestre, e `highway` descreve a via para o carro. Largura de calçada, pavimento, arborização e travessia não entram porque não existem como dado. Ver "O que a classe da via não mede".
9. **`transito_tranquilo` não mede criminalidade.** O nome diz isso agora — chamava-se `seguranca_viaria`, e o rótulo antigo confundia num projeto que cruza o índice com ocorrências policiais na Fase 2. A limitação sobrevive ao rename: nada no IAC mede risco pessoal.
10. **O índice não vê pista de atletismo como pista.** `espaco_dedicado` é fração de área (teto estrutural de ~15% da célula para uma pista de 400 m; mediana observada de 6,6%) e `densidade_malha` é densidade linear, que um oval fechado não produz. Resultado: 2 das 18 células com pista mapeada caem no decil inferior do IAC. O construto certo é proximidade a equipamento, que é dimensão nova — ver a seção sobre a forma funcional.
11. **Pavimento não é medido, e não pode ser com o dado atual.** A etiqueta `surface` do OSM está **ausente em 62,1% da extensão** da rede. Onde está presente, 96,1% é pavimento declarado — porque quem mapeia `surface` mapeia asfalto. É a mesma assimetria do `lit`: ausência significa "ninguém mapeou", e usar a etiqueta puniria exatamente a periferia mal mapeada. Três células da inspeção visual tinham rua de terra com `surface` ausente em 100% da extensão.

---

---

## Verificação do recálculo

Executado em 7/10. O que foi conferido contra o arquivo novo, e não apenas previsto:

| Verificação | Resultado |
|---|---|
| Coluna `transito_tranquilo` presente, `seguranca_viaria` ausente | ✓ |
| `transito_tranquilo` bruto: mediana, zeros, abaixo de 0,2, exatamente 1 | ✓ bate com os quatro valores previstos |
| `iluminacao` bruta: mediana 0,461 e 21,0% abaixo de 0,3 | ✓ bate com o previsto |
| `densidade_malha`, `espaco_dedicado` e `declividade` brutas **idênticas** à rodada anterior | ✓ nada mais se moveu |
| 4.508 células, 4.030 com IAC, as mesmas 478 sem | ✓ |
| `iac` salvo reproduz a média ponderada base a partir das colunas normalizadas | ✓ diferença máxima de 0 |
| Todas as dimensões normalizadas em [0, 1] | ✓ |

A mediana de `transito_tranquilo` ter saído em 0,864, e não em 0,802, é a prova de que a etapa 5 reclassificou a camada em vez de ler a coluna gravada — ver desafio 18.

---

## Como recalcular

```python
from curitiba_run.features import dimensions, suitability_index as si
from curitiba_run.ingestion import geocuritiba

postes = geocuritiba.filtrar_postes_de_iluminacao(postes_brutos)
espacos = concat([osm_espacos, geocuritiba.filtrar_areas_publicas(verdes)])

brutas = dimensions.calcular_todas(malha, arestas, nos, espacos,
                                   declividade_raster, pontos_luz=postes)
normalizadas = si.normalizar_dimensoes(brutas)     # inverte a declividade
iac = si.compor(normalizadas)

cenarios = si.avaliar_cenarios_de_peso(normalizadas)
estabilidade = si.estabilidade_do_ranking(cenarios)
```

Os valores brutos ficam disponíveis de propósito: "3,2 km de calçada por km²" comunica no relatório; "0,71 normalizado" não.
