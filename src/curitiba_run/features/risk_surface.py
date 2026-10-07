"""Superfície de risco: densidade de ocorrências por célula.

Normalizada por área e por população, desagregada pelas classes da taxonomia.
Estimativa por densidade kernel para suavizar o ruído de células pequenas, com
suavização bayesiana empírica onde a exposição é baixa (risco R5).
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


def agregar_por_celula(
    ocorrencias: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    por_classe: bool = True,
) -> pd.DataFrame:
    raise NotImplementedError


def densidade_kernel(ocorrencias: gpd.GeoDataFrame, malha: gpd.GeoDataFrame) -> pd.Series:
    raise NotImplementedError


def suavizar_bayesiano_empirico(contagens: pd.Series, populacao: pd.Series) -> pd.Series:
    """Encolhe taxas de células com pouca exposição em direção à média global."""
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError("Fase 2/3 — ver README §6")


if __name__ == "__main__":
    main()
