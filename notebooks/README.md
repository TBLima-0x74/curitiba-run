# Notebooks

Notebooks servem para **exploração e narrativa**. Lógica reutilizável mora em `src/curitiba_run/`.

Todo notebook commitado é executável de cima a baixo e tem as saídas limpas
(`nbstripout` roda no `pre-commit`).

| Notebook | Fase | Conteúdo |
|----------|------|----------|
| `00_exploracao_fontes.ipynb` | 0 | Inspeção inicial de cada fonte, qualidade e cobertura |
| `01_eda_espacial.ipynb` | 4 | Descritivas, Moran, LISA e tipologia de quadrantes |
| `02_equidade.ipynb` | 5 | Lorenz, concentração por decil e o teste de H5 |
| `03_modelagem.ipynb` | 5 | Regressão espacial e análise de sensibilidade |
