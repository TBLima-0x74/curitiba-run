"""Índice de Adequação à Corrida (IAC).

Índice composto de cinco dimensões, normalizado de 0 a 1 por célula. A escolha
dos pesos é arbitrária por natureza — por isso `avaliar_cenarios_de_peso` não é
um extra, é parte do resultado (risco R3). Um índice composto sem análise de
sensibilidade a peso é um número arbitrário disfarçado de medida.

Ver docs/indice_adequacao.md para as dimensões e sua justificativa.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from curitiba_run.config import (
    IAC_DIMENSOES,
    IAC_DIMENSOES_INVERTIDAS,
    IAC_PESOS_BASE,
    IAC_PESOS_CENARIOS,
    NORMALIZACAO_PERCENTIS,
)

log = logging.getLogger(__name__)


def normalizar(
    serie: pd.Series,
    percentis: tuple[float, float] = NORMALIZACAO_PERCENTIS,
    inverter: bool = False,
) -> pd.Series:
    """Normaliza para [0, 1] com corte robusto de outliers.

    Valores fora dos percentis informados são truncados antes da normalização,
    para que uma única célula extrema não comprima toda a distribuição.

    `inverter=True` para dimensões em que "mais é pior" — declividade, por exemplo.
    """
    valores = pd.to_numeric(serie, errors="coerce")
    baixo, alto = np.nanpercentile(valores, percentis)

    if np.isclose(alto, baixo):
        # Sem variação entre os percentis: devolver o ponto médio evita dividir
        # por zero, mas o resultado é uma CONSTANTE — a dimensão deixa de
        # carregar informação e só dilui as demais. Foi assim que a densidade de
        # postes do OSM injetou 0,25 fixo em toda célula sem ninguém notar.
        nome = serie.name or "série sem nome"
        log.warning(
            "Dimensão %r é constante: percentis %s coincidem em %.6g. "
            "normalizar devolveu 0,5 para todas as %d células — ela não "
            "distingue nada e seu peso está sendo desperdiçado.",
            nome, percentis, baixo, len(valores),
        )
        return pd.Series(np.where(valores.isna(), np.nan, 0.5), index=serie.index)

    escalado = ((valores.clip(baixo, alto) - baixo) / (alto - baixo)).clip(0, 1)
    return 1 - escalado if inverter else escalado


def normalizar_dimensoes(brutas: pd.DataFrame) -> pd.DataFrame:
    """Normaliza o quadro de dimensões brutas, invertendo as que pedem inversão.

    Centraliza a regra para que nenhum ponto do pipeline precise lembrar que
    declividade alta é ruim: `IAC_DIMENSOES_INVERTIDAS` decide.
    """
    return pd.DataFrame(
        {
            coluna: normalizar(brutas[coluna], inverter=coluna in IAC_DIMENSOES_INVERTIDAS)
            for coluna in brutas.columns
        }
    )


def validar_pesos(pesos: dict[str, float], tolerancia: float = 1e-6) -> None:
    """Garante que os pesos cobrem exatamente as dimensões e somam 1."""
    faltando = set(IAC_DIMENSOES) - set(pesos)
    sobrando = set(pesos) - set(IAC_DIMENSOES)
    if faltando or sobrando:
        raise ValueError(f"Pesos inconsistentes. Faltando: {faltando}. Sobrando: {sobrando}")

    total = sum(pesos.values())
    if abs(total - 1.0) > tolerancia:
        raise ValueError(f"Os pesos devem somar 1, somaram {total:.6f}")


def compor(
    dimensoes: pd.DataFrame,
    pesos: dict[str, float] | None = None,
) -> pd.Series:
    """Compõe o IAC como média ponderada das dimensões já normalizadas.

    Espera um DataFrame com uma coluna por dimensão de `IAC_DIMENSOES`, todas
    em [0, 1]. Células com qualquer dimensão ausente resultam em NaN — a
    imputação, se houver, é decisão explícita a montante.
    """
    pesos = pesos or IAC_PESOS_BASE
    validar_pesos(pesos)

    faltando = set(IAC_DIMENSOES) - set(dimensoes.columns)
    if faltando:
        raise ValueError(f"Dimensões ausentes no DataFrame: {faltando}")

    ordenadas = dimensoes[list(IAC_DIMENSOES)]
    vetor = pd.Series(pesos)[list(IAC_DIMENSOES)]
    return ordenadas.mul(vetor, axis=1).sum(axis=1, min_count=len(IAC_DIMENSOES))


def avaliar_cenarios_de_peso(
    dimensoes: pd.DataFrame,
    cenarios: dict[str, dict[str, float]] | None = None,
) -> pd.DataFrame:
    """Calcula o IAC sob cada esquema de pesos. Uma coluna por cenário.

    O resultado alimenta `reports/validacoes/sensibilidade.md`: se o ranking de células
    muda muito entre cenários, o índice não sustenta conclusões fortes e isso
    precisa ser dito.
    """
    cenarios = cenarios or IAC_PESOS_CENARIOS
    return pd.DataFrame({nome: compor(dimensoes, pesos) for nome, pesos in cenarios.items()})


def estabilidade_do_ranking(cenarios: pd.DataFrame) -> pd.DataFrame:
    """Correlação de Spearman entre os rankings produzidos por cada cenário.

    Valores altos indicam que a conclusão não depende da escolha de pesos.
    """
    return cenarios.corr(method="spearman")


def classificar_alto_baixo(
    iac: pd.Series,
    corte: float | None = None,
) -> pd.Series:
    """Classifica cada célula em `alto` ou `baixo`. **É a unidade de comunicação do IAC.**

    A posição exata de uma célula no ranking contínuo depende dos pesos, que são
    arbitrários: entre os cenários testados, só 41,4% das células mantêm o
    quartil. A classificação binária mantém-se em 70,4% delas. Reportar
    alto/baixo não é perder resolução — é parar de afirmar a precisão que o
    índice não tem. Ver ADR 0003.

    O corte padrão é a **mediana**, o que torna a classe uma afirmação relativa
    a Curitiba, como toda a normalização do índice. Um corte explícito serve
    para testar a sensibilidade ao limiar.
    """
    corte = iac.median() if corte is None else corte
    classes = pd.Series(
        np.where(iac.isna(), None, np.where(iac >= corte, "alto", "baixo")),
        index=iac.index,
        dtype="object",
    )
    return classes.astype(pd.CategoricalDtype(["baixo", "alto"], ordered=True))


def robustez_da_classificacao(
    cenarios: pd.DataFrame,
    quantil: float = 0.5,
) -> pd.DataFrame:
    """Em quantos cenários de peso cada célula se mantém `alto`.

    É a camada de resultado que acompanha a classificação: uma célula alta nos
    quatro cenários é conclusão firme; uma célula que alterna é o índice dizendo
    "depende do que você valoriza", e dizer isso é honestidade, não omissão.

    **O limiar é um quantil, aplicado cenário por cenário — e não um valor
    absoluto.** Cada esquema de pesos produz sua própria distribuição, e `alto`
    significa "na metade superior *daquele* ranking". Um corte absoluto comum
    misturaria nível com posição: somar uma constante a um cenário não muda o
    ranking dele, mas mudaria a classe de várias células, e a robustez passaria
    a medir escala em vez de ordenação. Medido: com quantil por cenário, 70,4%
    das células de Curitiba são estáveis; com a mediana do `base` imposta a
    todos, o número cai para 36,2% — instabilidade inteiramente fabricada.

    `quantil` existe para testar a sensibilidade ao limiar, que é a decisão
    arbitrária que sobra depois de escolher a classificação binária.

    Colunas: uma `classe_<cenário>` por cenário, `n_alto`, `estavel` e
    `classe` — esta última a do cenário `base`, que é a que se reporta.
    """
    if not 0 < quantil < 1:
        raise ValueError(f"`quantil` deve ficar entre 0 e 1, recebeu {quantil}")

    classes = pd.DataFrame(
        {
            f"classe_{nome}": classificar_alto_baixo(
                cenarios[nome], corte=cenarios[nome].quantile(quantil)
            )
            for nome in cenarios.columns
        },
        index=cenarios.index,
    )

    e_alto = classes.apply(lambda c: c.astype("object") == "alto")
    tem_valor = cenarios.notna().all(axis=1)

    resultado = classes.copy()
    # Tipos anuláveis de propósito. Com `.where`, `estavel` virava coluna de
    # objeto (True/False/None), e `~estavel` em objeto é negação bit a bit de
    # inteiro: devolve −2 e −1, e somar isso dava −6.869 células "instáveis"
    # em vez de 1.191. `boolean` e `Int8` mantêm a ausência sem esse risco.
    resultado["n_alto"] = e_alto.sum(axis=1).where(tem_valor).astype("Int8")
    resultado["estavel"] = (
        resultado["n_alto"].isin([0, len(cenarios.columns)]).astype("boolean").where(tem_valor)
    )

    base = "base" if "base" in cenarios.columns else cenarios.columns[0]
    resultado["classe"] = classes[f"classe_{base}"]
    return resultado


def resumo_da_robustez(robustez: pd.DataFrame) -> pd.DataFrame:
    """Tabela de uma linha por nível de concordância, para o relatório."""
    n = int(robustez["n_alto"].notna().sum())
    contagem = robustez["n_alto"].value_counts().sort_index()
    total_cenarios = int(robustez["n_alto"].max())

    linhas = []
    for valor, quantidade in contagem.items():
        valor = int(valor)
        if valor == 0:
            rotulo = "baixo em todos os cenários"
        elif valor == total_cenarios:
            rotulo = "alto em todos os cenários"
        else:
            rotulo = f"alto em {valor} de {total_cenarios} — depende do peso"
        linhas.append({"concordância": rotulo, "células": int(quantidade), "%": 100 * quantidade / n})

    return pd.DataFrame(linhas)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raise NotImplementedError(
        "Requer as dimensões calculadas a partir de OSM, IPPUC e DEM. Ver README §6, Fase 1."
    )


if __name__ == "__main__":
    main()
