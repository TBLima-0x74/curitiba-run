# Pipeline ponta a ponta. `make all` parte de um clone limpo e reproduz os resultados.
.DEFAULT_GOAL := help
PY := uv run

.PHONY: help setup lint test clean
.PHONY: raw raw-ippuc raw-osm fase1 malhas grid iac risk analytic eda equity models report all

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup:  ## Cria o ambiente e instala hooks
	uv sync --extra dev
	$(PY) pre-commit install

lint:  ## Roda o linter
	$(PY) ruff check .

test:  ## Roda os testes (exclui os que dependem de rede)
	$(PY) pytest -m "not network"

# ---------------------------------------------------------------- Fase 0 a 2
fase1:  ## Fase 1 num comando: limite -> malhas -> OSM -> IAC (precisa de internet)
	$(PY) python scripts/fase1.py

malhas:  ## Só as malhas H3 (dispensa internet)
	$(PY) python scripts/fase1.py --so-malha

raw: raw-ippuc raw-osm  ## Baixa as fontes brutas já implementadas

raw-ippuc:
	$(PY) python -m curitiba_run.ingestion.ippuc

raw-osm:
	$(PY) python -m curitiba_run.ingestion.osm

# Pendentes (Fases 2 e 3): sigesguarda, sesp, ibge, dem

# ------------------------------------------------------------------- Fase 1 a 3
grid:  ## Constrói a malha H3 recortada pelo município
	$(PY) python -m curitiba_run.processing.grid

iac:  ## Calcula o Índice de Adequação à Corrida
	$(PY) python -m curitiba_run.features.suitability_index

risk:  ## Constrói a superfície de risco
	$(PY) python -m curitiba_run.features.risk_surface

analytic:  ## Monta a tabela analítica (join espacial + acessibilidade)
	$(PY) python -m curitiba_run.processing.spatial_join

# --------------------------------------------------------------- Fase 4 a 6
eda:  ## Análise exploratória e tipologia
	$(PY) python -m curitiba_run.features.typology

equity:  ## Análise de equidade (Lorenz, concentração, H5)
	$(PY) python -m curitiba_run.analysis.equity

models:  ## Modelos espaciais
	$(PY) python -m curitiba_run.analysis.models

report:  ## Gera figuras e mapa interativo
	$(PY) python -m curitiba_run.viz.maps
	$(PY) python -m curitiba_run.viz.charts

all: raw grid iac risk analytic eda equity models report  ## Pipeline completo

clean:  ## Remove intermediários (preserva data/raw)
	rm -rf data/interim/* data/processed/*
	find . -type d -name __pycache__ -exec rm -rf {} +
