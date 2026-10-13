"""Testes da leitura da população por bairro do Censo 2022, com arquivo sintético."""

import zipfile

import pandas as pd
import pytest

from curitiba_run.config import BAIRROS_CURITIBA
from curitiba_run.ingestion import ibge


def agregado(tmp_path, linhas=None, codificacao="latin-1", nome="Agregados_por_bairros_basico_BR_X.zip"):
    """Zip com um CSV no formato do IBGE: ';' e acentos em latin-1."""
    if linhas is None:
        linhas = [
            ("4106902", "CIDADE INDUSTRIAL" if b == "Cidade Industrial de Curitiba" else b, "1000")
            for b in BAIRROS_CURITIBA
        ]
        linhas.append(("4119152", "Centro", "999999"))  # outro município, mesmo nome
    corpo = "CD_UF;CD_MUN;NM_MUN;CD_BAIRRO;NM_BAIRRO;V0001\n" + "\n".join(
        f"41;{m};X;{i};{b};{v}" for i, (m, b, v) in enumerate(linhas)
    )
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("Agregados_por_bairros_basico_BR.csv", corpo.encode(codificacao))
    return caminho


def test_le_os_75_bairros_de_curitiba_e_ignora_outro_municipio(tmp_path):
    pop = ibge.populacao_por_bairro(agregado(tmp_path))
    assert len(pop) == 75
    assert pop["populacao"].sum() == 75_000


def test_grafia_do_ibge_casa_com_o_nome_oficial(tmp_path):
    pop = ibge.populacao_por_bairro(agregado(tmp_path)).set_index("bairro")
    assert pop.loc["Cidade Industrial de Curitiba", "populacao"] == 1000


def test_acentos_em_utf8_tambem_funcionam(tmp_path):
    pop = ibge.populacao_por_bairro(agregado(tmp_path, codificacao="utf-8"))
    assert "Água Verde" in set(pop["bairro"])


def test_bairro_oficial_ausente_falha_com_o_nome(tmp_path):
    linhas = [("4106902", b, "1000") for b in BAIRROS_CURITIBA if b != "Riviera"]
    with pytest.raises(ValueError, match="Riviera"):
        ibge.populacao_por_bairro(agregado(tmp_path, linhas))


def test_nome_que_nao_casa_falha_em_vez_de_sumir(tmp_path):
    linhas = [("4106902", b, "1000") for b in BAIRROS_CURITIBA] + [("4106902", "Vila Inventada", "50")]
    with pytest.raises(ValueError, match="Vila Inventada"):
        ibge.populacao_por_bairro(agregado(tmp_path, linhas))


def test_populacao_sigilosa_falha(tmp_path):
    linhas = [("4106902", b, "X" if b == "Caximba" else "1000") for b in BAIRROS_CURITIBA]
    with pytest.raises(ValueError, match="Caximba"):
        ibge.populacao_por_bairro(agregado(tmp_path, linhas))


def test_sem_arquivo_explica_onde_baixar(tmp_path):
    with pytest.raises(FileNotFoundError, match="Agregados"):
        ibge.localizar_agregado_bairros(tmp_path)


def test_coluna_ausente_lista_o_que_falta(tmp_path):
    caminho = tmp_path / "Agregados_por_bairros_basico_BR_Y.csv"
    pd.DataFrame({"CD_MUN": ["4106902"], "NM_BAIRRO": ["Centro"]}).to_csv(caminho, sep=";", index=False)
    with pytest.raises(ValueError, match="V0001"):
        ibge.populacao_por_bairro(caminho)


def test_grafia_botiatuvinha_do_ibge_casa_com_butiatuvinha(tmp_path):
    """O Censo 2022 escreve "Botiatuvinha"; a lista oficial, "Butiatuvinha".

    Foi o que a verificação de nomes pegou na primeira execução com o arquivo
    real: sem o alias, o bairro ficaria sem população e a leitura falharia.
    """
    linhas = [
        ("4106902", "Botiatuvinha" if b == "Butiatuvinha" else b, "1000") for b in BAIRROS_CURITIBA
    ]
    pop = ibge.populacao_por_bairro(agregado(tmp_path, linhas)).set_index("bairro")
    assert pop.loc["Butiatuvinha", "populacao"] == 1000
