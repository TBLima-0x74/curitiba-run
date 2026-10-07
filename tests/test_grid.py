"""Testes da malha H3.

Dependem de h3 e geopandas instalados; são pulados se as bibliotecas faltarem.
"""

import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("h3")

from shapely.geometry import Polygon  # noqa: E402

from curitiba_run.config import CRS_GEOGRAFICO, CRS_METRICO  # noqa: E402
from curitiba_run.processing import grid  # noqa: E402


@pytest.fixture
def limite_sintetico():
    """Quadrado de ~0,02 grau próximo a Curitiba, suficiente para várias células."""
    poly = Polygon([(-49.30, -25.48), (-49.28, -25.48), (-49.28, -25.46), (-49.30, -25.46)])
    return gpd.GeoDataFrame(geometry=[poly], crs=CRS_GEOGRAFICO)


def test_celulas_do_poligono_nao_e_vazio(limite_sintetico):
    celulas = grid.celulas_do_poligono(limite_sintetico.geometry.iloc[0], resolucao=9)
    assert len(celulas) > 0


def test_cobertura_overlap_inclui_mais_celulas_que_center(limite_sintetico):
    """O modo overlap existe para fechar as lacunas de borda do preenchimento clássico."""
    poly = limite_sintetico.geometry.iloc[0]
    centro = grid.celulas_do_poligono(poly, 9, cobertura="center")
    overlap = grid.celulas_do_poligono(poly, 9, cobertura="overlap")
    assert centro <= overlap
    assert len(overlap) > len(centro)


def test_cobertura_invalida_e_rejeitada(limite_sintetico):
    with pytest.raises(ValueError, match="overlap.*center"):
        grid.celulas_do_poligono(limite_sintetico.geometry.iloc[0], 9, cobertura="talvez")


def test_construir_malha_devolve_crs_metrico(limite_sintetico):
    malha = grid.construir_malha(limite_sintetico, resolucao=9)
    assert malha.crs.to_string() == CRS_METRICO
    assert {"h3", "geometry", "area_km2"} <= set(malha.columns)


def test_celulas_tem_area_plausivel_na_resolucao_9(limite_sintetico):
    malha = grid.construir_malha(limite_sintetico, resolucao=9)
    # H3 r9 tem área média em torno de 0,1 km².
    assert malha["area_km2"].between(0.05, 0.20).all()


def test_indices_h3_sao_unicos(limite_sintetico):
    malha = grid.construir_malha(limite_sintetico, resolucao=9)
    assert malha["h3"].is_unique


def test_recorte_produz_fracao_entre_zero_e_um(limite_sintetico):
    malha = grid.construir_malha(limite_sintetico, resolucao=9)
    recortada = grid.recortar_pelo_limite(malha, limite_sintetico)
    assert recortada["fracao_no_municipio"].between(0, 1).all()
    assert recortada["fracao_no_municipio"].max() == pytest.approx(1.0, abs=1e-6)


def test_malha_overlap_cobre_a_area_inteira(limite_sintetico):
    """Soma de controle: nenhuma fração do território fica sem célula."""
    malha = grid.recortar_pelo_limite(
        grid.construir_malha(limite_sintetico, resolucao=9), limite_sintetico
    )
    info = grid.verificar_cobertura(malha, limite_sintetico)
    assert info["lacuna_relativa"] == pytest.approx(0.0, abs=1e-6)


def test_verificar_cobertura_denuncia_lacuna(limite_sintetico):
    """O preenchimento por centro deixa buracos — e a verificação precisa acusar."""
    malha = grid.recortar_pelo_limite(
        grid.construir_malha(limite_sintetico, resolucao=9, cobertura="center"),
        limite_sintetico,
    )
    with pytest.raises(ValueError, match="Cobertura insuficiente"):
        grid.verificar_cobertura(malha, limite_sintetico)


def test_verificar_cobertura_exige_recorte_previo(limite_sintetico):
    malha = grid.construir_malha(limite_sintetico, resolucao=9)
    with pytest.raises(ValueError, match="recortar_pelo_limite"):
        grid.verificar_cobertura(malha, limite_sintetico)
