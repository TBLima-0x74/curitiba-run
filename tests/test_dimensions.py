"""Testes das dimensões do IAC, com geometrias de medidas conhecidas.

O download do OSM precisa de rede; tudo o que vem depois dele não precisa. Estes
testes exercitam o recorte por célula, as densidades e as razões contra valores
exatos — se a soma dos comprimentos por célula não bate com o comprimento da
linha, há perda ou dupla contagem no overlay, e o teste falha.
"""

import numpy as np
import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("h3")

from curitiba_run.features import dimensions as dim  # noqa: E402
from curitiba_run.processing import grid  # noqa: E402
from tests.fixtures import cidade_sintetica as cs  # noqa: E402


@pytest.fixture(scope="module")
def malha():
    limite = cs.area_de_estudo()
    m = grid.construir_malha(limite.to_crs("EPSG:4326"), resolucao=9)
    return grid.recortar_pelo_limite(m, limite)


# ------------------------------------------------------------------- helpers


def test_comprimento_por_celula_conserva_o_total(malha):
    """Uma linha recortada em N pedaços continua tendo o mesmo comprimento."""
    linha = gpd.GeoDataFrame(geometry=[cs.linha_horizontal(comprimento=2000.0)], crs=malha.crs)
    por_celula = dim.comprimento_por_celula(linha, malha)
    assert por_celula.sum() == pytest.approx(2000.0, rel=1e-6)


def test_comprimento_por_celula_distribui_entre_varias_celulas(malha):
    linha = gpd.GeoDataFrame(geometry=[cs.linha_horizontal()], crs=malha.crs)
    por_celula = dim.comprimento_por_celula(linha, malha)
    assert (por_celula > 0).sum() > 3


def test_comprimento_ponderado_por_coluna(malha):
    """Peso 0 zera a contribuição; peso 1 devolve o comprimento cheio."""
    linhas = gpd.GeoDataFrame(
        {"peso": [1.0, 0.0]},
        geometry=[cs.linha_horizontal(offset_y=600), cs.linha_horizontal(offset_y=1400)],
        crs=malha.crs,
    )
    total = dim.comprimento_por_celula(linhas, malha)
    ponderado = dim.comprimento_por_celula(linhas, malha, coluna_peso="peso")
    assert total.sum() == pytest.approx(4000.0, rel=1e-6)
    assert ponderado.sum() == pytest.approx(2000.0, rel=1e-6)


def test_area_por_celula_conserva_area_do_parque(malha):
    parque = cs.parque(lado_parque=400.0)
    por_celula = dim.area_por_celula(parque, malha)
    assert por_celula.sum() == pytest.approx(400.0**2, rel=1e-3)


def test_area_por_celula_nao_conta_sobreposicao_duas_vezes(malha):
    """Dois polígonos idênticos — OSM e IPPUC mapeando o mesmo parque — contam uma vez."""
    p = cs.parque(lado_parque=400.0)
    duplicado = gpd.GeoDataFrame(pd.concat([p, p], ignore_index=True), crs=p.crs)
    assert dim.area_por_celula(duplicado, malha).sum() == pytest.approx(400.0**2, rel=1e-3)


def test_contagem_por_celula_conserva_o_total(malha):
    pts = cs.postes(n=40)
    assert dim.contagem_por_celula(pts, malha).sum() == pytest.approx(40.0)


def test_media_zonal_reflete_o_gradiente(malha, tmp_path):
    caminho = cs.raster_declividade(tmp_path / "decl.tif")
    media = dim.media_zonal(caminho, malha)

    centroides = malha.set_index("h3").geometry.centroid.x
    validos = media.dropna()
    corr = np.corrcoef(centroides.reindex(validos.index), validos)[0, 1]
    # Declividade cresce de oeste para leste: correlação com x deve ser forte.
    assert corr > 0.95


def test_suavizar_por_vizinhanca_preserva_media_aproximada(malha):
    valores = pd.Series(
        np.random.default_rng(0).random(len(malha)), index=malha["h3"].to_numpy()
    )
    suave = dim.suavizar_por_vizinhanca(valores, peso_vizinho=0.5)
    assert suave.mean() == pytest.approx(valores.mean(), abs=0.05)
    assert suave.std() < valores.std()  # suavizar reduz dispersão


def test_suavizar_com_peso_zero_e_identidade(malha):
    valores = pd.Series(1.0, index=malha["h3"].to_numpy())
    pd.testing.assert_series_equal(dim.suavizar_por_vizinhanca(valores, peso_vizinho=0.0), valores)


# ----------------------------------------------------------------- dimensões


def test_superficie_caminhavel_em_km_por_km2(malha):
    arestas = cs.malha_viaria()
    densidade = dim.superficie_caminhavel(arestas, malha)

    comprimento_total_km = arestas.length.sum() / 1000
    area_total_km2 = malha["area_km2"].sum()
    media_esperada = comprimento_total_km / area_total_km2

    ponderada = (densidade * malha.set_index("h3")["area_km2"]).sum() / area_total_km2
    assert ponderada == pytest.approx(media_esperada, rel=1e-3)


def test_transito_tranquilo_fica_entre_zero_e_um(malha):
    razao = dim.transito_tranquilo(cs.malha_viaria(), malha).dropna()
    assert razao.between(0, 1).all()


def test_transito_tranquilo_e_nan_onde_nao_ha_via(malha):
    """Ausência de via não é via ruim — precisa virar NaN, não zero."""
    poucas = cs.malha_viaria().iloc[:1]
    razao = dim.transito_tranquilo(poucas, malha)
    assert razao.isna().sum() > 0


def test_transito_tranquilo_maxima_quando_tudo_e_baixo_trafego(malha):
    arestas = cs.malha_viaria()
    arestas["baixo_trafego"] = 1.0
    razao = dim.transito_tranquilo(arestas, malha).dropna()
    assert razao.max() == pytest.approx(1.0, rel=1e-6)


def test_transito_tranquilo_exige_a_coluna_de_classificacao(malha):
    arestas = cs.malha_viaria().drop(columns=["baixo_trafego"])
    with pytest.raises(ValueError, match="classificar_hierarquia_viaria"):
        dim.transito_tranquilo(arestas, malha)


def test_espaco_dedicado_e_fracao_valida(malha):
    fracao = dim.espaco_dedicado(cs.parque(), malha)
    assert fracao.between(0, 1).all()
    assert fracao.max() > 0


def test_espaco_dedicado_beneficia_o_entorno(malha):
    """Sem suavização, só quem contém o parque pontua; com ela, o entorno também."""
    sem = dim.espaco_dedicado(cs.parque(), malha, peso_vizinho=0.0)
    com = dim.espaco_dedicado(cs.parque(), malha, peso_vizinho=0.5)
    assert (com > 0).sum() > (sem > 0).sum()


def test_continuidade_conta_apenas_intersecoes(malha):
    nos = cs.nos_da_malha(n=25, grau=4)
    nos.loc[nos.index[:10], "grau"] = 2  # becos sem saída não são interseção
    densidade = dim.continuidade(nos, malha, grau_minimo=3)
    area_total = malha["area_km2"].sum()
    assert (densidade * malha.set_index("h3")["area_km2"]).sum() == pytest.approx(15.0, rel=1e-6)
    assert densidade.sum() > 0
    assert area_total > 0


def test_declividade_devolve_graus_e_segue_o_gradiente(malha, tmp_path):
    """Valor bruto em graus, não invertido — a inversão mora na normalização."""
    caminho = cs.raster_declividade(tmp_path / "decl.tif", graus_min=0, graus_max=20)
    valores = dim.declividade(malha, caminho).dropna()

    centroides = malha.set_index("h3").geometry.centroid.x.reindex(valores.index)
    assert np.corrcoef(centroides, valores)[0, 1] > 0.95   # cresce para leste
    assert valores.between(0, 20).all()                     # em graus, não em 0–1


def test_declividade_exige_raster_com_erro_acionavel(malha):
    with pytest.raises(ValueError, match="geocuritiba"):
        dim.declividade(malha, None)


def test_densidade_malha_funde_as_duas_componentes(malha):
    """A fusão existe porque as duas correlacionavam 0,95 e dobravam o peso."""
    arestas, nos = cs.malha_viaria(), cs.nos_da_malha()
    fundida = dim.densidade_malha(arestas, nos, malha)

    assert fundida.dropna().between(0, 1).all()
    assert len(fundida) == len(malha)

    from curitiba_run.features import suitability_index as si
    km = si.normalizar(dim.superficie_caminhavel(arestas, malha))
    inter = si.normalizar(dim.continuidade(nos, malha))
    pd.testing.assert_series_equal(fundida, (km + inter) / 2, check_names=False)


def test_densidade_malha_reaproveita_o_recorte(malha):
    arestas, nos = cs.malha_viaria(), cs.nos_da_malha()
    pedacos = dim.recortar_linhas(arestas, malha)
    pd.testing.assert_series_equal(
        dim.densidade_malha(arestas, nos, malha),
        dim.densidade_malha(arestas, nos, malha, pedacos=pedacos),
        check_names=False,
    )


def test_iluminacao_usa_so_os_postes_por_padrao(malha):
    """`lit` do OSM entra só sob pedido — ver docstring de `iluminacao`."""
    arestas = cs.malha_viaria()
    so_postes = dim.iluminacao(malha, cs.postes(), arestas)
    com_lit = dim.iluminacao(malha, cs.postes(), arestas, usar_lit=True)

    assert so_postes.dropna().between(0, 1).all()
    assert so_postes.dropna().std() > 0
    assert not so_postes.equals(com_lit)


def test_lit_ausente_derruba_a_nota_de_quem_tem_poste(malha):
    """Onde `lit` não foi mapeado, ligá-lo só pode baixar a nota.

    É a mecânica do defeito encontrado em Curitiba: `lit` ausente entra como
    zero e, valendo metade do peso, puxa para baixo células que têm poste. Como
    a composição é média ponderada, `0,5·postes + 0,5·0 < postes` sempre que
    houver poste — então a asserção vale para qualquer cidade, não só para a
    distribuição curitibana.
    """
    arestas = cs.malha_viaria()
    arestas["iluminada"] = 0.0
    arestas.loc[arestas.index[0], "iluminada"] = 1.0   # mapeado numa via só

    sem_lit = dim.iluminacao(malha, cs.postes(), arestas)
    com_lit = dim.iluminacao(malha, cs.postes(), arestas, usar_lit=True)
    cobertura = dim.comprimento_por_celula(arestas, malha, coluna_peso="iluminada")

    nao_mapeadas = cobertura[cobertura == 0].index
    alvo = [h for h in nao_mapeadas if sem_lit.get(h, 0) > 0]
    assert len(alvo) > 5, "a fixture precisa de células com poste e sem lit"
    assert (com_lit.loc[alvo] < sem_lit.loc[alvo]).all()


def test_iluminacao_exige_postes(malha):
    """A cobertura `lit` sozinha não sustenta a dimensão."""
    with pytest.raises(ValueError, match="Informe .pontos_luz"):
        dim.iluminacao(malha, arestas=cs.malha_viaria())


def test_iluminacao_e_ausente_onde_nao_ha_via(malha):
    """Não há como avaliar a iluminação de uma rua que não existe."""
    poucas = cs.malha_viaria().iloc[:1]
    valores = dim.iluminacao(malha, pontos_luz=cs.postes(), arestas=poucas)
    assert valores.isna().sum() > 0


def test_iluminacao_normaliza_postes_por_km_de_via(malha):
    """Dobrar a via com os mesmos postes piora a iluminação relativa.

    É esta propriedade que descorrelaciona a dimensão da densidade da malha:
    com normalização por área, mais via daria mais iluminação.
    """
    postes = cs.postes(n=60)
    poucas_vias = cs.malha_viaria(n_horizontais=2, n_verticais=2)
    muitas_vias = cs.malha_viaria(n_horizontais=8, n_verticais=8)

    com_poucas = dim.iluminacao(malha, postes, poucas_vias, peso_pontos=1.0).dropna()
    com_muitas = dim.iluminacao(malha, postes, muitas_vias, peso_pontos=1.0).dropna()

    comuns = com_poucas.index.intersection(com_muitas.index)
    assert len(comuns) > 5
    # Mais quilômetros de rua para os mesmos postes: a razão cai na média.
    assert com_muitas.loc[comuns].mean() < com_poucas.loc[comuns].mean()


def test_iluminacao_exige_vias_para_normalizar_os_postes(malha):
    with pytest.raises(ValueError, match="km de via"):
        dim.iluminacao(malha, pontos_luz=cs.postes())


def test_iluminacao_exige_alguma_fonte(malha):
    with pytest.raises(ValueError, match="Informe .pontos_luz"):
        dim.iluminacao(malha)


# --------------------------------------------------------------- integração


def test_calcular_todas_produz_as_cinco_dimensoes(malha, tmp_path):
    from curitiba_run.config import IAC_DIMENSOES

    camadas = cs.cidade_completa()[1]
    dims = dim.calcular_todas(
        malha,
        arestas=camadas["arestas"],
        nos=camadas["nos"],
        espacos=camadas["espacos"],
        declividade_raster=cs.raster_declividade(tmp_path / "d.tif"),
        pontos_luz=camadas["pontos_luz"],
    )
    assert list(dims.columns) == list(IAC_DIMENSOES)
    assert len(dims.columns) == 5
    assert len(dims) == len(malha)
    assert dims.index.name == "h3"


def test_pipeline_completo_ate_o_iac(malha, tmp_path):
    """Da geometria bruta ao índice composto, sem tocar a rede."""
    from curitiba_run.features import suitability_index as si

    camadas = cs.cidade_completa()[1]
    brutas = dim.calcular_todas(
        malha,
        arestas=camadas["arestas"],
        nos=camadas["nos"],
        espacos=camadas["espacos"],
        declividade_raster=cs.raster_declividade(tmp_path / "d.tif"),
        pontos_luz=camadas["pontos_luz"],
    )
    normalizadas = si.normalizar_dimensoes(brutas)
    iac = si.compor(normalizadas)

    validos = iac.dropna()
    assert len(validos) > 0
    assert validos.between(0, 1).all()

    cenarios = si.avaliar_cenarios_de_peso(normalizadas)
    estabilidade = si.estabilidade_do_ranking(cenarios)
    # Os cenários discordam nos pesos, não na leitura do território.
    assert estabilidade.min().min() > 0.5


# ------------------------------------------------- reaproveitamento do recorte


def test_recorte_reaproveitado_da_o_mesmo_resultado(malha):
    """A otimização não pode mudar o número — só o tempo que leva para obtê-lo."""
    arestas = cs.malha_viaria()
    pedacos = dim.recortar_linhas(arestas, malha, ("baixo_trafego", "iluminada"))

    for coluna in (None, "baixo_trafego", "iluminada"):
        sem = dim.comprimento_por_celula(arestas, malha, coluna_peso=coluna)
        com = dim.comprimento_por_celula(arestas, malha, coluna_peso=coluna, pedacos=pedacos)
        pd.testing.assert_series_equal(sem, com, check_names=False)


def test_dimensoes_com_recorte_pronto_batem_com_o_calculo_direto(malha):
    arestas = cs.malha_viaria()
    pedacos = dim.recortar_linhas(arestas, malha, ("baixo_trafego", "iluminada"))

    pd.testing.assert_series_equal(
        dim.superficie_caminhavel(arestas, malha),
        dim.superficie_caminhavel(arestas, malha, pedacos=pedacos),
        check_names=False,
    )
    pd.testing.assert_series_equal(
        dim.transito_tranquilo(arestas, malha),
        dim.transito_tranquilo(arestas, malha, pedacos=pedacos),
        check_names=False,
    )
    pd.testing.assert_series_equal(
        dim.iluminacao(malha, cs.postes(), arestas),
        dim.iluminacao(malha, cs.postes(), arestas, pedacos=pedacos),
        check_names=False,
    )


def test_recorte_conserva_o_comprimento_total(malha):
    arestas = cs.malha_viaria()
    pedacos = dim.recortar_linhas(arestas, malha)
    assert pedacos["_m"].sum() == pytest.approx(arestas.length.sum(), rel=1e-6)


def test_recorte_exige_que_as_colunas_de_peso_existam(malha):
    with pytest.raises(ValueError, match="Colunas de peso ausentes"):
        dim.recortar_linhas(cs.malha_viaria(), malha, ("inexistente",))


def test_peso_ausente_no_recorte_tem_erro_acionavel(malha):
    arestas = cs.malha_viaria()
    pedacos = dim.recortar_linhas(arestas, malha)  # sem colunas de peso
    with pytest.raises(ValueError, match="colunas_peso"):
        dim.comprimento_por_celula(arestas, malha, coluna_peso="baixo_trafego", pedacos=pedacos)


def test_area_por_celula_repara_poligono_invalido(malha):
    """Polígono com auto-interseção é comum no OSM e derrubaria o union_all."""
    from shapely.geometry import Polygon

    gravata = Polygon([(670200, 7180200), (670600, 7180600),
                       (670600, 7180200), (670200, 7180600)])
    assert not gravata.is_valid

    camada = gpd.GeoDataFrame(geometry=[gravata], crs=malha.crs)
    resultado = dim.area_por_celula(camada, malha)
    assert resultado.sum() > 0
    assert resultado.notna().all()
