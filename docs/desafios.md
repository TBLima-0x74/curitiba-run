# Desafios do projeto

Registro honesto dos obstáculos que mudaram o projeto, do que foi feito e do que cada um ensinou. Não é uma lista de tarefas concluídas — é onde o projeto quase deu errado.

Um padrão atravessa quase todos eles e vale adiantar: **nenhum desses defeitos causou uma falha**. Nenhum derrubou o programa, nenhum apareceu como erro vermelho. Todos teriam produzido um número plausível e errado.

---

## Parte 1 — Viabilidade

### 1. A premissa original era juridicamente inviável

O projeto nasceu para cruzar quilômetros corridos no Strava com dados de criminalidade. A cláusula 5.4 da API Policy da Strava veda processar seus dados *"even in an aggregated, de-identified, or anonymized manner, for the purposes of analytics"*, e a 2.3 impede exibir dados de outros atletas.

O obstáculo não era técnico. Era **contratual**, e por isso não se resolvia subindo de tier de acesso — a política vale igualmente para todos. Descobrir isso exigiu ler o documento jurídico antes de escrever a primeira linha de ingestão.

**O que ensinou:** verificar a licença é parte do levantamento de viabilidade, não etapa burocrática posterior. Um projeto inteiro pode estar morto na cláusula 5.4 de um documento que ninguém lê.

### 2. A métrica original era temporalmente incoerente

Independentemente da licença, a medida pretendida tinha um defeito grave: `effort_count` é **cumulativo desde a criação do segmento**, sem janela temporal. Um segmento de oito anos atrás e outro do ano passado não são comparáveis entre si, e nenhum dos dois é comparável com uma base de ocorrências de período definido.

A variável explicativa e a de desfecho estariam medidas em escalas temporais incompatíveis. O cálculo rodaria normalmente e devolveria um número sem sentido.

**O que ensinou:** antes de usar um campo, perguntar sobre qual intervalo ele é medido. Um contador sem janela não é uma taxa.

### 3. O plano de contingência dependia de recrutamento impossível

Com a Strava fora, a alternativa era um estudo de escolha de rota com corredores voluntários. Sem rede local para recrutar, ele caiu junto.

A tentação seguinte era recorrer a assessorias esportivas. A análise mostrou que seria pior: os vieses dessa amostra **se alinham com a variável de interesse**, o que é diferente de ser apenas grande.

| Problema | Por que é fatal, não apenas limitante |
|----------|---------------------------------------|
| Falta de suporte comum | Assessorias concentram-se no cinturão de renda alta. Haveria quase nenhuma observação nas faixas de criminalidade que o estudo quer explorar — o modelo extrapolaria para fora da amostra |
| A rota não é do indivíduo | Treino em grupo segue percurso do treinador, já pré-filtrado por segurança. A variável dependente fica contaminada pelo próprio mecanismo em estudo |
| *N* efetivo | Trinta pessoas de três assessorias são três clusters, não trinta observações |

**O que ensinou:** quando o viés aponta na direção da variável de interesse, ele não é ressalva de rodapé — é razão para mudar o desenho.

### 4. A pergunta foi reformulada para caber nos dados

O desfecho das três primeiras: **mudar a pergunta em vez de forçar dados ruins numa pergunta que eles não sustentam.**

De *"onde as pessoas correm versus onde há crime"* — que tem problema de identificação insolúvel, porque a relação é bidirecional e nenhum dado disponível a resolve — para *"quem tem acesso a espaço adequado e seguro para correr"*.

A pergunta nova é **descritiva por natureza**, e descritivo é exatamente o que os dados sustentam. Ela não precisa de uma estratégia de identificação que nunca teria.

**O que ensinou:** reformular a pergunta é uma decisão de projeto legítima, não derrota. A pergunta errada com dados perfeitos continua sendo a pergunta errada.

---

## Parte 2 — Metodologia

### 5. Três das seis dimensões do índice estavam quebradas

O primeiro IAC rodou sem erro algum e produziu 4.508 valores entre 0 e 0,81. Parecia pronto. A validação mostrou outra coisa:

| Dimensão | Defeito | Como apareceu |
|----------|---------|---------------|
| `superficie_caminhavel` e `continuidade` | Mediam a mesma coisa | Correlação de Spearman de 0,95. Juntas somavam **40% do peso** num único construto contado duas vezes. Remover `continuidade` mudava o ranking em apenas ρ = 0,970 |
| `conforto` | Estava invertida | Sem modelo de terreno, sobrava só cobertura vegetal do OSM — que mapeia onde **não** há cidade. Correlação de −0,36 com a malha caminhável e −0,09 com o próprio índice: penalizava área urbana densa |
| `iluminacao` | Metade era constante | 523 postes do OSM para 4.508 células. Quase toda célula valia zero, os percentis 2 e 98 coincidiam, e a normalização caía no ramo degenerado |

Nenhum dos três apareceria sem olhar a correlação entre dimensões e a distribuição de cada uma. O índice funcionava perfeitamente e não media o que dizia medir.

**Correções aplicadas:** fusão em `densidade_malha` com peso 0,20; `conforto` substituída por `declividade` a partir do MDT do IPPUC; postes oficiais no lugar dos do OSM.

**O que ensinou:** um índice composto precisa de diagnóstico interno — correlação entre dimensões, distribuição de cada uma, análise de remoção — antes de qualquer interpretação. Rodar não é validar.

### 6. A função de normalização escondia o problema

O defeito da iluminação sobreviveu porque `normalizar` tinha um ramo defensivo: quando os percentis coincidem, devolver 0,5 evita dividir por zero. Correto e silencioso.

Esse 0,5 injetava **0,25 fixo em toda célula do município**, sem uma linha de log. Um tratamento de borda bem-intencionado transformou uma dimensão morta em ruído invisível.

**Correção:** a função agora emite aviso nomeando a dimensão e o valor que colapsou.

**O que ensinou:** tratamento defensivo que não avisa é o lugar onde defeitos moram. Degradar silenciosamente é pior que falhar.

### 7. Os pesos são arbitrários, e isso precisa ser medido

Nenhum procedimento deriva os pesos do índice a partir dos dados — são escolha do autor. A resposta não é fingir objetividade, é medir a sensibilidade: o IAC é calculado sob quatro esquemas de peso e se reporta a correlação de Spearman entre os rankings.

Na primeira rodada a estabilidade mínima ficou em **0,757**, entre os cenários `infraestrutura` e `percepção`. Passa, mas estava sendo puxada pelos defeitos acima.

**O que ensinou:** um índice composto sem análise de sensibilidade a peso é um número arbitrário disfarçado de medida.

---

## Parte 3 — Execução

### 8. A rede de saída bloqueava todas as fontes

Nem o ambiente de nuvem nem a VM local alcançavam Overpass, Nominatim, IPPUC, IBGE ou o portal de dados abertos. Só hosts do GitHub respondiam.

Duas saídas, em vez de parar:

- **O limite municipal veio da malha do IBGE republicada no GitHub** — 435,4 km² contra os ~435 km² oficiais.
- **Toda a lógica posterior ao download foi verificada com uma cidade sintética** de medidas conhecidas. Os testes afirmam igualdades exatas: a soma dos comprimentos por célula bate com o comprimento da linha original, a soma das áreas bate com a área do parque mesmo quando ele aparece duplicado.

A ingestão real rodou depois, em máquina com internet aberta, sem alterar uma linha.

**O que ensinou:** ambiente bloqueado não impede progresso. Separar "o que precisa de rede" de "o que não precisa" permite verificar quase tudo offline.

### 9. A malha perdia 1% do município em silêncio

O preenchimento padrão do H3 (`h3shape_to_cells`) inclui apenas células cujo **centro** cai dentro do polígono. Para Curitiba isso descartava **4,1 km²** — quase 1% do território, inteiramente concentrado na borda.

O efeito seria perverso: a perda é toda periférica, e o projeto investiga justamente desigualdade centro-periferia. O erro teria descido silenciosamente por todas as fases e aparecido no fim como "a periferia tem menos infraestrutura" — **uma confirmação falsa da própria hipótese**.

**Correção:** contenção por sobreposição, mais `verificar_cobertura`, que falha alto se a lacuna passar de 0,1%. Hoje: 0,0000% nas três resoluções.

**O que ensinou:** toda transformação espacial merece soma de controle. E vale perguntar em que direção um erro empurraria o resultado — quando empurra na direção da hipótese, a vigilância precisa dobrar.

### 10. O Parquet recusou as camadas do OSM

Após baixar 185.386 arestas com sucesso, a gravação falhou com `cannot mix list and non-list, non-null values`.

Causa: uma aresta simplificada pelo osmnx **funde várias *ways*** do OSM. Quando isso acontece, `osmid`, `highway` e `name` viram lista naquela linha e seguem escalares nas demais. O Arrow exige tipo homogêneo por coluna.

**Correção:** `sanear_para_parquet` converte para texto apenas as colunas de tipo misto, unindo valores múltiplos com `;`. Colunas numéricas não são tocadas. O erro foi **reproduzido como teste antes da correção** — se um dia esse teste parar de falhar, o saneamento virou obsoleto e pode sair.

**O que ensinou:** dado colaborativo tem cardinalidade irregular por natureza. Entre o download e a persistência cabe uma camada de saneamento.

---

---

## Parte 4 — Depois que o índice rodou

### 11. Consertar a redundância derrubou uma métrica de qualidade

Ao descorrelacionar a iluminação, a estabilidade entre cenários de peso **caiu de 0,863 para 0,697**. Parecia regressão. Não era.

Dimensões redundantes produzem estabilidade espúria: se todas medem a mesma coisa, mudar o peso não altera o ranking, e a métrica acusa solidez onde há apenas repetição. Eliminada a redundância, o peso passou a importar de verdade — e a métrica passou a dizer a verdade.

A tentação seguinte era ajustar os pesos para o número subir. Testei: três conjuntos diferentes para o cenário base deixam o piso **inalterado**, porque o par mais divergente é `infraestrutura` × `percepção` e não envolve o base. A única forma de elevar o número seria aproximar os cenários entre si — isto é, testar menos para obter um resultado mais tranquilizador.

**O arco se repetiu, e o desfecho fecha o assunto.** Depois de desligar o `lit` e reclassificar a hierarquia viária, o piso caiu de novo, para **0,624** — e as duas dimensões corrigidas passaram a ser as mais independentes de todas (VIF de 1,01 e 1,03), que é precisamente o que derruba o piso, porque são elas que os dois cenários extremos ponderam de forma mais oposta. A métrica de redundância e a de estabilidade se movem em direções contrárias por mecanismo. A decisão tomada não foi mexer no número, foi parar de depender dele: o IAC passou a ser comunicado como `alto`/`baixo`, que se mantém em 70,4% das células contra 41,4% do quartil — [ADR 0003](adr/0003-alto-baixo-como-unidade-de-comunicacao.md). O argumento completo está em `indice_adequacao.md`, na seção "As correções foram necessárias".

**O que ensinou:** uma métrica de qualidade pode piorar porque o sistema melhorou. Antes de reagir a um número que caiu, vale perguntar o que ele mede e se a queda não é a própria correção aparecendo.

### 12. Agregar antes de classificar quase produziu uma conclusão invertida

O primeiro teste de completude do OSM comparou as unidades de conservação oficiais com os polígonos mapeados e devolveu **4,3% de cobertura** — que leria como catástrofe e confirmaria o pior cenário do risco R1.

Era artefato de agregação. A camada inclui **duas APAs somando 197 km²**, quase metade do município: zoneamento ambiental, não parque. O OSM faz certo em não mapeá-las como área verde.

Separando por categoria antes de medir, a conclusão se inverte: nos 60 parques e bosques **públicos**, a cobertura mediana do OSM é de **93%**.

**O que ensinou:** quando um número agregado contradiz fortemente a expectativa, o primeiro suspeito é a composição do agregado, não o fenômeno. Um único registro desproporcional pode carregar a estatística inteira — e aqui eram dois.

### 13. A dimensão media caminhabilidade, não corrida

O Parque Barigui é um dos melhores lugares para correr em Curitiba. Na dimensão `densidade_malha` ele fica no **percentil 26** da cidade.

A causa é a origem do construto. A dimensão foi montada sobre literatura de **caminhabilidade**, onde densidade de interseções é virtude: quarteirão curto, rota direta, pedestre indo a algum lugar. **Quem corre não vai a lugar nenhum** — sai e volta ao mesmo ponto. Variedade de rota quase não importa, e interseção deixa de ser conectividade para virar interrupção.

Medido: células de parque têm 0,30× a extensão de via e **0,11× as interseções** das células urbanas.

Quatro reformulações foram testadas — só extensão, extensão contígua, componente conexo de vias sem carro — e nenhuma resolve. A quarta parecia resolver até se olhar o que ela media: componentes de 1.422 km, 1.017 km e 740 km, que são malhas residenciais inteiras da cidade e não circuitos de parque.

O problema não é aritmético. **Densidade linear não distingue 3 km de rua interrompida de 1,6 km de pista contínua sem carro** — os números reais de uma célula residencial e de uma do Barigui. Soma-se o risco R4: o circuito do Barigui tem cerca de 6 km e a célula tem 0,1 km², então o loop é grande demais para ser visto na resolução em que medimos.

A correção foi baixar o peso de 0,20 para 0,15, passando o excedente a `espaco_dedicado`. A dimensão não saiu porque densidade perto de zero é genuinamente ruim — é ela que separa rodovia e área não urbanizada do resto.

**O que ensinou:** uma dimensão emprestada de outra literatura carrega as premissas daquela literatura. Caminhabilidade e corrida parecem o mesmo construto e divergem num ponto decisivo: se o trajeto tem destino. Vale perguntar, de cada medida herdada, qual pergunta ela foi desenhada para responder.

E vale registrar como o defeito apareceu: **não foi por teste nem por diagnóstico estatístico, mas por alguém que conhece a cidade olhar o resultado e estranhar.** Nenhuma checagem interna acusaria — a dimensão estava coerente consigo mesma.

### 14. Uma componente viva, variando, e ainda assim envenenando a medida

A dimensão de iluminação era metade densidade de postes oficiais, metade fração de via com `lit=yes` no OpenStreetMap. A observação veio de olhar o resultado: ruas com postes suficientes recebendo nota de 0,2.

O `lit` está **ausente em 66% das células** de Curitiba. Mediana bruta 0,000, mediana normalizada 0,000. Valendo metade do peso, ele rebaixava a dimensão por construção: células com densidade de poste no quartil superior terminavam com nota mediana de 0,34, e **um terço delas abaixo de 0,3**.

A causa é conceitual: **ausência no OSM significa "ninguém mapeou", não "não há iluminação"**. Falta de dado entrava como evidência de ausência — o risco R1 operando dentro de uma dimensão.

E havia um segundo defeito na mesma componente: quem mapeia `lit` no OSM mapeia avenida. Ela correlacionava **−0,30** com segurança viária, ou seja, media em parte "tem via arterial", que para corrida é sinal negativo.

Desligá-la elevou a mediana de 0,259 para 0,461, derrubou a fatia de células abaixo de 0,3 de 58% para 21%, e limpou o viés: a correlação com `transito_tranquilo` (então chamada `seguranca_viaria`) foi para −0,07 e com `densidade_malha` de 0,31 para 0,08.

**O que ensinou:** o aviso que eu havia colocado em `normalizar` não disparou, e corretamente — a série não era constante, tinha percentil 98 em 0,78. **Uma componente pode estar viva, variar, passar em toda checagem automática, e ainda assim estar envenenando a medida por enviesamento assimétrico.** Zero por falta de dado e zero por medição são indistinguíveis numa coluna de números, e só se separam perguntando de onde o dado veio.

Vale notar que este e o anterior vieram do mesmo lugar: alguém olhando um número e achando estranho. Nenhum teste pegaria.

### 15. A etiqueta descreve o carro, não quem corre

Mesma origem dos dois anteriores: alguém olhou o resultado e estranhou. Células em **0** na dimensão de segurança, em lugares que não têm nada de perigoso.

Dois defeitos diferentes estavam ali, e o primeiro é de nomenclatura.

**`seguranca_viaria` significa segurança no trânsito.** Não há um dado de criminalidade dentro dela — é a razão entre extensão de via de baixo tráfego e extensão total. O nome confundiu o próprio autor na leitura do resultado, e a Fase 2 cruza esse índice com ocorrências policiais: duas colunas vizinhas, uma chamada segurança e outra crime, medindo coisas sem relação. A dimensão foi renomeada para `transito_tranquilo`.

**O segundo defeito era de classificação.** Um 0 quer dizer "100% da via mapeada aqui é de alto tráfego". Nas 30 células zeradas, **73,5% da extensão é `tertiary`** — que no OSM é coletora de bairro, com comércio, faixa de pedestre e carro a 40, e que eu havia agrupado com `motorway` e `trunk`. Quase todo o fenômeno vinha de uma classe só, mal alocada. Na direção contrária, a canaleta do BRT (`busway`, 158 km) valia 0,5 por não constar de nenhuma lista.

Reclassificando `tertiary` como ambígua e `busway` como alto tráfego: mediana de 0,802 para 0,864, células em exatamente 0 de 30 para 10, abaixo de 0,2 de 85 para 40, e ρ de 0,970 entre as duas versões — a correção mexe na cauda, que é onde o defeito estava, e não no corpo.

**Mas a limitação de fundo nenhuma reclassificação resolve.** Só **9,3% da rede caminhável** de Curitiba são passeio ou trilha mapeada à parte. Nos outros 90,7% o pedestre viaja no eixo da rua, e `highway` descreve a função da via **para o automóvel**. Em nove de cada dez quilômetros, a nota é uma afirmação sobre carros usada como proxy de experiência de quem corre. Uma avenida de calçada larga e arborizada e uma marginal sem passeio recebem a mesma etiqueta. Largura, pavimento, arborização, travessia, carro estacionado sobre o passeio: nada disso entra, e nada disso existe como dado para Curitiba na escala do município.

Isso é limite do dado, não do cálculo, e não tem correção numérica. A única resposta honesta é não ler a dimensão como qualidade de percurso — ela sustenta a afirmação mais estreita de que *a via mapeada aqui é predominantemente arterial*, ou não é.

**O que ensinou:** duas coisas, e a segunda importa mais.

A primeira é que **o nome de uma variável é parte da medida**. Um rótulo que promete mais do que o cálculo entrega engana primeiro quem escreveu o código, e depois todo mundo. Aqui o nome ia encostar numa coluna de criminalidade uma fase adiante.

A segunda é sobre a correção que funcionou bem demais. Reclassificar `tertiary` resolveu um defeito real e mensurável, e por isso mesmo é um convite a parar — o número melhorou, a cauda limpou, segue o jogo. Mas o defeito corrigido era de alocação dentro de um esquema cuja validade era a questão de verdade. **Consertar bem um detalhe de um proxy fraco não fortalece o proxy**, e dá a sensação contrária. Vale perguntar, depois de cada correção que dá certo, se ela não acabou de esconder a pergunta maior.

### 16. A pista de atletismo é invisível, e a suspeita estava certa pelo motivo errado

A inspeção visual das 25 células produziu a observação: pista de atletismo é o melhor lugar que existe para correr, e aparecia com nota baixa em `densidade_malha` e `espaco_dedicado`. O enunciado era que isso acontecia de forma sistemática.

**Medi antes de documentar, e o enunciado geral não se sustenta.** Cruzando as 31 feições `leisure=track` com esporte de corrida contra a malha r9, as 18 células que contêm pista ficam na mediana do **percentil 78** em `densidade_malha`, **84** em `espaco_dedicado` e **85** no IAC. Nenhuma delas abaixo da mediana em espaço. Documentar "pistas recebem nota baixa" teria colocado no repositório uma afirmação falsa.

**Só que a medição encontrou algo pior.** O índice não pontua a pista — pontua a vizinhança dela:

- **2 das 18 células com pista estão no decil inferior do IAC.** Uma pista de 10.494 m² numa célula de percentil 3,5; outra de 13.403 m² em percentil 9,6.
- A pista inspecionada, da Universidade Positivo, está no percentil 98,7 — com `densidade_malha` de 0,999 e `espaco_dedicado` de 0,073. Ela pontua pela malha do Ecoville em volta. **O índice acertou aquela célula sem ter visto a pista.**

A causa é a forma funcional, não o peso. `espaco_dedicado` é fração de área, e uma pista de 400 m com o miolo ocupa 1,0 a 1,5 ha contra os 10,1 ha da célula: teto estrutural de ~15%, mediana observada de **6,6%**. `densidade_malha` é densidade linear com interseções, e um oval fechado não produz nem uma nem outra — é o Barigui do desafio 13 outra vez, agora no caso mais nítido possível, porque aqui o equipamento é feito exclusivamente para correr.

A correção não é um coeficiente: é uma dimensão de **proximidade a equipamento**, que muda a pergunta do índice e arrasta a discussão de acesso público (o `leisure=track` do OSM mistura kart, velódromo fechado e campus privado). Ficou no backlog, e a limitação ficou escrita.

**O que ensinou:** uma observação de campo pode estar certa sobre o mecanismo e errada sobre a magnitude, e as duas coisas precisam ser separadas antes de virar documentação. Se eu tivesse escrito o que foi relatado, teria registrado um fato falso; se tivesse descartado por não se confirmar no agregado, teria perdido duas pistas de atletismo no decil inferior do índice. **O agregado refutou o enunciado e a cauda confirmou a intuição.** É o desafio 12 ao contrário: lá o agregado mentia por composição, aqui o agregado diz a verdade e ainda assim esconde o caso que importa.

### 17. A terceira vez que a ausência de etiqueta quase virou medida

Três células da inspeção foram marcadas como rua de terra ou estrada sem pavimento, com IAC entre 0,64 e 0,77. A reação natural é usar a etiqueta `surface` do OSM, que o projeto já baixa.

Medi primeiro, por causa do desafio 14. **`surface` está ausente em 62,1% da extensão da rede**, e onde está presente 96,1% é pavimento declarado — porque quem mapeia `surface` mapeia asfalto. Nas três células em questão, a etiqueta estava ausente em **100% da extensão**.

Usá-la produziria o mesmo defeito do `lit`, com o mesmo sinal: ausência lida como evidência, punindo a periferia mal mapeada — e o viés aponta, de novo, na direção da hipótese H1.

**O que ensinou:** esta é a terceira ocorrência da mesma assimetria (`lit`, completude de via, `surface`), e a repetição é o achado. Virou regra do projeto: **nenhuma etiqueta opcional do OSM entra no índice sem que se meça antes a cobertura dela e a direção do viés de quem a preenche.** Uma etiqueta parcialmente preenchida não é uma medida com ruído — é uma medida de quem mapeia, disfarçada de medida do território.

### 18. A correção estava no código e não teria chegado ao número

Com as correções escritas, a pergunta natural era "basta rodar o script da Fase 1?". Não bastava, e a razão é estrutural.

A coluna `baixo_trafego` é **derivada** — sai de `classificar_hierarquia_viaria` aplicada à etiqueta `highway`. Só que ela era calculada no **download** e gravada dentro de `arestas.parquet`, a camada crua. E a etapa 4 da Fase 1 pula o que já existe em disco, de propósito, porque rebaixar a rede caminhável do Overpass leva minutos.

As duas decisões são defensáveis em separado. Juntas, significam que **mudar a hierarquia viária em `osm.py` não tinha efeito nenhum** enquanto o arquivo existisse. O script rodaria do começo ao fim, imprimiria as cinco dimensões, salvaria o IAC — com a classificação antiga. Nenhum erro, nenhum aviso.

Quantificando o que teria passado: reclassificar a camada gravada muda **17.718 arestas, 1.406 km, 10,7% da extensão da rede**. Alto tráfego cai de 3.001 km para 1.910 km.

**Correção:** a classificação passou a ser reaplicada na etapa 5, a cada execução, sobre a camada lida do disco. É operação pura sobre uma coluna e custa quase nada. A camada crua guarda o que o download trouxe; o que é derivado se deriva na hora de usar.

Isso trouxe à tona um segundo defeito, latente, que só apareceria aí: `_primeiro`, a função que resolve tags com múltiplos valores, entendia a **lista** que o osmnx devolve mas não o **texto unido por `;`** que `sanear_para_parquet` grava. Reclassificar do disco leria `"primary;secondary"` como classe desconhecida e mandaria a aresta para 0,5 — em silêncio, se eu não tivesse acabado de colocar o aviso de classe desconhecida no desafio 15. Com a correção, `tipo_via` recalculado da camada gravada reproduz exatamente o `tipo_via` original nas 185.386 arestas, e dois testes fixam a ida e volta.

**O que ensinou:** é o desafio 6 outra vez, num lugar diferente. Lá, um tratamento de borda silencioso escondia uma dimensão morta; aqui, um cache silencioso esconde uma correção que não chegou. **Guardar em disco o que é derivado cria uma segunda fonte de verdade, e a antiga ganha por omissão.** Vale a regra: coluna derivada não se persiste junto com o dado cru, e se persistir, o passo que a consome recalcula.

E vale notar de onde veio: não de um teste, mas de levar a sério uma pergunta operacional de uma linha. "Basta rodar o script?" era a pergunta certa.

## Parte 5 — Fase 2

### 19. Três formas de uma ocorrência sumir sem erro

A base da Guarda Municipal tinha três armadilhas, todas do mesmo tipo: dado que existe e desaparece no caminho sem nenhuma mensagem.

**A CIC quase sumiu.** A base escreve o maior bairro da cidade de duas formas: "Cidade Industrial de Curitiba" e "CIDADE INDUSTRIAL". Comparando com a lista oficial dos 75 bairros, a segunda grafia não casava — e ela tinha **11.639 registros — 99,7% de todos os da CIC**; a grafia oficial aparece só 40 vezes. Sem um alias, o bairro mais populoso e um dos mais pobres de Curitiba apareceria quase sem ocorrências, ou seja, como **um dos mais seguros**. É o desafio 9 outra vez: perda concentrada num lugar só, e justamente na periferia.

**Um espaço invisível apagava um crime.** "Importunação sexual" está gravada com espaço não separável (U+00A0) entre as palavras. Comparado com o texto digitado, não casava: as **339 ocorrências** sumiam do recorte. A limpeza de texto agora troca esse caractere antes de qualquer comparação, e um teste fixa o caso.

**A própria Guarda virava risco.** Dos 228 disparos de arma registrados, **201 são da Guarda** — munição letal, menos letal ou dispositivo elétrico. Contados como ocorrência, eles transformariam a presença policial em perigo. Só os disparos de terceiros entram.

Nos três casos o pipeline rodaria até o fim e entregaria uma tabela plausível.

**O que ensinou:** comparar a base com uma referência externa — aqui, a lista oficial de bairros — é o que expõe o que falta. Olhar só o que casou nunca mostra o que não casou. E, de novo, vale perguntar em que direção a perda empurra o resultado: os três defeitos subestimariam o risco onde a hipótese do projeto espera encontrá-lo.

## O risco que continua aberto

Nenhuma correção eliminou o **R1**, que segue sendo a ameaça central à validade.

A completude do OpenStreetMap acompanha a renda: bairros centrais e ricos são mais mapeados. **478 células — 10,6% do município — não têm nenhuma via caminhável no OSM**, e não são células de borda: 264 delas estão inteiramente dentro de Curitiba. Concentram-se na periferia sul e oeste.

Parte disso é real — o sul de Curitiba é semirrural e há cinturão verde a oeste. Parte é sub-mapeamento. **Separar os dois é obrigatório antes de qualquer conclusão**, porque o viés aponta exatamente na direção da hipótese H1: calçadas que existem mas ninguém mapeou fariam o índice subestimar a infraestrutura justamente onde se espera que ela seja menor.

A descoberta do ArcGIS Server público do IPPUC destravou a referência que faltava. Medir a completude do OSM por decil de renda deixou de ser impossível e passou a ser tarefa pendente — e ela é resultado do projeto, não etapa de controle de qualidade.

---

## O padrão

Dezenove desafios, e a recorrência importa mais que qualquer um deles: **nenhum se manifestou como erro.**

A licença não gerou exceção. O `effort_count` sem janela teria somado normalmente. O viés da amostra produziria coeficientes com intervalo de confiança estreito. As três dimensões quebradas devolveram 4.508 valores bem-comportados. A malha com lacuna fechou todas as contas. Só o Parquet realmente quebrou — e foi o mais fácil de todos.

O trabalho que encontrou os outros dezoito foi **ler a licença, checar a correlação entre dimensões, conferir somas de controle, perguntar em que direção cada erro empurraria o resultado — e olhar um lugar que se conhece e estranhar o número**. Nada disso aparece em um pipeline verde.

É por isso que a Fase 1 incluía uma etapa de validação explícita, e por que ela consumiu mais tempo que a implementação.
