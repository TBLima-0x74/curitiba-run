"""Supressão de baixa contagem antes de publicar (ADR 0007)."""

import numpy as np
import pandas as pd
import pytest

from curitiba_run.ingestion import sesp
from curitiba_run.processing import supressao


def _taxa(contagens: dict[str, int]) -> pd.DataFrame:
    n = pd.Series(contagens)
    return pd.DataFrame({
        "bairro": n.index,
        "populacao": 10_000,
        "n_ocorrencias": n.to_numpy(),
        "gravidade": n.to_numpy() * 0.5,
        "taxa_gravidade": n.to_numpy() * 1.3,
        "taxa_gravidade_eb": n.to_numpy() * 1.2,
        "taxa_gravidade_norm": np.linspace(0, 1, len(n)),
        "classe_risco": ["alto" if v >= 20 else "baixo" for v in n],
        "n_estupro": [1] * len(n),
        "n_furto": n.to_numpy() - 1,
        "populacao_pequena": False,
    })


def test_suprime_abaixo_de_cinco_e_publica_cinco():
    pub = supressao.suprimir_bairros(_taxa({"A": 0, "B": 3, "C": 4, "D": 5, "E": 40, "F": 60}))
    assert pub.set_index("bairro")["suprimido"].to_dict() == {
        "A": True, "B": True, "C": True, "D": False, "E": False, "F": False,
    }


def test_bairro_suprimido_perde_contagem_taxas_nota_e_classe():
    pub = supressao.suprimir_bairros(_taxa({"A": 0, "B": 3, "C": 4, "D": 30, "E": 40})).set_index("bairro")
    for coluna in supressao.VALORES:
        assert pub.loc[["A", "B", "C"], coluna].isna().all(), coluna
        assert pub.loc[["D", "E"], coluna].notna().all(), coluna
    assert pub.loc["B", "populacao"] == 10_000  # do Censo, já é pública


def test_nenhuma_contagem_por_tipo_sai_por_bairro():
    pub = supressao.suprimir_bairros(_taxa({"A": 10, "B": 30}))
    assert not [c for c in pub.columns if c.startswith("n_") and c != "n_ocorrencias"]
    assert "gravidade" not in pub.columns


def test_complemento_quando_um_unico_suprimido_seria_deduzido_por_diferenca():
    # Só B abaixo do limiar: total da cidade − publicados = 3, exatamente o de B.
    sup = supressao.mascara(pd.Series({"A": 50, "B": 3, "C": 7, "D": 9}))
    assert sup["B"]
    assert sup["C"]  # o menor publicado entra no complemento
    assert not sup["A"]
    assert not sup["D"]


def test_complemento_quando_a_soma_prova_ocorrencia_em_todos():
    # Dois suprimidos somando 8: cada um tem entre 0 e 4, logo os dois têm 4.
    sup = supressao.mascara(pd.Series({"A": 4, "B": 4, "C": 6, "D": 100}))
    assert sup[["A", "B", "C"]].all()
    assert not sup["D"]


def test_sem_complemento_quando_a_soma_nao_revela_ninguem():
    # Como nos dados reais: 0, 0, 3, 4, 4 — soma 11 entre 5 bairros, cada um pode ser 0.
    n = pd.Series({"A": 0, "B": 0, "C": 3, "D": 4, "E": 4, "F": 6, "G": 90})
    sup = supressao.mascara(n)
    assert sup.sum() == 5
    assert not sup["F"]


def test_bairro_zerado_sozinho_nao_exige_complemento():
    sup = supressao.mascara(pd.Series({"A": 0, "B": 6, "C": 90}))
    assert sup.tolist() == [True, False, False]


def test_celula_herda_o_bairro_ja_suprimido():
    bairros = supressao.suprimir_bairros(_taxa({"A": 2, "B": 30, "C": 40}))
    celulas = pd.DataFrame({
        "h3": ["x", "y", "z"], "bairro": ["A", "B", "C"], "fracao_bairro": 1.0,
        "bairro_por_proximidade": False, "celula_dividida": False,
        "taxa_gravidade_norm": [0.9, 0.5, 0.1],  # valor original, não pode passar
    })
    pub = supressao.suprimir_celulas(celulas, bairros).set_index("h3")
    assert np.isnan(pub.loc["x", "taxa_gravidade_norm"])
    assert pub.loc["x", "suprimido"]
    supressao.verificar(pub.reset_index(), "celulas")


def test_tipo_na_cidade_com_o_mesmo_limiar():
    ocorrencias = pd.DataFrame({"bairro": ["A", "B"], "n_homicidio": [1, 2], "n_furto": [300, 400],
                                "n_roubo": [50, 60], "n_estupro": [10, 9]})
    t = supressao.por_tipo_cidade(ocorrencias).set_index("tipo")
    assert t.loc["homicidio", "suprimido"]
    assert pd.isna(t.loc["homicidio", "n"])
    assert t.loc["furto", "n"] == 700
    assert t.loc["roubo", "peso"] == 1.0
    supressao.verificar(t.reset_index(), "por_tipo")


def test_comparacao_suprime_bairro_baixo_em_qualquer_fonte():
    # D é o complemento nas duas fontes, porque A e B estão sozinhos abaixo do limiar.
    gm = supressao.suprimir_bairros(_taxa({"A": 2, "B": 30, "C": 40, "D": 6}))
    sp = supressao.suprimir_bairros(_taxa({"A": 50, "B": 3, "C": 40, "D": 7}))
    comp = pd.DataFrame({"bairro": ["A", "B", "C", "D"], "taxa_gravidade_eb_gm": [1.0, 2, 3, 4],
                         "taxa_gravidade_eb_sesp": [1.0, 2, 3, 4],
                         "classes_concordam": [True, False, True, True],
                         "log_razao_gm_sesp": [0.1, -0.2, 0.0, 0.3], "n_ocorrencias_gm": [2, 30, 40, 6],
                         "n_ocorrencias_sesp": [50, 3, 40, 7]})
    pub = supressao.suprimir_comparacao(comp, gm, sp).set_index("bairro")
    assert pub.loc[["A", "B", "D"], "suprimido"].all()
    assert pub.loc[["A", "B"], "log_razao_gm_sesp"].isna().all()
    assert pub.loc["C", "log_razao_gm_sesp"] == 0.0
    supressao.verificar(pub.reset_index(), "comparacao")


@pytest.mark.parametrize(
    ("df", "mensagem"),
    [
        (pd.DataFrame({"bairro": ["A"], "n_estupro": [7]}), "por tipo"),
        (pd.DataFrame({"bairro": ["A"], "n_ocorrencias": [3]}), "abaixo de 5"),
        (pd.DataFrame({"bairro": ["A"], "n_ocorrencias": [np.nan], "taxa_gravidade_eb": [12.0],
                       "suprimido": [True]}), "suprimida com valor"),
    ],
)
def test_verificar_barra_o_que_escapou(df, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        supressao.verificar(df, "teste")


def test_tabela_dos_dados_reais_passa_na_verificacao():
    pub = supressao.suprimir_bairros(_taxa({"A": 0, "B": 3, "C": 4, "D": 6, "E": 90}))
    supressao.verificar(pub, "bairros")


def test_publicacao_da_sesp_exige_autorizacao_explicita_no_adr(tmp_path):
    assert not sesp.publicacao_permitida(tmp_path)  # sem ADR
    adr = tmp_path / "0006-base-legal-sesp.md"
    adr.write_text("# ADR 0006\n\nUso interno autorizado.\n", encoding="utf-8")
    assert not sesp.publicacao_permitida(tmp_path)
    adr.write_text("# ADR 0006\n\n**Publicação de agregados:** permitida\n", encoding="utf-8")
    assert sesp.publicacao_permitida(tmp_path)
