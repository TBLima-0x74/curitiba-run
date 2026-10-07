"""Malha hexagonal H3 recortada pelo limite municipal.

Hexágonos evitam a arbitrariedade dos limites administrativos e têm vizinhança
uniforme. A análise é repetida nas resoluções 8, 9 e 10 para testar a
sensibilidade ao MAUP (risco R4).

Cobertura de borda
------------------
O preenchimento padrão do H3 (`h3shape_to_cells`) inclui apenas células cujo
**centro** cai dentro do polígono, o que deixa faixas do município sem célula
alguma. Para Curitiba isso descartava ~4 km² (quase 1% da área). O modo
`overlap` inclui toda célula que intersecta o limite, garantindo cobertura
completa ao custo de células parcialmente externas — que a coluna
`fracao_no_municipio` permite ponderar ou excluir.
"""

from __future__ import annotations

import logging

import geopandas as gpd
import h3
from shapely.geometry import Polygon

from curitiba_run.config import (
    CRS_GEOGRAFICO,
    CRS_METRICO,
    H3_RESOLUCAO,
    PROCESSED,
)

log = logging.getLogger(__name__)


def celulas_do_poligono(
    geometria,
    resolucao: int = H3_RESOLUCAO,
    cobertura: str = "overlap",
) -> set[str]:
    """Índices H3 que cobrem uma geometria em coordenadas geográficas.

    Aceita Polygon ou MultiPolygon, em EPSG:4326.

    `cobertura="overlap"` inclui toda célula que intersecta a geometria —
    garante que o município inteiro tenha célula. `cobertura="center"` usa o
    preenchimento clássico, mais enxuto porém com lacunas na borda.
    """
    if cobertura not in {"overlap", "center"}:
        raise ValueError(f"cobertura deve ser 'overlap' ou 'center', recebido {cobertura!r}")

    poligonos = getattr(geometria, "geoms", [geometria])
    celulas: set[str] = set()

    for poly in poligonos:
        shape = h3.geo_to_h3shape(poly.__geo_interface__)

        if cobertura == "overlap" and hasattr(h3, "h3shape_to_cells_experimental"):
            celulas.update(h3.h3shape_to_cells_experimental(shape, resolucao, contain="overlap"))
        else:
            if cobertura == "overlap":
                log.warning(
                    "h3shape_to_cells_experimental indisponível nesta versão do h3; "
                    "usando preenchimento por centro, que deixa lacunas na borda."
                )
            celulas.update(h3.h3shape_to_cells(shape, resolucao))

    return celulas


def celula_para_poligono(celula: str) -> Polygon:
    """Converte um índice H3 no polígono correspondente (lon, lat)."""
    fronteira = h3.cell_to_boundary(celula)
    return Polygon([(lng, lat) for lat, lng in fronteira])


def construir_malha(
    limite: gpd.GeoDataFrame,
    resolucao: int = H3_RESOLUCAO,
    cobertura: str = "overlap",
) -> gpd.GeoDataFrame:
    """Constrói a malha H3 cobrindo o limite informado.

    Devolve um GeoDataFrame no CRS métrico com as colunas:
      - `h3`: índice da célula
      - `geometry`: polígono do hexágono
      - `area_km2`: área do hexágono completo
    """
    limite_geo = limite.to_crs(CRS_GEOGRAFICO)
    unido = limite_geo.geometry.union_all()

    celulas = sorted(celulas_do_poligono(unido, resolucao, cobertura))
    log.info("Malha H3 r%d (%s): %d células", resolucao, cobertura, len(celulas))

    malha = gpd.GeoDataFrame(
        {"h3": celulas},
        geometry=[celula_para_poligono(c) for c in celulas],
        crs=CRS_GEOGRAFICO,
    ).to_crs(CRS_METRICO)

    malha["area_km2"] = malha.area / 1e6
    return malha


def recortar_pelo_limite(
    malha: gpd.GeoDataFrame,
    limite: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Acrescenta a fração de cada célula que cai dentro do limite municipal.

    Células de borda ficam parcialmente fora. `fracao_no_municipio` permite
    ponderar densidades ou excluir células com fração muito baixa.
    """
    limite_m = limite.to_crs(malha.crs)
    recorte = limite_m.geometry.union_all()

    malha = malha.copy()
    malha["area_efetiva_km2"] = malha.geometry.intersection(recorte).area / 1e6
    malha["fracao_no_municipio"] = (malha["area_efetiva_km2"] / malha["area_km2"]).clip(0, 1)
    return malha


def verificar_cobertura(
    malha: gpd.GeoDataFrame,
    limite: gpd.GeoDataFrame,
    tolerancia: float = 0.001,
) -> dict[str, float]:
    """Confere que a malha cobre o município. Falha alto se houver lacuna.

    Soma de controle da Fase 3: a área efetiva coberta pelas células precisa
    bater com a área do município dentro da tolerância informada.
    """
    if "area_efetiva_km2" not in malha.columns:
        raise ValueError("Rode `recortar_pelo_limite` antes de verificar a cobertura")

    area_municipio = limite.to_crs(malha.crs).area.sum() / 1e6
    area_coberta = malha["area_efetiva_km2"].sum()
    lacuna = (area_municipio - area_coberta) / area_municipio

    resultado = {
        "area_municipio_km2": area_municipio,
        "area_coberta_km2": area_coberta,
        "lacuna_relativa": lacuna,
        "n_celulas": len(malha),
    }

    if abs(lacuna) > tolerancia:
        raise ValueError(
            f"Cobertura insuficiente: {lacuna:.2%} do município sem célula "
            f"(tolerância {tolerancia:.2%}). {resultado}"
        )

    log.info("Cobertura ok: %d células, lacuna %.4f%%", len(malha), 100 * lacuna)
    return resultado


def salvar(malha: gpd.GeoDataFrame, resolucao: int) -> None:
    destino = PROCESSED / f"malha_h3_r{resolucao}.parquet"
    malha.to_parquet(destino)
    log.info("Malha salva em %s", destino)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from curitiba_run.config import H3_RESOLUCOES_SENSIBILIDADE, RAW
    from curitiba_run.ingestion.ippuc import carregar_limite

    limite = carregar_limite(RAW / "ippuc" / "limite_municipal.gpkg")

    for resolucao in H3_RESOLUCOES_SENSIBILIDADE:
        malha = recortar_pelo_limite(construir_malha(limite, resolucao), limite)
        verificar_cobertura(malha, limite)
        salvar(malha, resolucao)


if __name__ == "__main__":
    main()
