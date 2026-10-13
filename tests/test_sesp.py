"""Testes da ingestão da SESP-PR, com arquivos sintéticos em formatos plausíveis.

O esquema real só será conhecido quando a resposta ao pedido via LAI chegar;
estes testes fixam o que o código promete fazer com qualquer formato razoável.
"""

import pandas as pd
import pytest

from curitiba_run.config import BAIRROS_CURITIBA
from curitiba_run.features import risk_surface as rs
from curitiba_run.ingestion import sesp


def arquivo_mensal(tmp_path, linhas, codificacao="latin-1"):
    corpo = "Município;Bairro;Natureza;Ano;Mês;Tipo de Local\n" + "\n".join(";".join(linha) for linha in linhas)
    caminho = tmp_path / "sesp_resposta.csv"
    caminho.write_bytes(corpo.encode(codificacao))
    return caminho


LINHAS = [
    ("CURITIBA", "Centro", "ROUBO A TRANSEUNTE", "2024", "3", "Via pública"),
    ("CURITIBA", "Centro", "ROUBO", "2024", "4", "Via pública"),
    ("CURITIBA", "Centro", "ROUBO", "2024", "5", "Residência"),
    ("CURITIBA", "Batel", "TENTATIVA DE HOMICÍDIO", "2025", "1", "Via pública"),
    ("CURITIBA", "Batel", "HOMICÍDIO DOLOSO", "2025", "2", "Via pública"),
    ("CURITIBA", "Batel", "LESÃO CORPORAL - VIOLÊNCIA DOMÉSTICA", "2025", "2", "Residência"),
    ("CURITIBA", "Batel", "ESTELIONATO", "2025", "2", "Comércio"),
    ("CURITIBA", "CIDADE INDUSTRIAL", "ESTUPRO", "2025", "6", "Via pública"),
    ("CURITIBA", "Centro", "FURTO A TRANSEUNTE", "2022", "12", "Via pública"),
    ("SÃO JOSÉ DOS PINHAIS", "Centro", "ROUBO A TRANSEUNTE", "2024", "3", "Via pública"),
]


@pytest.fixture
def com_adr(tmp_path, monkeypatch):
    pasta = tmp_path / "adr"
    pasta.mkdir()
    (pasta / "0006-base-legal-sesp.md").write_text("# ADR 0006", encoding="utf-8")
    monkeypatch.setattr(sesp, "PASTA_ADR", pasta)
    return pasta


def test_sem_adr_de_base_legal_nada_entra(tmp_path):
    with pytest.raises(PermissionError, match="0006"):
        sesp.verificar_base_legal(tmp_path)


def test_reconhece_colunas_com_acento_e_data_mensal(tmp_path):
    df, mensal = sesp.padronizar_esquema(sesp.carregar(arquivo_mensal(tmp_path, LINHAS)))
    assert mensal
    assert df["data"].min() == pd.Timestamp("2022-12-01")


def test_filtra_curitiba(tmp_path):
    df, _ = sesp.padronizar_esquema(sesp.carregar(arquivo_mensal(tmp_path, LINHAS)))
    assert len(df) == len(LINHAS) - 1


def test_classificacao_segue_as_regras_da_guarda(tmp_path):
    df, _ = sesp.padronizar_esquema(sesp.carregar(arquivo_mensal(tmp_path, LINHAS)))
    tipos = [None if pd.isna(t) else t for t in sesp.classificar_natureza(df)["tipo"]]
    assert tipos[:8] == [
        "roubo",                # a transeunte
        "roubo",                # genérico, mas em via pública
        None,                   # genérico em residência
        "tentativa_homicidio",  # antes de homicídio
        "homicidio",
        None,                   # violência doméstica sai
        None,                   # estelionato não interessa
        "estupro",
    ]


def test_colunas_irreconheciveis_listam_o_que_veio(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text("Coluna A;Coluna B\n1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Coluna A"):
        sesp.padronizar_esquema(sesp.carregar(caminho))


def test_pipeline_completo(tmp_path, com_adr):
    tabela, relatorio = sesp.pipeline(arquivo_mensal(tmp_path, LINHAS))
    assert len(tabela) == len(BAIRROS_CURITIBA)
    t = tabela.set_index("bairro")
    assert t.loc["Centro", "n_roubo"] == 2
    assert t.loc["Cidade Industrial de Curitiba", "n_estupro"] == 1
    assert t["pct_em_equipamento_urbano"].isna().all()  # coluna que só a Guarda tem
    assert "ESTELIONATO" in relatorio["naturezas_nao_classificadas"]
    assert relatorio["periodo"].endswith("2025-06-30 (mensal)")


def test_comparacao_entre_fontes():
    bairros = [f"B{i:02d}" for i in range(20)]
    gm = pd.DataFrame({
        "bairro": bairros,
        "taxa_gravidade_eb": [float(i) for i in range(20)],
        "classe_risco": ["baixo"] * 10 + ["alto"] * 10,
        "n_ocorrencias": [10] * 20,
        "pct_em_equipamento_urbano": [5.0] * 20,
    })
    sesp_ = gm.drop(columns="pct_em_equipamento_urbano").copy()
    sesp_.loc[0, "classe_risco"] = "alto"
    tabela, resumo = rs.comparar_fontes(gm, sesp_)
    assert resumo["rho_taxas"] == pytest.approx(1.0)
    assert resumo["classes_concordam_pct"] == pytest.approx(95.0)
    assert resumo["gm_baixo_sesp_alto"] == ["B00"]


def test_comparacao_independe_do_volume_total_de_cada_fonte():
    """A SESP registrar 10× mais no total não pode pintar a cidade toda de azul."""
    bairros = [f"B{i:02d}" for i in range(20)]
    gm = pd.DataFrame({
        "bairro": bairros,
        "taxa_gravidade_eb": [1.0 + i for i in range(20)],
        "classe_risco": ["baixo"] * 10 + ["alto"] * 10,
        "n_ocorrencias": [10] * 20,
        "pct_em_equipamento_urbano": [5.0] * 20,
    })
    sesp_ = gm.drop(columns="pct_em_equipamento_urbano").assign(taxa_gravidade_eb=lambda d: 10 * d["taxa_gravidade_eb"])
    tabela, _ = rs.comparar_fontes(gm, sesp_)
    assert tabela["log_razao_gm_sesp"].abs().max() < 0.02
