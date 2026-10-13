"""Nomes de bairro: limpeza, chave de comparação e nome oficial.

Usado por toda fonte que identifica lugar pelo nome do bairro — a base da
Guarda Municipal, o Censo do IBGE —, para que todas casem com a mesma lista
oficial dos 75 bairros de `config.BAIRROS_CURITIBA`.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

from curitiba_run.config import BAIRRO_ALIASES, BAIRROS_CURITIBA


def limpar_texto(valor) -> str | None:
    """Espaços normais, sem sobra nas pontas, e vazio vira ausente.

    A base da Guarda usa espaço não separável (U+00A0) em "Importunação sexual".
    Sem isto, a comparação exata falha e as 339 ocorrências somem sem erro.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = re.sub(r"\s+", " ", str(valor).replace("\xa0", " ")).strip()
    return texto or None


def chave(valor) -> str | None:
    """Forma de comparação: sem acento, maiúscula, espaços normalizados."""
    texto = limpar_texto(valor)
    if texto is None:
        return None
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sem_acento.upper()


OFICIAIS = {chave(b): b for b in BAIRROS_CURITIBA}
ALIASES = {chave(k): v for k, v in BAIRRO_ALIASES.items()}


def normalizar_bairro(serie: pd.Series) -> pd.Series:
    """Nome oficial do bairro, ou ausente se o nome não designa bairro de Curitiba."""
    return serie.map(chave).map(lambda k: OFICIAIS.get(k) or ALIASES.get(k))


# ------------------------------------------------------------ bairro → H3

# Abaixo disto, a célula está dividida entre bairros a ponto de a nota herdada
# representar menos da metade dela. É marcada, não descartada.
FRACAO_DOMINANTE_MINIMA = 0.5

# A malha H3 foi recortada pelo limite municipal do IBGE, que é generalizado; os
# bairros vêm dos setores do IPPUC, que seguem o limite oficial. Os dois
# contornos divergem em média 80 m, e células da borda podem não tocar nenhum
# bairro. Essas recebem o bairro mais próximo, até esta distância — além dela,
# a divergência já não é de contorno, e o pipeline para.
DISTANCIA_MAXIMA_PROXIMIDADE_M = 500


def atribuir_bairro_dominante(malha, bairros) -> pd.DataFrame:
    """Para cada célula H3, o bairro que ocupa a maior parte dela.

    A fração é calculada sobre a parte da célula coberta por algum bairro, e não
    sobre o hexágono inteiro: assim uma célula da divisa do município não parece
    dividida só porque metade dela está fora de Curitiba.

    Células da borda que não tocam nenhum bairro — por divergência entre o
    limite do IBGE e o do IPPUC — recebem o bairro mais próximo e saem marcadas
    em `bairro_por_proximidade`, com `fracao_bairro` ausente.

    Devolve `h3`, `bairro`, `fracao_bairro`, `bairro_por_proximidade` e `celula_dividida`.
    """
    import geopandas as gpd

    from curitiba_run.config import CRS_METRICO

    celulas = malha[["h3", "geometry"]].to_crs(CRS_METRICO)
    poligonos = bairros[["bairro", "geometry"]].to_crs(CRS_METRICO)

    pedacos = gpd.overlay(celulas, poligonos, how="intersection", keep_geom_type=True)
    pedacos["area"] = pedacos.area
    pedacos = pedacos[pedacos["area"] > 0]

    por_par = pedacos.groupby(["h3", "bairro"], as_index=False)["area"].sum()
    por_par["fracao_bairro"] = por_par["area"] / por_par.groupby("h3")["area"].transform("sum")

    dominante = (
        por_par.sort_values(["h3", "fracao_bairro"], ascending=[True, False])
        .drop_duplicates("h3")[["h3", "bairro", "fracao_bairro"]]
    )
    resultado = celulas[["h3"]].merge(dominante, on="h3", how="left")
    resultado["bairro_por_proximidade"] = resultado["bairro"].isna()

    orfas = celulas[celulas["h3"].isin(resultado.loc[resultado["bairro_por_proximidade"], "h3"])]
    if not orfas.empty:
        vizinho = gpd.sjoin_nearest(
            orfas, poligonos, how="left", distance_col="distancia_m"
        ).drop_duplicates("h3")
        longe = vizinho[vizinho["distancia_m"] > DISTANCIA_MAXIMA_PROXIMIDADE_M]
        if not longe.empty:
            raise ValueError(
                f"{len(longe)} células a mais de {DISTANCIA_MAXIMA_PROXIMIDADE_M} m de qualquer "
                "bairro: as duas malhas não descrevem o mesmo território."
            )
        mapa = vizinho.set_index("h3")["bairro"]
        orfa = resultado["bairro_por_proximidade"]
        resultado.loc[orfa, "bairro"] = resultado.loc[orfa, "h3"].map(mapa)

    resultado["celula_dividida"] = resultado["fracao_bairro"] < FRACAO_DOMINANTE_MINIMA
    return resultado.reset_index(drop=True)
