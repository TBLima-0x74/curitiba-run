"""Testes da composição do Índice de Adequação à Corrida."""

import numpy as np
import pandas as pd
import pytest

from curitiba_run.config import IAC_DIMENSOES, IAC_PESOS_BASE
from curitiba_run.features import suitability_index as si


def dimensoes_sinteticas(n: int = 50, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({dim: rng.random(n) for dim in IAC_DIMENSOES})


def test_normalizar_produz_intervalo_unitario():
    serie = pd.Series([0, 1, 2, 3, 4, 5, 100])
    resultado = si.normalizar(serie)
    assert resultado.min() >= 0
    assert resultado.max() <= 1


def test_normalizar_inverte_quando_pedido():
    serie = pd.Series(range(10))
    normal = si.normalizar(serie)
    invertida = si.normalizar(serie, inverter=True)
    assert normal.idxmax() == invertida.idxmin()


def test_normalizar_serie_constante_nao_divide_por_zero():
    resultado = si.normalizar(pd.Series([7.0] * 5))
    assert resultado.notna().all()
    assert (resultado == 0.5).all()


def test_normalizar_avisa_quando_a_serie_e_constante(caplog):
    """O ramo degenerado precisa gritar: foi ele que escondeu a iluminação morta."""
    serie = pd.Series([0.0] * 100, name="densidade_postes")
    with caplog.at_level("WARNING"):
        si.normalizar(serie)
    mensagens = [r.getMessage() for r in caplog.records]
    assert any("constante" in m for m in mensagens)
    assert any("densidade_postes" in m for m in mensagens)


def test_normalizar_nao_avisa_quando_ha_variacao(caplog):
    with caplog.at_level("WARNING"):
        si.normalizar(pd.Series(np.linspace(0, 1, 100)))
    assert not caplog.records


def test_normalizar_dimensoes_inverte_so_as_marcadas():
    """Declividade alta é ruim; densidade alta é boa. A regra mora num lugar só."""
    brutas = pd.DataFrame({
        "declividade": np.linspace(0, 20, 50),
        "espaco_dedicado": np.linspace(0, 1, 50),
    })
    norm = si.normalizar_dimensoes(brutas)
    assert norm["declividade"].iloc[0] > norm["declividade"].iloc[-1]
    assert norm["espaco_dedicado"].iloc[0] < norm["espaco_dedicado"].iloc[-1]


def test_validar_pesos_rejeita_soma_diferente_de_um():
    pesos = dict.fromkeys(IAC_DIMENSOES, 0.1)
    with pytest.raises(ValueError, match="somar 1"):
        si.validar_pesos(pesos)


def test_validar_pesos_rejeita_dimensao_desconhecida():
    pesos = {**IAC_PESOS_BASE, "dimensao_inventada": 0.0}
    with pytest.raises(ValueError, match="Sobrando"):
        si.validar_pesos(pesos)


def test_compor_com_dimensoes_maximas_resulta_em_um():
    dims = pd.DataFrame({dim: [1.0] for dim in IAC_DIMENSOES})
    assert si.compor(dims).iloc[0] == pytest.approx(1.0)


def test_compor_propaga_ausencia():
    dims = dimensoes_sinteticas(3)
    dims.loc[0, IAC_DIMENSOES[0]] = np.nan
    assert pd.isna(si.compor(dims).iloc[0])


def test_compor_falha_com_dimensao_ausente():
    dims = dimensoes_sinteticas(5).drop(columns=[IAC_DIMENSOES[0]])
    with pytest.raises(ValueError, match="Dimensões ausentes"):
        si.compor(dims)


def test_cenarios_de_peso_geram_uma_coluna_por_cenario():
    cenarios = si.avaliar_cenarios_de_peso(dimensoes_sinteticas())
    assert "base" in cenarios.columns
    assert "iguais" in cenarios.columns
    assert len(cenarios) == 50


def test_estabilidade_do_ranking_tem_diagonal_unitaria():
    cenarios = si.avaliar_cenarios_de_peso(dimensoes_sinteticas())
    corr = si.estabilidade_do_ranking(cenarios)
    assert np.allclose(np.diag(corr.to_numpy()), 1.0)


# ------------------------------------------- classificação alto/baixo (ADR 0003)


def _iac_sintetico():
    import pandas as pd

    return pd.Series([0.1, 0.2, 0.3, 0.7, 0.8, 0.9], name="iac")


def test_classificacao_corta_na_mediana_por_padrao():
    classes = si.classificar_alto_baixo(_iac_sintetico())
    assert classes.tolist() == ["baixo", "baixo", "baixo", "alto", "alto", "alto"]


def test_classificacao_aceita_corte_explicito():
    """O limiar é parâmetro porque a sensibilidade a ele precisa ser testável."""
    classes = si.classificar_alto_baixo(_iac_sintetico(), corte=0.25)
    assert classes.tolist() == ["baixo", "baixo", "alto", "alto", "alto", "alto"]


def test_classificacao_preserva_ausencia():
    """Célula sem IAC não é `baixo` — ausência de medida não é medida de carência."""
    import numpy as np
    import pandas as pd

    iac = pd.Series([0.1, np.nan, 0.9])
    classes = si.classificar_alto_baixo(iac)
    assert classes.isna().tolist() == [False, True, False]


def test_classificacao_e_ordenada():
    """Categoria ordenada para que `> "baixo"` funcione em filtro e gráfico."""
    classes = si.classificar_alto_baixo(_iac_sintetico())
    assert classes.cat.ordered
    assert list(classes.cat.categories) == ["baixo", "alto"]


def _cenarios_sinteticos():
    import pandas as pd

    # A célula do meio alterna de lado conforme o cenário; as pontas não.
    return pd.DataFrame(
        {
            "base": [0.1, 0.4, 0.6, 0.9],
            "iguais": [0.1, 0.45, 0.55, 0.9],
            "percepcao": [0.1, 0.6, 0.4, 0.9],
        }
    )


def test_robustez_conta_em_quantos_cenarios_a_celula_e_alta():
    r = si.robustez_da_classificacao(_cenarios_sinteticos())
    assert r["n_alto"].tolist() == [0, 1, 2, 3]


def test_robustez_marca_as_pontas_como_estaveis_e_o_meio_como_nao():
    r = si.robustez_da_classificacao(_cenarios_sinteticos())
    assert r["estavel"].tolist() == [True, False, False, True]


def test_robustez_corta_por_cenario_e_nao_globalmente():
    """Deslocar um cenário inteiro não pode inventar instabilidade.

    Somar uma constante a um cenário não muda o ranking dele. Se o corte fosse
    a mediana global, a célula passaria a parecer que mudou de classe — e o
    número de robustez mediria escala em vez de ordenação.
    """
    cen = _cenarios_sinteticos()
    deslocado = cen.assign(percepcao=cen["percepcao"] + 10)

    assert (
        si.robustez_da_classificacao(deslocado)["n_alto"].tolist()
        == si.robustez_da_classificacao(cen)["n_alto"].tolist()
    )


def test_robustez_reporta_a_classe_do_cenario_base():
    r = si.robustez_da_classificacao(_cenarios_sinteticos())
    assert r["classe"].tolist() == ["baixo", "baixo", "alto", "alto"]


def test_robustez_preserva_ausencia():
    import numpy as np

    cen = _cenarios_sinteticos()
    cen.loc[1, "iguais"] = np.nan
    r = si.robustez_da_classificacao(cen)
    assert bool(r.loc[1, ["n_alto", "estavel"]].isna().all())


def test_resumo_da_robustez_soma_cem_por_cento():
    resumo = si.resumo_da_robustez(si.robustez_da_classificacao(_cenarios_sinteticos()))
    assert abs(resumo["%"].sum() - 100) < 1e-9
    assert resumo["células"].sum() == 4


def test_robustez_rejeita_quantil_fora_do_intervalo():
    with pytest.raises(ValueError, match="quantil"):
        si.robustez_da_classificacao(_cenarios_sinteticos(), quantil=1.5)


def test_robustez_com_quantil_diferente_muda_o_recorte():
    """O limiar é a decisão arbitrária que sobra; precisa ser testável."""
    cen = _cenarios_sinteticos()
    frouxo = si.robustez_da_classificacao(cen, quantil=0.25)
    apertado = si.robustez_da_classificacao(cen, quantil=0.75)
    assert frouxo["n_alto"].sum() > apertado["n_alto"].sum()


def test_negar_estavel_conta_as_instaveis():
    """`~estavel` precisa ser negação lógica, não bit a bit.

    Em coluna de objeto, `~True` vale −2: a soma das "instáveis" saía negativa.
    """
    import numpy as np

    cen = _cenarios_sinteticos()
    cen.loc[0, "iguais"] = np.nan
    r = si.robustez_da_classificacao(cen)
    assert str(r["estavel"].dtype) == "boolean"
    assert str(r["n_alto"].dtype) == "Int8"
    assert int((~r["estavel"]).sum()) == 2
    assert int(r["estavel"].sum()) == 1
