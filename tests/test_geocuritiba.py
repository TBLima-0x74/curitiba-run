"""Testes da ingestão do GeoCuritiba.

As chamadas de rede não são testadas aqui. O que é testado é a derivação da
declividade, que é pura computação e onde um erro de sinal ou de unidade
passaria despercebido até contaminar o índice inteiro.
"""

import numpy as np
import pytest

pytest.importorskip("rasterio")

import rasterio  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from curitiba_run.ingestion import geocuritiba as geo  # noqa: E402

CRS = "EPSG:31982"


def plano_inclinado(caminho, graus: float, resolucao: float = 10.0, n: int = 50):
    """DTM que é um plano com inclinação exata, para conferir o resultado."""
    passo_z = resolucao * np.tan(np.radians(graus))
    z = (np.arange(n, dtype="float32") * passo_z)[None, :].repeat(n, axis=0)

    perfil = {
        "driver": "GTiff", "height": n, "width": n, "count": 1, "dtype": "float32",
        "crs": CRS, "transform": from_origin(670000, 7180000, resolucao, resolucao),
    }
    with rasterio.open(caminho, "w", **perfil) as dst:
        dst.write(z, 1)
    return caminho


@pytest.mark.parametrize("graus", [0.0, 5.0, 10.0, 25.0])
def test_declividade_recupera_a_inclinacao_exata(tmp_path, graus):
    mdt = plano_inclinado(tmp_path / "mdt.tif", graus=graus)
    saida = geo.derivar_declividade(mdt, tmp_path / "decl.tif")

    with rasterio.open(saida) as src:
        valores = src.read(1)

    # As bordas usam diferença de um lado só; o miolo é o que importa.
    miolo = valores[2:-2, 2:-2]
    assert np.allclose(miolo, graus, atol=0.01)


def test_declividade_nao_depende_do_sinal_da_encosta(tmp_path):
    """Subir 10° e descer 10° são a mesma declividade."""
    subida = geo.derivar_declividade(plano_inclinado(tmp_path / "a.tif", 12.0), tmp_path / "da.tif")

    descida_mdt = tmp_path / "b.tif"
    with rasterio.open(subida.parent / "a.tif") as src:
        z, perfil = src.read(1), src.profile
    with rasterio.open(descida_mdt, "w", **perfil) as dst:
        dst.write(-z, 1)
    descida = geo.derivar_declividade(descida_mdt, tmp_path / "db.tif")

    with rasterio.open(subida) as a, rasterio.open(descida) as b:
        assert np.allclose(a.read(1)[2:-2, 2:-2], b.read(1)[2:-2, 2:-2], atol=0.01)


def test_declividade_preserva_crs_e_grade(tmp_path):
    mdt = plano_inclinado(tmp_path / "mdt.tif", 8.0)
    saida = geo.derivar_declividade(mdt, tmp_path / "decl.tif")

    with rasterio.open(mdt) as origem, rasterio.open(saida) as destino:
        assert destino.crs == origem.crs
        assert destino.transform == origem.transform
        assert destino.shape == origem.shape


def test_declividade_de_terreno_plano_e_zero(tmp_path):
    mdt = plano_inclinado(tmp_path / "mdt.tif", 0.0)
    saida = geo.derivar_declividade(mdt, tmp_path / "decl.tif")
    with rasterio.open(saida) as src:
        assert np.allclose(src.read(1), 0.0, atol=1e-6)


def test_urls_apontam_para_o_servidor_do_ippuc():
    """Guarda contra alguém trocar o host sem perceber."""
    for url in (geo.CAMADA_POSTES, geo.SERVICO_MDT, geo.SERVICO_UNIDADES_CONSERVACAO):
        assert url.startswith("https://geocuritiba.ippuc.org.br/server/rest/services")


# ------------------------------------------------- filtros de tipo e acesso


def _postes_sinteticos():
    import geopandas as gpd
    from shapely.geometry import Point

    return gpd.GeoDataFrame(
        {"tipoposte": [2, 2, 2, 4, 4, 3, 5, 0]},
        geometry=[Point(i, i) for i in range(8)],
        crs=CRS,
    )


def test_filtro_de_postes_descarta_rede_eletrica():
    """Poste de rede elétrica não ilumina — contá-lo premiaria distribuição aérea."""
    filtrados = geo.filtrar_postes_de_iluminacao(_postes_sinteticos())
    assert set(filtrados["tipoposte"]) == {2, 3}
    assert len(filtrados) == 4


def test_filtro_de_postes_exige_a_coluna():
    import geopandas as gpd
    from shapely.geometry import Point

    sem = gpd.GeoDataFrame(geometry=[Point(0, 0)], crs=CRS)
    with pytest.raises(ValueError, match="tipoposte"):
        geo.filtrar_postes_de_iluminacao(sem)


def test_dominio_de_tipoposte_bate_com_o_do_servico():
    assert geo.TIPO_POSTE[2] == "Iluminação"
    assert geo.TIPO_POSTE[4] == "Rede elétrica"
    assert 4 not in geo.TIPOS_POSTE_ILUMINACAO


def _sem_acento(texto: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )


def test_nao_ha_ponderacao_entre_tipos_de_poste():
    """A camada não traz potência nem altura, então não há equivalência física."""
    texto = _sem_acento(geo.equivalencia_entre_tipos_de_poste())
    assert "funcional" in texto
    assert "inventado" in texto
    for campo in geo.CAMPOS_AUSENTES_NA_CAMADA:
        assert _sem_acento(campo) in texto, f"a justificativa não menciona {campo}"


def _areas_sinteticas():
    import geopandas as gpd
    from shapely.geometry import Polygon

    def quadrado(x, lado):
        return Polygon([(x, 0), (x + lado, 0), (x + lado, lado), (x, lado)])

    return gpd.GeoDataFrame(
        {
            "camada_id": [2, 3, 4, 5, 7, 10, 1],
            "sigla": ["PQ", "PQ", "BQ", "BCBU", "RPPNM", "APA", "ESEC"],
        },
        geometry=[quadrado(i * 2000, 100) for i in range(6)] + [quadrado(12000, 10000)],
        crs=CRS,
    )


def test_filtro_de_areas_mantem_so_as_publicas():
    publicas = geo.filtrar_areas_publicas(_areas_sinteticas())
    assert set(publicas["camada_id"]) == {2, 3, 4, 5}
    assert "RPPNM" not in set(publicas["sigla"])
    assert "APA" not in set(publicas["sigla"])


def test_filtro_de_areas_funciona_pela_sigla():
    areas = _areas_sinteticas().drop(columns=["camada_id"])
    publicas = geo.filtrar_areas_publicas(areas)
    assert set(publicas["sigla"]) == {"PQ", "BQ", "BCBU"}


def test_filtro_de_areas_exige_coluna_de_categoria():
    areas = _areas_sinteticas().drop(columns=["camada_id", "sigla"])
    with pytest.raises(ValueError, match="público de privado"):
        geo.filtrar_areas_publicas(areas)


def test_apa_sozinha_dominaria_a_area_total():
    """As duas APAs de Curitiba somam 197 km² — quase metade do município."""
    areas = _areas_sinteticas()
    publicas = geo.filtrar_areas_publicas(areas)
    assert publicas.area.sum() < areas.area.sum() / 10
