"""Testes da tipologia de quadrantes."""

import pandas as pd

from curitiba_run.features import typology


def test_classifica_os_quatro_quadrantes():
    iac = pd.Series([0.9, 0.9, 0.1, 0.1])
    risco = pd.Series([0.1, 0.9, 0.1, 0.9])
    resultado = typology.classificar(iac, risco, corte_iac=0.5, corte_risco=0.5)

    assert list(resultado) == [
        "privilegiado",
        "subutilizado",
        "latente",
        "duplamente_penalizado",
    ]


def test_corte_padrao_usa_mediana_e_nao_deixa_quadrante_vazio():
    iac = pd.Series([0.1, 0.2, 0.8, 0.9])
    risco = pd.Series([0.1, 0.9, 0.1, 0.9])
    resultado = typology.classificar(iac, risco)
    assert resultado.notna().all()
    assert resultado.nunique() == 4


def test_ausencia_propaga_para_o_rotulo():
    iac = pd.Series([0.9, None])
    risco = pd.Series([0.1, 0.1])
    resultado = typology.classificar(iac, risco, corte_iac=0.5, corte_risco=0.5)
    assert pd.isna(resultado.iloc[1])


def test_perfilar_soma_cem_por_cento_da_populacao():
    tabela = pd.DataFrame(
        {
            "h3": ["a", "b", "c", "d"],
            "populacao": [100, 200, 300, 400],
            "quadrante": ["latente", "latente", "privilegiado", "subutilizado"],
        }
    )
    perfil = typology.perfilar(tabela)
    assert perfil["pct_populacao"].sum() == 100.0
    assert perfil.loc["latente", "n_celulas"] == 2
