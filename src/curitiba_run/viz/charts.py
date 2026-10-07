"""Gráficos: curvas de Lorenz, perfis por decil, sensibilidade a pesos e escalas."""

from __future__ import annotations

import pandas as pd


def grafico_lorenz(pop_acum, valor_acum, destino=None):
    raise NotImplementedError


def grafico_por_decil(resumo: pd.DataFrame, destino=None):
    raise NotImplementedError


def grafico_sensibilidade_pesos(cenarios: pd.DataFrame, destino=None):
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError("Fase 6 — ver README §6")


if __name__ == "__main__":
    main()
