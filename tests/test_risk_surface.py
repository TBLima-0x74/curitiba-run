"""Testes da taxa por habitante e da normalização de 0 a 1."""

import pandas as pd
import pytest

from curitiba_run.features import risk_surface as rs


def tabelas(n=50):
    bairros = [f"B{i:02d}" for i in range(n)]
    ocorr = pd.DataFrame(
        {
            "bairro": bairros,
            "n_ocorrencias": [10 + i for i in range(n)],
            "gravidade": [2.0 * (1 + i) for i in range(n)],
        }
    )
    ocorr["gravidade_anual"] = ocorr["gravidade"] / 2  # dois anos de base
    pop = pd.DataFrame({"bairro": bairros, "populacao": [10_000] * n})
    return ocorr, pop


def test_taxa_e_gravidade_anual_por_cem_mil():
    ocorr, pop = tabelas()
    t = rs.taxa_por_habitante(ocorr, pop).set_index("bairro")
    assert t.loc["B00", "taxa_gravidade"] == pytest.approx(1.0 / 10_000 * 100_000)


def test_taxa_de_ocorrencias_usa_o_mesmo_periodo():
    ocorr, pop = tabelas()
    t = rs.taxa_por_habitante(ocorr, pop).set_index("bairro")
    assert t.loc["B00", "taxa_ocorrencias"] == pytest.approx(10 / 2 / 10_000 * 100_000)


def test_normalizada_fica_entre_zero_e_um():
    t = rs.taxa_por_habitante(*tabelas())
    assert t["taxa_gravidade_norm"].between(0, 1).all()
    assert t["taxa_gravidade_norm"].min() == 0 and t["taxa_gravidade_norm"].max() == 1


def test_um_bairro_extremo_nao_esmaga_os_outros():
    """Com mínimo-máximo puro, um Centro 100× maior jogaria os demais perto de zero.

    Feito com 75 bairros de propósito. O percentil 98 interpolado só deixa o
    extremo de fora quando 0,98·(n−1) ≤ n−2, isto é, com n ≥ 51. Com 50
    bairros ele já puxaria o teto para cima — Curitiba tem 75, e passa.
    """
    ocorr, pop = tabelas(75)
    ocorr.loc[ocorr["bairro"] == "B74", ["gravidade", "gravidade_anual"]] = [20_000.0, 10_000.0]
    t = rs.taxa_por_habitante(ocorr, pop, escala="linear")
    assert t["taxa_gravidade_norm"].median() == pytest.approx(0.5, abs=0.05)


def test_ordem_e_preservada():
    t = rs.taxa_por_habitante(*tabelas())
    assert t["taxa_gravidade"].rank().corr(t["taxa_gravidade_norm"].rank()) > 0.99


def test_marca_populacao_pequena():
    ocorr, pop = tabelas()
    pop.loc[0, "populacao"] = 800
    t = rs.taxa_por_habitante(ocorr, pop).set_index("bairro")
    assert t.loc["B00", "populacao_pequena"] and not t.loc["B01", "populacao_pequena"]


def test_bairro_sem_populacao_falha():
    ocorr, pop = tabelas()
    with pytest.raises(ValueError, match="B03"):
        rs.taxa_por_habitante(ocorr, pop[pop["bairro"] != "B03"])


def test_populacao_zero_falha():
    ocorr, pop = tabelas()
    pop.loc[0, "populacao"] = 0
    with pytest.raises(ValueError, match="zero"):
        rs.taxa_por_habitante(ocorr, pop)


def cauda_pesada(n=75):
    """Como Curitiba: a maioria baixa, poucos bairros muito acima."""
    ocorr, pop = tabelas(n)
    graves = [1.0] * (n - 4) + [400.0, 500.0, 600.0, 800.0]
    ocorr["gravidade"] = [g * (1 + i / n) for i, g in enumerate(graves)]
    ocorr["gravidade_anual"] = ocorr["gravidade"] / 2
    return ocorr, pop


def test_escala_log_espalha_a_cauda_pesada():
    linear = rs.taxa_por_habitante(*cauda_pesada(), escala="linear")
    log = rs.taxa_por_habitante(*cauda_pesada(), escala="log")
    assert log["taxa_gravidade_norm"].median() > 5 * linear["taxa_gravidade_norm"].median()


def test_escala_log_preserva_a_ordem_e_a_classe_alto_baixo():
    linear = rs.taxa_por_habitante(*cauda_pesada(), escala="linear")["taxa_gravidade_norm"]
    log = rs.taxa_por_habitante(*cauda_pesada(), escala="log")["taxa_gravidade_norm"]
    assert linear.rank().corr(log.rank()) > 0.99
    assert ((linear >= linear.median()) == (log >= log.median())).all()


def test_escala_log_e_o_padrao_e_zero_continua_zero():
    ocorr, pop = tabelas()
    ocorr.loc[0, ["gravidade", "gravidade_anual"]] = [0.0, 0.0]
    t = rs.taxa_por_habitante(ocorr, pop).set_index("bairro")
    assert t.loc["B00", "taxa_gravidade_norm"] == 0


def test_escala_desconhecida_falha():
    with pytest.raises(ValueError, match="escala"):
        rs.taxa_por_habitante(*tabelas(), escala="raiz")


def test_classe_de_risco_corta_na_mediana_dos_bairros():
    t = rs.taxa_por_habitante(*tabelas(75))
    assert (t["classe_risco"] == "alto").sum() == 38
    assert (t["classe_risco"] == "baixo").sum() == 37
    mediana = t["taxa_gravidade"].median()
    assert (t.loc[t["classe_risco"] == "alto", "taxa_gravidade"] >= mediana).all()


def test_classe_nao_depende_da_escala():
    """Log e linear têm a mesma ordem: a classe tem de sair igual."""
    log = rs.taxa_por_habitante(*cauda_pesada(), escala="log")["classe_risco"]
    linear = rs.taxa_por_habitante(*cauda_pesada(), escala="linear")["classe_risco"]
    assert (log == linear).all()


def test_celula_herda_a_classe_do_bairro():
    import pandas as pd

    ocorr, pop = tabelas(4)
    taxa = rs.taxa_por_habitante(ocorr, pop, suavizar=False)
    atrib = pd.DataFrame(
        {
            "h3": ["a", "b", "c"],
            "bairro": ["B00", "B03", "B03"],
            "fracao_bairro": [1.0, 1.0, 0.6],
            "bairro_por_proximidade": [False] * 3,
            "celula_dividida": [False] * 3,
        }
    )
    c = rs.risco_por_celula(atrib, taxa).set_index("h3")
    assert c.loc["a", "classe_risco"] == "baixo"
    assert c.loc["b", "classe_risco"] == c.loc["c", "classe_risco"] == "alto"


# ------------------------------------------------------ Bayes empírico


def _bairros_eb():
    """Um bairro grande e vários pequenos, com taxas observadas iguais em média."""
    import pandas as pd

    gravidade = pd.Series([1000.0, 40.0, 0.0, 6.0, 30.0, 12.0, 25.0, 8.0])
    exposicao = pd.Series([1_000_000.0, 2_000, 2_000, 2_000, 20_000, 20_000, 20_000, 20_000])
    return gravidade, exposicao


def test_bairro_grande_quase_nao_muda():
    g, e = _bairros_eb()
    eb = rs.suavizar_bayesiano_empirico(g, e)
    assert eb.loc[0, "peso_proprio"] > 0.95
    assert eb.loc[0, "taxa_eb"] == pytest.approx(g[0] / e[0], rel=0.05)


def test_bairro_pequeno_e_puxado_para_a_media():
    g, e = _bairros_eb()
    eb = rs.suavizar_bayesiano_empirico(g, e)
    media = g.sum() / e.sum()
    bruta = g / e
    assert abs(eb.loc[1, "taxa_eb"] - media) < abs(bruta[1] - media)
    assert eb.loc[1, "peso_proprio"] < eb.loc[0, "peso_proprio"]


def test_zero_ocorrencias_em_bairro_pequeno_nao_fica_zero():
    """Nenhuma ocorrência em poucos moradores é evidência fraca de segurança."""
    g, e = _bairros_eb()
    assert rs.suavizar_bayesiano_empirico(g, e).loc[2, "taxa_eb"] > 0


def test_sem_variacao_real_todos_recebem_a_media():
    import pandas as pd

    g = pd.Series([10.0, 11.0, 9.0, 10.0])
    e = pd.Series([10_000.0] * 4)
    eb = rs.suavizar_bayesiano_empirico(g, e)
    assert (eb["peso_proprio"] == 0).all()
    assert (eb["taxa_eb"] == eb["taxa_eb"].iloc[0]).all()


def test_mais_dispersao_por_ocorrencia_encolhe_mais():
    """κ alto (notas feitas de poucos eventos graves) = menos confiança no bairro."""
    g, e = _bairros_eb()
    baixo = rs.suavizar_bayesiano_empirico(g, e, kappa=0.1)["peso_proprio"]
    alto = rs.suavizar_bayesiano_empirico(g, e, kappa=0.9)["peso_proprio"]
    assert (alto <= baixo + 1e-12).all() and (alto < baixo).any()


def test_kappa_e_um_quando_todas_as_ocorrencias_pesam_um():
    import pandas as pd

    from curitiba_run.features import gravidade

    tipos_peso_um = [t for t, p in gravidade.pesos().items() if p == 1]
    tabela = pd.DataFrame({f"n_{t}": [5, 3] for t in tipos_peso_um})
    assert rs.fator_de_dispersao(tabela) == pytest.approx(1.0)


def test_kappa_menor_que_um_com_tipos_leves():
    import pandas as pd

    tabela = pd.DataFrame({"n_roubo": [10], "n_ameaca": [100]})
    assert 0 < rs.fator_de_dispersao(tabela) < 1
