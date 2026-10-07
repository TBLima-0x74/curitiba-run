"""Análise de equidade: quem tem acesso a espaço seguro para correr.

O módulo entrega o teste da hipótese central H5 — a desigualdade no acesso a
espaço *seguro* é maior que a desigualdade na infraestrutura isolada, porque os
dois gradientes se compõem em vez de se compensarem.

Se H5 se confirma, qualquer análise de infraestrutura que ignore segurança
subestima sistematicamente a desigualdade real de acesso à atividade física.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# `trapezoid` só existe a partir do numpy 2.0; `trapz` é o nome anterior.
_trapezoid = getattr(np, "trapezoid", None) or np.trapz


def curva_de_lorenz(
    valor: pd.Series,
    populacao: pd.Series,
) -> tuple[np.ndarray, np.ndarray]:
    """Curva de Lorenz do `valor` ponderada por `populacao`.

    Devolve (fração acumulada de população, fração acumulada do valor), ambas
    começando em zero. A diagonal representa distribuição perfeitamente igual.
    """
    df = pd.DataFrame({"valor": valor, "populacao": populacao}).dropna()
    df = df[df["populacao"] > 0].sort_values("valor")

    if df.empty:
        raise ValueError("Sem observações válidas para a curva de Lorenz")

    pop = df["populacao"].to_numpy(dtype=float)
    total = df["valor"].to_numpy(dtype=float) * pop

    pop_acum = np.insert(np.cumsum(pop) / pop.sum(), 0, 0.0)
    valor_acum = np.insert(np.cumsum(total) / total.sum(), 0, 0.0)
    return pop_acum, valor_acum


def gini(valor: pd.Series, populacao: pd.Series) -> float:
    """Coeficiente de Gini ponderado, calculado pela área sob a curva de Lorenz.

    0 = distribuição igualitária; 1 = concentração máxima.
    """
    x, y = curva_de_lorenz(valor, populacao)
    return float(1 - 2 * _trapezoid(y, x))


def indice_de_concentracao(
    valor: pd.Series,
    populacao: pd.Series,
    ordenador: pd.Series,
) -> float:
    """Índice de concentração do `valor` em relação ao gradiente de `ordenador`.

    Diferente do Gini, ordena pelo `ordenador` (tipicamente renda) em vez de
    pelo próprio valor. Positivo indica que o benefício se concentra no topo do
    gradiente; negativo, na base. É a métrica correta para "quem tem acesso".
    """
    df = pd.DataFrame(
        {"valor": valor, "populacao": populacao, "ordenador": ordenador}
    ).dropna()
    df = df[df["populacao"] > 0].sort_values("ordenador")

    if df.empty:
        raise ValueError("Sem observações válidas para o índice de concentração")

    pop = df["populacao"].to_numpy(dtype=float)
    val = df["valor"].to_numpy(dtype=float)

    fracao_pop = pop / pop.sum()
    # Posição relativa acumulada de cada grupo (ponto médio do intervalo).
    rank = np.cumsum(fracao_pop) - fracao_pop / 2

    media = np.average(val, weights=pop)
    if np.isclose(media, 0):
        return 0.0

    return float(2 * np.sum(fracao_pop * val * (rank - 0.5)) / media)


def por_decil(
    tabela: pd.DataFrame,
    coluna_valor: str,
    coluna_populacao: str = "populacao",
    coluna_renda: str = "renda_per_capita",
    n: int = 10,
) -> pd.DataFrame:
    """Média do valor por decil populacional de renda, com razão topo/base."""
    df = tabela[[coluna_valor, coluna_populacao, coluna_renda]].dropna()
    df = df[df[coluna_populacao] > 0].sort_values(coluna_renda)

    pop_acum = df[coluna_populacao].cumsum() / df[coluna_populacao].sum()
    df["decil"] = np.minimum((pop_acum * n).apply(np.ceil).astype(int), n)

    resumo = df.groupby("decil").apply(
        lambda g: pd.Series(
            {
                "populacao": g[coluna_populacao].sum(),
                "media_ponderada": np.average(g[coluna_valor], weights=g[coluna_populacao]),
                "renda_mediana": g[coluna_renda].median(),
            }
        ),
        include_groups=False,
    )
    return resumo


def testar_h5(
    tabela: pd.DataFrame,
    coluna_iac: str = "iac",
    coluna_acesso_seguro: str = "acesso_seguro",
    coluna_populacao: str = "populacao",
    coluna_renda: str = "renda_per_capita",
) -> pd.DataFrame:
    """Compara a concentração da infraestrutura isolada com a do acesso seguro.

    H5 se sustenta se o índice de concentração do acesso seguro for maior que o
    da infraestrutura isolada — os dois gradientes se compõem.

    Devolve uma tabela com as duas métricas e a diferença, pronta para o relatório.
    """
    linhas = []
    for rotulo, coluna in (
        ("infraestrutura (IAC)", coluna_iac),
        ("acesso seguro", coluna_acesso_seguro),
    ):
        linhas.append(
            {
                "medida": rotulo,
                "gini": gini(tabela[coluna], tabela[coluna_populacao]),
                "indice_concentracao": indice_de_concentracao(
                    tabela[coluna], tabela[coluna_populacao], tabela[coluna_renda]
                ),
            }
        )

    resultado = pd.DataFrame(linhas).set_index("medida")
    resultado.loc["diferença"] = resultado.loc["acesso seguro"] - resultado.loc["infraestrutura (IAC)"]
    return resultado


def main() -> None:
    raise NotImplementedError("Fase 5 — ver README §6")


if __name__ == "__main__":
    main()
