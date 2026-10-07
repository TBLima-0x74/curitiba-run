"""Modelagem espacial.

Escopo deliberadamente contido (risco R8): regressão do IAC e do acesso seguro
sobre renda, densidade e distância ao centro, com termo espacial escolhido por
diagnóstico. GWR e MGWR ficam como extensão — ver README §13.

Cautela obrigatória: os coeficientes descrevem associação, não efeito causal.
A pergunta do projeto é descritiva e de equidade, e não requer identificação.
"""

from __future__ import annotations

import pandas as pd


def diagnosticar_dependencia_espacial(residuos: pd.Series, w) -> dict:
    """Testes de multiplicadores de Lagrange para escolher entre SAR e SEM."""
    raise NotImplementedError


def ajustar_ols(tabela: pd.DataFrame, formula: str):
    raise NotImplementedError


def ajustar_sar(tabela: pd.DataFrame, y: str, x: list[str], w):
    raise NotImplementedError


def ajustar_sem(tabela: pd.DataFrame, y: str, x: list[str], w):
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError("Fase 5 — ver README §6")


if __name__ == "__main__":
    main()
