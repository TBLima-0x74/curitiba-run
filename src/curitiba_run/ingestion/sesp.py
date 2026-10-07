"""Estatísticas criminais da SESP-PR / CAPE — camada de validação agregada.

https://www.seguranca.pr.gov.br/CAPE/Estatisticas

Cobre crimes de competência estadual que a Guarda Municipal não registra da
mesma forma. Não substitui o SiGesGuarda: serve para checar se a distribuição
municipal derivada da base da GM é plausível.
"""

from __future__ import annotations

from curitiba_run.config import RAW


def baixar() -> None:
    raise NotImplementedError


def main() -> None:
    (RAW / "sesp").mkdir(parents=True, exist_ok=True)
    raise NotImplementedError("Fase 2 — ver README §6")


if __name__ == "__main__":
    main()
