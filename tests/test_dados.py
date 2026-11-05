"""Testes dos dados que o painel lê: formato, cobertura contra os totais dos agregados e faixas plausíveis.
Os limites de cobertura são os medidos na montagem (medidos na montagem dos arquivos), com folga pequena."""
import json
from pathlib import Path

import pandas as pd
import pytest

D = Path(__file__).resolve().parents[1] / "data"
mun = pd.read_csv(D / "municipios.csv", dtype={"cod": str})
perfil = json.loads((D / "perfil_agregados.json").read_text(encoding="utf-8"))
popproj = pd.read_csv(D / "pop_uf_projecao.csv")
malha = json.loads((D / "municipios.geojson").read_text(encoding="utf-8"))
com_poligono = {f["properties"]["codarea"][:6] for f in malha["features"]}
nomes = pd.read_csv(D / "municipios_nomes.csv", dtype=str)

ARQ = {"sim": "sim_obitos.csv", "sih": "sihsus_internacoes.csv", "tiss": "tiss_cons_eventos.csv",
       "sib": "sib_vinculos.csv", "ibge": "ibge_pop_municipio.csv"}
# cobertura mínima da soma por município contra o total do agregado (medida em 04/11/2026, com folga)
COBERTURA_MIN = {"sim": 0.975, "sih": 0.96, "tiss": 0.965, "sib": 0.999, "ibge": 0.999}


def total(base):
    return mun[mun["base"] == base].groupby("ano")["valor"].sum()


def test_formato():
    assert list(mun.columns) == ["base", "ano", "cod", "valor"]
    assert set(mun["base"]) == set(ARQ)
    assert mun["cod"].str.fullmatch(r"\d{6}").all()
    assert (mun["valor"] >= 0).all()
    assert not mun.duplicated(["base", "ano", "cod"]).any()


@pytest.mark.parametrize("base", list(ARQ))
def test_cobertura_contra_o_agregado(base):
    ref = pd.Series({int(k): v for k, v in perfil[ARQ[base]]["por_ano"].items()})
    soma = total(base)
    comum = soma.index.intersection(ref.index)
    assert len(comum) > 0
    cob = soma[comum] / ref[comum]
    assert cob.min() >= COBERTURA_MIN[base], (base, cob.idxmin(), cob.min())
    assert cob.max() <= 1.0001, (base, cob.idxmax(), cob.max())


@pytest.mark.parametrize("base", list(ARQ))
def test_poucos_codigos_sem_poligono_nos_anos_recentes(base):
    t = mun[(mun["base"] == base) & (mun["ano"] >= 2010)]
    fora = t.loc[~t["cod"].isin(com_poligono), "valor"].sum() / t["valor"].sum()
    assert fora < 0.01, (base, fora)


def test_so_um_municipio_sem_poligono_na_lista_de_nomes():
    sem = set(nomes["cod7"].str[:6]) - com_poligono
    assert sem == {"510183"}, sem


def test_populacao_por_estado_completa():
    assert popproj["uf"].nunique() == 27
    por_ano = popproj.groupby("ano")["uf"].nunique()
    assert (por_ano[(por_ano.index >= 2000) & (por_ano.index <= 2030)] == 27).all()
    assert {2022, 2023} <= set(popproj["ano"])
    br_2019 = popproj[popproj["ano"] == 2019]["pop"].sum()
    assert 200e6 < br_2019 < 215e6


def test_populacao_estado_igual_soma_municipal_em_2024():
    m = mun[(mun["base"] == "ibge") & (mun["ano"] == 2024)]
    assert m["valor"].sum() == popproj[popproj["ano"] == 2024]["pop"].sum()


def test_taxas_brutas_brasil_em_faixa_plausivel():
    pop = popproj.groupby("ano")["pop"].sum()
    obitos, internacoes = total("sim"), total("sih")
    assert 550 < obitos[2019] / pop[2019] * 1e5 < 720          # mortalidade bruta de cerca de 6 por mil
    assert obitos[2021] > obitos[2019]                          # a covid aparece em 2021
    assert 4000 < internacoes[2019] / pop[2019] * 1e5 < 7500   # internações no SUS por 100 mil habitantes


def test_sih_bate_com_o_total_anual_de_referencia():
    """Totais anuais de referência das internações no SUS (conferidos em 04/11/2026)."""
    s = total("sih")
    assert s[2000] == 11_937_323 - 1   # 1 internação de 2000 sem município de residência válido (log da montagem)
    assert s[2008] == 10_743_603       # nenhuma sem município


def test_sih_2025_e_2026_dos_dbc_seguem_a_relacao_dos_anos_anteriores():
    """2025 e 2026 vieram direto dos arquivos mensais. Contra o total por estado e ano, que inclui as internações de
    longa permanência, a razão é estável: 0,9895 em 2023, 0,9906 em 2024, 0,9908 em 2025 e 2026."""
    ref = {int(k): v for k, v in perfil["sihsus_internacoes.csv"]["por_ano"].items()}
    s = total("sih")
    assert {2025, 2026} <= set(s.index)
    for ano in (2023, 2024, 2025, 2026):
        assert 0.985 < s[ano] / ref[ano] < 0.995, (ano, s[ano] / ref[ano])
