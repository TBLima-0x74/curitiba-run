"""Tipologia de quadrantes: cruzamento entre adequação e risco.

                 Baixo risco          Alto risco
  Alto IAC       privilegiado         subutilizado
  Baixo IAC      latente              duplamente_penalizado

O quadrante `latente` — seguro, mas sem infraestrutura — é o achado de maior
valor prático: são as áreas onde investir em infraestrutura teria retorno
imediato, sem depender de política de segurança.
"""

from __future__ import annotations

import pandas as pd

from curitiba_run.config import QUADRANTES


def classificar(
    iac: pd.Series,
    risco: pd.Series,
    corte_iac: float | None = None,
    corte_risco: float | None = None,
) -> pd.Series:
    """Classifica cada célula em um dos quatro quadrantes.

    Por padrão o corte é a mediana de cada variável, o que garante quadrantes
    não vazios. Cortes explícitos permitem testar a sensibilidade da tipologia
    ao limiar — recomendado antes de comunicar os resultados.
    """
    corte_iac = iac.median() if corte_iac is None else corte_iac
    corte_risco = risco.median() if corte_risco is None else corte_risco

    alto_iac = iac >= corte_iac
    alto_risco = risco >= corte_risco

    rotulos = pd.Series(index=iac.index, dtype="object")
    for (chave_iac, chave_risco), rotulo in QUADRANTES.items():
        selecao = (alto_iac == chave_iac) & (alto_risco == chave_risco)
        rotulos.loc[selecao] = rotulo

    rotulos.loc[iac.isna() | risco.isna()] = pd.NA
    return rotulos.astype("category")


def perfilar(tabela: pd.DataFrame, coluna_quadrante: str = "quadrante") -> pd.DataFrame:
    """Caracteriza cada quadrante por população, renda média e número de células.

    É esta tabela que responde "quem vive em cada quadrante" — o cerne da
    pergunta de equidade.
    """
    agregacoes = {
        "h3": "count",
        "populacao": "sum",
        "renda_per_capita": "median",
        "iac": "mean",
        "risco": "mean",
    }
    presentes = {k: v for k, v in agregacoes.items() if k in tabela.columns}
    perfil = tabela.groupby(coluna_quadrante, observed=True).agg(presentes)

    if "populacao" in perfil.columns:
        perfil["pct_populacao"] = 100 * perfil["populacao"] / perfil["populacao"].sum()

    return perfil.rename(columns={"h3": "n_celulas"})


def main() -> None:
    raise NotImplementedError("Fase 4 — ver README §6")


if __name__ == "__main__":
    main()
