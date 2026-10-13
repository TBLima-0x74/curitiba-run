"""Supressão de baixa contagem antes de publicar (ADR 0007).

"Uma ocorrência neste bairro" pode identificar uma vítima. Por isso nada sai do
projeto sem passar por aqui:

- **Bairro com menos de `LIMIAR_SUPRESSAO` ocorrências** (5) não tem valor
  publicado: contagem, taxas, nota e classe ficam vazias e a linha sai marcada
  `suprimido`. A taxa precisa sair junto com a contagem, porque taxa ×
  população (pública) devolve a gravidade — e a suavizada também se inverte,
  com o κ documentado.
- **Supressão complementar.** O total da cidade é público, então a soma dos
  bairros suprimidos se obtém por diferença. Se essa soma permitir deduzir que
  algum deles tem ocorrência, o bairro publicado de menor contagem também é
  suprimido, até que não permita.
- **Nenhuma contagem por tipo por bairro.** "Um estupro no bairro X" é
  exatamente o que a regra existe para evitar, e suprimir só as células baixas
  não basta: o total do bairro menos os outros tipos devolve a escondida. Tipo
  só sai somado para a cidade, com o mesmo limiar.

O que fica em `data/processed/` continua completo e fora do Git: as fases
seguintes calculam com tudo, e só o que é publicado passa por aqui.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from curitiba_run.config import LIMIAR_SUPRESSAO
from curitiba_run.features import gravidade

COLUNAS_BAIRRO = [
    "bairro", "populacao", "n_ocorrencias", "taxa_gravidade", "taxa_gravidade_eb",
    "taxa_gravidade_norm", "classe_risco", "populacao_pequena",
]
# O que some de um bairro suprimido. `populacao` é do Censo e já é pública.
VALORES = ["n_ocorrencias", "taxa_gravidade", "taxa_gravidade_eb", "taxa_gravidade_norm", "classe_risco"]
COLUNAS_CELULA = ["h3", "bairro", "fracao_bairro", "bairro_por_proximidade", "celula_dividida"]
# Identificam a linha ou vêm de fonte pública; não somem na supressão.
NAO_SENSIVEIS = {"suprimido", "populacao", "populacao_pequena", "tipo", "rotulo", "peso", *COLUNAS_CELULA}


def mascara(n: pd.Series, limiar: int = LIMIAR_SUPRESSAO) -> pd.Series:
    """Quem suprimir: abaixo do limiar, mais o complemento que a diferença exige.

    Cada suprimido tem entre 0 e `limiar − 1` ocorrências. Conhecida a soma S
    dos k suprimidos, o menor valor possível de cada um é
    S − (k − 1)(limiar − 1). Se isso for ao menos 1, todos os suprimidos têm
    ocorrência comprovada — e com k = 1, o valor sai exato. Nesse caso entra
    também o publicado de menor contagem: como ele tem 5 ou mais, e quem olha
    de fora não sabe qual dos suprimidos é ele, a soma deixa de prender os
    outros. É a regra clássica da supressão complementar.
    """
    n = n.astype(float)
    sup = n < limiar
    soma, k = n[sup].sum(), int(sup.sum())
    if k and (~sup).any() and soma - (k - 1) * (limiar - 1) >= 1:
        sup[n[~sup].idxmin()] = True
    return sup


def suprimir_bairros(taxa: pd.DataFrame, limiar: int = LIMIAR_SUPRESSAO) -> pd.DataFrame:
    """Tabela por bairro publicável: sem contagem por tipo, com os baixos suprimidos."""
    pub = taxa[[c for c in COLUNAS_BAIRRO if c in taxa.columns]].copy()
    pub = pub.round({"taxa_gravidade": 2, "taxa_gravidade_eb": 2, "taxa_gravidade_norm": 4})
    pub["suprimido"] = mascara(taxa["n_ocorrencias"], limiar).to_numpy()
    for coluna in VALORES:
        if coluna in pub:
            if pub[coluna].dtype.kind in "iu":
                pub[coluna] = pub[coluna].astype("Int64")
            else:
                pub[coluna] = pub[coluna].astype("object" if coluna == "classe_risco" else float)
            pub.loc[pub["suprimido"], coluna] = pd.NA if pub[coluna].dtype == "Int64" else np.nan
    return pub


def suprimir_celulas(celulas: pd.DataFrame, bairros_publicados: pd.DataFrame) -> pd.DataFrame:
    """A malha H3 com a nota do bairro já suprimida — a célula só herda o que é publicável."""
    base = celulas[[c for c in COLUNAS_CELULA if c in celulas.columns]]
    return base.merge(bairros_publicados.drop(columns=["populacao"], errors="ignore"),
                      on="bairro", how="left", validate="many_to_one")


def por_tipo_cidade(ocorrencias: pd.DataFrame, estrategia: str = "minima",
                    limiar: int = LIMIAR_SUPRESSAO) -> pd.DataFrame:
    """Contagem de cada tipo na cidade inteira, com o mesmo limiar e o mesmo complemento."""
    pesos = gravidade.pesos(estrategia)
    tipos = [t for t in gravidade.TIPOS if f"n_{t}" in ocorrencias.columns]
    t = pd.DataFrame({
        "tipo": tipos,
        "rotulo": [gravidade.TIPOS[x].rotulo for x in tipos],
        "peso": [round(pesos[x], 3) for x in tipos],
        "n": [int(ocorrencias[f"n_{x}"].sum()) for x in tipos],
    })
    t["suprimido"] = mascara(t["n"], limiar)
    t["n"] = t["n"].astype("Int64")
    t.loc[t["suprimido"], "n"] = pd.NA
    return t


def suprimir_comparacao(comparacao: pd.DataFrame, gm: pd.DataFrame, sesp: pd.DataFrame) -> pd.DataFrame:
    """GM × SESP: o bairro sai vazio se estiver suprimido em qualquer das duas.

    Sem `pct_em_equipamento_urbano`: percentual × total devolve uma subcontagem
    do bairro, e subcontagem por bairro não se publica.
    """
    sup = (
        comparacao[["bairro"]]
        .merge(gm[["bairro", "suprimido"]], on="bairro", how="left")
        .merge(sesp[["bairro", "suprimido"]], on="bairro", how="left", suffixes=("_gm", "_sesp"))
    )
    suprimido = (sup["suprimido_gm"].fillna(True) | sup["suprimido_sesp"].fillna(True)).astype(bool).to_numpy()
    pub = comparacao.drop(columns=["pct_em_equipamento_urbano"], errors="ignore")
    for coluna in pub.columns.drop("bairro"):
        pub[coluna] = pub[coluna].astype("object" if pub[coluna].dtype.kind in "biuO" else float)
        pub.loc[suprimido, coluna] = np.nan
    pub["suprimido"] = suprimido
    return pub


def verificar(df: pd.DataFrame, nome: str, limiar: int = LIMIAR_SUPRESSAO) -> None:
    """Última barreira antes de gravar: para se algo identificável escapou.

    - nenhuma contagem por tipo em tabela por bairro ou por célula;
    - nenhuma contagem publicada abaixo do limiar;
    - linha suprimida sem nenhum valor.
    """
    por_lugar = "bairro" in df.columns or "h3" in df.columns
    contagens = [c for c in df.columns if c == "n" or c.startswith("n_")]
    if por_lugar:
        por_tipo = [c for c in contagens if not c.startswith("n_ocorrencias")]
        if por_tipo:
            raise ValueError(f"{nome}: contagem por tipo em tabela por lugar: {por_tipo}")
    for coluna in contagens:
        valores = pd.to_numeric(df[coluna], errors="coerce").dropna()
        if (valores < limiar).any():
            raise ValueError(f"{nome}: {coluna} publica contagem abaixo de {limiar}")
    if "suprimido" in df.columns:
        restantes = [c for c in df.columns if c not in NAO_SENSIVEIS]
        vazado = df.loc[df["suprimido"].astype(bool), restantes].notna().any()
        if vazado.any():
            raise ValueError(f"{nome}: linha suprimida com valor em {list(vazado[vazado].index)}")
