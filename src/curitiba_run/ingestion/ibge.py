"""Setores censitários do IBGE: população, densidade e renda domiciliar.

Base de toda a análise de equidade (Fase 5) e denominador das taxas.
A interpolação dos setores para a malha H3 acontece em `processing.spatial_join`.
"""

from __future__ import annotations

import geopandas as gpd

from curitiba_run.config import IBGE_MUNICIPIO, RAW


def baixar_setores(municipio: str = IBGE_MUNICIPIO) -> gpd.GeoDataFrame:
    raise NotImplementedError


def main() -> None:
    (RAW / "ibge").mkdir(parents=True, exist_ok=True)
    raise NotImplementedError("Fase 0/3 — ver README §6")


if __name__ == "__main__":
    main()
