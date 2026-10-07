"""Testes das métricas de equidade."""

import numpy as np
import pandas as pd
import pytest

from curitiba_run.analysis import equity


def test_gini_zero_para_distribuicao_igualitaria():
    valor = pd.Series([5.0] * 10)
    populacao = pd.Series([100.0] * 10)
    assert equity.gini(valor, populacao) == pytest.approx(0.0, abs=1e-9)


def test_gini_alto_para_concentracao_extrema():
    valor = pd.Series([0.0] * 99 + [100.0])
    populacao = pd.Series([1.0] * 100)
    assert equity.gini(valor, populacao) > 0.9


def test_curva_de_lorenz_comeca_na_origem_e_termina_em_um():
    x, y = equity.curva_de_lorenz(pd.Series([1.0, 2.0, 3.0]), pd.Series([1.0, 1.0, 1.0]))
    assert x[0] == pytest.approx(0.0)
    assert y[0] == pytest.approx(0.0)
    assert x[-1] == pytest.approx(1.0)
    assert y[-1] == pytest.approx(1.0)


def test_indice_de_concentracao_positivo_quando_beneficio_segue_a_renda():
    n = 100
    renda = pd.Series(np.arange(n, dtype=float))
    valor = renda.copy()  # acesso cresce com a renda
    populacao = pd.Series(np.ones(n))
    assert equity.indice_de_concentracao(valor, populacao, renda) > 0


def test_indice_de_concentracao_negativo_quando_beneficio_inverte_a_renda():
    n = 100
    renda = pd.Series(np.arange(n, dtype=float))
    valor = renda.iloc[::-1].reset_index(drop=True)
    populacao = pd.Series(np.ones(n))
    assert equity.indice_de_concentracao(valor, populacao, renda) < 0


def test_indice_de_concentracao_nulo_quando_beneficio_e_uniforme():
    n = 50
    renda = pd.Series(np.arange(n, dtype=float))
    valor = pd.Series(np.full(n, 3.0))
    populacao = pd.Series(np.ones(n))
    assert equity.indice_de_concentracao(valor, populacao, renda) == pytest.approx(0.0, abs=1e-9)


def test_testar_h5_detecta_composicao_dos_gradientes():
    """Acesso seguro deve concentrar mais que infraestrutura isolada."""
    n = 200
    rng = np.random.default_rng(1)
    renda = pd.Series(np.linspace(0, 1, n))
    iac = renda * 0.5 + 0.25                      # gradiente moderado
    risco = 1 - renda                             # risco cai com a renda
    acesso_seguro = iac * (1 - risco)             # os dois gradientes se compõem

    tabela = pd.DataFrame(
        {
            "iac": iac,
            "acesso_seguro": acesso_seguro,
            "populacao": rng.integers(50, 500, n).astype(float),
            "renda_per_capita": renda,
        }
    )
    resultado = equity.testar_h5(tabela)
    assert resultado.loc["diferença", "indice_concentracao"] > 0


def test_por_decil_cobre_toda_a_populacao():
    n = 100
    tabela = pd.DataFrame(
        {
            "acesso": np.linspace(0, 1, n),
            "populacao": np.ones(n) * 10,
            "renda_per_capita": np.linspace(500, 5000, n),
        }
    )
    resumo = equity.por_decil(tabela, "acesso")
    assert resumo["populacao"].sum() == pytest.approx(1000.0)
    assert len(resumo) == 10
