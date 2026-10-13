"""Mapas de cada índice verificado, fase a fase.

Uso, a partir da raiz do repositório:

    python scripts/mapas_evolucao.py

Gera um PNG por mapa em `reports/figures/evolucao/`, com o prefixo da fase,
para acompanhar como a análise evolui. Um mapa cujo insumo ainda não existe é
pulado com aviso — rodar de novo depois de cada fase acrescenta os novos.

Para acrescentar o mapa de uma fase futura, basta uma entrada em `MAPAS`. Os
mapas da SESP-PR e da comparação GM × SESP aparecem sozinhos quando a base
chegar e `scripts/fase2_ocorrencias.py` for rodado.

Cores (validadas com o validador de paleta do projeto de visualização):
  - adequação (Fase 1): uma rampa de azul, claro → escuro = pior → melhor;
  - risco (Fase 2): uma rampa de laranja, claro → escuro = menor → maior;
  - robustez entre cenários: divergente vermelho ↔ cinza ↔ azul;
  - sem dado: cinza com hachura, para não se confundir com o valor mais baixo;
  - suprimido (menos de 5 ocorrências, ADR 0007): o mesmo cinza, hachura na
    direção oposta — não há valor, por proteção, e não por falta de dado.
Os mapas de ocorrências já saem com a supressão aplicada. Os PNGs ficam fora
do Git pelo tamanho; os da SESP só podem sair do projeto se o ADR 0006 permitir.
"""

from __future__ import annotations

import logging
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from curitiba_run.config import (  # noqa: E402
    CRS_METRICO,
    FIGURES,
    H3_RESOLUCAO,
    LIMIAR_SUPRESSAO,
    PROCESSED,
    RAW,
)
from curitiba_run.processing import supressao  # noqa: E402

log = logging.getLogger("mapas")
DESTINO = FIGURES / "evolucao"

# ------------------------------------------------------------------ paleta
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_FRACA = "#898781"
CONTORNO = "#c3c2b7"
LINHA_FINA = "#e1e0d9"
SEM_DADO = "#e1e0d9"

AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
LARANJA = ["#fde6dc", "#f8c4ab", "#f2a07c", "#eb6834", "#c8501f", "#a13b10", "#6b2408"]

RAMPAS = {
    "azul": LinearSegmentedColormap.from_list("adequacao", AZUL),
    "laranja": LinearSegmentedColormap.from_list("risco", LARANJA),
    # Divergente com meio cinza: 0,5 = as duas fontes concordam.
    "divergente": LinearSegmentedColormap.from_list(
        "gm_sesp", ["#184f95", "#86b6ef", "#f0efec", "#ef9594", "#b52f2e"]
    ),
}

# Classes binárias: dois passos da rampa que passam no teste ordinal.
CLASSES_AZUL = {"baixo": "#86b6ef", "alto": "#184f95"}
CLASSES_LARANJA = {"baixo": "#f2a07c", "alto": "#a13b10"}

# Robustez: 0 = baixo em todos os cenários … 4 = alto em todos. O meio é cinza,
# porque "depende do peso" não é nem bom nem ruim.
ROBUSTEZ = ["#b52f2e", "#ef9594", "#f0efec", "#86b6ef", "#184f95"]
ROTULOS_ROBUSTEZ = [
    "baixo em todos os cenários",
    "alto em 1 de 4",
    "alto em 2 de 4",
    "alto em 3 de 4",
    "alto em todos os cenários",
]


# ------------------------------------------------------------------ dados


def _malha() -> gpd.GeoDataFrame:
    return gpd.read_parquet(PROCESSED / f"malha_h3_r{H3_RESOLUCAO}.parquet")[["h3", "geometry"]].to_crs(
        CRS_METRICO
    )


def _com_h3(df: pd.DataFrame) -> pd.DataFrame:
    return df if "h3" in df.columns else df.reset_index().rename(columns={"index": "h3"})


def carregar_fase1() -> gpd.GeoDataFrame:
    iac = _com_h3(pd.read_parquet(PROCESSED / f"iac_h3_r{H3_RESOLUCAO}.parquet"))
    return _malha().merge(iac, on="h3", how="left")


def _bairros_publicaveis(fonte: str) -> pd.DataFrame:
    """A tabela por bairro já suprimida: o mapa mostra só o que pode sair do projeto."""
    return supressao.suprimir_bairros(pd.read_csv(PROCESSED / f"taxa_ocorrencias_{fonte}_por_bairro.csv"))


def carregar_fonte(fonte: str) -> gpd.GeoDataFrame:
    """A célula traz o bairro; a nota e a classe vêm da tabela por bairro, que é a fonte."""
    celulas = pd.read_parquet(PROCESSED / f"risco_{fonte}_h3_r{H3_RESOLUCAO}.parquet")[["h3", "bairro"]]
    taxa = _bairros_publicaveis(fonte)
    colunas = [c for c in ("bairro", "taxa_gravidade_norm", "classe_risco", "suprimido") if c in taxa.columns]
    return _malha().merge(celulas.merge(taxa[colunas], on="bairro", how="left"), on="h3", how="left")


def carregar_fase2() -> gpd.GeoDataFrame:
    return carregar_fonte("gm")


def carregar_sesp() -> gpd.GeoDataFrame:
    return carregar_fonte("sesp")


def carregar_comparacao() -> gpd.GeoDataFrame:
    celulas = pd.read_parquet(PROCESSED / f"risco_gm_h3_r{H3_RESOLUCAO}.parquet")[["h3", "bairro"]]
    comp = supressao.suprimir_comparacao(
        pd.read_csv(PROCESSED / "comparacao_gm_sesp_por_bairro.csv"),
        _bairros_publicaveis("gm"), _bairros_publicaveis("sesp"),
    )[["bairro", "log_razao_gm_sesp", "suprimido"]]
    comp["log_razao_gm_sesp"] = comp["log_razao_gm_sesp"].astype(float)
    teto = comp["log_razao_gm_sesp"].abs().quantile(0.95) or 1.0
    # −1 = SESP registra proporcionalmente mais; +1 = a Guarda registra mais.
    comp["excesso_gm"] = (comp["log_razao_gm_sesp"] / teto).clip(-1, 1) / 2 + 0.5
    return _malha().merge(celulas.merge(comp, on="bairro", how="left"), on="h3", how="left")


def carregar_principal() -> gpd.GeoDataFrame:
    """A fonte da camada de risco: SESP quando existir, Guarda enquanto não."""
    try:
        return carregar_sesp()
    except FileNotFoundError:
        return carregar_fase2()


def _contornos():
    limite = gpd.read_file(RAW / "ippuc" / "limite_municipal.gpkg").to_crs(CRS_METRICO)
    caminho = RAW / "ippuc" / "bairros.parquet"
    bairros = gpd.read_parquet(caminho).to_crs(CRS_METRICO) if caminho.exists() else None
    return limite, bairros


# ------------------------------------------------------------------ desenho


@dataclass
class Mapa:
    arquivo: str
    titulo: str
    subtitulo: str
    coluna: str
    carregar: object
    tipo: str = "continuo"  # continuo | classe | robustez
    rampa: str = "azul"
    classes: dict = field(default_factory=dict)
    rotulo_escala: str = ""
    divisas_de_bairro: bool = False


def _suprimidos(dados: gpd.GeoDataFrame) -> pd.Series:
    if "suprimido" not in dados.columns:
        return pd.Series(False, index=dados.index)
    return dados["suprimido"].fillna(False).astype(bool)


def _pintar(ax, dados: gpd.GeoDataFrame, mapa: Mapa):
    """Desenha uma camada; devolve o que a legenda ou a barra de cores precisa."""
    sup = _suprimidos(dados)
    vazio = dados[dados[mapa.coluna].isna() & ~sup]
    if not vazio.empty:
        vazio.plot(ax=ax, color=SEM_DADO, edgecolor=TINTA_FRACA, hatch="////", linewidth=0)
    if sup.any():
        dados[sup].plot(ax=ax, color=SEM_DADO, edgecolor=TINTA_FRACA, hatch="\\\\\\\\", linewidth=0)

    validos = dados[dados[mapa.coluna].notna()]
    if mapa.tipo == "continuo":
        validos.plot(ax=ax, column=mapa.coluna, cmap=RAMPAS[mapa.rampa], vmin=0, vmax=1, linewidth=0)
        return None
    if mapa.tipo == "classe":
        for classe, cor in mapa.classes.items():
            validos[validos[mapa.coluna].astype(str) == classe].plot(ax=ax, color=cor, linewidth=0)
        return [Patch(facecolor=cor, label=classe) for classe, cor in reversed(mapa.classes.items())]
    if mapa.tipo == "robustez":
        norma = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], 5)
        validos.plot(ax=ax, column=mapa.coluna, cmap=ListedColormap(ROBUSTEZ), norm=norma, linewidth=0)
        return [Patch(facecolor=c, label=r) for c, r in reversed(list(zip(ROBUSTEZ, ROTULOS_ROBUSTEZ, strict=True)))]
    raise ValueError(mapa.tipo)


def _moldura(ax, limite, bairros, divisas: bool):
    if divisas and bairros is not None:
        bairros.boundary.plot(ax=ax, color=SUPERFICIE, linewidth=0.5)
    limite.boundary.plot(ax=ax, color=CONTORNO, linewidth=0.8)
    ax.set_axis_off()
    ax.set_aspect("equal")


def _legenda_vazio() -> Patch:
    return Patch(facecolor=SEM_DADO, edgecolor=TINTA_FRACA, hatch="////", label="sem dado")


def _legenda_suprimido() -> Patch:
    return Patch(facecolor=SEM_DADO, edgecolor=TINTA_FRACA, hatch="\\\\\\\\",
                 label=f"suprimido: menos de {LIMIAR_SUPRESSAO} ocorrências")


def _legendas_de_ausencia(dados: gpd.GeoDataFrame, coluna: str) -> list[Patch]:
    sup = _suprimidos(dados)
    itens = [_legenda_vazio()] if (dados[coluna].isna() & ~sup).any() else []
    return itens + ([_legenda_suprimido()] if sup.any() else [])


def _barra(fig, ax, rampa, rotulo):
    sm = plt.cm.ScalarMappable(cmap=rampa, norm=plt.Normalize(0, 1))
    barra = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02, aspect=40)
    barra.set_ticks([0, 0.25, 0.5, 0.75, 1])
    barra.set_ticklabels(["0", "0,25", "0,5", "0,75", "1"])
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=TINTA_2, labelsize=8, length=0)
    if rotulo:
        barra.set_label(rotulo, color=TINTA_2, fontsize=9)


def _cabecalho(fig, titulo, subtitulo, rodape):
    largura = int(fig.get_figwidth() * 14.5)  # caracteres por linha no corpo 9,5
    fig.text(0.04, 0.965, titulo, fontsize=15, fontweight="bold", color=TINTA, va="top")
    fig.text(0.04, 0.925, textwrap.fill(subtitulo, largura), fontsize=9.5, color=TINTA_2, va="top",
             linespacing=1.4)
    fig.text(0.04, 0.015, rodape, fontsize=7.5, color=TINTA_FRACA)


def desenhar(mapa: Mapa, dados: gpd.GeoDataFrame, limite, bairros) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 9), facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.88, bottom=0.07)

    itens = _pintar(ax, dados, mapa)
    _moldura(ax, limite, bairros, mapa.divisas_de_bairro)

    ausencias = _legendas_de_ausencia(dados, mapa.coluna)
    if itens is None:
        _barra(fig, ax, RAMPAS[mapa.rampa], mapa.rotulo_escala)
        if ausencias:
            ax.legend(handles=ausencias, loc="lower right", frameon=False, fontsize=8, labelcolor=TINTA_2)
    else:
        ax.legend(handles=itens + ausencias, loc="lower right", frameon=False, fontsize=8.5,
                  labelcolor=TINTA_2)

    n = int(dados[mapa.coluna].notna().sum())
    _cabecalho(fig, mapa.titulo, mapa.subtitulo,
               f"Malha H3 r{H3_RESOLUCAO} · {n} de {len(dados)} células com valor · curitiba-run")
    destino = DESTINO / mapa.arquivo
    fig.savefig(destino, dpi=160, facecolor=SUPERFICIE)
    plt.close(fig)
    return destino


def painel_dimensoes(dados: gpd.GeoDataFrame, limite, bairros) -> Path:
    """As cinco dimensões e o IAC na mesma escala: como o índice se compõe."""
    paineis = [
        ("densidade_malha", "Densidade da malha"),
        ("espaco_dedicado", "Espaço dedicado"),
        ("transito_tranquilo", "Trânsito tranquilo"),
        ("declividade", "Terreno plano"),
        ("iluminacao", "Iluminação"),
        ("iac", "IAC"),
    ]
    fig, eixos = plt.subplots(2, 3, figsize=(13, 10.5), facecolor=SUPERFICIE)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.1, wspace=0.02, hspace=0.12)
    for ax, (coluna, nome) in zip(eixos.flat, paineis, strict=True):
        ax.set_facecolor(SUPERFICIE)
        _pintar(ax, dados, Mapa("", "", "", coluna, None))
        _moldura(ax, limite, bairros, False)
        ax.set_title(nome, fontsize=11, color=TINTA, fontweight="bold" if coluna == "iac" else "normal", pad=4, y=1.0)

    sm = plt.cm.ScalarMappable(cmap=RAMPAS["azul"], norm=plt.Normalize(0, 1))
    barra = fig.colorbar(sm, ax=eixos, orientation="horizontal", fraction=0.025, pad=0.03, aspect=60)
    barra.set_ticks([0, 0.25, 0.5, 0.75, 1])
    barra.set_ticklabels(["0 · pior", "0,25", "0,5", "0,75", "1 · melhor"])
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=TINTA_2, labelsize=9, length=0)
    eixos.flat[-1].legend(handles=[_legenda_vazio()], loc="lower right", frameon=False, fontsize=8,
                          labelcolor=TINTA_2)

    _cabecalho(
        fig,
        "Fase 1 · As cinco dimensões e o IAC",
        "Cada dimensão normalizada de 0 a 1 contra a distribuição de Curitiba. Declividade invertida: "
        "1 = terreno plano. O IAC é a média ponderada das cinco (pesos 0,15 · 0,30 · 0,25 · 0,15 · 0,15).",
        f"Malha H3 r{H3_RESOLUCAO} · células sem via caminhável ficam sem valor nas dimensões de razão e no IAC "
        "· curitiba-run",
    )
    destino = DESTINO / "fase1_0_dimensoes.png"
    fig.savefig(destino, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)
    return destino


def painel_evolucao(f1: gpd.GeoDataFrame, f2: gpd.GeoDataFrame, limite, bairros) -> Path:
    """Fase a fase, lado a lado e na mesma moldura: o que o projeto mede até aqui."""
    fig = plt.figure(figsize=(13, 8.6), facecolor=SUPERFICIE)
    x0, y0, x1, y1 = limite.total_bounds
    folga = 0.03 * max(x1 - x0, y1 - y0)
    paineis = (
        (0.03, f1, "iac", "azul", "Fase 1 · Adequação à corrida (IAC)", False, ("0 · pior", "1 · melhor")),
        (0.52, f2, "taxa_gravidade_norm", "laranja", "Fase 2 · Ocorrências por habitante", True,
         ("0 · menor", "1 · maior")),
    )
    for x, dados, coluna, rampa, nome, divisas, extremos in paineis:
        ax = fig.add_axes([x, 0.17, 0.45, 0.62])
        ax.set_facecolor(SUPERFICIE)
        _pintar(ax, dados, Mapa("", "", "", coluna, None, rampa=rampa))
        _moldura(ax, limite, bairros, divisas)
        ax.set_xlim(x0 - folga, x1 + folga)
        ax.set_ylim(y0 - folga, y1 + folga)
        ax.set_title(nome, fontsize=11.5, color=TINTA, pad=8, y=1.0)

        cax = fig.add_axes([x + 0.07, 0.11, 0.31, 0.017])
        sm = plt.cm.ScalarMappable(cmap=RAMPAS[rampa], norm=plt.Normalize(0, 1))
        barra = fig.colorbar(sm, cax=cax, orientation="horizontal")
        barra.set_ticks([0, 0.5, 1])
        barra.set_ticklabels([extremos[0], "0,5", extremos[1]])
        barra.outline.set_visible(False)
        barra.ax.tick_params(colors=TINTA_2, labelsize=8, length=0)

    _cabecalho(
        fig,
        "Evolução da análise",
        "À esquerda, onde a infraestrutura favorece a corrida. À direita, onde há mais ocorrências graves por "
        "morador — a nota do bairro, herdada por cada hexágono. A Fase 4 cruza os dois.",
        "Fase 2: SESP-PR quando disponível, senão Guarda Municipal; escala logarítmica. "
        f"Hachura /: sem dado · hachura \\: suprimido, menos de {LIMIAR_SUPRESSAO} ocorrências (ADR 0007) "
        "· curitiba-run",
    )
    destino = DESTINO / "evolucao_fases.png"
    fig.savefig(destino, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)
    return destino


MAPAS = [
    Mapa("fase1_1_iac.png", "Fase 1 · Índice de Adequação à Corrida",
         "Média ponderada das cinco dimensões. Quanto mais escuro, mais adequado para correr.",
         "iac", carregar_fase1, rotulo_escala="IAC (0 = pior, 1 = melhor)"),
    Mapa("fase1_2_iac_classe.png", "Fase 1 · IAC alto e baixo",
         "A unidade de comunicação do projeto (ADR 0003): corte na mediana do município.",
         "classe", carregar_fase1, tipo="classe", classes=CLASSES_AZUL),
    Mapa("fase1_3_robustez.png", "Fase 1 · Robustez da classe entre cenários de peso",
         "Em quantos dos quatro esquemas de peso a célula fica alta. Cinza: a conclusão depende do peso.",
         "n_alto", carregar_fase1, tipo="robustez"),
    Mapa("fase2_1_taxa.png", "Fase 2 · Ocorrências da GM por habitante",
         "Gravidade anual por 100 mil moradores, em escala logarítmica. Nota do bairro, herdada por cada "
         "hexágono. Bairros de passagem ficam inflados.",
         "taxa_gravidade_norm", carregar_fase2, rampa="laranja", divisas_de_bairro=True,
         rotulo_escala="taxa normalizada (0 = menor, 1 = maior)"),
    Mapa("fase2_2_risco_classe.png", "Fase 2 · Ocorrências da GM: classe alta e baixa",
         "Corte na mediana dos 75 bairros. Ocorrências registradas pela Guarda, não risco.",
         "classe_risco", carregar_fase2, tipo="classe", classes=CLASSES_LARANJA, divisas_de_bairro=True),
    Mapa("fase2_3_sesp_taxa.png", "Fase 2 · Ocorrências da SESP-PR por habitante",
         "Mesma regra da Guarda: gravidade anual por 100 mil moradores, suavizada, em escala logarítmica.",
         "taxa_gravidade_norm", carregar_sesp, rampa="laranja", divisas_de_bairro=True,
         rotulo_escala="taxa normalizada (0 = menor, 1 = maior)"),
    Mapa("fase2_4_sesp_classe.png", "Fase 2 · SESP-PR: classe alta e baixa",
         "Corte na mediana dos 75 bairros.",
         "classe_risco", carregar_sesp, tipo="classe", classes=CLASSES_LARANJA, divisas_de_bairro=True),
    Mapa("fase2_5_gm_vs_sesp.png", "Fase 2 · Onde a Guarda registra mais que a polícia",
         "Cada bairro comparado à média de cada fonte. Vermelho: a GM registra proporcionalmente mais — "
         "o viés de presença. Azul: a SESP registra proporcionalmente mais. Cinza: as duas concordam.",
         "excesso_gm", carregar_comparacao, rampa="divergente", divisas_de_bairro=True,
         rotulo_escala="0 = SESP registra mais · 0,5 = concordam · 1 = GM registra mais"),
]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    DESTINO.mkdir(parents=True, exist_ok=True)
    limite, bairros = _contornos()

    cache: dict = {}

    def obter(carregar):
        if carregar not in cache:
            try:
                cache[carregar] = carregar()
            except (FileNotFoundError, KeyError) as erro:
                cache[carregar] = erro
        return cache[carregar]

    for mapa in MAPAS:
        dados = obter(mapa.carregar)
        if isinstance(dados, Exception) or mapa.coluna not in dados.columns:
            log.warning("  pulado %-26s insumo ausente (%s)", mapa.arquivo,
                        dados if isinstance(dados, Exception) else f"coluna {mapa.coluna}")
            continue
        log.info("  %s", desenhar(mapa, dados, limite, bairros).relative_to(FIGURES.parent.parent))

    f1, f2 = obter(carregar_fase1), obter(carregar_principal)
    if not isinstance(f1, Exception):
        log.info("  %s", painel_dimensoes(f1, limite, bairros).relative_to(FIGURES.parent.parent))
    if not isinstance(f1, Exception) and not isinstance(f2, Exception):
        log.info("  %s", painel_evolucao(f1, f2, limite, bairros).relative_to(FIGURES.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
