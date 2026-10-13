"""Censo 2022 do IBGE: população por bairro e, mais adiante, por setor.

A população por bairro é o denominador da taxa de ocorrências da Fase 2. Vem do
arquivo "básico" dos Agregados por Bairros, publicado pelo IBGE em:
https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/

Baixe o `Agregados_por_bairros_basico_BR_*.zip` e salve em `data/raw/ibge/`.
O arquivo cobre o Brasil inteiro; o filtro por município acontece aqui.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pandas as pd

from curitiba_run.config import BAIRROS_CURITIBA, IBGE_MUNICIPIO, RAW
from curitiba_run.processing.bairros import normalizar_bairro

log = logging.getLogger(__name__)

DESTINO = RAW / "ibge"
PADRAO_BAIRROS = "Agregados_por_bairros_basico*"

# V0001 = "Total de pessoas", segundo a documentação dos Agregados do Censo 2022.
COLUNA_POPULACAO = "V0001"


def localizar_agregado_bairros(pasta: Path = DESTINO) -> Path:
    candidatos = sorted(p for p in pasta.glob(PADRAO_BAIRROS) if p.suffix in {".zip", ".csv"})
    if not candidatos:
        raise FileNotFoundError(
            f"Nenhum '{PADRAO_BAIRROS}.zip' em {pasta}. Baixe o arquivo básico dos "
            "Agregados por Bairros do Censo 2022 no FTP do IBGE (ver o topo de "
            "ingestion/ibge.py) e salve nessa pasta."
        )
    return candidatos[-1]


def _ler_csv(conteudo: bytes) -> pd.DataFrame:
    """O IBGE não documenta separador nem codificação; detecta os dois."""
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            texto = conteudo.decode(codificacao)
        except UnicodeDecodeError:
            continue
        separador = ";" if texto.split("\n", 1)[0].count(";") > texto.split("\n", 1)[0].count(",") else ","
        return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str)
    raise ValueError("Não foi possível decodificar o arquivo do IBGE.")


def ler_agregado(caminho: Path) -> pd.DataFrame:
    if caminho.suffix == ".zip":
        with zipfile.ZipFile(caminho) as z:
            csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not csvs:
                raise ValueError(f"O zip {caminho.name} não tem nenhum .csv dentro.")
            conteudo = z.read(csvs[0])
    else:
        conteudo = caminho.read_bytes()
    df = _ler_csv(conteudo)
    df.columns = [c.strip().upper() for c in df.columns]
    return df


def populacao_por_bairro(
    caminho: Path | None = None,
    municipio: str = IBGE_MUNICIPIO,
) -> pd.DataFrame:
    """População residente de cada um dos 75 bairros, pelo Censo 2022.

    Falha alto se algum bairro oficial não aparecer, ou se algum bairro do IBGE
    não casar com a lista oficial — os dois casos produziriam taxa errada sem
    nenhum aviso, como quase aconteceu com a CIC na base da Guarda.
    """
    caminho = caminho or localizar_agregado_bairros()
    df = ler_agregado(caminho)

    faltando = {"CD_MUN", "NM_BAIRRO", COLUNA_POPULACAO} - set(df.columns)
    if faltando:
        raise ValueError(
            f"O arquivo do IBGE não tem as colunas {sorted(faltando)}. "
            f"Colunas encontradas: {list(df.columns)[:15]}…"
        )

    cidade = df[df["CD_MUN"].str.strip() == municipio].copy()
    if cidade.empty:
        raise ValueError(f"Nenhum bairro do município {municipio} no arquivo {caminho.name}.")

    cidade["bairro"] = normalizar_bairro(cidade["NM_BAIRRO"])
    sem_casar = sorted(cidade.loc[cidade["bairro"].isna(), "NM_BAIRRO"].unique())
    if sem_casar:
        raise ValueError(
            f"Bairros do IBGE que não casam com a lista oficial: {sem_casar}. "
            "Acrescente a grafia em BAIRRO_ALIASES (config.py)."
        )

    cidade["populacao"] = pd.to_numeric(cidade[COLUNA_POPULACAO].str.strip(), errors="coerce")
    sem_valor = sorted(cidade.loc[cidade["populacao"].isna(), "bairro"])
    if sem_valor:
        raise ValueError(f"População ausente ou sigilosa para: {sem_valor}.")

    resultado = cidade.groupby("bairro", as_index=False)["populacao"].sum()

    ausentes = sorted(set(BAIRROS_CURITIBA) - set(resultado["bairro"]))
    if ausentes:
        raise ValueError(f"Bairros oficiais sem população no arquivo do IBGE: {ausentes}.")

    resultado["populacao"] = resultado["populacao"].astype(int)
    log.info(
        "População de %d bairros, total de %s habitantes (%s)",
        len(resultado), f"{resultado['populacao'].sum():,}".replace(",", "."), caminho.name,
    )
    return resultado


def baixar_setores(municipio: str = IBGE_MUNICIPIO):
    """Setores censitários com renda — insumo da Fase 3."""
    raise NotImplementedError


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(populacao_por_bairro().to_string(index=False))


if __name__ == "__main__":
    main()
