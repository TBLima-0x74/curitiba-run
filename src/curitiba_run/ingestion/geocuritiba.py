"""Camadas do GeoCuritiba (IPPUC) pela API REST do ArcGIS.

O portal do IPPUC expõe um ArcGIS Server público em
`https://geocuritiba.ippuc.org.br/server/rest/services`. Isso resolve de uma vez
três lacunas que o OSM não cobre bem:

- **Postes** — inventário oficial, contra 523 pontos no OSM. É a dimensão de
  iluminação deixando de ser ruído.
- **MDT 2019** — modelo digital de terreno a 0,5 m, de onde sai a declividade.
  Muito melhor que os 30 m de um DEM global.
- **Áreas verdes e ciclovias oficiais** — a referência contra a qual a
  completude do OSM é medida (risco R1).

⚠️  O serviço é público, mas é infraestrutura de terceiro: as consultas são
    paginadas e com pausa entre páginas. Nada aqui deve ser rodado em laço.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import geopandas as gpd

from curitiba_run.config import CRS_METRICO, INTERIM, RAW

log = logging.getLogger(__name__)

BASE = "https://geocuritiba.ippuc.org.br/server/rest/services"
DESTINO = RAW / "ippuc"

# Camadas confirmadas no catálogo do GeoCuritiba.
CAMADA_POSTES = f"{BASE}/GeoCuritiba/Publico_Interno_GeoCuritiba_BaseCartografica_para_MC/MapServer/61"
SERVICO_MDT = f"{BASE}/GeoCuritiba/MDT_2019/ImageServer"
SERVICO_UNIDADES_CONSERVACAO = (
    f"{BASE}/GeoCuritiba/Publico_Sistema_Municipal_de_Unidades_de_Conservacao/FeatureServer"
)
SERVICO_CICLOVIA = f"{BASE}/GeoCuritiba/CICLOVIA_dashboard/FeatureServer"

# Domínio do campo `tipoposte`, lido dos metadados da camada 61.
TIPO_POSTE = {
    0: "Desconhecido",
    2: "Iluminação",
    3: "Ornamental",
    4: "Rede elétrica",
    5: "Sinalização",
    99: "Outros",
    9999: "A ser preenchido",
}

# Só estes iluminam. `Rede elétrica` é distribuição de energia: um poste de
# rede não ilumina nada, e contá-lo inflaria a dimensão em bairros onde a
# distribuição é aérea.
TIPOS_POSTE_ILUMINACAO = (2, 3)

# A camada não traz potência, luminária, carga nem altura — só função e
# material. Ver `equivalencia_entre_tipos_de_poste` para o porquê de não haver
# ponderação por intensidade.
CAMPOS_AUSENTES_NA_CAMADA = ("potencia", "luminaria", "lampada", "carga", "altura")

# O serviço de unidades de conservação tem uma camada por categoria.
CAMADAS_UNIDADES_CONSERVACAO = {
    1: "Estação Ecológica",
    2: "Parque Natural Municipal",
    3: "Parque Linear",
    4: "Bosque Municipal",
    5: "Bosque de Conservação da Biodiversidade Urbana",
    6: "Refúgio da Vida Silvestre",
    7: "Reserva Particular do Patrimônio Natural Municipal",
    8: "Específicas",
    10: "Área de Proteção Ambiental",
    11: "Área de Relevante Interesse Ecológico",
}

# Espaço público aberto, onde de fato se corre. Ficam de fora:
#   7  RPPNM  — reserva em propriedade **privada**, sem acesso público
#   10 APA    — zoneamento ambiental: as duas de Curitiba somam 197 km², quase
#               metade do município. Não são parque, são regra de uso do solo
#   1, 6, 11  — acesso restrito ou misto (científico, proteção integral)
#   8  Específicas — categoria heterogênea (jardim botânico, zoológico)
CAMADAS_PUBLICAS = (2, 3, 4, 5)

# Siglas correspondentes, para filtrar um conjunto já baixado.
SIGLAS_PUBLICAS = frozenset({"PQ", "BQ", "BCBU"})

PAGINA = 2000          # feições por requisição
PAUSA_SEGUNDOS = 0.5   # entre páginas, por educação com o servidor
TIMEOUT = 180


def _get_json(url: str, params: dict) -> dict:
    alvo = f"{url}?{urlencode(params)}"
    with urlopen(alvo, timeout=TIMEOUT) as resposta:  # noqa: S310 — host fixo, https
        return json.loads(resposta.read())


def consultar_camada(
    url_camada: str,
    where: str = "1=1",
    campos: str = "*",
    pagina: int = PAGINA,
) -> gpd.GeoDataFrame:
    """Baixa uma camada inteira de um MapServer/FeatureServer, paginando.

    O ArcGIS limita quantas feições devolve por requisição (tipicamente 1000 ou
    2000) e sinaliza o corte com `exceededTransferLimit`. Ignorar isso é o erro
    clássico: a camada parece ter baixado e vem truncada.
    """
    partes: list[gpd.GeoDataFrame] = []
    offset = 0

    while True:
        dados = _get_json(
            f"{url_camada}/query",
            {
                "where": where,
                "outFields": campos,
                "returnGeometry": "true",
                "outSR": "31982",
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": pagina,
            },
        )

        feicoes = dados.get("features", [])
        if not feicoes:
            break

        partes.append(gpd.GeoDataFrame.from_features(feicoes, crs=CRS_METRICO))
        log.info("  %d feições (offset %d)", len(feicoes), offset)

        if len(feicoes) < pagina:
            break

        offset += pagina
        time.sleep(PAUSA_SEGUNDOS)

    if not partes:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRICO)

    import pandas as pd

    return gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=CRS_METRICO)


# ----------------------------------------------------------------- postes


def baixar_postes(destino: Path = DESTINO) -> gpd.GeoDataFrame:
    """Inventário completo de postes de Curitiba, sem filtrar.

    A camada cobre postes em geral. O recorte para iluminação fica em
    `filtrar_postes_de_iluminacao`, aplicado na hora de usar — assim o dado
    bruto permanece completo e o filtro fica visível no pipeline.
    """
    log.info("Baixando postes do GeoCuritiba")
    postes = consultar_camada(CAMADA_POSTES, campos="objectid,tipoposte,matconstr")

    if "tipoposte" in postes.columns:
        contagem = postes["tipoposte"].map(TIPO_POSTE).value_counts().to_dict()
        log.info("  por tipo: %s", contagem)

    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / "postes.parquet"
    postes.to_parquet(caminho)
    log.info("Postes: %d feições -> %s", len(postes), caminho)
    return postes


def filtrar_postes_de_iluminacao(postes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Mantém apenas os postes que de fato iluminam.

    `tipoposte` é um domínio codificado: 2 é iluminação, 3 ornamental, 4 rede
    elétrica. Postes de rede elétrica não iluminam — contá-los faria a dimensão
    premiar bairros com distribuição aérea de energia, que não é o que se quer
    medir.
    """
    if "tipoposte" not in postes.columns:
        raise ValueError("Coluna `tipoposte` ausente — rebaixe a camada com esse campo")

    filtrados = postes[postes["tipoposte"].isin(TIPOS_POSTE_ILUMINACAO)]
    log.info(
        "Postes de iluminação: %d de %d (%.1f%%)",
        len(filtrados), len(postes), 100 * len(filtrados) / max(len(postes), 1),
    )
    return filtrados


def equivalencia_entre_tipos_de_poste() -> str:
    """Por que os tipos de poste não são ponderados entre si.

    A pergunta natural é se um poste de um tipo "vale" mais que outro — por
    área iluminada ou por potência. A resposta, para **esta** camada, é não:

    - `tipoposte` é uma classificação **funcional** (iluminação, rede elétrica,
      sinalização), não uma escala de intensidade. Não há ordem entre as
      categorias.
    - A camada **não traz** potência, luminária, lâmpada, carga nem altura.
      Sem altura e sem fluxo luminoso, a área iluminada por poste não é
      derivável.
    - `matconstr` é material de construção (concreto, metal, madeira), que não
      guarda relação estável com intensidade luminosa.

    Qualquer peso entre tipos seria inventado. A decisão correta é binária:
    manter os que iluminam e descartar os que não iluminam.
    """
    return equivalencia_entre_tipos_de_poste.__doc__


# -------------------------------------------------------------------- MDT


def baixar_mdt(
    resolucao_m: float = 10.0,
    destino: Path = DESTINO,
    lado_tile_px: int = 2000,
) -> Path:
    """Baixa o modelo digital de terreno em mosaico, reamostrado.

    O MDT nativo tem 0,5 m, o que daria 46.000 × 70.800 pixels para o município
    inteiro — centenas de gigabytes sem necessidade alguma. Para declividade
    média em células de 0,1 km², 10 m é mais que suficiente.

    O `exportImage` do ArcGIS tem teto de tamanho por requisição, então a área
    é dividida em tiles e remontada localmente.
    """
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    info = _get_json(SERVICO_MDT, {"f": "pjson"})
    ext = info["extent"]
    xmin, ymin, xmax, ymax = ext["xmin"], ext["ymin"], ext["xmax"], ext["ymax"]

    largura = int((xmax - xmin) / resolucao_m)
    altura = int((ymax - ymin) / resolucao_m)
    log.info("MDT: %d x %d px a %.1f m", largura, altura, resolucao_m)

    mosaico = np.full((altura, largura), np.nan, dtype="float32")
    passo = lado_tile_px

    for linha in range(0, altura, passo):
        for coluna in range(0, largura, passo):
            h = min(passo, altura - linha)
            w = min(passo, largura - coluna)

            tile_xmin = xmin + coluna * resolucao_m
            tile_xmax = tile_xmin + w * resolucao_m
            tile_ymax = ymax - linha * resolucao_m
            tile_ymin = tile_ymax - h * resolucao_m

            url = f"{SERVICO_MDT}/exportImage?" + urlencode(
                {
                    "bbox": f"{tile_xmin},{tile_ymin},{tile_xmax},{tile_ymax}",
                    "bboxSR": "31982",
                    "imageSR": "31982",
                    "size": f"{w},{h}",
                    "format": "tiff",
                    "pixelType": "F32",
                    "interpolation": "RSP_BilinearInterpolation",
                    "f": "image",
                }
            )
            with urlopen(url, timeout=TIMEOUT) as resposta:  # noqa: S310
                bruto = resposta.read()

            caminho_tmp = INTERIM / "_tile.tif"
            caminho_tmp.parent.mkdir(parents=True, exist_ok=True)
            caminho_tmp.write_bytes(bruto)

            with rasterio.open(caminho_tmp) as src:
                mosaico[linha : linha + h, coluna : coluna + w] = src.read(1)

            log.info("  tile linha %d coluna %d", linha, coluna)
            time.sleep(PAUSA_SEGUNDOS)

    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / "mdt.tif"
    perfil = {
        "driver": "GTiff",
        "height": altura,
        "width": largura,
        "count": 1,
        "dtype": "float32",
        "crs": CRS_METRICO,
        "transform": from_origin(xmin, ymax, resolucao_m, resolucao_m),
        "nodata": float("nan"),
        "compress": "deflate",
    }
    with rasterio.open(caminho, "w", **perfil) as dst:
        dst.write(mosaico, 1)

    log.info("MDT salvo em %s", caminho)
    return caminho


def derivar_declividade(mdt: Path, destino: Path | None = None) -> Path:
    """Converte o MDT em raster de declividade, em graus.

    Usa o gradiente de Horn simplificado: a inclinação em cada pixel é o
    arco-tangente da magnitude do gradiente da superfície. Como o raster está em
    metros nos dois eixos, a conta é direta.
    """
    import numpy as np
    import rasterio

    destino = destino or mdt.with_name("declividade.tif")

    with rasterio.open(mdt) as src:
        z = src.read(1).astype("float64")
        perfil = src.profile
        res_x, res_y = abs(src.transform.a), abs(src.transform.e)

    dz_dy, dz_dx = np.gradient(z, res_y, res_x)
    graus = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))).astype("float32")

    perfil.update(dtype="float32", count=1, compress="deflate")
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(graus, 1)

    log.info(
        "Declividade: %s (mediana %.2f°, p95 %.2f°)",
        destino,
        float(np.nanmedian(graus)),
        float(np.nanpercentile(graus, 95)),
    )
    return destino


# --------------------------------------------------- camadas de validação


def baixar_areas_verdes(
    destino: Path = DESTINO,
    apenas_publicas: bool = False,
) -> gpd.GeoDataFrame:
    """Unidades de conservação municipais, uma camada por categoria.

    Por padrão baixa todas, porque a comparação com o OSM (risco R1) precisa do
    conjunto completo para saber o que o OSM mapeia e o que não mapeia.
    `apenas_publicas=True` restringe às categorias de acesso público aberto.
    """
    import pandas as pd

    camadas = _get_json(SERVICO_UNIDADES_CONSERVACAO, {"f": "pjson"})["layers"]
    ids = [c["id"] for c in camadas]
    if apenas_publicas:
        ids = [i for i in ids if i in CAMADAS_PUBLICAS]

    log.info("Unidades de conservação: %d camadas", len(ids))

    partes = []
    for i in ids:
        nome = CAMADAS_UNIDADES_CONSERVACAO.get(i, f"camada {i}")
        log.info("  %s", nome)
        parte = consultar_camada(f"{SERVICO_UNIDADES_CONSERVACAO}/{i}")
        if not parte.empty:
            parte["camada_id"] = i
            parte["categoria"] = nome
            partes.append(parte)

    tudo = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=CRS_METRICO)

    destino.mkdir(parents=True, exist_ok=True)
    nome_arquivo = "areas_verdes_publicas" if apenas_publicas else "areas_verdes"
    tudo.to_parquet(destino / f"{nome_arquivo}.parquet")
    log.info("%s: %d feições", nome_arquivo, len(tudo))
    return tudo


def filtrar_areas_publicas(areas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Mantém só espaço público aberto, onde de fato se corre.

    Descarta, por ordem de impacto:

    - **RPPNM** (67 unidades) — Reserva Particular do Patrimônio Natural
      Municipal. São **propriedade privada**: o município concede benefício
      fiscal em troca da preservação, e não há acesso público.
    - **APA** (2 unidades, 197 km²) — zoneamento ambiental cobrindo quase
      metade do município. Incluir isso faria o índice declarar que meia cidade
      é parque.
    - **ESEC, RVS, ARIE** — acesso restrito ou misto.

    Funciona tanto pela coluna `camada_id` quanto pela `sigla`, conforme o
    conjunto tenha vindo de `baixar_areas_verdes` ou de uma consulta plana.
    """
    if "camada_id" in areas.columns:
        publicas = areas[areas["camada_id"].isin(CAMADAS_PUBLICAS)]
    elif "sigla" in areas.columns:
        publicas = areas[areas["sigla"].isin(SIGLAS_PUBLICAS)]
    else:
        raise ValueError("Sem `camada_id` nem `sigla` — impossível separar público de privado")

    area_antes = areas.area.sum() / 1e6
    area_depois = publicas.area.sum() / 1e6
    log.info(
        "Áreas públicas: %d de %d unidades | %.1f km² de %.1f km²",
        len(publicas), len(areas), area_depois, area_antes,
    )
    return publicas


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    baixar_postes()
    baixar_areas_verdes()  # completas: a validação do R1 precisa do conjunto todo
    derivar_declividade(baixar_mdt())


if __name__ == "__main__":
    main()
