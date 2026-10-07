"""Fase 1 completa em um comando: limite → malhas → OSM → dimensões → IAC.

Uso, a partir da raiz do repositório:

    python scripts/fase1.py

Precisa de internet aberta para Overpass e Nominatim. Cada etapa pula o que já
existe em disco, então reexecutar depois de uma queda continua de onde parou —
`--refazer` força tudo de novo.

O script insere `src/` no path por conta própria, então funciona sem instalar o
pacote. Se você usou `uv sync`, `uv run python scripts/fase1.py` também serve.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

log = logging.getLogger("fase1")


def _duracao(inicio: float) -> str:
    seg = time.time() - inicio
    return f"{seg:.0f}s" if seg < 90 else f"{seg / 60:.1f}min"


def etapa(titulo: str):
    """Delimita uma etapa no log, com tempo e erro legível."""

    class _Etapa:
        def __enter__(self):
            self.t = time.time()
            log.info("")
            log.info("=" * 68)
            log.info("  %s", titulo)
            log.info("=" * 68)
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                log.info("  ✓ %s concluída em %s", titulo, _duracao(self.t))
            else:
                log.error("  ✗ %s falhou: %s", titulo, exc)
            return False

    return _Etapa()


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa a Fase 1 do projeto")
    parser.add_argument("--refazer", action="store_true", help="ignora o que já está em disco")
    parser.add_argument("--so-malha", action="store_true", help="para depois das malhas (não usa internet)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    from curitiba_run.config import H3_RESOLUCOES_SENSIBILIDADE, PROCESSED, RAW

    DESTINO_IPPUC = RAW / "ippuc"
    from curitiba_run.ingestion import ippuc
    from curitiba_run.processing import grid

    # ------------------------------------------------------------------ limite
    with etapa("1/5  Limite municipal"):
        limite = ippuc.baixar_limite(forcar=args.refazer)
        area = limite.to_crs("EPSG:31982").area.sum() / 1e6
        log.info("  Curitiba: %.1f km² (referência oficial ~435 km²) | fonte: %s",
                 area, limite["fonte"].iloc[0])

    # ------------------------------------------------------------------ malhas
    with etapa("2/5  Malhas H3"):
        for res in H3_RESOLUCOES_SENSIBILIDADE:
            destino = PROCESSED / f"malha_h3_r{res}.parquet"
            if destino.exists() and not args.refazer:
                log.info("  r%d já existe, pulando", res)
                continue
            malha = grid.recortar_pelo_limite(grid.construir_malha(limite, resolucao=res), limite)
            info = grid.verificar_cobertura(malha, limite)
            grid.salvar(malha, res)
            log.info("  r%d: %d células, lacuna %.4f%%", res, info["n_celulas"],
                     100 * info["lacuna_relativa"])

    if args.so_malha:
        log.info("\n--so-malha: parando aqui.")
        return 0

    # ------------------------------------------------------------ GeoCuritiba
    from curitiba_run.ingestion import geocuritiba

    with etapa("3/5  Camadas do GeoCuritiba (IPPUC)"):
        caminho_declividade = DESTINO_IPPUC / "declividade.tif"
        if caminho_declividade.exists() and not args.refazer:
            log.info("  Declividade e postes já existem, pulando.")
        else:
            log.info("  Postes oficiais e modelo digital de terreno a 10 m.")
            geocuritiba.baixar_postes()
            geocuritiba.baixar_areas_verdes()
            geocuritiba.derivar_declividade(geocuritiba.baixar_mdt())

    # --------------------------------------------------------------------- OSM
    from curitiba_run.ingestion import osm

    with etapa("4/5  Camadas do OpenStreetMap"):
        if (osm.DESTINO / "arestas.parquet").exists() and not args.refazer:
            log.info("  Camadas já existem, pulando. Use --refazer para rebaixar.")
        else:
            log.info("  A rede caminhável de Curitiba é uma consulta pesada ao Overpass.")
            log.info("  Espere alguns minutos. As respostas ficam em cache — reexecutar é rápido.")
            poligono = osm._poligono_do_municipio()
            nos, arestas = osm.baixar_rede(poligono)
            osm.salvar(
                {
                    "nos": nos,
                    "arestas": arestas,
                    "espacos_dedicados": osm.baixar_espacos_dedicados(poligono),
                    "arborizacao": osm.baixar_arborizacao(poligono),
                    "postes": osm.baixar_iluminacao(poligono),
                }
            )

    # -------------------------------------------------------------------- IAC
    with etapa("5/5  Dimensões e IAC"):
        import geopandas as gpd
        import pandas as pd

        from curitiba_run.config import H3_RESOLUCAO
        from curitiba_run.features import dimensions
        from curitiba_run.features import suitability_index as si

        malha = gpd.read_parquet(PROCESSED / f"malha_h3_r{H3_RESOLUCAO}.parquet")

        from curitiba_run.ingestion import geocuritiba

        # Postes: só os que iluminam. `Rede elétrica` é distribuição de energia.
        postes = geocuritiba.filtrar_postes_de_iluminacao(
            gpd.read_parquet(DESTINO_IPPUC / "postes.parquet")
        )

        # Espaço dedicado: OSM mais as unidades de conservação **públicas**.
        # Fora ficam as RPPNM, que são propriedade privada, e as APAs, que são
        # zoneamento e sozinhas cobrem quase metade do município.
        verdes = gpd.read_parquet(DESTINO_IPPUC / "areas_verdes.parquet")
        verdes["geometry"] = verdes.geometry.make_valid()
        espacos = gpd.GeoDataFrame(
            pd.concat(
                [
                    osm.carregar("espacos_dedicados")[["geometry"]],
                    geocuritiba.filtrar_areas_publicas(verdes)[["geometry"]],
                ],
                ignore_index=True,
            ),
            crs=malha.crs,
        )

        # A classificação viária é **reaplicada a cada execução**, e não lida do
        # disco. A coluna `baixo_trafego` é derivada, mas era gravada junto com
        # a camada crua no download — então mudar a hierarquia em `osm.py` não
        # tinha efeito nenhum enquanto `arestas.parquet` existisse, porque a
        # etapa 4 pula o que já está em disco. O número sairia plausível e
        # velho, que é o modo de falha recorrente deste projeto.
        # Reclassificar é uma operação pura sobre uma coluna: custa quase nada.
        arestas = osm.classificar_hierarquia_viaria(osm.carregar("arestas"))
        log.info("  Hierarquia viária reclassificada a partir de `osm.py`.")
        por_classe = arestas.groupby("baixo_trafego", dropna=False).size()
        for valor, n in por_classe.sort_index(ascending=False).items():
            rotulo = {1.0: "baixo tráfego", 0.5: "ambígua", 0.0: "alto tráfego"}.get(valor, str(valor))
            log.info("    %-14s %6d arestas", rotulo, n)

        brutas = dimensions.calcular_todas(
            malha,
            arestas=arestas,
            nos=osm.carregar("nos"),
            espacos=espacos,
            declividade_raster=DESTINO_IPPUC / "declividade.tif",
            pontos_luz=postes,
        )

        normalizadas = si.normalizar_dimensoes(brutas)
        iac = si.compor(normalizadas)

        cenarios = si.avaliar_cenarios_de_peso(normalizadas)
        estabilidade = si.estabilidade_do_ranking(cenarios)

        # A classificação alto/baixo é a unidade de comunicação do IAC, e a
        # robustez entre cenários de peso vai junto com ela — não como anexo.
        # O ranking contínuo mantém o quartil em 41% das células; a classe
        # binária se mantém em 70%. Ver ADR 0003.
        robustez = si.robustez_da_classificacao(cenarios)

        saida = (
            brutas.add_prefix("bruto_")
            .join(normalizadas)
            .assign(iac=iac)
            .join(robustez[["classe", "n_alto", "estavel"]])
        )
        saida.to_parquet(PROCESSED / f"iac_h3_r{H3_RESOLUCAO}.parquet")

        log.info("")
        log.info("  IAC calculado para %d células (%d com valor)", len(iac), int(iac.notna().sum()))
        log.info("  Estabilidade mínima entre cenários de peso: %.3f", estabilidade.min().min())
        log.info("")
        log.info("  Classificação alto/baixo e robustez entre os %d cenários:", len(cenarios.columns))
        for _, linha in si.resumo_da_robustez(robustez).iterrows():
            log.info("    %-44s %5d  (%4.1f%%)", linha["concordância"], linha["células"], linha["%"])
        estaveis = robustez["estavel"].sum()
        log.info("  Classe estável em todos os cenários: %d células (%.1f%%)",
                 int(estaveis), 100 * estaveis / int(robustez["estavel"].notna().sum()))
        log.info("")
        log.info("  Salvo em %s", PROCESSED / f"iac_h3_r{H3_RESOLUCAO}.parquet")

    log.info("\nFase 1 concluída. Próximo passo: DEM e camadas do IPPUC "
             "(ver reports/fase1_status.md).")
    return 0


HOSTS_NECESSARIOS = (
    "overpass-api.de",
    "nominatim.openstreetmap.org",
    "ippuc.org.br",
    "geocuritiba.ippuc.org.br",
    "dadosabertos.curitiba.pr.gov.br",
    "servicodados.ibge.gov.br",
)


def _e_erro_de_rede(erro: BaseException) -> bool:
    nome = type(erro).__name__
    return isinstance(erro, OSError) or nome in {
        "ConnectionError", "ProxyError", "SSLError", "Timeout",
        "ConnectTimeout", "ReadTimeout", "URLError", "MaxRetryError",
    }


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.warning("\nInterrompido. O cache foi preservado — rode de novo para continuar.")
        sys.exit(130)
    except ModuleNotFoundError as erro:
        log.error("\nDependência faltando: %s", erro.name)
        log.error("Instale com:  pip install geopandas osmnx h3 rasterio pyarrow matplotlib")
        sys.exit(1)
    except Exception as erro:  # noqa: BLE001 — o objetivo é a mensagem, não o rastro
        if not _e_erro_de_rede(erro):
            raise
        log.error("\n" + "=" * 68)
        log.error("  Sem acesso à rede necessária para baixar os dados.")
        log.error("=" * 68)
        log.error("  Detalhe: %s", erro)
        log.error("")
        log.error("  Esta máquina precisa alcançar:")
        for host in HOSTS_NECESSARIOS:
            log.error("    - %s", host)
        log.error("")
        log.error("  Se estiver atrás de proxy corporativo ou VPN, tente de uma rede aberta.")
        log.error("  As malhas H3 não dependem de internet: `python scripts/fase1.py --so-malha`.")
        sys.exit(2)
