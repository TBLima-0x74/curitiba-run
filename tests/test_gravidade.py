"""Testes dos pesos de gravidade derivados do Código Penal."""

import pytest

from curitiba_run.features import gravidade as g


def test_pesos_ficam_entre_zero_e_um_e_o_maior_vale_um():
    p = g.pesos()
    assert all(0 < v <= 1 for v in p.values())
    assert max(p.values()) == 1


def test_estupro_e_mais_grave_que_furto():
    p = g.pesos()
    assert p["estupro"] > p["furto"]


def test_tentativa_vale_metade_do_consumado():
    """Art. 14, parágrafo único: redução de 1/3 a 2/3; metade é o ponto médio."""
    p = g.pesos()
    assert p["tentativa_homicidio"] == pytest.approx(p["homicidio"] / 2)
    assert p["tentativa_lesao_corporal"] == pytest.approx(p["lesao_corporal"] / 2)


def test_nao_existe_tentativa_de_contravencao():
    """Art. 4º da LCP: tentativa de contravenção não é punível."""
    assert "tentativa_vias_de_fato" not in g.TIPOS


def test_pesos_sao_derivados_e_nao_digitados():
    """Mudar a pena na tabela muda o peso — não há número solto para esquecer."""
    t = g.TIPOS["furto"]
    assert g.pesos()["furto"] == pytest.approx(t.pena_min_dias / max(x.pena_min_dias for x in g.TIPOS.values()))


def test_estrategia_media_preserva_a_ordem_do_topo():
    media = g.pesos("media")
    assert media["homicidio"] == 1
    assert media["estupro"] > media["furto"] > media["vias_de_fato"]


def test_estrategia_desconhecida_falha():
    with pytest.raises(ValueError, match="estratégia"):
        g.pesos("maxima_inventada")


def test_tabela_tem_uma_linha_por_tipo_ordenada():
    t = g.tabela()
    assert len(t) == len(g.TIPOS)
    assert t["peso"].is_monotonic_decreasing
