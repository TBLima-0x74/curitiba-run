"""Fase 2: ocorrências → taxa por habitante → hexágono, para cada fonte disponível.

Uso, a partir da raiz do repositório:

    python scripts/fase2_ocorrencias.py

Fontes:
  - Guarda Municipal (SiGesGuarda), em `data/raw/sigesguarda/` — sempre;
  - SESP-PR, em `data/raw/sesp/` — quando o arquivo existir **e** o ADR 0006
    com a base legal estiver escrito. Sem o ADR, a SESP é pulada com aviso.

Para cada fonte, três etapas:
  1. ocorrências de interesse com peso de gravidade → `ocorrencias_<fonte>_por_bairro.csv`
  2. taxa por 100 mil, suavizada e normalizada, com classe → `taxa_ocorrencias_<fonte>_por_bairro.csv`
  3. nota do bairro em cada hexágono → `risco_<fonte>_h3_r9.parquet`

Com as duas fontes, compara GM e SESP bairro a bairro
(`comparacao_gm_sesp_por_bairro.csv`) — é a medida do viés de presença da
Guarda. E grava `risco_h3_r9.parquet` com a fonte principal: a SESP quando
existir, a Guarda enquanto não.

Por fim, publica em `data/publicado/` só o que passou pela supressão de baixa
contagem (ADR 0007): bairro com menos de 5 ocorrências sai sem valor, e
nenhuma contagem por tipo sai por bairro. A SESP só é publicada se o ADR 0006
disser "Publicação de agregados: permitida".

Só a etapa 3 precisa de internet, e só na primeira vez: baixa os limites de
bairro do GeoCuritiba para `data/raw/ippuc/bairros.parquet`.
"""

import logging
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from curitiba_run.config import H3_RESOLUCAO, LIMIAR_SUPRESSAO, PROCESSED, PUBLICADO  # noqa: E402
from curitiba_run.features import risk_surface  # noqa: E402
from curitiba_run.ingestion import ibge, sesp, sigesguarda  # noqa: E402
from curitiba_run.processing import supressao  # noqa: E402

log = logging.getLogger("fase2")


def saidas(fonte: str) -> dict[str, Path]:
    return {
        "ocorrencias": PROCESSED / f"ocorrencias_{fonte}_por_bairro.csv",
        "taxa": PROCESSED / f"taxa_ocorrencias_{fonte}_por_bairro.csv",
        "h3": PROCESSED / f"risco_{fonte}_h3_r{H3_RESOLUCAO}.parquet",
    }


SAIDA_PRINCIPAL = PROCESSED / f"risco_h3_r{H3_RESOLUCAO}.parquet"
SAIDA_COMPARACAO = PROCESSED / "comparacao_gm_sesp_por_bairro.csv"


def carregar_fontes() -> dict[str, tuple]:
    """Roda a etapa 1 de cada fonte disponível; a Guarda é obrigatória."""
    fontes = {"gm": sigesguarda.pipeline()}
    try:
        fontes["sesp"] = sesp.pipeline()
    except FileNotFoundError:
        log.info("  SESP-PR: nenhum arquivo em data/raw/sesp/ — segue só com a Guarda.")
    except PermissionError as erro:
        log.warning("  SESP-PR: arquivo presente, mas sem base legal registrada. %s", erro)
    return fontes


def atribuicao_h3():
    """Bairro dominante de cada hexágono — calculado uma vez, serve a todas as fontes."""
    import geopandas as gpd

    from curitiba_run.ingestion import geocuritiba
    from curitiba_run.processing import bairros as proc_bairros

    try:
        limites = geocuritiba.carregar_bairros()
    except (OSError, LookupError) as erro:
        log.warning("  Sem limites de bairro: %s", erro)
        return None
    malha = gpd.read_parquet(PROCESSED / f"malha_h3_r{H3_RESOLUCAO}.parquet")
    return proc_bairros.atribuir_bairro_dominante(malha, limites)


def processar(fonte: str, ocorrencias, relatorio, populacao, atribuicao):
    caminhos = saidas(fonte)
    nome = {"gm": "Guarda Municipal", "sesp": "SESP-PR"}[fonte]

    log.info("")
    log.info("── %s ──", nome)
    log.info("1/3  Ocorrências por bairro")
    ocorrencias.to_csv(caminhos["ocorrencias"], index=False, encoding="utf-8-sig")
    for chave, valor in relatorio.items():
        log.info("  %s: %s", chave, valor)
    if relatorio.get("naturezas_nao_classificadas"):
        log.info("  >> Revise as naturezas não classificadas acima: as que atingem a pessoa na rua")
        log.info("     precisam de um padrão em ingestion/sesp.py (CLASSIFICACAO).")

    if populacao is None:
        return None, None
    log.info("2/3  Taxa por 100 mil habitantes")
    taxa = risk_surface.taxa_por_habitante(ocorrencias, populacao)
    taxa.to_csv(caminhos["taxa"], index=False, encoding="utf-8-sig")
    colunas = ["bairro", "populacao", "taxa_gravidade", "taxa_gravidade_eb", "classe_risco", "n_ocorrencias"]
    log.info(taxa.nlargest(6, "taxa_gravidade_eb")[colunas].round(2).to_string(index=False))
    contagem = taxa["classe_risco"].value_counts()
    log.info("  Classe (mediana dos 75 bairros): %d alto, %d baixo",
             contagem.get("alto", 0), contagem.get("baixo", 0))

    if atribuicao is None:
        return taxa, None
    log.info("3/3  Bairro → hexágono H3 r%d", H3_RESOLUCAO)
    celulas = risk_surface.risco_por_celula(atribuicao, taxa)
    celulas.to_parquet(caminhos["h3"])
    por_classe = celulas["classe_risco"].value_counts()
    log.info("  %d células: %d alto, %d baixo · %d por proximidade · %d divididas",
             len(celulas), por_classe.get("alto", 0), por_classe.get("baixo", 0),
             int(celulas["bairro_por_proximidade"].sum()), int(celulas["celula_dividida"].sum()))
    return taxa, celulas


def gravar_publicavel(df, nome: str) -> None:
    supressao.verificar(df, nome)
    df.to_csv(PUBLICADO / nome, index=False, encoding="utf-8-sig")
    log.info("  %s", nome)


def publicar(fonte: str, ocorrencias, taxa, celulas):
    """Grava em data/publicado/ a versão suprimida; devolve a tabela por bairro publicada."""
    PUBLICADO.mkdir(parents=True, exist_ok=True)
    gravar_publicavel(supressao.por_tipo_cidade(ocorrencias), f"ocorrencias_{fonte}_por_tipo_curitiba.csv")
    if taxa is None:
        return None
    bairros = supressao.suprimir_bairros(taxa)
    gravar_publicavel(bairros, f"risco_{fonte}_por_bairro.csv")
    if celulas is not None:
        gravar_publicavel(supressao.suprimir_celulas(celulas, bairros), f"risco_{fonte}_h3_r{H3_RESOLUCAO}.csv")
    suprimidos = bairros.loc[bairros["suprimido"], "bairro"].tolist()
    log.info("  %d bairros suprimidos (menos de %d ocorrências, mais o complemento): %s",
             len(suprimidos), LIMIAR_SUPRESSAO, ", ".join(suprimidos) or "nenhum")
    return bairros


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    fontes = carregar_fontes()
    try:
        populacao = ibge.populacao_por_bairro()
    except FileNotFoundError as erro:
        log.warning("  %s — só a etapa 1 será gravada.", erro)
        populacao = None
    atribuicao = atribuicao_h3() if populacao is not None else None

    resultados = {f: processar(f, *fontes[f], populacao, atribuicao) for f in fontes}
    taxas = {f: r[0] for f, r in resultados.items()}

    comparacao = None
    if taxas.get("gm") is not None and taxas.get("sesp") is not None:
        log.info("")
        log.info("── Guarda Municipal × SESP-PR ──")
        comparacao, resumo = risk_surface.comparar_fontes(taxas["gm"], taxas["sesp"])
        comparacao.to_csv(SAIDA_COMPARACAO, index=False, encoding="utf-8-sig")
        for chave, valor in resumo.items():
            log.info("  %s: %s", chave, valor)

    log.info("")
    log.info("── Publicação: data/publicado/ (supressão do ADR 0007) ──")
    publicados = {}
    for fonte, (taxa, celulas) in resultados.items():
        if fonte == "sesp" and not sesp.publicacao_permitida():
            log.info("  SESP-PR não publicada: o ADR 0006 não diz \"Publicação de agregados: permitida\".")
            continue
        publicados[fonte] = publicar(fonte, fontes[fonte][0], taxa, celulas)
    if comparacao is not None and publicados.get("gm") is not None and publicados.get("sesp") is not None:
        gravar_publicavel(
            supressao.suprimir_comparacao(comparacao, publicados["gm"], publicados["sesp"]),
            "comparacao_gm_sesp_por_bairro.csv",
        )

    principal = "sesp" if "sesp" in taxas and saidas("sesp")["h3"].exists() else "gm"
    if saidas(principal)["h3"].exists():
        shutil.copyfile(saidas(principal)["h3"], SAIDA_PRINCIPAL)
        log.info("")
        log.info("Fonte principal da camada de risco: %s → %s", principal, SAIDA_PRINCIPAL.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
