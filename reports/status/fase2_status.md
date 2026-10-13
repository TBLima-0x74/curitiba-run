# Fase 2 — situação

**Em andamento.** A primeira etapa está pronta: as ocorrências da Guarda Municipal viram uma tabela por bairro, filtrada e ponderada por gravidade. A fonte policial, da SESP-PR, aguarda resposta a um pedido via Lei de Acesso à Informação.

O que a fase entrega ao final: uma **camada de risco por bairro**, em taxa por habitante e classificada em alto/baixo, que cada hexágono da malha H3 herda para cruzar com o IAC na Fase 4.

---

## O que está pronto

### Base legal

O uso das bases do Portal de Dados Abertos de Curitiba está autorizado: as Regras de Utilização permitem uso "livre para qualquer finalidade ou atividade, no limite das restrições legais". As três condições que o projeto adotou — só base municipal, dado bruto nunca publicado, supressão de bairro com contagem baixa — estão no [ADR 0004](../../docs/adr/0004-base-legal-dados-de-ocorrencias.md).

### A base da Guarda Municipal

| | |
|---|---|
| Arquivo | `data/raw/sigesguarda/2026-10-01_sigesguarda_-_Base_de_Dados.csv` |
| Registros | 236.897 |
| Período | 24/11/2022 a 01/10/2026 |
| Geografia | Bairro e nome da rua, **sem coordenada** — só 0,6% dos logradouros têm número |

Por não ter coordenada, a unidade desta fonte é o **bairro**, não o hexágono.

### O pipeline

`python scripts/fase2_ocorrencias.py` → `data/processed/ocorrencias_gm_por_bairro.csv`, com os 75 bairros oficiais.

| Etapa | Registros |
|---|---:|
| Lidos | 236.897 |
| No período (2023 a 1/10/2026) | 234.701 |
| De interesse | 6.454 |
| Com bairro de Curitiba | 6.443 |

Entra só o que atinge uma pessoa, ou o que ela carrega, na rua. Saem trânsito, furto de patrimônio público, violência doméstica e os disparos feitos pela própria Guarda. Regras e contagens em [`taxonomia_ocorrencias.md`](../../docs/taxonomia_ocorrencias.md).

### Os pesos de gravidade

Cada tipo pesa a sua pena mínima no Código Penal, dividida pela maior: homicídio, estupro e roubo a transeunte valem 1; furto 0,167; vias de fato 0,007. Decisão, alternativas rejeitadas e consequências no [ADR 0005](../../docs/adr/0005-peso-de-gravidade-pela-pena-minima.md).

| Sensibilidade (pena mínima × ponto médio) | |
|---|---:|
| ρ do ranking dos 75 bairros | 0,993 |
| Bairros na mesma classe alto/baixo | 94,7% |

### Código

**160 testes passando**, 64 deles da Fase 2: pesos derivados da tabela de penas, regras de inclusão, união das grafias de bairro, contrato de esquema das bases da Guarda e do IBGE, taxa e normalização.

---

## Três defeitos encontrados antes de virarem resultado

Todos fariam ocorrências sumirem sem erro, e os três subestimariam o risco. Detalhe no desafio 19 de [`desafios.md`](../../docs/desafios.md).

| Defeito | Tamanho | Correção |
|---|---|---|
| A CIC grafada como "CIDADE INDUSTRIAL" não casava com o nome oficial | 99,7% dos registros do bairro | Tabela de grafias alternativas em `config.py` |
| Espaço não separável em "Importunação sexual" | 339 ocorrências | Limpeza de texto antes de comparar |
| Disparos da própria Guarda contados como ocorrência | 201 de 228 disparos | Só disparo de terceiro entra |

---

## Taxa por habitante — primeiro resultado

População do **Censo 2022**, 75 bairros, total de **1.773.718 habitantes** — o número oficial de Curitiba. A CIC soma 172.510. Na primeira execução, a verificação de nomes parou o pipeline: o IBGE grafa **"Botiatuvinha"**, e a lista oficial, "Butiatuvinha". Sem a verificação, o bairro ficaria sem população em silêncio. Alias acrescentado e travado em teste.

| Bairro | Residentes | Gravidade por ano por 100 mil | Normalizada (log) |
|---|---:|---:|---:|
| São Francisco | 5.008 | 417,6 | 1,000 |
| Taboão | 3.470 | 350,2 | 1,000 |
| Centro | 38.671 | 311,9 | 0,990 |
| Jardim Botânico | 5.442 | 213,1 | 0,924 |
| Centro Cívico | 4.473 | 91,7 | 0,779 |

**O que mudou ao dividir pela população.** O Centro, que tinha quatro vezes a gravidade total do segundo colocado, cai para o terceiro lugar. O ranking por taxa e o por total concordam só em parte (ρ = 0,787).

**O que a tabela mostra, de fato.** Três dos quatro primeiros têm pouca gente morando e muita gente passando: São Francisco, com o centro histórico; o Centro; e o Jardim Botânico, com a rodoferroviária. É a ressalva do denominador residente aparecendo nos números, não uma surpresa. O quarto, Taboão, tem 3.470 moradores e **está entre os 9 bairros abaixo de 5.000 habitantes**, cuja taxa é instável — 63 ocorrências bastam para colocá-lo em segundo.

**A escala passou a ser logarítmica.** Na linear, a mediana era 0,026 e 60 dos 75 bairros ficavam abaixo de 0,1 — num mapa, quase todos teriam a mesma cor. Com `log(1 + taxa)` antes da normalização, a mediana vai a **0,390**, os quartis a 0,24 · 0,39 · 0,53, e só 8 bairros ficam abaixo de 0,1. A classe alto/baixo sai idêntica nas duas escalas.

---

## Vieses conhecidos

1. **A Guarda registra onde está.** No recorte de interesse, 22,6% das ocorrências acontecem em equipamento municipal (estação-tubo, terminal, unidade de saúde), contra 9% da base inteira. A coluna `pct_em_equipamento_urbano` acompanha cada bairro.
2. **O roubo domina.** Responde por 77,4% da gravidade total: na prática, a camada mostra onde se rouba gente na rua.
3. **Violência doméstica residual** em ameaça e vias de fato, que não têm subcategoria. Contida pelo peso baixo — são 53,4% das ocorrências e 2,6% da gravidade.
4. **Lei nova no meio do período.** A Lei nº 15.397/2026 subiu a pena do roubo; os pesos seguem a lei vigente.
5. **Denominador residente em bairros de passagem.** São Francisco, Centro e Jardim Botânico têm poucos moradores e muita circulação, então a taxa por residente infla. Não há dado público de população flutuante por bairro para corrigir. **Decidido manter como limitação**: a taxa desses bairros se lê como teto. A sensibilidade a denominadores de exposição (km de via, área) fica como extensão futura.

---

## SESP-PR: pedido via LAI

O portal de dados da SESP-PR está fora do ar há mais de um ano. O pedido de microdados desidentificados de Curitiba, por bairro e mês, desde 2023, foi protocolado no sistema de ouvidoria e LAI do Paraná.

| | |
|---|---|
| Protocolo | **26.719.234-0** (e-Protocolo do Paraná) |
| Data | 09/10/2026, 09:08 |
| Prazo legal | 20 dias, prorrogáveis por mais 10 (Lei nº 12.527/2011) — em dias corridos, **29/10/2026**, ou **08/11/2026** com prorrogação |

Até a resposta, a camada se chama **"ocorrências registradas pela GM"**, não "risco".

### O código já está pronto para receber a base

O esquema do arquivo é desconhecido, então `ingestion/sesp.py` não supõe nada que não precise: reconhece as colunas pelo nome (bairro, natureza, data ou ano e mês, tipo de local, município), classifica a natureza por padrões e lista no relatório toda natureza que não casou com nenhum. Daí em diante a SESP passa pelas mesmas três etapas da Guarda — gravidade, taxa com Bayes empírico e classe, hexágono — e o script compara as duas fontes.

**A base legal é imposta em código:** sem um `docs/adr/0006-*.md`, a ingestão da SESP para com aviso e o pipeline segue só com a Guarda. Testado de ponta a ponta numa cópia isolada do projeto, com um arquivo sintético no lugar da resposta: sem o ADR, a SESP é pulada; com ele, as três etapas rodam, a comparação sai e a SESP passa a ser a fonte principal da camada de risco.

### Quando a resposta chegar

1. **Salvar o arquivo** (CSV ou XLSX, como vier) em `data/raw/sesp/`. Fica fora do Git, como todo dado bruto.
2. **Escrever o ADR 0006** em `docs/adr/0006-base-legal-sesp.md`: protocolo, data e órgão da resposta, o que foi entregue, as condições de uso que a resposta impuser, e a confirmação de que os dados vêm desidentificados. **Se a resposta permitir publicar agregados, o ADR traz a linha `Publicação de agregados: permitida`**; sem ela, a SESP é usada mas nada dela vai para `data/publicado/` ([ADR 0007](../../docs/adr/0007-supressao-de-baixa-contagem.md)). Se a resposta impuser limiar de supressão maior que 5, o ADR registra e `LIMIAR_SUPRESSAO`, em `config.py`, muda.
3. **Rodar** `python scripts/fase2_ocorrencias.py`.
4. **Se parar por coluna**, a mensagem lista as colunas do arquivo: acrescentar o nome que faltou em `CANDIDATAS` (`ingestion/sesp.py`) e rodar de novo.
5. **Revisar `naturezas_nao_classificadas`** no relatório da etapa 1. Cada natureza que atinge a pessoa na rua ganha um padrão em `CLASSIFICACAO`, com o tipo penal do ADR 0005; violência doméstica já é excluída. Roubo e furto genéricos só entram se o tipo de local disser via pública. Rodar de novo até a lista conter só o que deve ficar de fora.
6. **Ler o resumo "Guarda Municipal × SESP-PR"** e registrar em `reports/validacoes/qualidade_dados_seguranca.md` (ver abaixo).
7. **Rodar** `python scripts/mapas_evolucao.py`: entram os mapas de taxa e classe da SESP, o mapa de comparação, e o painel da evolução passa a usar a SESP.

### O que sai

| Arquivo em `data/processed/` | Conteúdo |
|---|---|
| `ocorrencias_sesp_por_bairro.csv` | Mesma estrutura da tabela da Guarda, sem `pct_em_equipamento_urbano` |
| `taxa_ocorrencias_sesp_por_bairro.csv` | Taxa observada e suavizada, nota 0–1, classe alto/baixo |
| `risco_sesp_h3_r9.parquet` | A taxa na malha H3 |
| `comparacao_gm_sesp_por_bairro.csv` | As duas fontes lado a lado, bairro a bairro |
| `risco_h3_r9.parquet` | **A camada de risco do projeto**: cópia da SESP quando ela existe; da Guarda, enquanto não |

E em `data/publicado/`, só se o ADR 0006 permitir: `risco_sesp_por_bairro.csv`, `risco_sesp_h3_r9.csv`, `ocorrencias_sesp_por_tipo_curitiba.csv` e `comparacao_gm_sesp_por_bairro.csv`, todos suprimidos.

### A comparação mede o viés da Guarda

Cada fonte é posta relativa à **própria média** antes da razão, para que a diferença de volume entre as bases — a SESP registra muito mais — não pinte a cidade inteira de uma cor. O resumo dá:

- **`rho_taxas`** — correlação de Spearman entre as taxas das duas fontes. Alta: a Guarda ordena os bairros como a polícia;
- **`classes_concordam_pct`** — % de bairros com a mesma classe nas duas;
- **`rho_excesso_gm_vs_equipamento`** — correlação entre o quanto a Guarda registra a mais e a fração das ocorrências dela em equipamento municipal. **Positiva e alta é o viés de presença medido**: a Guarda vê mais onde está;
- **`gm_alto_sesp_baixo`** e **`gm_baixo_sesp_alto`** — os bairros que trocam de classe, a lista a examinar.

Esses números fecham o item de validação e decidem o critério de saída: a camada de risco passa a vir da SESP, e a da Guarda fica como contraponto.

---

## Pendente para fechar a fase

- [x] **Taxa por habitante** — calculada e normalizada de 0 a 1 (`taxa_ocorrencias_gm_por_bairro.csv`)
- [x] **Escala da normalização** — logarítmica
- [x] **Bairros de passagem** — decidido como limitação declarada, sem correção (ver Vieses conhecidos)
- [x] **Suavização bayesiana empírica** — Marshall (1991), adaptada a gravidade ponderada (κ = 0,825). Peso próprio mediano de 0,99, nenhum bairro muda de classe: o ruído era menor do que parecia, porque o que instabiliza a taxa é o número de ocorrências, e o Taboão tem 63. Bayes empírico local fica como extensão
- [x] **Bairro → hexágono** — os limites vêm da união dos setores censitários 2022 do GeoCuritiba, que não publica camada de bairros. Conferido com os dados reais: as 4.508 células recebem bairro, os 75 bairros chegam ao mapa (o menor, Alto da Glória, com 9 células), 27 células divididas (0,6%) e 37 de borda atribuídas por proximidade
- [x] **Limite municipal da malha H3** — mantido o do IBGE, com a divergência medida e declarada como limitação: 0,55 km² da cidade oficial (0,13%) fora da malha, em 61 faixas de ~24 m de largura na divisa, em 17 bairros periféricos (no máximo 1,3% da área de um bairro) e cerca de 1.200 moradores estimados (0,07%). Não afeta a camada de risco, que é por bairro; no IAC, cada faixa é uma borda de célula que ficou de fora. Os dados do IPPUC estão alinhados com o OSM, então a divergência é do contorno do IBGE, não de datum
- [x] **Classe alto/baixo de risco** pela mediana dos 75 bairros (8,81 por 100 mil), como no [ADR 0003](../../docs/adr/0003-alto-baixo-como-unidade-de-comunicacao.md): 38 bairros alto, 37 baixo; 1.328 das 4.508 células e 36% da população em risco alto
- [x] **Regra de supressão** ([ADR 0007](../../docs/adr/0007-supressao-de-baixa-contagem.md)) — bairro com menos de 5 ocorrências sai sem valor, com supressão complementar quando a diferença do total o revelaria; nenhuma contagem por tipo por bairro. Na Guarda, 5 bairros suprimidos (Lamenha Pequena, Riviera, Ahú, Caximba, Jardim Social), sem complemento. O publicável vai para `data/publicado/`, e os mapas já saem suprimidos
- [ ] **Validação** em `reports/validacoes/qualidade_dados_seguranca.md`: quanto da nota de cada bairro é presença da Guarda — com a SESP, sai do resumo da comparação
- [x] **SESP-PR: código** — ingestão sem esquema fixo, trava do ADR 0006, as três etapas e a comparação com a Guarda, testados com arquivo sintético
- [ ] **SESP-PR: dados** — resposta (prazo 29/10 ou 08/11), ADR 0006, roteiro acima

### Critério de saída

Uma camada de risco por bairro, em taxa por habitante, com classe alto/baixo, documentada, e com o viés de presença da Guarda **medido** — corrigido pela SESP-PR se a resposta vier, ou declarado como limitação se não vier.
