"""Extração da malha viária e de pedestres de Curitiba a partir do OpenStreetMap.

Insumo principal do Índice de Adequação à Corrida (Fase 1).

⚠️  Ameaça à validade R1: a completude do OSM é correlacionada com renda.
    Bairros centrais e ricos são mais mapeados, então calçadas que existem na
    periferia mas ninguém mapeou fazem o IAC subestimar a infraestrutura lá —
    **enviesando o resultado exatamente na direção da hipótese H1.**
    `validacao.completude_por_renda` mede esse viés e o reporta como resultado
    do projeto, não como nota de rodapé.
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

from curitiba_run.config import CRS_GEOGRAFICO, CRS_METRICO, INTERIM, MUNICIPIO, RAW, UF

log = logging.getLogger(__name__)

PLACE = f"{MUNICIPIO}, {UF}, Brazil"
DESTINO = RAW / "osm"

# `walk` já exclui vias de acesso restrito e inclui calçadas e trilhas.
NETWORK_TYPE = "walk"

# Hierarquia viária. Correr é agradável no primeiro grupo e desagradável ou
# perigoso no segundo — a dimensão `transito_tranquilo` é a razão entre eles.
#
# RESSALVA DE CONSTRUTO. A classe da via é um proxy fraco do que se quer medir.
# Só 9,3% da rede caminhável de Curitiba são calçada ou trilha mapeada à parte;
# nos outros 90,7% o eixo da rua carrega o pedestre, e a etiqueta `highway`
# descreve a função da via para o carro, não a experiência de quem corre nela.
# Uma avenida arborizada de calçada larga pontua igual a uma marginal.
# Ver "O que a classe da via não mede" em docs/indice_adequacao.md.
VIAS_BAIXO_TRAFEGO = frozenset(
    {
        "residential", "living_street", "pedestrian", "footway", "path",
        "track", "steps", "cycleway", "service",
    }
)
VIAS_ALTO_TRAFEGO = frozenset(
    {
        "motorway", "trunk", "primary", "secondary",
        "motorway_link", "trunk_link", "primary_link", "secondary_link",
        # Canaleta do BRT: via exclusiva de biarticulado, fluxo alto e contínuo.
        # Caía na faixa ambígua por omissão, valendo 0,5 em 158 km de rede.
        "busway",
    }
)
# Ambíguas por decisão, não por esquecimento. `tertiary` no OSM é coletora de
# bairro — comércio, faixa de pedestre, carro a 40 — e agrupá-la com rodovia
# respondia por 73,5% das células zeradas na dimensão. Forçá-la para baixo
# tráfego seria o erro oposto: coletora não é rua de quarteirão.
VIAS_AMBIGUAS = frozenset({"tertiary", "tertiary_link", "unclassified", "road"})

TAGS_ESPACO_DEDICADO = {
    "leisure": ["park", "pitch", "track", "sports_centre", "garden", "recreation_ground"],
    "landuse": ["recreation_ground", "village_green"],
}
TAGS_ARBORIZACAO = {
    "natural": ["wood", "scrub"],
    "landuse": ["forest", "grass", "meadow"],
    "leisure": ["nature_reserve"],
}
TAGS_ILUMINACAO = {"highway": "street_lamp"}

# `lit` não vem por padrão no osmnx; sem isto a dimensão de iluminação nasce vazia.
TAGS_VIA_EXTRAS = ["lit", "surface", "sidewalk", "foot"]


def _configurar_osmnx() -> None:
    """Ajusta o osmnx antes de qualquer download.

    O cache em disco é essencial: a rede caminhável de Curitiba é uma consulta
    pesada ao Overpass, e sem cache cada reexecução repete o download inteiro.
    """
    import osmnx as ox

    faltando = [t for t in TAGS_VIA_EXTRAS if t not in ox.settings.useful_tags_way]
    if faltando:
        ox.settings.useful_tags_way = list(ox.settings.useful_tags_way) + faltando
        log.info("Tags de via acrescentadas ao osmnx: %s", faltando)

    cache = INTERIM / "osmnx_cache"
    cache.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(cache)
    ox.settings.requests_timeout = 600


def _primeiro(valor):
    """Primeiro valor de uma tag do OSM, venha ela do osmnx ou do Parquet.

    O osmnx devolve **lista** quando a tag tem múltiplos valores. Depois de
    `sanear_para_parquet` a mesma tag volta do disco como texto unido por `;`.
    As duas formas precisam dar o mesmo resultado, senão reclassificar uma
    camada já gravada leria `"primary;secondary"` como classe desconhecida —
    e o OSM não usa `;` dentro de um valor de `highway` ou `lit`.
    """
    if isinstance(valor, (list, tuple, set)):
        return next(iter(valor), None)
    if isinstance(valor, str) and ";" in valor:
        return valor.split(";")[0]
    return valor


# ------------------------------------------------------------------- extração


def _poligono_do_municipio():
    """Limite municipal em EPSG:4326, usado como recorte de toda extração.

    Extrair por polígono em vez de por nome dispensa o Nominatim e — o que
    importa mais — garante que a rede e a malha analítica cubram exatamente o
    mesmo território. Resolver o nome de novo abriria espaço para divergência.
    """
    from curitiba_run.ingestion.ippuc import carregar_limite

    return carregar_limite().to_crs(CRS_GEOGRAFICO).geometry.union_all()


def baixar_rede(poligono=None, network_type: str = NETWORK_TYPE):
    """Baixa o grafo caminhável e devolve (nós, arestas) projetados no CRS métrico.

    Os nós trazem `grau` (número de vias que chegam ao nó), base da dimensão de
    continuidade. As arestas trazem `baixo_trafego` e `iluminada`.
    """
    import osmnx as ox

    _configurar_osmnx()
    poligono = poligono if poligono is not None else _poligono_do_municipio()
    log.info("Baixando rede %r pelo polígono municipal (pode levar alguns minutos)", network_type)

    grafo = ox.graph_from_polygon(poligono, network_type=network_type)
    grafo = ox.project_graph(grafo, to_crs=CRS_METRICO)

    nos, arestas = ox.graph_to_gdfs(grafo, nodes=True, edges=True)

    nos = nos.reset_index()
    nos["grau"] = nos["street_count"] if "street_count" in nos.columns else 0

    arestas = classificar_hierarquia_viaria(arestas.reset_index())
    log.info("Rede: %d nós, %d arestas", len(nos), len(arestas))
    return nos, arestas


def classificar_hierarquia_viaria(arestas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Rotula cada aresta quanto a tráfego e iluminação.

    - `baixo_trafego`: 1 para via residencial, calçada, trilha ou similar.
    - `iluminada`: 1 quando `lit` indica iluminação presente.

    Vias ambíguas (`tertiary`, `unclassified`) recebem 0,5 em `baixo_trafego`:
    forçá-las para um extremo inventaria certeza que o dado não tem. Classe
    fora das três listas cai no mesmo 0,5, mas emite aviso — um 0,5 por decisão
    e um 0,5 por desconhecimento são indistinguíveis na coluna de números.
    """
    arestas = arestas.copy()
    tipo = arestas["highway"].map(_primeiro) if "highway" in arestas.columns else pd.Series(index=arestas.index)

    arestas["tipo_via"] = tipo

    desconhecidas = set(tipo.dropna().unique()) - (
        VIAS_BAIXO_TRAFEGO | VIAS_ALTO_TRAFEGO | VIAS_AMBIGUAS
    )
    if desconhecidas:
        log.warning(
            "Classes de via fora das três listas, entrando como 0,5: %s",
            ", ".join(sorted(map(str, desconhecidas))),
        )

    arestas["baixo_trafego"] = (
        tipo.map(lambda t: 1.0 if t in VIAS_BAIXO_TRAFEGO else (0.0 if t in VIAS_ALTO_TRAFEGO else 0.5))
        .astype(float)
    )

    if "lit" in arestas.columns:
        lit = arestas["lit"].map(_primeiro)
        arestas["iluminada"] = lit.isin(["yes", "24/7", "automatic", "limited"]).astype(float)
    else:
        log.warning("Tag `lit` ausente nas arestas — dimensão de iluminação ficará só com os postes")
        arestas["iluminada"] = 0.0

    return arestas


def _baixar_features(tags: dict, rotulo: str, poligono=None) -> gpd.GeoDataFrame:
    import osmnx as ox

    _configurar_osmnx()
    poligono = poligono if poligono is not None else _poligono_do_municipio()
    log.info("Baixando %s", rotulo)

    feicoes = ox.features_from_polygon(poligono, tags=tags)
    poligonos = feicoes[feicoes.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    log.info("%s: %d polígonos", rotulo, len(poligonos))
    return poligonos.to_crs(CRS_METRICO)[["geometry"]].reset_index(drop=True)


def baixar_espacos_dedicados(poligono=None) -> gpd.GeoDataFrame:
    """Parques, praças, pistas e campos mapeados no OSM."""
    return _baixar_features(TAGS_ESPACO_DEDICADO, "espaços dedicados", poligono)


def baixar_arborizacao(poligono=None) -> gpd.GeoDataFrame:
    """Cobertura vegetal — componente de sombra na dimensão de conforto."""
    return _baixar_features(TAGS_ARBORIZACAO, "arborização", poligono)


def baixar_iluminacao(poligono=None) -> gpd.GeoDataFrame:
    """Postes de iluminação mapeados no OSM.

    Cobertura tipicamente baixa no Brasil. A base municipal de iluminação
    pública é mais completa e deve ser preferida quando disponível —
    ver `ingestion.dados_abertos_curitiba`.
    """
    import osmnx as ox

    _configurar_osmnx()
    poligono = poligono if poligono is not None else _poligono_do_municipio()
    feicoes = ox.features_from_polygon(poligono, tags=TAGS_ILUMINACAO)
    pontos = feicoes[feicoes.geometry.geom_type == "Point"]
    log.info("Postes no OSM: %d", len(pontos))
    return pontos.to_crs(CRS_METRICO)[["geometry"]].reset_index(drop=True)


# ---------------------------------------------------------------- persistência


def _achatar(valor):
    """Converte um valor de tag do OSM em texto, ou None."""
    if isinstance(valor, (list, tuple, set)):
        return ";".join(str(v) for v in valor) or None
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    return str(valor)


def sanear_para_parquet(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Homogeneíza colunas de tipo misto para que o Parquet aceite gravar.

    Uma aresta simplificada pelo osmnx funde várias *ways* do OSM, e nesse caso
    `osmid`, `highway`, `name`, `lanes` e companhia viram **lista** naquela
    linha e seguem escalares nas demais. O Arrow exige um tipo por coluna e
    recusa a mistura com "cannot mix list and non-list, non-null values".

    Colunas assim viram texto, com os valores múltiplos unidos por `;`. Colunas
    numéricas e a geometria não são tocadas — `baixo_trafego`, `iluminada` e
    `grau`, que é o que a análise consome, continuam numéricas.
    """
    gdf = gdf.copy()
    nome_geom = gdf.geometry.name

    for coluna in gdf.columns:
        if coluna == nome_geom or gdf[coluna].dtype != object:
            continue

        serie = gdf[coluna]
        tem_lista = serie.map(lambda v: isinstance(v, (list, tuple, set))).any()
        tipos_distintos = len(set(serie.dropna().map(type))) > 1

        if tem_lista or tipos_distintos:
            gdf[coluna] = serie.map(_achatar)
            log.debug("  coluna %r saneada para texto", coluna)

    return gdf


def salvar(camadas: dict[str, gpd.GeoDataFrame], destino: Path = DESTINO) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for nome, gdf in camadas.items():
        caminho = destino / f"{nome}.parquet"
        sanear_para_parquet(gdf).to_parquet(caminho)
        log.info("  %-22s %6d feições -> %s", nome, len(gdf), caminho.name)


def carregar(nome: str, destino: Path = DESTINO) -> gpd.GeoDataFrame:
    caminho = destino / f"{nome}.parquet"
    if not caminho.exists():
        raise FileNotFoundError(
            f"{caminho} não existe. Rode `make raw` (ou `python -m curitiba_run.ingestion.osm`) "
            "numa máquina com acesso ao Overpass/Nominatim."
        )
    return gpd.read_parquet(caminho)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    nos, arestas = baixar_rede()
    salvar(
        {
            "nos": nos,
            "arestas": arestas,
            "espacos_dedicados": baixar_espacos_dedicados(),
            "arborizacao": baixar_arborizacao(),
            "postes": baixar_iluminacao(),
        }
    )
    log.info("Ingestão do OSM concluída em %s", DESTINO)


if __name__ == "__main__":
    main()
