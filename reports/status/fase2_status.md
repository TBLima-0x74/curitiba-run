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

**116 testes passando**, 20 deles da Fase 2: pesos derivados da tabela de penas, regras de inclusão, união das grafias de bairro, contrato de esquema da base.

---

## Três defeitos encontrados antes de virarem resultado

Todos fariam ocorrências sumirem sem erro, e os três subestimariam o risco. Detalhe no desafio 19 de [`desafios.md`](../../docs/desafios.md).

| Defeito | Tamanho | Correção |
|---|---|---|
| A CIC grafada como "CIDADE INDUSTRIAL" não casava com o nome oficial | 99,7% dos registros do bairro | Tabela de grafias alternativas em `config.py` |
| Espaço não separável em "Importunação sexual" | 339 ocorrências | Limpeza de texto antes de comparar |
| Disparos da própria Guarda contados como ocorrência | 201 de 228 disparos | Só disparo de terceiro entra |

---

## Resultado preliminar — ainda não é risco

| Bairro | Gravidade por ano |
|---|---:|
| Centro | 120,6 |
| Boqueirão | 28,0 |
| São Francisco | 20,9 |
| Taboão | 12,2 |
| Jardim Botânico | 11,6 |

**Não ler como ranking de risco.** Os números são totais, não taxa por habitante, e o Centro concentra gente, comércio e Guarda. Cinco bairros têm menos de 5 ocorrências — Riviera e Lamenha Pequena, nenhuma.

---

## Vieses conhecidos

1. **A Guarda registra onde está.** No recorte de interesse, 22,6% das ocorrências acontecem em equipamento municipal (estação-tubo, terminal, unidade de saúde), contra 9% da base inteira. A coluna `pct_em_equipamento_urbano` acompanha cada bairro.
2. **O roubo domina.** Responde por 77,4% da gravidade total: na prática, a camada mostra onde se rouba gente na rua.
3. **Violência doméstica residual** em ameaça e vias de fato, que não têm subcategoria. Contida pelo peso baixo — são 53,4% das ocorrências e 2,6% da gravidade.
4. **Lei nova no meio do período.** A Lei nº 15.397/2026 subiu a pena do roubo; os pesos seguem a lei vigente.

---

## SESP-PR: pedido via LAI

O portal de dados da SESP-PR está fora do ar há mais de um ano. O pedido de microdados desidentificados de Curitiba, por bairro e mês, desde 2023, foi protocolado no sistema de ouvidoria e LAI do Paraná.

| | |
|---|---|
| Protocolo | _a preencher_ |
| Data | outubro de 2026 |
| Prazo legal | 20 dias, prorrogáveis por mais 10 (Lei nº 12.527/2011) |

Quando a resposta chegar, ela é a base legal do **ADR 0006**, e só então `ingestion/sesp.py` pode ser implementado. Até lá, a camada se chama **"ocorrências registradas pela GM"**, não "risco".

---

## Pendente para fechar a fase

- [ ] **Taxa por habitante** — dividir a gravidade pela população do Censo 2022 por bairro
- [ ] **Bairro → hexágono** — cada célula H3 herda a nota do bairro que ocupa a maior parte dela
- [ ] **Classe alto/baixo de risco** pela mediana dos 75 bairros, como no [ADR 0003](../../docs/adr/0003-alto-baixo-como-unidade-de-comunicacao.md)
- [ ] **Regra de supressão** de bairro com contagem baixa antes de publicar qualquer mapa (ADR 0004)
- [ ] **Validação** em `reports/validacoes/qualidade_dados_seguranca.md`: quanto da nota de cada bairro é presença da Guarda
- [ ] **SESP-PR** — resposta, ADR 0006, ingestão e comparação com a Guarda

### Critério de saída

Uma camada de risco por bairro, em taxa por habitante, com classe alto/baixo, documentada, e com o viés de presença da Guarda **medido** — corrigido pela SESP-PR se a resposta vier, ou declarado como limitação se não vier.
