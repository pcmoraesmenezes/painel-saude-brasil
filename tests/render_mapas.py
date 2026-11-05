"""Gera PNG das figuras (kaleido) sobre o fundo do tema escuro, para conferir o visual sem navegador.
Uso: python3 tests/render_mapas.py SAIDA_DIR"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "app"))
import mapas as fig  # noqa: E402

D = RAIZ / "data"
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
FUNDO = "#0e1117"


def salvar(f, nome, w=1100, h=None):
    f.update_layout(paper_bgcolor=FUNDO)
    f.write_image(str(out / nome), width=w, height=h or f.layout.height)


geo_uf = fig.orientar(json.loads((D / "uf.geojson").read_text()))
geo_m = fig.orientar(json.loads((D / "municipios.geojson").read_text()))
sete = {f["properties"]["codarea"][:6]: f["properties"]["codarea"] for f in geo_m["features"]}
mun = pd.read_csv(D / "municipios.csv", dtype={"cod": str})
nomes = pd.read_csv(D / "municipios_nomes.csv", dtype=str)
nomes = {c[:6]: f"{n} ({u})" for c, n, u in zip(nomes["cod7"], nomes["nome"], nomes["uf"])}

m = mun[(mun.base == "sim") & (mun.ano == 2019) & (mun.valor >= 5) & mun.cod.isin(sete)]
salvar(fig.mapa(geo_m, geo_uf, [sete[c] for c in m.cod], m.valor, [nomes.get(c, c) for c in m.cod], fig.COR["obitos"],
                usar_log=True, titulo_barra="óbitos", altura=640), "mun_obitos.png", 1000)
u = mun[(mun.base == "sih") & (mun.ano == 2019)].copy()
u["uf"] = u.cod.str[:2]
u = u.groupby("uf").valor.sum()
salvar(fig.mapa(geo_uf, geo_uf, u.index, u.values, [str(x) for x in u.values], fig.COR["sus"],
                titulo_barra="internações", altura=520), "uf_sus.png", 800)
top = u.sort_values(ascending=False).head(10)
salvar(fig.barras(list(top.index), list(top.values), [f"{int(v):,}".replace(",", ".") for v in top.values],
                  fig.COR["sus"], float(u.mean()), "média dos estados"), "ranking.png", 520)
perfil = json.loads((D / "perfil_agregados.json").read_text())
pa = pd.Series({int(k): v for k, v in perfil["tiss_cons_eventos.csv"]["por_ano"].items()}).sort_index()
salvar(fig.serie_anual(pa.index, pa.values, fig.COR["planos"], {}, "Internações"), "serie.png", 900)
sih = perfil["sihsus_internacoes.csv"]; pa2 = pd.Series({int(k): v for k, v in sih["por_ano"].items()}).sort_index()
salvar(fig.serie_anual(pa2.index, pa2.values, fig.COR["sus"], {2026: 7}, "Internações"), "serie_incompleto.png", 900)
ks = list(perfil)
salvar(fig.periodo(ks, [perfil[k]["ano_min"] for k in ks], [perfil[k]["ano_max"] for k in ks],
                   [fig.COR["sus"]] * len(ks), [perfil[k]["anos_distintos"] for k in ks]), "periodo.png", 900)
print("ok")
