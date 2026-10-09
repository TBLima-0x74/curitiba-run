"""Testes do pipeline da Guarda Municipal, com uma base sintética no esquema real."""

import pandas as pd
import pytest

from curitiba_run.config import BAIRROS_CURITIBA
from curitiba_run.features import gravidade
from curitiba_run.ingestion import sigesguarda as sg


def base_sintetica() -> pd.DataFrame:
    linhas = [
        # bairro, natureza, subcategoria, data, equipamento
        ("Centro", "Roubo", "Transeunte", "10/03/2024", "f"),
        ("CENTRO", "Furto", "Transeunte", "11/03/2024", "t"),
        ("centro", "Furto", "Equipamento/patrimônio público", "12/03/2024", "t"),
        ("CIDADE INDUSTRIAL", "Estupro", None, "01/06/2025", "f"),
        ("Batel", "Importunação\xa0sexual", None, "02/02/2024", "f"),
        ("Batel", "Agressão física/verbal", "Violência doméstica contra mulher", "02/02/2024", "f"),
        ("Batel", "Disparo de arma", "Disparo de arma por GM com munição letal", "03/02/2024", "f"),
        ("Batel", "Trânsito", None, "03/02/2024", "f"),
        ("Campo Pequeno", "Roubo", "Transeunte", "05/05/2024", "f"),
        ("Centro", "Roubo", "Transeunte", "30/12/2022", "f"),
    ]
    df = pd.DataFrame(
        linhas,
        columns=[
            "ATENDIMENTO_BAIRRO_NOME", "NATUREZA1_DESCRICAO", "SUBCATEGORIA1_DESCRICAO",
            "OCORRENCIA_DATA", "FLAG_EQUIPAMENTO_URBANO",
        ],
    )
    df["LOGRADOURO_NOME"] = "Rua Sem Número"
    return df


@pytest.fixture
def classificada():
    df = sg.padronizar_esquema(base_sintetica())
    df = df[df["data"] >= pd.Timestamp("2023-01-01")]
    return sg.classificar_natureza(df)


def test_espaco_nao_separavel_nao_faz_a_ocorrencia_sumir(classificada):
    """A base real escreve "Importunação\\xa0sexual"; sem limpeza, 339 casos somem."""
    assert "importunacao_sexual" in set(classificada["tipo"].dropna())


def test_cidade_industrial_vira_o_bairro_oficial(classificada):
    """Sem o alias, 99,7% dos registros da CIC sumiam e ela parecia segura."""
    assert "Cidade Industrial de Curitiba" in set(classificada["bairro"].dropna())


def test_grafias_do_mesmo_bairro_se_unem(classificada):
    assert (classificada["bairro"] == "Centro").sum() == 3


def test_bairro_de_outro_municipio_fica_ausente(classificada):
    assert classificada.loc[classificada["bairro_original"] == "Campo Pequeno", "bairro"].isna().all()


def test_so_entra_o_que_atinge_pessoa_na_rua(classificada):
    def tipo(subcategoria):
        return classificada.loc[classificada["subcategoria"] == subcategoria, "tipo"]

    assert tipo("Equipamento/patrimônio público").isna().all()
    assert tipo("Violência doméstica contra mulher").isna().all()
    assert tipo("Disparo de arma por GM com munição letal").isna().all()
    assert tipo("Transeunte").notna().all()


def test_transito_nao_entra(classificada):
    assert classificada.loc[classificada["natureza"] == "Trânsito", "tipo"].isna().all()


def test_agregado_tem_os_75_bairros_inclusive_sem_ocorrencia(classificada):
    t = sg.agregar_por_bairro(classificada)
    assert len(t) == len(BAIRROS_CURITIBA) == 75
    assert t.loc[t["bairro"] == "Abranches", "n_ocorrencias"].item() == 0


def test_gravidade_e_a_soma_dos_pesos(classificada):
    t = sg.agregar_por_bairro(classificada).set_index("bairro")
    p = gravidade.pesos()
    assert t.loc["Centro", "gravidade"] == pytest.approx(p["roubo"] + p["furto"])
    assert t.loc["Centro", "n_roubo"] == 1 and t.loc["Centro", "n_furto"] == 1


def test_2022_fica_fora(classificada):
    """2022 só tem novembro e dezembro: incompleto, sai do período."""
    assert classificada["data"].min() >= pd.Timestamp("2023-01-01")


def test_esquema_alterado_falha_com_o_nome_da_coluna():
    with pytest.raises(ValueError, match="NATUREZA1_DESCRICAO"):
        sg.padronizar_esquema(base_sintetica().drop(columns=["NATUREZA1_DESCRICAO"]))


def test_todo_tipo_classificado_tem_peso():
    """Um tipo no mapa sem pena na tabela viraria NaN na gravidade, em silêncio."""
    destinos = set()
    for alvo in sg.CLASSIFICACAO.values():
        destinos |= {alvo} if isinstance(alvo, str) else set(alvo.values())
    assert destinos <= set(gravidade.TIPOS)


def test_lista_oficial_tem_75_bairros_sem_repeticao():
    assert len(BAIRROS_CURITIBA) == len({sg.chave(b) for b in BAIRROS_CURITIBA}) == 75
