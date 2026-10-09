"""Caminhos, constantes e parâmetros do projeto.

Ponto único de configuração: nenhum módulo deve conter caminho ou constante
mágica. Alterar o índice, a malha ou a projeção acontece aqui.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------- caminhos
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

for _d in (RAW, INTERIM, PROCESSED, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ território
MUNICIPIO = "Curitiba"
UF = "PR"
IBGE_MUNICIPIO = "4106902"

# Caixa envolvente aproximada, usada apenas para consultas iniciais ao OSM.
# O recorte definitivo é feito pelo limite oficial do IPPUC.
BBOX = {"north": -25.33, "south": -25.66, "east": -49.17, "west": -49.40}

# ---------------------------------------------------------------- projeções
CRS_GEOGRAFICO = "EPSG:4326"          # ingestão
CRS_METRICO = "EPSG:31982"            # SIRGAS 2000 / UTM 22S — todo cálculo métrico

# ---------------------------------------------------------------------- malha
H3_RESOLUCAO = 9                      # primária (~0,1 km² por célula)
H3_RESOLUCOES_SENSIBILIDADE = (8, 9, 10)

# Células com população abaixo deste limiar entram na análise descritiva,
# mas são excluídas das estimativas de taxa (ver risco R5).
POPULACAO_MINIMA_CELULA = 20

# ------------------------------------------------- Índice de Adequação à Corrida
# As cinco dimensões do IAC. Os pesos são uma escolha arbitrária e documentada:
# a análise de sensibilidade (Fase 5) reporta a estabilidade dos resultados
# sob esquemas alternativos. Ver docs/indice_adequacao.md.
# `transito_tranquilo` chamava-se `seguranca_viaria`. O nome anterior sugeria
# criminalidade, que ela não mede — é a razão entre extensão de via de baixo
# tráfego e extensão total. A Fase 2 cruza o índice com ocorrências policiais,
# e as duas colunas lado a lado com nomes parecidos enganavam na leitura.
IAC_DIMENSOES = (
    "densidade_malha",
    "espaco_dedicado",
    "transito_tranquilo",
    "declividade",
    "iluminacao",
)

# Dimensões em que "mais é pior" — entram invertidas na normalização.
IAC_DIMENSOES_INVERTIDAS = frozenset({"declividade"})

# O peso de `densidade_malha` caiu de 0,20 para 0,15, e os 0,05 foram para
# `espaco_dedicado`. Motivo: a densidade linear vem da literatura de
# caminhabilidade, onde interseção é virtude — quarteirão curto, rota direta,
# pedestre indo a algum lugar. Quem corre não vai a lugar nenhum: sai e volta
# ao mesmo ponto, e interseção vira interrupção. A medida penaliza parque em
# 3x na extensão e 9x nas interseções, e o Parque Barigui, um dos melhores
# lugares para correr em Curitiba, fica no percentil 26 dessa dimensão.
# O peso excedente foi para `espaco_dedicado`, que é a dimensão que de fato
# identifica esses lugares. Ver docs/indice_adequacao.md.
IAC_PESOS_BASE = {
    "densidade_malha": 0.15,
    "espaco_dedicado": 0.30,
    "transito_tranquilo": 0.25,
    "declividade": 0.15,
    "iluminacao": 0.15,
}

# Esquemas alternativos para a análise de sensibilidade (R3).
IAC_PESOS_CENARIOS = {
    "base": IAC_PESOS_BASE,
    "iguais": dict.fromkeys(IAC_DIMENSOES, 1 / len(IAC_DIMENSOES)),
    "infraestrutura": {
        "densidade_malha": 0.30,
        "espaco_dedicado": 0.40,
        "transito_tranquilo": 0.15,
        "declividade": 0.10,
        "iluminacao": 0.05,
    },
    "percepcao": {
        "densidade_malha": 0.10,
        "espaco_dedicado": 0.15,
        "transito_tranquilo": 0.35,
        "declividade": 0.10,
        "iluminacao": 0.30,
    },
}

# Declividade acima deste valor inviabiliza corrida contínua; serve de teto
# na inversão da dimensão.
DECLIVIDADE_MAXIMA_GRAUS = 15.0

# Percentis usados na normalização robusta, para conter outliers.
NORMALIZACAO_PERCENTIS = (2.0, 98.0)

# ------------------------------------------------------------- acessibilidade
VELOCIDADE_CAMINHADA_KMH = 4.8
LIMIARES_CAMINHADA_MIN = (5, 10, 15)

# ------------------------------------------------------------------- tipologia
# Rótulos dos quadrantes do cruzamento IAC x risco (dicotomizados pela mediana).
QUADRANTES = {
    (True, False): "privilegiado",         # alto IAC, baixo risco
    (True, True): "subutilizado",          # alto IAC, alto risco
    (False, False): "latente",             # baixo IAC, baixo risco
    (False, True): "duplamente_penalizado",
}

RANDOM_SEED = 42

# ------------------------------------------------------------------ Bairros
# Os 75 bairros oficiais de Curitiba. Conferidos contra a base da Guarda
# Municipal: todos os 75 aparecem nela, e nenhum nome desta lista fica sem
# registro. A comparação é feita sem acento e sem caixa (`chave_de_bairro`).
BAIRROS_CURITIBA = (
    "Abranches", "Água Verde", "Ahú", "Alto Boqueirão", "Alto da Glória",
    "Alto da Rua XV", "Atuba", "Augusta", "Bacacheri", "Bairro Alto",
    "Barreirinha", "Batel", "Bigorrilho", "Boa Vista", "Bom Retiro", "Boqueirão",
    "Butiatuvinha", "Cabral", "Cachoeira", "Cajuru", "Campina do Siqueira",
    "Campo Comprido", "Campo de Santana", "Capão da Imbuia", "Capão Raso",
    "Cascatinha", "Caximba", "Centro", "Centro Cívico",
    "Cidade Industrial de Curitiba", "Cristo Rei", "Fanny", "Fazendinha",
    "Ganchinho", "Guabirotuba", "Guaíra", "Hauer", "Hugo Lange",
    "Jardim Botânico", "Jardim das Américas", "Jardim Social", "Juvevê",
    "Lamenha Pequena", "Lindóia", "Mercês", "Mossunguê", "Novo Mundo",
    "Orleans", "Parolin", "Pilarzinho", "Pinheirinho", "Portão", "Prado Velho",
    "Rebouças", "Riviera", "Santa Cândida", "Santa Felicidade",
    "Santa Quitéria", "Santo Inácio", "São Braz", "São Francisco", "São João",
    "São Lourenço", "São Miguel", "Seminário", "Sítio Cercado", "Taboão",
    "Tarumã", "Tatuquara", "Tingui", "Uberaba", "Umbará", "Vila Izabel",
    "Vista Alegre", "Xaxim",
)

# Grafias alternativas que designam um bairro oficial. Sem a primeira linha,
# 11.639 registros da CIC (99,7% dos dela) — o maior bairro da cidade, e de baixa renda —
# sumiriam em silêncio, e a CIC pareceria segura. Ver desafio 19.
BAIRRO_ALIASES = {
    "CIDADE INDUSTRIAL": "Cidade Industrial de Curitiba",
    "CIC": "Cidade Industrial de Curitiba",
}

# 2022 só tem novembro e dezembro na base da Guarda Municipal.
OCORRENCIAS_INICIO = "2023-01-01"
