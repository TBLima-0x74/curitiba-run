"""Cidade sintética para validar o pipeline sem depender de rede.

O download do OSM exige Overpass e Nominatim. Tudo o que acontece **depois** do
download — recorte por célula, densidades, razões, normalização, composição —
pode e deve ser verificado sem rede, com geometrias cujas medidas são
conhecidas de antemão.

É isso que este módulo constrói: uma malha real de Curitiba recortada num
pedaço pequeno, com vias, parques e postes de dimensões exatas, para que os
testes possam afirmar "a soma dos comprimentos por célula é igual ao
comprimento da linha" em vez de apenas "rodou sem erro".
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point, Polygon

from curitiba_run.config import CRS_METRICO

# Canto sudoeste do recorte, em coordenadas métricas plausíveis para Curitiba
# (SIRGAS 2000 / UTM 22S).
ORIGEM_X = 670_000.0
ORIGEM_Y = 7_180_000.0
LADO = 2_000.0  # 2 km de lado


def area_de_estudo() -> gpd.GeoDataFrame:
    """Quadrado de 2 km de lado que faz as vezes de limite municipal."""
    quadrado = Polygon(
        [
            (ORIGEM_X, ORIGEM_Y),
            (ORIGEM_X + LADO, ORIGEM_Y),
            (ORIGEM_X + LADO, ORIGEM_Y + LADO),
            (ORIGEM_X, ORIGEM_Y + LADO),
        ]
    )
    return gpd.GeoDataFrame({"nome": ["sintetica"]}, geometry=[quadrado], crs=CRS_METRICO)


def linha_horizontal(comprimento: float = LADO, offset_y: float = LADO / 2) -> LineString:
    """Linha reta de comprimento exato, atravessando a área de estudo."""
    y = ORIGEM_Y + offset_y
    return LineString([(ORIGEM_X, y), (ORIGEM_X + comprimento, y)])


def malha_viaria(n_horizontais: int = 5, n_verticais: int = 5) -> gpd.GeoDataFrame:
    """Grade regular de vias, metade residencial e metade arterial.

    O comprimento total é conhecido: (n_h + n_v) * LADO metros.
    """
    linhas, tipos, iluminada = [], [], []

    for i in range(n_horizontais):
        y = ORIGEM_Y + LADO * (i + 0.5) / n_horizontais
        linhas.append(LineString([(ORIGEM_X, y), (ORIGEM_X + LADO, y)]))
        tipos.append("residential" if i % 2 == 0 else "primary")
        iluminada.append(1.0 if i % 2 == 0 else 0.0)

    for j in range(n_verticais):
        x = ORIGEM_X + LADO * (j + 0.5) / n_verticais
        linhas.append(LineString([(x, ORIGEM_Y), (x, ORIGEM_Y + LADO)]))
        tipos.append("footway" if j % 2 == 0 else "secondary")
        iluminada.append(1.0 if j % 2 == 0 else 0.0)

    return gpd.GeoDataFrame(
        {
            "highway": tipos,
            "iluminada": iluminada,
            "baixo_trafego": [
                1.0 if t in {"residential", "footway"} else 0.0 for t in tipos
            ],
        },
        geometry=linhas,
        crs=CRS_METRICO,
    )


def nos_da_malha(n: int = 25, grau: int = 4) -> gpd.GeoDataFrame:
    """Interseções distribuídas em grade, todas com o mesmo grau."""
    lado = int(np.sqrt(n))
    pontos = [
        Point(
            ORIGEM_X + LADO * (i + 0.5) / lado,
            ORIGEM_Y + LADO * (j + 0.5) / lado,
        )
        for i in range(lado)
        for j in range(lado)
    ]
    return gpd.GeoDataFrame({"grau": [grau] * len(pontos)}, geometry=pontos, crs=CRS_METRICO)


def parque(lado_parque: float = 400.0) -> gpd.GeoDataFrame:
    """Parque quadrado de área conhecida (`lado_parque ** 2` m²), no canto sudoeste."""
    x0, y0 = ORIGEM_X + 100, ORIGEM_Y + 100
    quadrado = Polygon(
        [
            (x0, y0),
            (x0 + lado_parque, y0),
            (x0 + lado_parque, y0 + lado_parque),
            (x0, y0 + lado_parque),
        ]
    )
    return gpd.GeoDataFrame({"tipo": ["park"]}, geometry=[quadrado], crs=CRS_METRICO)


def postes(n: int = 40, seed: int = 7) -> gpd.GeoDataFrame:
    """Postes espalhados por metade da área, criando gradiente de iluminação."""
    rng = np.random.default_rng(seed)
    xs = ORIGEM_X + rng.uniform(0, LADO / 2, n)
    ys = ORIGEM_Y + rng.uniform(0, LADO, n)
    return gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in zip(xs, ys, strict=True)], crs=CRS_METRICO)


def raster_declividade(caminho, graus_min: float = 0.0, graus_max: float = 20.0):
    """Raster sintético com declividade crescendo de oeste para leste.

    Permite testar `media_zonal` com resultado previsível: células a leste têm
    declividade maior, logo conforto menor.
    """
    import rasterio
    from rasterio.transform import from_origin

    largura = altura = 200
    resolucao = LADO / largura

    gradiente = np.linspace(graus_min, graus_max, largura, dtype="float32")
    dados = np.tile(gradiente, (altura, 1))

    transform = from_origin(ORIGEM_X, ORIGEM_Y + LADO, resolucao, resolucao)
    perfil = {
        "driver": "GTiff",
        "height": altura,
        "width": largura,
        "count": 1,
        "dtype": "float32",
        "crs": CRS_METRICO,
        "transform": transform,
    }
    with rasterio.open(caminho, "w", **perfil) as dst:
        dst.write(dados, 1)

    return caminho


def cidade_completa(malha_resolucao: int = 9):
    """Devolve (malha, camadas) prontos para `dimensions.calcular_todas`."""
    from curitiba_run.processing import grid

    limite = area_de_estudo()
    malha = grid.recortar_pelo_limite(
        grid.construir_malha(limite.to_crs("EPSG:4326"), resolucao=malha_resolucao), limite
    )

    camadas = {
        "arestas": malha_viaria(),
        "nos": nos_da_malha(),
        "espacos": parque(),
        "pontos_luz": postes(),
        "arborizacao": parque(lado_parque=300.0),
    }
    return malha, camadas
