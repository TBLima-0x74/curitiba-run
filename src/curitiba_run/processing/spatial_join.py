"""Integração: uma tabela analítica, uma linha por célula.

Junta IAC, superfície de risco, população, renda e acessibilidade na malha H3.

Validação obrigatória: somas de controle. O total de ocorrências e de população
alocados na malha precisa bater com o total das fontes de origem — divergência
indica perda silenciosa no join.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


def interpolar_setores(
    setores: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    colunas: list[str],
) -> pd.DataFrame:
    """Interpola variáveis dos setores censitários para a malha, por área ponderada.

    Assume distribuição homogênea dentro do setor — aproximação aceita e
    registrada nas limitações.
    """
    raise NotImplementedError


def montar_tabela_analitica() -> gpd.GeoDataFrame:
    """Consolida todas as camadas na tabela analítica principal."""
    raise NotImplementedError


def validar_somas_de_controle(tabela: gpd.GeoDataFrame, totais_origem: dict[str, float]) -> None:
    """Falha alto se algum total alocado divergir da origem além da tolerância."""
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError("Fase 3 — ver README §6")


if __name__ == "__main__":
    main()
