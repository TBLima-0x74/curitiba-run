"""Cálculo das seis dimensões do Índice de Adequação à Corrida.

Cada função recebe camadas brutas e a malha, e devolve uma `Series` indexada
por `h3` com o **valor bruto** da dimensão — sem normalizar. A normalização e a
composição ficam em `suitability_index`, para que o valor bruto continue
disponível e interpretável no relatório ("3,2 km de calçada por km²" comunica;
"0,71 normalizado" não).

Todas as operações métricas acontecem em EPSG:31982 (SIRGAS 2000 / UTM 22S).
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# --------------------------------------------------------------------- helpers


def _alinhar_crs(camada: gpd.GeoDataFrame, malha: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Garante que a camada esteja no CRS métrico da malha."""
    if camada.crs is None:
        raise ValueError("Camada sem CRS definido — impossível alinhar com a malha")
    return camada.to_crs(malha.crs) if camada.crs != malha.crs else camada


def _validar_geometrias(camada: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repara polígonos inválidos antes de qualquer união ou interseção.

    Polígonos do OSM com auto-interseção são comuns — um parque mapeado por
    várias pessoas ao longo dos anos acaba assim. Uma única geometria inválida
    derruba `union_all` com `TopologyException`, e o erro não diz qual feição
    causou. Reparar antes custa pouco e evita uma falha opaca no meio do
    pipeline.
    """
    invalidas = ~camada.geometry.is_valid
    n = int(invalidas.sum())
    if n:
        log.info("  %d geometria(s) inválida(s) reparada(s)", n)
        camada = camada.copy()
        camada.loc[invalidas, camada.geometry.name] = camada.loc[invalidas].geometry.make_valid()
        camada = camada[camada.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    return camada


def _serie_por_celula(malha: gpd.GeoDataFrame, valores: pd.Series, preencher: float = 0.0) -> pd.Series:
    """Reindexa um agregado parcial para todas as células da malha."""
    return valores.reindex(malha["h3"].to_numpy()).fillna(preencher)


def recortar_linhas(
    linhas: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    colunas_peso: tuple[str, ...] = (),
) -> gpd.GeoDataFrame:
    """Recorta as linhas pelos limites das células — **uma única vez**.

    É de longe a operação mais cara do pipeline: a rede caminhável de Curitiba
    tem ~185 mil arestas e a malha r9 ~4,5 mil células. Três dimensões do IAC
    dependem desse recorte e duas delas o usam duas vezes (total e ponderado),
    o que daria cinco recortes idênticos se cada função fizesse o seu.

    Calcule aqui e repasse o resultado pelo parâmetro `pedacos`.

    Devolve um frame com `h3`, `_m` (metros dentro da célula) e as colunas de
    peso solicitadas.
    """
    linhas = _alinhar_crs(linhas, malha)

    faltando = [c for c in colunas_peso if c not in linhas.columns]
    if faltando:
        raise ValueError(f"Colunas de peso ausentes nas linhas: {faltando}")

    pedacos = gpd.overlay(
        linhas[["geometry", *colunas_peso]],
        malha[["h3", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    pedacos["_m"] = pedacos.length if not pedacos.empty else pd.Series(dtype=float)
    return pedacos


def comprimento_por_celula(
    linhas: gpd.GeoDataFrame | None,
    malha: gpd.GeoDataFrame,
    coluna_peso: str | None = None,
    pedacos: gpd.GeoDataFrame | None = None,
) -> pd.Series:
    """Extensão de linha (em metros) dentro de cada célula.

    Um trecho que atravessa três hexágonos contribui para os três na proporção
    correta. `coluna_peso` pondera a extensão por uma coluna booleana ou
    numérica — "extensão em vias de baixo tráfego", por exemplo.

    Passe `pedacos` (saída de `recortar_linhas`) para reaproveitar um recorte
    já feito em vez de refazê-lo.
    """
    if pedacos is None:
        if linhas is None or linhas.empty:
            return _serie_por_celula(malha, pd.Series(dtype=float))
        pedacos = recortar_linhas(linhas, malha, (coluna_peso,) if coluna_peso else ())

    if pedacos.empty:
        return _serie_por_celula(malha, pd.Series(dtype=float))

    metros = pedacos["_m"]
    if coluna_peso:
        if coluna_peso not in pedacos.columns:
            raise ValueError(
                f"Coluna de peso {coluna_peso!r} ausente no recorte. Inclua-a em "
                "`colunas_peso` ao chamar `recortar_linhas`."
            )
        metros = metros * pedacos[coluna_peso].astype(float)

    return _serie_por_celula(malha, metros.groupby(pedacos["h3"]).sum())


def area_por_celula(poligonos: gpd.GeoDataFrame, malha: gpd.GeoDataFrame) -> pd.Series:
    """Área (m²) de polígonos dentro de cada célula, sem dupla contagem.

    Os polígonos são dissolvidos antes do recorte: dois parques sobrepostos —
    situação comum quando OSM e IPPUC mapeiam o mesmo espaço — contam uma vez.
    """
    if poligonos.empty:
        return _serie_por_celula(malha, pd.Series(dtype=float))

    poligonos = _validar_geometrias(_alinhar_crs(poligonos, malha))
    unido = gpd.GeoDataFrame(geometry=[poligonos.geometry.union_all()], crs=malha.crs)

    pedacos = gpd.overlay(unido, malha[["h3", "geometry"]], how="intersection", keep_geom_type=True)
    if pedacos.empty:
        return _serie_por_celula(malha, pd.Series(dtype=float))

    pedacos["_a"] = pedacos.area
    return _serie_por_celula(malha, pedacos.groupby("h3")["_a"].sum())


def contagem_por_celula(pontos: gpd.GeoDataFrame, malha: gpd.GeoDataFrame) -> pd.Series:
    """Número de pontos dentro de cada célula."""
    if pontos.empty:
        return _serie_por_celula(malha, pd.Series(dtype=float))

    pontos = _alinhar_crs(pontos, malha)
    juncao = gpd.sjoin(pontos[["geometry"]], malha[["h3", "geometry"]], how="inner", predicate="within")
    return _serie_por_celula(malha, juncao.groupby("h3").size().astype(float))


def media_zonal(
    raster_path,
    malha: gpd.GeoDataFrame,
    banda: int = 1,
) -> pd.Series:
    """Média de um raster dentro de cada célula.

    Rasteriza os índices das células uma única vez e agrega com `bincount`, o
    que evita abrir uma janela por célula — a diferença é de minutos para
    segundos numa malha de milhares de hexágonos.
    """
    import rasterio
    from rasterio.features import rasterize

    with rasterio.open(raster_path) as src:
        dados = src.read(banda, masked=True)
        malha_r = malha.to_crs(src.crs)

        formas = ((geom, i + 1) for i, geom in enumerate(malha_r.geometry))
        zonas = rasterize(
            formas,
            out_shape=(src.height, src.width),
            transform=src.transform,
            fill=0,
            dtype="int32",
        )

    valido = (zonas > 0) & ~np.ma.getmaskarray(dados)
    indices = zonas[valido]
    valores = np.asarray(dados)[valido].astype(float)

    soma = np.bincount(indices, weights=valores, minlength=len(malha) + 1)[1:]
    n = np.bincount(indices, minlength=len(malha) + 1)[1:]

    with np.errstate(invalid="ignore", divide="ignore"):
        media = np.where(n > 0, soma / n, np.nan)

    return pd.Series(media, index=malha["h3"].to_numpy())


def suavizar_por_vizinhanca(valores: pd.Series, k: int = 1, peso_vizinho: float = 0.5) -> pd.Series:
    """Mistura o valor da célula com a média dos vizinhos no anel k.

    Um parque grande beneficia quem mora ao lado dele, não só quem está dentro
    do hexágono. `peso_vizinho=0` desliga a suavização.
    """
    import h3

    if peso_vizinho == 0:
        return valores

    mapa = valores.to_dict()
    suavizado = {}

    for celula, valor in mapa.items():
        vizinhos = [v for v in h3.grid_disk(celula, k) if v != celula and v in mapa]
        media_vizinhos = np.mean([mapa[v] for v in vizinhos]) if vizinhos else valor
        suavizado[celula] = (1 - peso_vizinho) * valor + peso_vizinho * media_vizinhos

    return pd.Series(suavizado).reindex(valores.index)


# ------------------------------------------------------------------ dimensões


def superficie_caminhavel(
    arestas: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    pedacos: gpd.GeoDataFrame | None = None,
) -> pd.Series:
    """Densidade de via caminhável, em km por km² de célula.

    Mede quanto percurso existe. Uma célula com 12 km de calçada oferece mais
    opção de rota que uma com 2 km, ainda que ambas tenham "calçada".
    """
    metros = comprimento_por_celula(arestas, malha, pedacos=pedacos)
    area_km2 = malha.set_index("h3")["area_km2"]
    return (metros / 1000) / area_km2.reindex(metros.index)


def espaco_dedicado(
    espacos: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    peso_vizinho: float = 0.5,
) -> pd.Series:
    """Fração da célula ocupada por parque, praça, pista ou campo.

    Suavizada pela vizinhança: estar ao lado do Barigui conta, ainda que o
    hexágono do endereço não toque o parque.
    """
    area_m2 = area_por_celula(espacos, malha)
    fracao = area_m2 / (malha.set_index("h3")["area_km2"].reindex(area_m2.index) * 1e6)
    return suavizar_por_vizinhanca(fracao.clip(0, 1), peso_vizinho=peso_vizinho)


def transito_tranquilo(
    arestas: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    coluna_baixo_trafego: str = "baixo_trafego",
    pedacos: gpd.GeoDataFrame | None = None,
) -> pd.Series:
    """Proporção da extensão caminhável que corre em via de baixo tráfego.

    É uma razão, não uma densidade: mede a *qualidade* do que existe. Uma
    célula cortada por uma via expressa e nada mais pontua baixo mesmo tendo
    muita extensão.

    Células sem nenhuma via recebem NaN — ausência de via não é "via ruim", e
    tratar como zero puniria indevidamente áreas não urbanizadas.
    """
    fonte = pedacos if pedacos is not None else arestas
    if coluna_baixo_trafego not in fonte.columns:
        raise ValueError(
            f"Coluna {coluna_baixo_trafego!r} ausente. Rode "
            "`ingestion.osm.classificar_hierarquia_viaria` antes."
        )

    total = comprimento_por_celula(arestas, malha, pedacos=pedacos)
    seguro = comprimento_por_celula(
        arestas, malha, coluna_peso=coluna_baixo_trafego, pedacos=pedacos
    )

    with np.errstate(invalid="ignore", divide="ignore"):
        razao = seguro / total

    return razao.where(total > 0)


def continuidade(nos: gpd.GeoDataFrame, malha: gpd.GeoDataFrame, grau_minimo: int = 3) -> pd.Series:
    """Densidade de interseções por km² — proxy de conectividade da malha.

    Muitas interseções significam quarteirões curtos e muitas rotas possíveis.
    Poucas indicam malha arbórea, condomínio fechado ou fundo de vale: caminhos
    que terminam sem saída e obrigam a voltar pelo mesmo lugar.
    """
    if "grau" in nos.columns:
        nos = nos[nos["grau"] >= grau_minimo]

    contagem = contagem_por_celula(nos, malha)
    area_km2 = malha.set_index("h3")["area_km2"]
    return contagem / area_km2.reindex(contagem.index)


def densidade_malha(
    arestas: gpd.GeoDataFrame,
    nos: gpd.GeoDataFrame,
    malha: gpd.GeoDataFrame,
    pedacos: gpd.GeoDataFrame | None = None,
) -> pd.Series:
    """Densidade da malha caminhável: extensão e interseções, fundidas.

    `superficie_caminhavel` (km/km²) e `continuidade` (interseções/km²) mediram
    a mesma coisa na primeira rodada — correlação de Spearman de 0,95. Em
    qualquer malha viária as duas são quase proporcionais, e mantê-las separadas
    dava 40% do peso do índice a um único construto contado duas vezes.

    As duas componentes continuam disponíveis em separado para o relatório; o
    que muda é que elas entram no índice como **uma** dimensão.

    Devolve já em escala 0 a 1, porque km/km² e interseções/km² não podem ser
    somados em unidade bruta. A normalização posterior do pipeline é monotônica
    e não altera o ranking.
    """
    from curitiba_run.features.suitability_index import normalizar

    km = superficie_caminhavel(arestas, malha, pedacos=pedacos)
    inter = continuidade(nos, malha)
    return (normalizar(km) + normalizar(inter)) / 2


def declividade(malha: gpd.GeoDataFrame, declividade_raster) -> pd.Series:
    """Declividade média da célula, em graus.

    Substitui a antiga dimensão `conforto`, que combinava declividade com
    cobertura vegetal. A cobertura vegetal do OSM mapeia onde **não** há cidade,
    então ela acabava medindo ausência de urbanização — correlação negativa com
    a malha caminhável e com o próprio índice. A declividade, essa sim, é um
    determinante real de onde se consegue correr.

    Devolve o valor **bruto em graus**: "mais é pior", e a inversão acontece na
    normalização, que conhece `IAC_DIMENSOES_INVERTIDAS`. Guardar graus aqui
    mantém o número interpretável no relatório — "média de 4,2°" comunica.
    """
    if declividade_raster is None:
        raise ValueError(
            "A dimensão de declividade exige um raster. Rode "
            "`ingestion.geocuritiba.baixar_mdt` para obter o modelo digital de "
            "terreno do IPPUC (0,5 m) ou aponte outro DEM."
        )
    return media_zonal(declividade_raster, malha)


def iluminacao(
    malha: gpd.GeoDataFrame,
    pontos_luz: gpd.GeoDataFrame | None = None,
    arestas: gpd.GeoDataFrame | None = None,
    coluna_iluminada: str = "iluminada",
    peso_pontos: float = 0.5,
    pedacos: gpd.GeoDataFrame | None = None,
    usar_lit: bool = False,
) -> pd.Series:
    """Iluminação pública: postes oficiais **por km de via**.

    A medida é uma razão, não uma densidade, e isso é deliberado. Normalizar
    postes por área (postes/km²) mede, na prática, densidade de rua: poste segue
    via, então bairro com muita rua tem muito poste. Com normalização por área
    esta dimensão correlacionou 0,81 com `densidade_malha`. Dividir por
    quilômetro de via responde à pergunta certa: **quão iluminada é a rua que
    existe.**

    `usar_lit` acrescenta a fração de via com `lit=yes` no OSM como segunda
    componente. **Desligado por padrão**, e a razão importa: `lit` está ausente
    em 66% das células de Curitiba, e ausente no OSM significa "ninguém mapeou",
    não "não há iluminação". Como ausência entrava como zero e a componente
    valia metade do peso, ela rebaixava a dimensão por construção — células com
    densidade de poste no quartil superior terminavam com nota mediana de 0,34,
    e um terço delas abaixo de 0,3.

    O `lit` também é enviesado na direção errada: quem mapeia iluminação no OSM
    mapeia avenida, então a componente correlacionava −0,30 com
    `transito_tranquilo`. Desligá-la derruba essa correlação para −0,07 e a
    correlação com `densidade_malha` de 0,31 para 0,08.

    O parâmetro fica disponível porque o dado existe e pode melhorar; a decisão
    de não usá-lo é que precisa ser explícita.

    Células sem via recebem valor ausente, como em `transito_tranquilo`: não há
    como avaliar a iluminação de uma rua que não existe.
    """
    componentes: list[pd.Series] = []
    pesos: list[float] = []

    fonte_vias = pedacos if pedacos is not None else arestas
    via_km = None
    if fonte_vias is not None:
        via_km = comprimento_por_celula(arestas, malha, pedacos=pedacos) / 1000

    if pontos_luz is not None and not pontos_luz.empty:
        if via_km is None:
            raise ValueError(
                "A densidade de postes é normalizada por km de via, então "
                "`arestas` (ou `pedacos`) é obrigatória junto com `pontos_luz`."
            )
        contagem = contagem_por_celula(pontos_luz, malha)
        with np.errstate(invalid="ignore", divide="ignore"):
            postes_por_km = contagem / via_km
        componentes.append(postes_por_km.where(via_km > 0))
        pesos.append(peso_pontos if usar_lit else 1.0)

    if usar_lit and fonte_vias is not None and coluna_iluminada in fonte_vias.columns:
        iluminada = comprimento_por_celula(
            arestas, malha, coluna_peso=coluna_iluminada, pedacos=pedacos
        ) / 1000
        with np.errstate(invalid="ignore", divide="ignore"):
            cobertura = iluminada / via_km
        componentes.append(cobertura.where(via_km > 0))
        pesos.append(1 - peso_pontos)

    if not componentes:
        raise ValueError(
            "Informe `pontos_luz`. Sem postes não há como medir iluminação — "
            "a cobertura `lit` do OSM sozinha não serve (ver docstring)."
        )

    # As componentes têm unidades diferentes — postes/km e proporção — então
    # cada uma vai a [0, 1] antes da média.
    from curitiba_run.features.suitability_index import normalizar

    pesos_norm = np.array(pesos) / sum(pesos)
    return sum(normalizar(c) * p for c, p in zip(componentes, pesos_norm, strict=True))


# ---------------------------------------------------------------- orquestração


def calcular_todas(
    malha: gpd.GeoDataFrame,
    arestas: gpd.GeoDataFrame,
    nos: gpd.GeoDataFrame,
    espacos: gpd.GeoDataFrame,
    declividade_raster,
    pontos_luz: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Calcula as cinco dimensões brutas, uma coluna cada, indexadas por `h3`.

    `declividade` sai em graus e `densidade_malha` já em 0 a 1; as demais em
    suas unidades naturais. A normalização — com a inversão da declividade —
    fica para `suitability_index.normalizar_dimensoes`.
    """
    log.info("Calculando dimensões do IAC para %d células", len(malha))

    pesos = tuple(c for c in ("baixo_trafego", "iluminada") if c in arestas.columns)
    log.info("  Recortando %d arestas pela malha (etapa mais cara, só uma vez)...", len(arestas))
    pedacos = recortar_linhas(arestas, malha, pesos)
    log.info("  %d segmentos após o recorte", len(pedacos))

    dims = pd.DataFrame(index=pd.Index(malha["h3"].to_numpy(), name="h3"))
    dims["densidade_malha"] = densidade_malha(arestas, nos, malha, pedacos=pedacos)
    dims["espaco_dedicado"] = espaco_dedicado(espacos, malha)
    dims["transito_tranquilo"] = transito_tranquilo(arestas, malha, pedacos=pedacos)
    dims["declividade"] = declividade(malha, declividade_raster)
    dims["iluminacao"] = iluminacao(malha, pontos_luz, arestas, pedacos=pedacos)

    for coluna in dims.columns:
        ausentes = dims[coluna].isna().sum()
        if ausentes:
            log.info("  %s: %d células sem valor (%.1f%%)", coluna, ausentes, 100 * ausentes / len(dims))

    return dims
