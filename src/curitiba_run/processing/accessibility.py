"""Acessibilidade em rede: distância caminhável real até espaço adequado e seguro.

É esta métrica que responde P3 do README — a parcela da população, por decil de
renda, que vive a 5, 10 e 15 minutos de espaço onde dá para correr com
segurança razoável.

Distância pela malha viária, não euclidiana: um parque do outro lado de uma via
expressa não está a 300 metros de ninguém.
"""

from __future__ import annotations

import geopandas as gpd
import networkx as nx
import pandas as pd

from curitiba_run.config import LIMIARES_CAMINHADA_MIN, VELOCIDADE_CAMINHADA_KMH


def minutos_para_metros(minutos: float, velocidade_kmh: float = VELOCIDADE_CAMINHADA_KMH) -> float:
    """Converte tempo de caminhada em distância de rede."""
    return velocidade_kmh * 1000 / 60 * minutos


def distancia_ate_destino(
    grafo: nx.MultiDiGraph,
    origens: gpd.GeoDataFrame,
    destinos: gpd.GeoDataFrame,
) -> pd.Series:
    """Distância em rede de cada origem ao destino mais próximo, em metros."""
    raise NotImplementedError


def cobertura_populacional(
    malha: gpd.GeoDataFrame,
    limiares_min: tuple[int, ...] = LIMIARES_CAMINHADA_MIN,
) -> pd.DataFrame:
    """Parcela da população dentro de cada limiar de caminhada, por decil de renda."""
    raise NotImplementedError
