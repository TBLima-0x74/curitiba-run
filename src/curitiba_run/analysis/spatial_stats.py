"""Autocorrelação e associação espacial (ecossistema PySAL).

Sequência da Fase 4: matriz de vizinhança, Moran global para IAC e risco,
LISA para clusters locais, e Moran bivariado para a associação entre os dois —
com envelope de significância por permutação.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


def matriz_de_vizinhanca(malha: gpd.GeoDataFrame, tipo: str = "queen"):
    """Constrói e padroniza por linha a matriz de pesos espaciais."""
    raise NotImplementedError


def moran_global(valores: pd.Series, w) -> dict:
    raise NotImplementedError


def moran_local(valores: pd.Series, w) -> pd.DataFrame:
    """LISA: rótulo de cluster (AA, BB, AB, BA) e significância por célula."""
    raise NotImplementedError


def moran_bivariado(x: pd.Series, y: pd.Series, w) -> dict:
    """Associação espacial entre IAC e risco."""
    raise NotImplementedError
