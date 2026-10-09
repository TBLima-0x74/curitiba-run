"""Geocodificação dos registros de ocorrência sem coordenada.

⚠️  Risco R2: se a falha de geocodificação for espacialmente enviesada — se
    endereços de certas regiões falharem mais que os de outras — o viés
    contamina toda a análise. O teste em `testar_vies_espacial` é obrigatório
    e seu resultado vai para o relatório, não para o log.
"""

from __future__ import annotations

import pandas as pd


def geocodificar(df: pd.DataFrame, coluna_endereco: str = "logradouro") -> pd.DataFrame:
    """Resolve endereços em coordenadas, com mais de um provedor e cache em disco."""
    raise NotImplementedError


def testar_vies_espacial(df: pd.DataFrame) -> pd.DataFrame:
    """Compara a taxa de sucesso da geocodificação entre bairros e decis de renda.

    Devolve a tabela que entra em `reports/validacoes/qualidade_dados_seguranca.md`.
    """
    raise NotImplementedError
