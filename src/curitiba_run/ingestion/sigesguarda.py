"""Ocorrências atendidas pela Guarda Municipal de Curitiba (SiGesGuarda).

Fonte: Portal de Dados Abertos de Curitiba, uso autorizado pelo ADR 0004.

**A base não tem coordenada.** Cada ocorrência traz o bairro e o nome da rua,
sem número — só 0,6% dos logradouros têm algum dígito. Por isso a unidade desta
fonte é o **bairro**, e não o hexágono H3.

**A base mede onde a Guarda atua, não onde há risco.** No recorte de interesse,
22,6% das ocorrências acontecem em equipamento municipal (estação-tubo,
terminal, unidade de saúde), contra 9% da base inteira: a Guarda protege
patrimônio público e registra onde está. Por isso as colunas de saída falam em
"ocorrências registradas pela GM", e `pct_em_equipamento_urbano` acompanha
cada bairro como indicador desse viés.

Ver docs/taxonomia_ocorrencias.md para as regras de inclusão e os pesos.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from curitiba_run.config import (
    BAIRRO_ALIASES,
    BAIRROS_CURITIBA,
    OCORRENCIAS_INICIO,
    PROCESSED,
    RAW,
)
from curitiba_run.features import gravidade

log = logging.getLogger(__name__)

DESTINO = RAW / "sigesguarda"
SAIDA = PROCESSED / "ocorrencias_gm_por_bairro.csv"

# Colunas da base original de que o pipeline depende. Se a Prefeitura renomear
# alguma, o pipeline para com a lista do que falta, em vez de produzir vazio.
COLUNAS = {
    "ATENDIMENTO_BAIRRO_NOME": "bairro_original",
    "NATUREZA1_DESCRICAO": "natureza",
    "SUBCATEGORIA1_DESCRICAO": "subcategoria",
    "OCORRENCIA_DATA": "data",
    "FLAG_EQUIPAMENTO_URBANO": "equipamento_urbano",
    "LOGRADOURO_NOME": "logradouro",
}

# Natureza → tipo do projeto. Um valor `str` vale para qualquer subcategoria;
# um `dict` restringe às subcategorias listadas e descarta as demais.
#
# Regras (ver docs/taxonomia_ocorrencias.md):
#   1. Só entra o que atinge uma pessoa, ou o que ela carrega, no espaço público.
#   2. Quando a subcategoria identifica o alvo, só a de pessoa na rua entra —
#      furto de patrimônio público, roubo a estabelecimento e violência
#      doméstica saem.
#   3. Disparo feito pela própria Guarda não é risco para quem corre e sai.
#   4. Tentativa de alvo indeterminado (tentativa de roubo ou de furto, que
#      podem ser contra comércio) sai, pela mesma coerência da regra 2.
#   5. Tipo ambíguo vira o tipo menos grave compatível (regra de `gravidade`).
CLASSIFICACAO: dict[str, str | dict[str, str]] = {
    "Roubo": {"Transeunte": "roubo"},
    "Furto": {"Transeunte": "furto"},
    "Agressão física/verbal": {"Agressão": "vias_de_fato"},
    "Ameaça": "ameaca",
    "Vias de Fato": "vias_de_fato",
    "Importunação sexual": "importunacao_sexual",
    "Importunação ofensiva ao pudor": "ato_obsceno",
    "Atos obscenos/libidinosos": "ato_obsceno",
    "Lesão Corporal": "lesao_corporal",
    "Disparo de arma": {
        "Disparo de arma por terceiro": "disparo_arma_fogo",
        "Disparo de Arma sem Vitima(s)": "disparo_arma_fogo",
        "Disparo de Arma Com Vitima(s)": "disparo_arma_fogo",
    },
    "Estupro": "estupro",
    "Homicídio": "homicidio",
    "Tentativa de homicídio": "tentativa_homicidio",
    "Tentativa": {
        "Tentativa de homicídio": "tentativa_homicidio",
        "Tentativa de sequestro": "tentativa_sequestro",
        "Tentativa de agressão": "tentativa_lesao_corporal",
    },
}


# ------------------------------------------------------------------ texto


def limpar_texto(valor) -> str | None:
    """Espaços normais, sem sobra nas pontas, e vazio vira ausente.

    A base usa espaço não separável (U+00A0) em "Importunação sexual". Sem isto,
    a comparação exata falha e as 339 ocorrências somem sem erro nenhum.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = re.sub(r"\s+", " ", str(valor).replace("\xa0", " ")).strip()
    return texto or None


def chave(valor) -> str | None:
    """Forma de comparação: sem acento, maiúscula, espaços normalizados."""
    texto = limpar_texto(valor)
    if texto is None:
        return None
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sem_acento.upper()


_OFICIAIS = {chave(b): b for b in BAIRROS_CURITIBA}
_ALIASES = {chave(k): v for k, v in BAIRRO_ALIASES.items()}
_CLASSIFICACAO = {
    chave(nat): (alvo if isinstance(alvo, str) else {chave(s): t for s, t in alvo.items()})
    for nat, alvo in CLASSIFICACAO.items()
}


def normalizar_bairro(serie: pd.Series) -> pd.Series:
    """Nome oficial do bairro, ou ausente se o nome não designa bairro de Curitiba."""
    chaves = serie.map(chave)
    return chaves.map(lambda k: _OFICIAIS.get(k) or _ALIASES.get(k))


# ------------------------------------------------------------------ etapas


def localizar_base(pasta: Path = DESTINO) -> Path:
    """O arquivo de base mais recente da pasta — o nome traz a data no início."""
    candidatos = sorted(pasta.glob("*Base_de_Dados*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            f"Nenhum '*Base_de_Dados*.csv' em {pasta}. Baixe a base da Guarda "
            "Municipal no Portal de Dados Abertos e salve nessa pasta."
        )
    return candidatos[-1]


def carregar(caminho: Path | None = None) -> pd.DataFrame:
    caminho = caminho or localizar_base()
    log.info("Lendo %s", caminho.name)
    return pd.read_csv(caminho, dtype=str, encoding="utf-8", low_memory=False)


def padronizar_esquema(bruto: pd.DataFrame) -> pd.DataFrame:
    """Seleciona, renomeia e limpa as colunas usadas. Falha alto se faltar alguma."""
    faltando = set(COLUNAS) - set(bruto.columns)
    if faltando:
        raise ValueError(
            f"A base mudou de esquema; faltam as colunas {sorted(faltando)}. "
            "Ajuste `COLUNAS` em ingestion/sigesguarda.py."
        )

    df = bruto[list(COLUNAS)].rename(columns=COLUNAS)
    for coluna in ("bairro_original", "natureza", "subcategoria", "logradouro"):
        df[coluna] = df[coluna].map(limpar_texto)

    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df["equipamento_urbano"] = df["equipamento_urbano"].map(chave).eq("T")
    df["bairro"] = normalizar_bairro(df["bairro_original"])
    return df


def classificar_natureza(df: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta `tipo`: o tipo do projeto, ou ausente quando a ocorrência não interessa."""

    def tipo(natureza, subcategoria):
        alvo = _CLASSIFICACAO.get(chave(natureza))
        if alvo is None or isinstance(alvo, str):
            return alvo
        return alvo.get(chave(subcategoria))

    df = df.copy()
    df["tipo"] = [tipo(n, s) for n, s in zip(df["natureza"], df["subcategoria"], strict=True)]
    return df


def agregar_por_bairro(
    df: pd.DataFrame,
    estrategia: str = "minima",
    limiar_baixa_contagem: int = 5,
) -> pd.DataFrame:
    """Uma linha por bairro oficial — os 75, inclusive os sem ocorrência.

    `gravidade` = Σ peso de cada ocorrência; `gravidade_anual` divide pelo
    período coberto, para ser comparável entre versões da base.
    """
    pesos = gravidade.pesos(estrategia)
    validas = df[df["tipo"].notna() & df["bairro"].notna()].copy()
    validas["peso"] = validas["tipo"].map(pesos)

    anos = (df["data"].max() - pd.Timestamp(OCORRENCIAS_INICIO)).days / 365.25

    por_tipo = (
        validas.pivot_table(index="bairro", columns="tipo", values="peso", aggfunc="size", fill_value=0)
        .reindex(columns=list(gravidade.TIPOS), fill_value=0)
        .add_prefix("n_")
    )
    resumo = validas.groupby("bairro").agg(
        n_ocorrencias=("tipo", "size"),
        gravidade=("peso", "sum"),
        pct_em_equipamento_urbano=("equipamento_urbano", "mean"),
    )

    tabela = (
        pd.DataFrame(index=pd.Index(sorted(BAIRROS_CURITIBA), name="bairro"))
        .join(resumo)
        .join(por_tipo)
    )
    contagens = ["n_ocorrencias", *por_tipo.columns]
    tabela[contagens] = tabela[contagens].fillna(0).astype(int)
    tabela["gravidade"] = tabela["gravidade"].fillna(0.0)
    tabela["pct_em_equipamento_urbano"] = 100 * tabela["pct_em_equipamento_urbano"]
    tabela["gravidade_anual"] = tabela["gravidade"] / anos
    tabela["baixa_contagem"] = tabela["n_ocorrencias"] < limiar_baixa_contagem

    ordem = [
        "n_ocorrencias", "gravidade", "gravidade_anual", "pct_em_equipamento_urbano",
        "baixa_contagem", *por_tipo.columns,
    ]
    return tabela[ordem].reset_index()


def pipeline(
    caminho: Path | None = None,
    estrategia: str = "minima",
) -> tuple[pd.DataFrame, dict]:
    """Base crua → tabela por bairro, mais um relatório do que entrou e saiu."""
    bruto = carregar(caminho)
    df = padronizar_esquema(bruto)
    df = df[df["data"] >= pd.Timestamp(OCORRENCIAS_INICIO)]
    df = classificar_natureza(df)

    interesse = df[df["tipo"].notna()]
    relatorio = {
        "registros_lidos": len(bruto),
        "no_periodo": len(df),
        "periodo": f"{OCORRENCIAS_INICIO} a {df['data'].max():%Y-%m-%d}",
        "de_interesse": len(interesse),
        "de_interesse_sem_bairro": int(interesse["bairro"].isna().sum()),
        "nomes_sem_bairro": interesse.loc[interesse["bairro"].isna(), "bairro_original"]
        .value_counts(dropna=False)
        .to_dict(),
        "recuperados_por_alias": int(
            df["bairro_original"].map(chave).isin(_ALIASES).sum()
        ),
        "por_tipo": interesse["tipo"].value_counts().to_dict(),
    }
    return agregar_por_bairro(df, estrategia), relatorio


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tabela, relatorio = pipeline()
    tabela.to_csv(SAIDA, index=False, encoding="utf-8-sig")
    for chave_relatorio, valor in relatorio.items():
        log.info("%s: %s", chave_relatorio, valor)
    log.info("Salvo em %s", SAIDA)


if __name__ == "__main__":
    main()
