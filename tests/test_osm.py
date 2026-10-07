"""Testes da ingestão do OSM.

O download em si precisa de rede e não é testado aqui. O que é testado é o que
quebrou na prática: a serialização das camadas e a classificação viária.
"""

import pytest

gpd = pytest.importorskip("geopandas")

from shapely.geometry import LineString, Point  # noqa: E402

from curitiba_run.ingestion import osm  # noqa: E402

CRS = "EPSG:31982"
LINHA = LineString([(0, 0), (100, 100)])


def arestas_como_o_osmnx_devolve() -> gpd.GeoDataFrame:
    """Reproduz o caso real: uma aresta simplificada funde várias ways do OSM.

    Quando isso acontece, `osmid`, `highway`, `name` e `lanes` viram lista
    naquela linha e seguem escalares nas demais — e o Arrow recusa a mistura.
    """
    return gpd.GeoDataFrame(
        {
            "osmid": [12345, [678, 910], 1121],
            "highway": ["residential", ["primary", "secondary"], "footway"],
            "name": ["Rua A", None, ["Rua B", "Rua C"]],
            "lanes": [None, ["2", "3"], "1"],
            "lit": ["yes", None, ["yes", "no"]],
            "length": [10.0, 20.0, 30.0],
        },
        geometry=[LINHA] * 3,
        crs=CRS,
    )


def test_gravacao_crua_falha_como_em_producao(tmp_path):
    """Confirma que o bug existe — se este teste parar de falhar, o saneamento ficou obsoleto."""
    with pytest.raises(Exception, match="cannot mix list and non-list"):
        arestas_como_o_osmnx_devolve().to_parquet(tmp_path / "cru.parquet")


def test_sanear_permite_gravar_e_reler(tmp_path):
    caminho = tmp_path / "arestas.parquet"
    osm.sanear_para_parquet(arestas_como_o_osmnx_devolve()).to_parquet(caminho)

    lido = gpd.read_parquet(caminho)
    assert len(lido) == 3
    assert lido["osmid"].tolist() == ["12345", "678;910", "1121"]
    assert lido["highway"].tolist() == ["residential", "primary;secondary", "footway"]


def test_sanear_preserva_colunas_numericas():
    """`baixo_trafego`, `iluminada` e `length` são o que a análise consome."""
    arestas = arestas_como_o_osmnx_devolve()
    limpo = osm.sanear_para_parquet(arestas)
    assert limpo["length"].dtype == arestas["length"].dtype
    assert limpo["length"].tolist() == [10.0, 20.0, 30.0]


def test_sanear_preserva_geometria_e_crs():
    limpo = osm.sanear_para_parquet(arestas_como_o_osmnx_devolve())
    assert limpo.crs == arestas_como_o_osmnx_devolve().crs
    assert limpo.geometry.geom_type.eq("LineString").all()


def test_sanear_nao_mexe_em_frame_ja_homogeneo():
    limpo_de_origem = gpd.GeoDataFrame(
        {"a": [1.0, 2.0], "b": ["x", "y"]}, geometry=[LINHA] * 2, crs=CRS
    )
    resultado = osm.sanear_para_parquet(limpo_de_origem)
    assert resultado["a"].tolist() == [1.0, 2.0]
    assert resultado["b"].tolist() == ["x", "y"]


def test_sanear_funciona_com_pontos(tmp_path):
    postes = gpd.GeoDataFrame(
        {"osmid": [1, [2, 3]]}, geometry=[Point(0, 0), Point(1, 1)], crs=CRS
    )
    osm.sanear_para_parquet(postes).to_parquet(tmp_path / "postes.parquet")
    assert gpd.read_parquet(tmp_path / "postes.parquet").shape[0] == 2


def test_salvar_sanea_automaticamente(tmp_path):
    """O saneamento mora em `salvar` — quem chama não precisa lembrar dele."""
    osm.salvar({"arestas": arestas_como_o_osmnx_devolve()}, destino=tmp_path)
    assert (tmp_path / "arestas.parquet").exists()


# ----------------------------------------------------- classificação viária


def test_classificacao_resolve_tags_em_lista():
    """Com `highway` em lista, vale o primeiro valor — e nada explode."""
    classificado = osm.classificar_hierarquia_viaria(arestas_como_o_osmnx_devolve())
    assert classificado["tipo_via"].tolist() == ["residential", "primary", "footway"]
    assert classificado["baixo_trafego"].tolist() == [1.0, 0.0, 1.0]


def test_vias_ambiguas_ficam_no_meio():
    """`unclassified` não é nem boa nem ruim; forçar um extremo inventaria certeza."""
    arestas = gpd.GeoDataFrame(
        {"highway": ["unclassified"]}, geometry=[LINHA], crs=CRS
    )
    assert osm.classificar_hierarquia_viaria(arestas)["baixo_trafego"].iloc[0] == 0.5


def test_iluminacao_marcada_a_partir_da_tag_lit():
    classificado = osm.classificar_hierarquia_viaria(arestas_como_o_osmnx_devolve())
    assert classificado["iluminada"].tolist() == [1.0, 0.0, 1.0]


def test_sem_tag_lit_a_coluna_nasce_zerada():
    arestas = gpd.GeoDataFrame({"highway": ["residential"]}, geometry=[LINHA], crs=CRS)
    assert osm.classificar_hierarquia_viaria(arestas)["iluminada"].iloc[0] == 0.0


# ------------------------------------------------- hierarquia: casos revisados


def _uma_aresta(classe: str) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"highway": [classe]}, geometry=[LINHA], crs=CRS)


def test_coletora_de_bairro_nao_e_rodovia():
    """`tertiary` é coletora com faixa de pedestre, não via expressa.

    Agrupá-la com `motorway` respondia por 73,5% das células zeradas na
    dimensão — lugares perfeitamente corríveis marcados como o pior caso.
    """
    assert osm.classificar_hierarquia_viaria(_uma_aresta("tertiary"))["baixo_trafego"].iloc[0] == 0.5
    assert "tertiary" not in osm.VIAS_ALTO_TRAFEGO


def test_canaleta_do_brt_e_alto_trafego():
    """Via exclusiva de biarticulado não é ambígua."""
    assert osm.classificar_hierarquia_viaria(_uma_aresta("busway"))["baixo_trafego"].iloc[0] == 0.0


def test_as_tres_listas_nao_se_sobrepoem():
    """Uma classe em duas listas tornaria o resultado dependente da ordem."""
    listas = (osm.VIAS_BAIXO_TRAFEGO, osm.VIAS_ALTO_TRAFEGO, osm.VIAS_AMBIGUAS)
    for i, a in enumerate(listas):
        for b in listas[i + 1:]:
            assert not (a & b), f"classe em duas listas: {a & b}"


def test_classe_desconhecida_avisa_antes_de_virar_meio(caplog):
    """0,5 por decisão e 0,5 por desconhecimento são indistinguíveis no número.

    Se o OSM criar uma classe nova, ela entra como ambígua em silêncio. O aviso
    é a única coisa que separa as duas situações.
    """
    import logging

    with caplog.at_level(logging.WARNING):
        resultado = osm.classificar_hierarquia_viaria(_uma_aresta("corredor_lunar"))

    assert resultado["baixo_trafego"].iloc[0] == 0.5
    assert any("corredor_lunar" in r.getMessage() for r in caplog.records)


def test_classe_conhecida_nao_gera_aviso(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        osm.classificar_hierarquia_viaria(_uma_aresta("tertiary"))

    assert not [r for r in caplog.records if "fora das três listas" in r.getMessage()]


def test_classificar_sobrevive_a_ida_e_volta_pelo_parquet(tmp_path):
    """Reclassificar uma camada já gravada tem de dar o mesmo resultado.

    `sanear_para_parquet` transforma `highway` em texto unido por `;` quando a
    aresta funde várias ways. A etapa 5 da Fase 1 reclassifica a camada lida do
    disco — se `_primeiro` não entendesse esse texto, a classe viria como
    desconhecida e a aresta cairia em 0,5 em silêncio.
    """
    cru = osm.classificar_hierarquia_viaria(arestas_como_o_osmnx_devolve())

    caminho = tmp_path / "arestas.parquet"
    osm.sanear_para_parquet(arestas_como_o_osmnx_devolve()).to_parquet(caminho)
    relido = osm.classificar_hierarquia_viaria(gpd.read_parquet(caminho))

    assert relido["tipo_via"].tolist() == cru["tipo_via"].tolist()
    assert relido["baixo_trafego"].tolist() == cru["baixo_trafego"].tolist()
    assert relido["iluminada"].tolist() == cru["iluminada"].tolist()


def test_classificar_e_idempotente():
    """Aplicar duas vezes não muda nada — a etapa 5 roda sobre dado já rotulado."""
    uma = osm.classificar_hierarquia_viaria(arestas_como_o_osmnx_devolve())
    duas = osm.classificar_hierarquia_viaria(uma)
    assert duas["baixo_trafego"].tolist() == uma["baixo_trafego"].tolist()
    assert duas["tipo_via"].tolist() == uma["tipo_via"].tolist()
