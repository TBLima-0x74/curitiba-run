"""Testes da passagem bairro → hexágono H3, com dois bairros sintéticos."""

import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("h3")

from shapely.geometry import box  # noqa: E402

from curitiba_run.config import CRS_METRICO  # noqa: E402
from curitiba_run.features import risk_surface as rs  # noqa: E402
from curitiba_run.ingestion import geocuritiba  # noqa: E402
from curitiba_run.processing import bairros as pb  # noqa: E402
from curitiba_run.processing import grid  # noqa: E402

X0, Y0 = 670_000, 7_180_000


@pytest.fixture
def dois_bairros():
    """Centro à esquerda, Batel à direita, divisa vertical em X0 + 2 km."""
    return gpd.GeoDataFrame(
        {"bairro": ["Centro", "Batel"]},
        geometry=[box(X0, Y0, X0 + 2000, Y0 + 2000), box(X0 + 2000, Y0, X0 + 4000, Y0 + 2000)],
        crs=CRS_METRICO,
    )


@pytest.fixture
def malha(dois_bairros):
    limite = gpd.GeoDataFrame(geometry=[dois_bairros.union_all()], crs=CRS_METRICO)
    return grid.recortar_pelo_limite(grid.construir_malha(limite, resolucao=9), limite)


def test_toda_celula_recebe_um_bairro(malha, dois_bairros):
    a = pb.atribuir_bairro_dominante(malha, dois_bairros)
    assert len(a) == len(malha)
    assert a["bairro"].notna().all()
    assert set(a["bairro"]) == {"Centro", "Batel"}


def test_celula_inteira_dentro_de_um_bairro_tem_fracao_um(malha, dois_bairros):
    a = pb.atribuir_bairro_dominante(malha, dois_bairros)
    assert (a["fracao_bairro"] > 0.999).sum() > 0
    assert a["fracao_bairro"].between(0.5, 1.0 + 1e-9).all()


def test_celula_da_divisa_do_municipio_nao_parece_dividida(malha, dois_bairros):
    """A fração é sobre a parte coberta por bairro, não sobre o hexágono inteiro."""
    a = pb.atribuir_bairro_dominante(malha, dois_bairros)
    borda = a[a["bairro"] == "Centro"].sort_values("fracao_bairro")
    assert not borda["celula_dividida"].all()


def test_bairro_dominante_e_o_de_maior_area(dois_bairros):
    limite = gpd.GeoDataFrame(geometry=[dois_bairros.union_all()], crs=CRS_METRICO)
    malha = grid.recortar_pelo_limite(grid.construir_malha(limite, resolucao=9), limite)
    a = pb.atribuir_bairro_dominante(malha, dois_bairros).set_index("h3")
    centroides = malha.to_crs(CRS_METRICO).set_index("h3").geometry.centroid
    longe_da_divisa = centroides[(centroides.x < X0 + 1500)]
    assert (a.loc[longe_da_divisa.index, "bairro"] == "Centro").all()


def test_celula_herda_a_taxa_do_bairro(malha, dois_bairros):
    import pandas as pd

    a = pb.atribuir_bairro_dominante(malha, dois_bairros)
    taxa = pd.DataFrame(
        {
            "bairro": ["Centro", "Batel"],
            "populacao": [100, 200],
            "taxa_gravidade": [50.0, 10.0],
            "taxa_gravidade_eb": [48.0, 11.0],
            "taxa_gravidade_norm": [1.0, 0.0],
            "classe_risco": ["alto", "baixo"],
            "populacao_pequena": [True, True],
        }
    )
    c = rs.risco_por_celula(a, taxa)
    assert len(c) == len(a)
    assert (c.loc[c["bairro"] == "Centro", "taxa_gravidade_norm"] == 1.0).all()


def test_celula_sem_bairro_falha():
    import pandas as pd

    a = pd.DataFrame({"h3": ["x"], "bairro": [None], "fracao_bairro": [None], "celula_dividida": [False]})
    with pytest.raises(ValueError, match="sem bairro"):
        rs.risco_por_celula(a, pd.DataFrame({"bairro": []}))


def test_malha_nacional_e_filtrada_para_curitiba():
    """Um "Centro" de outro município não pode ser unido ao de Curitiba."""
    from curitiba_run.config import BAIRROS_CURITIBA

    nomes = list(BAIRROS_CURITIBA) + ["Centro"]
    municipios = ["4106902"] * 75 + ["4119152"]
    bruto = gpd.GeoDataFrame(
        {"CD_MUN": municipios, "NM_BAIRRO": nomes},
        geometry=[box(X0 + i * 10, Y0, X0 + i * 10 + 5, Y0 + 5) for i in range(76)],
        crs=CRS_METRICO,
    )
    b = geocuritiba.padronizar_bairros(bruto).set_index("bairro")
    assert len(b) == 75
    assert b.loc["Centro"].geometry.area == pytest.approx(25)


def test_malha_sem_um_bairro_falha():
    from curitiba_run.config import BAIRROS_CURITIBA

    nomes = [b for b in BAIRROS_CURITIBA if b != "Riviera"]
    bruto = gpd.GeoDataFrame(
        {"NOME": nomes},
        geometry=[box(X0 + i * 10, Y0, X0 + i * 10 + 5, Y0 + 5) for i in range(len(nomes))],
        crs=CRS_METRICO,
    )
    with pytest.raises(ValueError, match="Riviera"):
        geocuritiba.padronizar_bairros(bruto)


def test_sem_camada_de_bairros_usa_os_setores_2022(monkeypatch):
    """O GeoCuritiba público não tem camada de bairros; tem setores censitários 2022."""
    servico = "https://exemplo/MapServer"
    respostas = {
        servico: {"layers": [
            {"id": 1, "name": "Setor Censitário - 2010"},
            {"id": 2, "name": "Setor Censitário - 2022"},
            {"id": 3, "name": "Renda Média (IBGE 2022)"},
        ]},
        f"{servico}/2": {"geometryType": "esriGeometryPolygon"},
    }
    monkeypatch.setattr(geocuritiba, "_get_json", lambda url, params: respostas.get(url, {}))
    assert geocuritiba.localizar_camada_de_bairros((servico,)) == f"{servico}/2"


def test_camada_de_bairros_tem_preferencia_sobre_setores(monkeypatch):
    servico = "https://exemplo/MapServer"
    respostas = {
        servico: {"layers": [
            {"id": 2, "name": "Setor Censitário - 2022"},
            {"id": 7, "name": "Divisa de Bairros"},
        ]},
        f"{servico}/2": {"geometryType": "esriGeometryPolygon"},
        f"{servico}/7": {"geometryType": "esriGeometryPolygon"},
    }
    monkeypatch.setattr(geocuritiba, "_get_json", lambda url, params: respostas.get(url, {}))
    assert geocuritiba.localizar_camada_de_bairros((servico,)) == f"{servico}/7"


def test_setores_unidos_pelo_bairro_viram_um_poligono_por_bairro():
    from curitiba_run.config import BAIRROS_CURITIBA

    nomes = [b for b in BAIRROS_CURITIBA for _ in range(3)]  # três setores por bairro
    bruto = gpd.GeoDataFrame(
        {"CD_SETOR": [str(i) for i in range(len(nomes))], "NM_BAIRRO": nomes},
        geometry=[box(X0 + i * 10, Y0, X0 + i * 10 + 10, Y0 + 10) for i in range(len(nomes))],
        crs=CRS_METRICO,
    )
    b = geocuritiba.padronizar_bairros(bruto)
    assert len(b) == 75
    assert b.set_index("bairro").loc["Centro"].geometry.area == pytest.approx(300)


def test_celula_fora_de_qualquer_bairro_recebe_o_mais_proximo(dois_bairros):
    """Divergência de contorno: célula a poucos metros da malha de bairros."""
    limite = gpd.GeoDataFrame(geometry=[dois_bairros.union_all().buffer(200)], crs=CRS_METRICO)
    malha = grid.recortar_pelo_limite(grid.construir_malha(limite, resolucao=9), limite)
    a = pb.atribuir_bairro_dominante(malha, dois_bairros)
    assert a["bairro"].notna().all()
    proximas = a[a["bairro_por_proximidade"]]
    assert len(proximas) > 0
    assert proximas["fracao_bairro"].isna().all()


def test_celula_longe_demais_falha(dois_bairros):
    limite = gpd.GeoDataFrame(geometry=[dois_bairros.union_all().buffer(1500)], crs=CRS_METRICO)
    malha = grid.recortar_pelo_limite(grid.construir_malha(limite, resolucao=9), limite)
    with pytest.raises(ValueError, match="mesmo território"):
        pb.atribuir_bairro_dominante(malha, dois_bairros)
