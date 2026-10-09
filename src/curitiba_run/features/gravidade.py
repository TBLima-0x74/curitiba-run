"""Peso de gravidade de cada tipo de ocorrência, de 0 a 1.

**Os pesos não são opinião: são derivados da pena mínima do Código Penal.**
É o método do Cambridge Crime Harm Index (Sherman, Neyroud e Neyroud, 2016),
que pondera cada crime pela pena que a lei atribui a ele, adaptado à
legislação brasileira. A vantagem sobre uma escala inventada é que o critério
é externo, público e reprodutível — quem discordar do peso está discordando
do legislador, e pode trocar a regra sem tocar no resto do pipeline.

Regras, todas implementadas aqui e não à mão:

1. **Pena de referência** = pena mínima do caput, na redação vigente.
   `estrategia="media"` usa o ponto médio entre mínimo e máximo, para
   análise de sensibilidade.
2. **Tentativa** = metade da pena do consumado. O art. 14, parágrafo único,
   reduz de 1/3 a 2/3; metade é o ponto médio da faixa legal.
3. **Tipo ambíguo** = o tipo menos grave compatível com o registro. Na
   dúvida, não se inflaciona o risco.
4. **Normalização**: divide-se pela maior pena de referência da tabela, de
   modo que o tipo mais grave vale 1.

Decisão: docs/adr/0005-peso-de-gravidade-pela-pena-minima.md.
Regras de inclusão: docs/taxonomia_ocorrencias.md.
"""

from __future__ import annotations

from dataclasses import dataclass

ANO = 365
MES = 30


@dataclass(frozen=True)
class TipoPenal:
    rotulo: str
    base_legal: str
    pena_min_dias: float
    pena_max_dias: float
    tentativa: bool = False


def _tentativa(t: TipoPenal, rotulo: str) -> TipoPenal:
    """Art. 14, parágrafo único: metade da pena do consumado."""
    return TipoPenal(
        rotulo=rotulo,
        base_legal=f"{t.base_legal} c/c art. 14, II e parágrafo único, CP",
        pena_min_dias=t.pena_min_dias / 2,
        pena_max_dias=t.pena_max_dias / 2,
        tentativa=True,
    )


_HOMICIDIO = TipoPenal("Homicídio", "art. 121, CP", 6 * ANO, 20 * ANO)
_SEQUESTRO = TipoPenal("Sequestro", "art. 148, CP", 1 * ANO, 3 * ANO)
_VIAS_DE_FATO = TipoPenal("Vias de fato", "art. 21, LCP", 15, 3 * MES)
_LESAO = TipoPenal("Lesão corporal", "art. 129, CP", 3 * MES, 1 * ANO)

# Lei nº 15.397/2026 elevou a pena do roubo simples para 6 a 10 anos e a máxima
# do furto simples para 6 anos. A tabela usa a redação vigente — ver a seção
# "Mudança de lei durante o período" em docs/taxonomia_ocorrencias.md.
TIPOS: dict[str, TipoPenal] = {
    "homicidio": _HOMICIDIO,
    "estupro": TipoPenal("Estupro", "art. 213, CP", 6 * ANO, 10 * ANO),
    "roubo": TipoPenal("Roubo a transeunte", "art. 157, CP (Lei 15.397/2026)", 6 * ANO, 10 * ANO),
    "tentativa_homicidio": _tentativa(_HOMICIDIO, "Tentativa de homicídio"),
    "disparo_arma_fogo": TipoPenal("Disparo de arma de fogo", "art. 15, Lei 10.826/2003", 2 * ANO, 4 * ANO),
    "furto": TipoPenal("Furto a transeunte", "art. 155, CP (Lei 15.397/2026)", 1 * ANO, 6 * ANO),
    "importunacao_sexual": TipoPenal("Importunação sexual", "art. 215-A, CP", 1 * ANO, 5 * ANO),
    "tentativa_sequestro": _tentativa(_SEQUESTRO, "Tentativa de sequestro"),
    "lesao_corporal": _LESAO,
    "ato_obsceno": TipoPenal("Ato obsceno", "art. 233, CP", 3 * MES, 1 * ANO),
    "ameaca": TipoPenal("Ameaça", "art. 147, CP", 1 * MES, 6 * MES),
    "vias_de_fato": _VIAS_DE_FATO,
    # Tentativa de contravenção não é punível (art. 4º da LCP), então "tentativa
    # de agressão" não pode ser tentativa de vias de fato. O tipo menos grave
    # compatível e punível é a tentativa de lesão corporal.
    "tentativa_lesao_corporal": _tentativa(_LESAO, "Tentativa de agressão"),
}


def pena_de_referencia(tipo: TipoPenal, estrategia: str = "minima") -> float:
    if estrategia == "minima":
        return tipo.pena_min_dias
    if estrategia == "media":
        return (tipo.pena_min_dias + tipo.pena_max_dias) / 2
    raise ValueError(f"estratégia desconhecida: {estrategia!r} (use 'minima' ou 'media')")


def pesos(estrategia: str = "minima") -> dict[str, float]:
    """Peso de 0 a 1 por tipo: pena de referência ÷ maior pena de referência."""
    ref = {k: pena_de_referencia(t, estrategia) for k, t in TIPOS.items()}
    teto = max(ref.values())
    return {k: v / teto for k, v in ref.items()}


def tabela(estrategia: str = "minima"):
    """A tabela de pesos como DataFrame, para o relatório e a documentação."""
    import pandas as pd

    p = pesos(estrategia)
    return (
        pd.DataFrame(
            [
                {
                    "tipo": k,
                    "rotulo": t.rotulo,
                    "base_legal": t.base_legal,
                    "pena_referencia_dias": pena_de_referencia(t, estrategia),
                    "peso": p[k],
                }
                for k, t in TIPOS.items()
            ]
        )
        .sort_values("peso", ascending=False)
        .reset_index(drop=True)
    )
