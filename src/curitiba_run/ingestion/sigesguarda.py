"""Ocorrências atendidas pela Guarda Municipal de Curitiba (SiGesGuarda).

Fonte primária de segurança pública — a única georreferenciável no nível do ponto.
https://dadosabertos.curitiba.pr.gov.br/

Cuidados conhecidos (Fase 2):
  - Nomes de colunas e categorias de natureza mudam entre períodos: a camada de
    padronização precisa de testes de contrato de esquema.
  - Registros sem coordenada exigem geocodificação; a taxa de sucesso deve ser
    medida **e testada quanto a viés espacial** (risco R2). Falha de
    geocodificação concentrada em certas regiões contamina toda a análise.
"""

from __future__ import annotations

import pandas as pd

from curitiba_run.config import RAW


def baixar(periodos: list[str] | None = None) -> None:
    """Baixa os arquivos publicados e persiste crus em `data/raw/sigesguarda/`."""
    raise NotImplementedError


def padronizar_esquema(df: pd.DataFrame) -> pd.DataFrame:
    """Harmoniza colunas entre períodos para um esquema único e estável."""
    raise NotImplementedError


def classificar_natureza(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia as naturezas originais para as classes analíticas do projeto.

    Ver docs/taxonomia_ocorrencias.md.
    """
    raise NotImplementedError


def main() -> None:
    (RAW / "sigesguarda").mkdir(parents=True, exist_ok=True)
    raise NotImplementedError("Fase 2 — ver README §6")


if __name__ == "__main__":
    main()
