"""Camadas oficiais de Curitiba: limite municipal, bairros, regionais, parques, ciclovias.

Fonte preferencial: IPPUC — https://ippuc.org.br/geodownloads/geo.html
e GeoCuritiba — https://geocuritiba.ippuc.org.br/

Papel duplo no projeto:
  1. Insumo do IAC (espaço dedicado, ciclovias, equipamentos).
  2. **Referência de validação do OSM** — é contra estas camadas que a
     completude do OSM é medida por decil de renda (risco R1). Por isso a
     fonte de contingência abaixo serve para o limite, mas não substitui o
     IPPUC nas camadas temáticas: validar OSM contra OSM não valida nada.
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd

from curitiba_run.config import CRS_GEOGRAFICO, IBGE_MUNICIPIO, RAW

log = logging.getLogger(__name__)

DESTINO = RAW / "ippuc"
ARQUIVO_LIMITE = DESTINO / "limite_municipal.gpkg"

# Contingência para o limite municipal quando o IPPUC está inacessível:
# malha municipal do IBGE republicada em repositório público.
URL_CONTINGENCIA_LIMITE = (
    "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-41-mun.json"
)


def baixar_limite(destino: Path = ARQUIVO_LIMITE, forcar: bool = False) -> gpd.GeoDataFrame:
    """Obtém o limite municipal de Curitiba e persiste em GeoPackage.

    Tenta o IPPUC; se falhar, cai para a malha do IBGE republicada no GitHub.
    A origem efetiva fica registrada na coluna `fonte`, para que o relatório
    possa declarar qual foi usada.
    """
    if destino.exists() and not forcar:
        log.info("Limite já presente em %s", destino)
        return gpd.read_file(destino)

    destino.parent.mkdir(parents=True, exist_ok=True)

    try:
        limite = _limite_do_ippuc()
        limite["fonte"] = "IPPUC"
    except Exception as erro:  # noqa: BLE001 — qualquer falha justifica a contingência
        log.warning("IPPUC inacessível (%s); usando a malha do IBGE republicada", erro)
        limite = _limite_de_contingencia()
        limite["fonte"] = "IBGE/geodata-br"

    limite.to_file(destino, driver="GPKG")
    log.info("Limite salvo em %s (fonte: %s)", destino, limite["fonte"].iloc[0])
    return limite


def _limite_do_ippuc() -> gpd.GeoDataFrame:
    """Limite oficial pelo serviço do GeoCuritiba.

    TODO(Fase 0): confirmar a URL do serviço de feições e o nome da camada
    contra o catálogo do GeoCuritiba. Enquanto isso, a contingência assume.
    """
    raise NotImplementedError("Endpoint do GeoCuritiba ainda não confirmado")


def _limite_de_contingencia(url: str = URL_CONTINGENCIA_LIMITE) -> gpd.GeoDataFrame:
    """Extrai Curitiba da malha municipal do Paraná."""
    import json
    from urllib.request import urlopen

    from shapely.geometry import shape

    with urlopen(url, timeout=120) as resposta:  # noqa: S310 — URL constante e https
        colecao = json.load(resposta)

    feicoes = [f for f in colecao["features"] if f["properties"].get("id") == IBGE_MUNICIPIO]
    if not feicoes:
        raise ValueError(f"Município {IBGE_MUNICIPIO} não encontrado em {url}")

    return gpd.GeoDataFrame(
        {"municipio": ["Curitiba"], "ibge": [IBGE_MUNICIPIO]},
        geometry=[shape(feicoes[0]["geometry"])],
        crs=CRS_GEOGRAFICO,
    )


def carregar_limite(caminho: Path = ARQUIVO_LIMITE) -> gpd.GeoDataFrame:
    """Lê o limite já baixado. Baixa na primeira chamada, se necessário."""
    if not caminho.exists():
        return baixar_limite(caminho)
    return gpd.read_file(caminho)


def baixar_parques_e_pracas() -> gpd.GeoDataFrame:
    """Parques, praças e bosques oficiais.

    TODO(Fase 1): sem contingência — é justamente esta camada que valida o OSM.
    """
    raise NotImplementedError("Requer acesso ao IPPUC")


def baixar_ciclovias() -> gpd.GeoDataFrame:
    """TODO(Fase 1): requer acesso ao IPPUC."""
    raise NotImplementedError("Requer acesso ao IPPUC")


def baixar_bairros() -> gpd.GeoDataFrame:
    """TODO(Fase 1): 75 bairros e 10 regionais, para a agregação de comunicação."""
    raise NotImplementedError("Requer acesso ao IPPUC")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    limite = baixar_limite()
    area = limite.to_crs("EPSG:31982").area.sum() / 1e6
    log.info("Curitiba: %.1f km² (referência oficial ~435 km²)", area)


if __name__ == "__main__":
    main()
