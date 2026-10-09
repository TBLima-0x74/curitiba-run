"""Fase 2, etapa 1: ocorrências da Guarda Municipal → tabela por bairro.

Uso, a partir da raiz do repositório:

    python scripts/fase2_ocorrencias.py

Lê a base mais recente em `data/raw/sigesguarda/`, mantém só as ocorrências de
interesse, aplica o peso de gravidade de cada tipo e grava
`data/processed/ocorrencias_gm_por_bairro.csv`. Não precisa de internet.
Regras e pesos: docs/taxonomia_ocorrencias.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from curitiba_run.ingestion.sigesguarda import main  # noqa: E402

if __name__ == "__main__":
    main()
