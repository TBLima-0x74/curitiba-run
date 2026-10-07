"""Mapas estáticos e o mapa interativo final.

Convenções de comunicação responsável (README §10):
  - O enquadramento é de acesso e direito, não de periculosidade.
  - Sem ranking de "bairros perigosos".
  - Incerteza reportada junto com a estimativa.
  - Paletas divergentes para a tipologia; sequenciais para IAC e risco.
"""

from __future__ import annotations

import geopandas as gpd


def mapa_iac(malha: gpd.GeoDataFrame, destino=None):
    raise NotImplementedError


def mapa_risco(malha: gpd.GeoDataFrame, destino=None):
    raise NotImplementedError


def mapa_tipologia(malha: gpd.GeoDataFrame, destino=None):
    """Mapa dos quatro quadrantes — a figura central do projeto."""
    raise NotImplementedError


def mapa_interativo(malha: gpd.GeoDataFrame, destino=None):
    """Folium com camadas alternáveis: IAC, risco, tipologia e acessibilidade."""
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError("Fase 6 — ver README §6")


if __name__ == "__main__":
    main()
