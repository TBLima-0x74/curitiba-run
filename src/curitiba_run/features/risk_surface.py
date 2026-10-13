"""Superfície de risco.

Hoje a unidade é o **bairro**: a base da Guarda Municipal não tem coordenada.
`taxa_por_habitante` transforma a gravidade anual de cada bairro em taxa por
100 mil residentes e a normaliza de 0 a 1. As funções por célula ficam para
quando houver fonte georreferenciada.

Ver docs/taxonomia_ocorrencias.md.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from curitiba_run.features.suitability_index import classificar_alto_baixo, normalizar

if TYPE_CHECKING:
    import geopandas as gpd

log = logging.getLogger(__name__)

POR_HABITANTES = 100_000

# Abaixo disto, poucas ocorrências movem muito a taxa. O valor é uma referência
# prática, não um parâmetro estimado; o bairro é marcado, não excluído.
POPULACAO_MINIMA_ESTAVEL = 5_000


def fator_de_dispersao(ocorrencias: pd.DataFrame, estrategia: str = "minima") -> float:
    """κ = E[w²] / E[w] sobre todas as ocorrências de interesse.

    A gravidade de um bairro é uma soma de pesos, não uma contagem. Se as
    ocorrências chegam como Poisson, a variância dessa soma é κ vezes a sua
    média — e não a média, como numa contagem simples. Um bairro cuja nota vem
    de poucos roubos (peso 1) oscila muito mais do que um cuja nota vem de
    muitas ameaças (peso 0,014); κ leva isso em conta.
    """
    from curitiba_run.features import gravidade

    pesos = pd.Series(gravidade.pesos(estrategia))
    contagens = pd.Series(
        {tipo: ocorrencias[f"n_{tipo}"].sum() for tipo in pesos.index if f"n_{tipo}" in ocorrencias}
    )
    if contagens.empty or contagens.sum() == 0:
        return 1.0  # sem composição por tipo: trata como contagem simples
    pesos = pesos[contagens.index]
    return float((contagens * pesos**2).sum() / (contagens * pesos).sum())


def suavizar_bayesiano_empirico(
    gravidade_total: pd.Series,
    exposicao: pd.Series,
    kappa: float = 1.0,
) -> pd.DataFrame:
    """Bayes empírico global (Marshall, 1991), adaptado a gravidade ponderada.

    `exposicao` é pessoa-ano: população × anos cobertos. Para cada bairro:

        θ̂     = Σ gravidade / Σ exposição               média da cidade
        s²     = Σ eᵢ (rᵢ − θ̂)² / Σ eᵢ  −  κ θ̂ / ē      variância real entre bairros
        wᵢ     = s² / (s² + κ θ̂ / eᵢ)                    quanto confiar no próprio bairro
        rᵢ_eb  = θ̂ + wᵢ (rᵢ − θ̂)

    O segundo termo de s² desconta a parte da dispersão que é só ruído de
    amostragem. Bairro grande tem wᵢ perto de 1 e quase não muda; bairro
    pequeno é puxado para a média da cidade, na proporção do quanto seu dado é
    pouco. Se s² sair negativo, não há variação real detectável e todos os
    bairros recebem θ̂.

    Devolve `taxa_eb` (por pessoa-ano) e `peso_proprio` (wᵢ).
    """
    if (exposicao <= 0).any():
        raise ValueError("Exposição zero ou negativa.")
    taxa = gravidade_total / exposicao
    media = gravidade_total.sum() / exposicao.sum()
    variancia = (exposicao * (taxa - media) ** 2).sum() / exposicao.sum() - kappa * media / exposicao.mean()
    variancia = max(variancia, 0.0)
    peso = variancia / (variancia + kappa * media / exposicao) if variancia > 0 else exposicao * 0.0
    return pd.DataFrame(
        {"taxa_eb": media + peso * (taxa - media), "peso_proprio": peso}, index=gravidade_total.index
    )


def taxa_por_habitante(
    ocorrencias: pd.DataFrame,
    populacao: pd.DataFrame,
    por: int = POR_HABITANTES,
    populacao_minima: int = POPULACAO_MINIMA_ESTAVEL,
    escala: str = "log",
    suavizar: bool = True,
) -> pd.DataFrame:
    """Gravidade anual por 100 mil residentes, e a mesma taxa normalizada de 0 a 1.

    **Bayes empírico por padrão.** Bairro com poucos moradores tem taxa que
    oscila com uma ou duas ocorrências. `taxa_gravidade_eb` puxa cada bairro
    em direção à média da cidade na medida em que seu próprio dado é pouco
    (ver `suavizar_bayesiano_empirico`), e é dela que saem a normalização e a
    classe. `taxa_gravidade` continua sendo a taxa observada, sem suavizar.

    **Escala logarítmica por padrão.** A taxa tem cauda pesada: em Curitiba,
    quatro bairros ficam muito acima dos outros 71, e na escala linear 60 dos
    75 caem abaixo de 0,1 — num mapa, quase todos teriam a mesma cor. O
    logaritmo (`log1p`, que leva zero a zero) espalha a parte de baixo sem
    mudar a ordem; a classe alto/baixo pela mediana sai idêntica nas duas.
    `escala="linear"` mantém a proporcionalidade, para quem precisar dela.

    Depois da escala, a normalização é a mesma do IAC: corte nos percentis 2 e 98 antes de
    escalar, para que um único bairro extremo não comprima os outros 74 perto
    de zero. Com 75 bairros, isso leva os dois extremos de cada lado a 0 e 1.
    Atenção: o percentil 98 interpolado só deixa o extremo de fora quando há
    pelo menos 51 unidades; com menos, um único outlier volta a puxar o teto.

    O denominador é a população **residente**. Bairro que recebe muita gente de
    fora — o Centro, sobretudo — fica com taxa inflada: as ocorrências acontecem
    com quem circula, e a divisão é por quem dorme ali.
    """
    if not ocorrencias["bairro"].is_unique or not populacao["bairro"].is_unique:
        raise ValueError("Bairro repetido em uma das tabelas: a junção duplicaria linhas.")

    tabela = ocorrencias.merge(populacao, on="bairro", how="left", validate="one_to_one")
    sem_populacao = sorted(tabela.loc[tabela["populacao"].isna(), "bairro"])
    if sem_populacao:
        raise ValueError(f"Bairros sem população: {sem_populacao}.")
    if (tabela["populacao"] <= 0).any():
        raise ValueError("População zero ou negativa: a taxa seria infinita.")

    anos = tabela["gravidade"].sum() / tabela["gravidade_anual"].sum()

    tabela["taxa_ocorrencias"] = tabela["n_ocorrencias"] / anos / tabela["populacao"] * por
    tabela["taxa_gravidade"] = tabela["gravidade_anual"] / tabela["populacao"] * por

    if suavizar:
        eb = suavizar_bayesiano_empirico(
            tabela["gravidade"], tabela["populacao"] * anos, fator_de_dispersao(tabela)
        )
        tabela["taxa_gravidade_eb"] = eb["taxa_eb"] * por
        tabela["peso_proprio"] = eb["peso_proprio"]
    else:
        tabela["taxa_gravidade_eb"] = tabela["taxa_gravidade"]
        tabela["peso_proprio"] = 1.0
    base = tabela["taxa_gravidade_eb"]

    if escala == "log":
        transformada = np.log1p(base)
    elif escala == "linear":
        transformada = base
    else:
        raise ValueError(f"escala desconhecida: {escala!r} (use 'log' ou 'linear')")
    tabela["taxa_gravidade_norm"] = normalizar(transformada.rename("taxa_gravidade"))
    tabela["populacao_pequena"] = tabela["populacao"] < populacao_minima

    # Corte pela mediana dos 75 bairros — cada bairro conta uma vez, qualquer
    # que seja o seu tamanho. A mediana das células daria à CIC, com 451
    # hexágonos, o peso de dezenas de bairros. Mesma regra do IAC (ADR 0003);
    # a taxa bruta e a normalizada têm a mesma ordem, então a classe é a mesma.
    tabela["classe_risco"] = classificar_alto_baixo(base, corte=base.median())

    inicio = [
        "bairro", "populacao", "taxa_gravidade", "taxa_gravidade_eb", "peso_proprio",
        "taxa_gravidade_norm", "classe_risco", "taxa_ocorrencias",
    ]
    return tabela[inicio + [c for c in tabela.columns if c not in inicio]]


def comparar_fontes(
    gm: pd.DataFrame,
    sesp: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Guarda Municipal contra SESP-PR, bairro a bairro.

    É a validação do viés de presença da Guarda: se a nota da GM fosse risco,
    as duas fontes concordariam na ordem dos bairros. Onde a GM fica acima da
    SESP, e isso acompanha a fração de ocorrências em equipamento municipal, a
    diferença é a Guarda registrando onde está.

    Usa a taxa suavizada de cada fonte. Devolve a tabela por bairro e um resumo.
    """
    colunas = ["bairro", "taxa_gravidade_eb", "classe_risco", "n_ocorrencias"]
    t = gm[colunas + ["pct_em_equipamento_urbano"]].merge(
        sesp[colunas], on="bairro", suffixes=("_gm", "_sesp"), validate="one_to_one"
    )
    t["classes_concordam"] = t["classe_risco_gm"].astype(str) == t["classe_risco_sesp"].astype(str)
    # Cada fonte relativa ao seu próprio nível: as duas registram volumes
    # diferentes no total, e o que interessa é a posição de cada bairro dentro
    # de cada fonte. Razão em log das posições: positiva onde a GM registra,
    # proporcionalmente, mais do que a polícia; zero onde as duas concordam.
    def relativa(taxa):
        media = taxa.mean()
        return np.log((taxa + 0.01 * media) / media)

    t["log_razao_gm_sesp"] = relativa(t["taxa_gravidade_eb_gm"]) - relativa(t["taxa_gravidade_eb_sesp"])

    def spearman(a, b):
        return float(a.rank().corr(b.rank()))

    resumo = {
        "bairros": len(t),
        "rho_taxas": round(spearman(t["taxa_gravidade_eb_gm"], t["taxa_gravidade_eb_sesp"]), 3),
        "classes_concordam_pct": round(100 * t["classes_concordam"].mean(), 1),
        "rho_excesso_gm_vs_equipamento": round(
            spearman(t["log_razao_gm_sesp"], t["pct_em_equipamento_urbano"].fillna(0)), 3
        ),
        "gm_alto_sesp_baixo": sorted(
            t.loc[(t["classe_risco_gm"] == "alto") & (t["classe_risco_sesp"] == "baixo"), "bairro"]
        ),
        "gm_baixo_sesp_alto": sorted(
            t.loc[(t["classe_risco_gm"] == "baixo") & (t["classe_risco_sesp"] == "alto"), "bairro"]
        ),
    }
    return t, resumo


def risco_por_celula(atribuicao: pd.DataFrame, taxa: pd.DataFrame) -> pd.DataFrame:
    """Cada célula H3 herda a taxa do seu bairro dominante.

    Falha alto se alguma célula ficar sem bairro. Bairro sem nenhuma célula em
    que seja dominante gera aviso: é limite da resolução, não erro.
    """
    sem_bairro = atribuicao["bairro"].isna().sum()
    if sem_bairro:
        raise ValueError(f"{sem_bairro} células sem bairro depois da atribuição por proximidade.")

    # Um bairro pequeno pode não ser o dominante em nenhum hexágono. Não é
    # defeito do cálculo, é limite da resolução — mas precisa aparecer.
    sem_celula = sorted(set(taxa["bairro"]) - set(atribuicao["bairro"]))
    if sem_celula:
        log.warning(
            "Bairros que não são dominantes em nenhuma célula, e cuja nota não chega "
            "ao mapa: %s", sem_celula,
        )

    colunas = [
        "bairro", "populacao", "taxa_gravidade", "taxa_gravidade_eb", "taxa_gravidade_norm",
        "classe_risco", "populacao_pequena",
    ]
    return atribuicao.merge(taxa[colunas], on="bairro", how="left", validate="many_to_one")


def agregar_por_celula(
    ocorrencias: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    por_classe: bool = True,
) -> pd.DataFrame:
    raise NotImplementedError


def densidade_kernel(ocorrencias: gpd.GeoDataFrame, malha: gpd.GeoDataFrame) -> pd.Series:
    raise NotImplementedError




def main() -> None:
    raise NotImplementedError("Fase 2/3 — ver README §6")


if __name__ == "__main__":
    main()
