"""Ocorrências da SESP-PR, recebidas via Lei de Acesso à Informação.

Pedido: protocolo 26.719.234-0 (e-Protocolo do Paraná), 09/10/2026. Ver
reports/status/fase2_status.md.

**O esquema do arquivo ainda é desconhecido** — a resposta pode vir em CSV ou
XLSX, com nomes de coluna e de natureza que não sabemos de antemão. Por isso
este módulo não supõe nada que não precise:

- as colunas são **reconhecidas pelo nome** (`CANDIDATAS`), e o erro lista as
  que encontrou quando falta alguma essencial;
- a natureza é classificada por **padrões** (`CLASSIFICACAO`), e toda natureza
  que não casar com nenhum aparece no relatório com a contagem — para que se
  decida, uma a uma, se entra;
- data completa ou só ano e mês servem.

**Base legal antes de dado.** O ADR 0004 bloqueia fonte estadual até haver um
ADR com a base legal dela. `verificar_base_legal` impõe isso em código: sem um
`docs/adr/0006-*.md`, a ingestão para.

Quando a base chegar: salvar o arquivo em `data/raw/sesp/`, escrever o ADR 0006
com a resposta oficial, rodar `python scripts/fase2_ocorrencias.py` e revisar
as naturezas não classificadas no relatório.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

import pandas as pd

from curitiba_run.config import IBGE_MUNICIPIO, OCORRENCIAS_INICIO, PROCESSED, RAW, ROOT
from curitiba_run.processing.bairros import chave, limpar_texto, normalizar_bairro

log = logging.getLogger(__name__)

DESTINO = RAW / "sesp"
SAIDA = PROCESSED / "ocorrencias_sesp_por_bairro.csv"
PASTA_ADR = ROOT / "docs" / "adr"
PADRAO_ADR_BASE_LEGAL = "0006-*.md"

# Nome interno → nomes plausíveis na resposta da SESP, já em `chave` (sem
# acento, maiúsculo). O primeiro que existir no arquivo é usado.
CANDIDATAS = {
    "bairro": ["BAIRRO", "NM_BAIRRO", "BAIRRO_FATO", "BAIRRO DO FATO", "BAIRRO_OCORRENCIA", "NOME_BAIRRO"],
    "natureza": ["NATUREZA", "DS_NATUREZA", "NATUREZA_OCORRENCIA", "TIPO_OCORRENCIA", "CRIME", "DELITO",
                 "TIPO", "DESCRICAO", "FATO"],
    "data": ["DATA", "DATA_FATO", "DT_FATO", "DATA_OCORRENCIA", "DATA DO FATO", "DT_OCORRENCIA"],
    "ano": ["ANO", "ANO_FATO", "ANO_OCORRENCIA"],
    "mes": ["MES", "MES_FATO", "MES_OCORRENCIA"],
    "tipo_local": ["TIPO_LOCAL", "LOCAL", "TIPO DE LOCAL", "AMBIENTE", "LOCAL_FATO", "TIPO_LOCAL_FATO"],
    "municipio": ["MUNICIPIO", "CIDADE", "NM_MUNICIPIO", "MUNICIPIO_FATO", "CD_MUNICIPIO", "COD_IBGE"],
}

# Natureza → tipo do projeto, por padrão sobre a `chave` do texto. A ordem
# importa: o primeiro padrão que casa decide ("TENTATIVA DE HOMICIDIO" antes de
# "HOMICIDIO"). Os tipos e os pesos são os mesmos da Guarda (ADR 0005).
CLASSIFICACAO: list[tuple[str, str]] = [
    (r"TENTATIVA.*HOMICIDIO|HOMICIDIO.*TENTAD", "tentativa_homicidio"),
    (r"FEMINICIDIO|HOMICIDIO|LATROCINIO", "homicidio"),
    (r"ESTUPRO", "estupro"),
    (r"IMPORTUNACAO SEXUAL", "importunacao_sexual"),
    (r"ATO OBSCENO", "ato_obsceno"),
    (r"DISPARO DE ARMA", "disparo_arma_fogo"),
    (r"TENTATIVA.*SEQUESTRO", "tentativa_sequestro"),
    (r"ROUBO.*(TRANSEUNTE|PEDESTRE|PESSOA)", "roubo"),
    (r"FURTO.*(TRANSEUNTE|PEDESTRE|PESSOA)", "furto"),
    (r"LESAO CORPORAL", "lesao_corporal"),
    (r"AMEACA", "ameaca"),
    (r"VIAS DE FATO", "vias_de_fato"),
]

# Roubo e furto genéricos só entram se o local for via pública — a mesma regra
# da Guarda: o alvo tem de ser a pessoa na rua, não o comércio ou a casa.
GENERICOS_SO_EM_VIA_PUBLICA = [(r"^ROUBO", "roubo"), (r"^FURTO", "furto")]
LOCAL_VIA_PUBLICA = r"VIA PUBLICA|LOGRADOURO|CALCADA|\bRUA\b|PRACA|PARQUE|PONTO DE ONIBUS"

# Violência doméstica sai, como na base da Guarda.
EXCLUIR = r"DOMESTIC|MARIA DA PENHA|FAMILIAR"


# ------------------------------------------------------------------ guarda


def verificar_base_legal(pasta: Path | None = None) -> Path:
    """O ADR com a base legal precisa existir antes de qualquer dado entrar."""
    pasta = pasta or PASTA_ADR
    adrs = sorted(pasta.glob(PADRAO_ADR_BASE_LEGAL))
    if not adrs:
        raise PermissionError(
            "Dados da SESP-PR só entram com base legal registrada (ADR 0004). "
            f"Escreva {pasta / '0006-base-legal-sesp.md'} com a resposta oficial ao pedido "
            "via LAI e rode de novo."
        )
    return adrs[-1]


# Linha que o ADR 0006 precisa conter para os agregados da SESP saírem do
# projeto. Usar dentro dele não é o mesmo que publicar: a resposta da LAI pode
# autorizar um e não o outro, e por isso a autorização é explícita.
MARCA_PUBLICACAO = re.compile(r"publica[çc][ãa]o\s+de\s+agregados\s*:\s*\**\s*permitida", re.IGNORECASE)


def publicacao_permitida(pasta: Path | None = None) -> bool:
    """O ADR 0006 autoriza publicar agregados da SESP? Sem ADR, ou sem a linha, não."""
    try:
        adr = verificar_base_legal(pasta)
    except PermissionError:
        return False
    return bool(MARCA_PUBLICACAO.search(adr.read_text(encoding="utf-8")))


# ------------------------------------------------------------------ leitura


def localizar_base(pasta: Path | None = None) -> Path:
    pasta = pasta or DESTINO
    candidatos = sorted(p for p in pasta.iterdir() if p.suffix.lower() in {".csv", ".xlsx", ".xls"}) \
        if pasta.exists() else []
    if not candidatos:
        raise FileNotFoundError(f"Nenhum .csv ou .xlsx em {pasta}.")
    if len(candidatos) > 1:
        log.warning("Vários arquivos em %s; usando o mais recente pelo nome: %s", pasta, candidatos[-1].name)
    return candidatos[-1]


def carregar(caminho: Path) -> pd.DataFrame:
    if caminho.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(caminho, dtype=str)
    conteudo = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    primeira = texto.split("\n", 1)[0]
    separador = max((";", ",", "\t", "|"), key=primeira.count)
    return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str)


def _mapear_colunas(bruto: pd.DataFrame) -> dict[str, str]:
    por_chave = {chave(c): c for c in bruto.columns}
    mapa = {}
    for interno, nomes in CANDIDATAS.items():
        achado = next((por_chave[n] for n in nomes if n in por_chave), None)
        if achado is not None:
            mapa[interno] = achado
    tem_data = "data" in mapa or {"ano", "mes"} <= set(mapa)
    if "bairro" not in mapa or "natureza" not in mapa or not tem_data:
        raise ValueError(
            "Não reconheci as colunas essenciais (bairro, natureza e data ou ano+mês). "
            f"Colunas do arquivo: {list(bruto.columns)}. Acrescente os nomes em `CANDIDATAS`."
        )
    return mapa


def padronizar_esquema(bruto: pd.DataFrame, municipio: str = IBGE_MUNICIPIO) -> tuple[pd.DataFrame, bool]:
    """Esquema interno: bairro_original, natureza, tipo_local, data, bairro.

    Devolve também se a data é só mensal — o período precisa disso.
    """
    mapa = _mapear_colunas(bruto)
    df = pd.DataFrame(index=bruto.index)
    df["bairro_original"] = bruto[mapa["bairro"]].map(limpar_texto)
    df["natureza"] = bruto[mapa["natureza"]].map(limpar_texto)
    df["tipo_local"] = bruto[mapa["tipo_local"]].map(limpar_texto) if "tipo_local" in mapa else None

    if "municipio" in mapa:
        valores = bruto[mapa["municipio"]].map(chave).fillna("")
        df = df[valores.isin({"CURITIBA", municipio, municipio[:6]})]
        bruto = bruto.loc[df.index]

    mensal = "data" not in mapa
    if mensal:
        df["data"] = pd.to_datetime(
            bruto[mapa["ano"]].str.strip() + "-" + bruto[mapa["mes"]].str.strip().str.zfill(2) + "-01",
            errors="coerce",
        )
    else:
        df["data"] = pd.to_datetime(bruto[mapa["data"]], dayfirst=True, errors="coerce")

    df["bairro"] = normalizar_bairro(df["bairro_original"])
    return df, mensal


def classificar_natureza(df: pd.DataFrame) -> pd.DataFrame:
    def tipo(natureza, local):
        n = chave(natureza) or ""
        if re.search(EXCLUIR, n):
            return None
        for padrao, destino in CLASSIFICACAO:
            if re.search(padrao, n):
                return destino
        via_publica = bool(local) and bool(re.search(LOCAL_VIA_PUBLICA, chave(local) or ""))
        for padrao, destino in GENERICOS_SO_EM_VIA_PUBLICA:
            if re.search(padrao, n) and via_publica:
                return destino
        return None

    df = df.copy()
    df["tipo"] = [tipo(n, loc) for n, loc in zip(df["natureza"], df["tipo_local"], strict=True)]
    return df


def pipeline(caminho: Path | None = None, estrategia: str = "minima") -> tuple[pd.DataFrame, dict]:
    """Arquivo da SESP → tabela por bairro, no mesmo formato da Guarda."""
    from curitiba_run.ingestion.sigesguarda import agregar_por_bairro

    adr = verificar_base_legal()
    caminho = caminho or localizar_base()
    log.info("Lendo %s (base legal: %s)", caminho.name, adr.name)

    bruto = carregar(caminho)
    df, mensal = padronizar_esquema(bruto)
    df = df[df["data"] >= pd.Timestamp(OCORRENCIAS_INICIO)]
    df = classificar_natureza(df)

    inicio = max(df["data"].min(), pd.Timestamp(OCORRENCIAS_INICIO))
    fim = df["data"].max() + (pd.offsets.MonthEnd(0) if mensal else pd.Timedelta(0))

    interesse = df[df["tipo"].notna()]
    nao_classificadas = (
        df.loc[df["tipo"].isna(), "natureza"].value_counts().head(40).to_dict()
    )
    relatorio = {
        "arquivo": caminho.name,
        "registros_lidos": len(bruto),
        "em_curitiba_no_periodo": len(df),
        "periodo": f"{inicio:%Y-%m-%d} a {fim:%Y-%m-%d}" + (" (mensal)" if mensal else ""),
        "de_interesse": len(interesse),
        "de_interesse_sem_bairro": int(interesse["bairro"].isna().sum()),
        "nomes_sem_bairro": interesse.loc[interesse["bairro"].isna(), "bairro_original"]
        .value_counts().head(20).to_dict(),
        "por_tipo": interesse["tipo"].value_counts().to_dict(),
        "naturezas_nao_classificadas": nao_classificadas,
        "tem_tipo_local": bool(df["tipo_local"].notna().any()),
    }
    return agregar_por_bairro(df, estrategia, inicio=inicio, fim=fim), relatorio


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tabela, relatorio = pipeline()
    tabela.to_csv(SAIDA, index=False, encoding="utf-8-sig")
    for k, v in relatorio.items():
        log.info("%s: %s", k, v)


if __name__ == "__main__":
    main()
