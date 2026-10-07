"""Modelo digital de elevação — insumo da dimensão de conforto do IAC.

A declividade é um determinante real de viabilidade de percurso, e em Curitiba
tem variação suficiente para importar. Copernicus DEM ou SRTM.
"""

from __future__ import annotations

from curitiba_run.config import RAW


def baixar() -> None:
    raise NotImplementedError


def calcular_declividade() -> None:
    """Deriva declividade em graus a partir do DEM, no CRS métrico."""
    raise NotImplementedError


def main() -> None:
    (RAW / "dem").mkdir(parents=True, exist_ok=True)
    raise NotImplementedError("Fase 1 — ver README §6")


if __name__ == "__main__":
    main()
