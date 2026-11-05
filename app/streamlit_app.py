"""Saúde no Brasil: painel de dados públicos de mortalidade, internações, planos de saúde e população.

Todo número exibido é calculado de arquivos em data/; nada é digitado à mão na tela.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mapas as fig  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
st.set_page_config(page_title="Saúde no Brasil: dados públicos", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2.4rem; max-width: 1500px;}
h1 {letter-spacing: -0.02em;}
.sub {color: #9aa4b2; font-size: 1.02rem; margin: -0.4rem 0 1.1rem 0;}
.cartao {background: #161b26; border: 1px solid #232b3a; border-left: 6px solid var(--cor); border-radius: 12px;
         padding: 14px 18px; margin: 4px 0 10px 0; height: 100%;}
.cartao .topo {font-size: 0.92rem; color: #cbd5e1; margin-bottom: 2px;}
.cartao .num {font-size: 2.1rem; font-weight: 700; line-height: 1.15; color: #f3f6fa;}
.cartao .rodape {color: #9aa4b2; font-size: 0.84rem; margin-top: 2px;}
.ficha {background: #161b26; border: 1px solid #232b3a; border-left: 6px solid var(--cor); border-radius: 12px;
        padding: 18px 22px; margin: 6px 0 12px 0;}
.ficha h3 {margin: 0 0 4px 0;}
.ficha .campo {margin: 6px 0; color: #cbd5e1;} .ficha .campo b {color: #f3f6fa;}
.ficha code {font-size: 0.82rem;}
.etiqueta {display: inline-block; padding: 2px 11px; border-radius: 12px; font-size: 0.78rem; background: #232b3a;
           color: #cbd5e1; margin-left: 8px; vertical-align: middle;}
</style>
""", unsafe_allow_html=True)

SECOES = [
    "Início",
    "1. De onde vêm os dados?",
    "2. De quando são?",
    "3. Onde estão no país?",
    "4. Como é um registro?",
    "5. Como as bases se cruzam?",
]

# Uma família por tipo de dado: nome de uso comum, cor fixa, tabela do perfil, unidade.
FAMILIAS = {
    "sim": dict(nome="Óbitos", cor="obitos", arq="sim_obitos.csv", unidade="óbitos", taxa=True),
    "sih": dict(nome="Internações no SUS", cor="sus", arq="sihsus_internacoes.csv", unidade="internações", taxa=True),
    "tiss": dict(nome="Internações em planos de saúde", cor="planos", arq="tiss_cons_eventos.csv",
                 unidade="internações", taxa=False),
    "sib": dict(nome="Vínculos com planos de saúde", cor="vinculos", arq="sib_vinculos.csv",
                unidade="vínculos ativos", taxa=False),
    "ibge": dict(nome="População", cor="pop", arq="ibge_pop_municipio.csv", unidade="habitantes", taxa=False),
}
# Tabela resumida -> arquivo bruto de onde sai a amostra.
BRUTO_DO_RESUMO = {"sim_obitos.csv": "SIM", "sihsus_internacoes.csv": "SIH", "tiss_cons_eventos.csv": "TISS",
                   "sib_vinculos.csv": "SIB"}
RESUMOS = {"sim_obitos.csv": "Óbitos", "sihsus_internacoes.csv": "Internações no SUS",
           "tiss_cons_eventos.csv": "Internações em planos de saúde", "sib_vinculos.csv": "Vínculos com planos de saúde"}
# Nome de uso comum e família de cada tabela agregada.
TABELAS = {
    "sim_obitos.csv": ("Óbitos no Brasil", "obitos"),
    "sih_atual": ("Internações no SUS", "sus"),
    "tiss_cons_eventos.csv": ("Internações em planos de saúde", "planos"),
    "sib_vinculos.csv": ("Vínculos com planos de saúde", "vinculos"),
    "ibge_pop.csv": ("População por estado (IBGE)", "pop"),
    "ibge_pop_municipio.csv": ("População por município (IBGE)", "pop"),
    "wpp_pop.csv": ("População de 5 países (ONU)", "pop"),
    "who_obitos.csv": ("Óbitos de vários países (OMS)", "obitos"),
    "gbd_obitos.csv": ("Óbitos estimados (IHME)", "obitos"),
    "tabuas_soa_iba.csv": ("Tábuas de mortalidade (SOA e IBA)", "outros"),
}
COR_DA_BASE = {"SIM": "obitos", "WHO": "obitos", "GBD 2023": "obitos", "SIH-SUS": "sus", "TISS hospitalar": "planos",
               "SIB": "vinculos", "IBGE": "pop", "WPP": "pop", "SOA": "outros", "IBA": "outros"}

UF = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
      "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
      "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
SIGLA_COD = {v: k for k, v in UF.items()}
MIN_CASOS = 5  # abaixo disso o município fica cinza: "poucos casos"




CRUZAMENTOS = {
    "Óbitos × população": ("Feito neste painel", "município (ou estado) e ano",
                           "Divide os óbitos do ano pela população do mesmo lugar e ano: é a taxa por 100 mil habitantes do mapa.",
                           "O município vale o de residência da pessoa. A população municipal só existe para 2015 a 2021 e "
                           "2024 em diante, e as duas fases são de revisões diferentes do IBGE."),
    "Internações no SUS × população": ("Feito neste painel", "município (ou estado) e ano",
                                       "Divide as internações do ano pela população do mesmo lugar e ano.",
                                       "Vale o município de residência do paciente, não o do hospital. O último ano disponível "
                                       "está incompleto e fica de fora da taxa."),
    "Internações em planos × população": ("Possível, não feito aqui", "município do beneficiário e ano",
                                          "Daria a internação em plano por habitante, ou por vínculo, em cada município.",
                                          "A contagem soma linhas do arquivo, não eventos distintos, e a população só cobre "
                                          "parte dos anos."),
    "Vínculos com planos × população": ("Possível, não feito aqui", "município e ano",
                                        "Daria a parcela da população com plano de saúde em cada município.",
                                        "O arquivo de vínculos é uma fotografia de uma data só; ele tem vínculos ativos e inativos."),
    "Óbitos × internações no SUS": ("Possível, não feito aqui", "município de residência, ano e causa (CID-10)",
                                    "Compararia onde se morre com onde se interna, pela mesma causa.",
                                    "Antes de 1996 os óbitos usam CID-9; as duas bases só têm o código de causa em comum a "
                                    "partir daí."),
    "Países (OMS e ONU)": ("Possível, não feito aqui", "país e ano",
                           "Daria a mortalidade por habitante de cada país, juntando óbitos da OMS e população da ONU.",
                           "Cada fonte nomeia os países de um jeito, então é preciso uma tabela de equivalência entre eles."),
}

CAMPOS = [
    ("Óbitos", "Residência da pessoa (6 dígitos; 7 até 1995)", "1 = masculino, 2 = feminino", "Código com unidade e valor"),
    ("Internações no SUS", "Residência do paciente (6 dígitos)", "1 = masculino, 3 = feminino", "Em anos"),
    ("Internações em planos", "Residência do beneficiário (6 dígitos)", "Masculino, Feminino", "Só faixa etária"),
    ("Vínculos com planos", "Residência do beneficiário (6 dígitos)", "M, F", "Só o ano de nascimento"),
    ("População (IBGE)", "Código de 7 dígitos; os 6 primeiros batem com as demais", "Ambos, Homens, Mulheres", "Idade simples"),
]

GRAFO = """digraph G {
 rankdir=LR; bgcolor="transparent"; nodesep=0.3; ranksep=1.2;
 node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=14, fontcolor="#0e1117", color="transparent", margin="0.2,0.12"];
 edge [color="#9aa4b2", fontcolor="#cbd5e1", fontname="Helvetica", fontsize=12, penwidth=1.6, arrowhead=none];
 SIM [label="Óbitos", fillcolor="#d9585a"];
 SIH [label="Internações no SUS", fillcolor="#3a88cc"];
 TIS [label="Internações em planos", fillcolor="#2e9e66"];
 SIB [label="Vínculos com planos", fillcolor="#bf8a24"];
 IBG [label="População (IBGE)", fillcolor="#8d6cc4"];
 WHO [label="Óbitos de países (OMS)", fillcolor="#d9585a"];
 WPP [label="População de países (ONU)", fillcolor="#8d6cc4"];
 SIM -> IBG [label="município e ano\nfeito"];
 SIH -> IBG [label="município e ano\nfeito"];
 TIS -> IBG [label="município e ano", style=dotted];
 SIB -> IBG [label="município", style=dotted];
 SIM -> SIH [label="município, ano e causa", style=dotted];
 WHO -> WPP [label="país e ano", style=dotted];
}"""


@st.cache_data
def carregar():
    perfil = json.loads((DATA / "perfil_agregados.json").read_text(encoding="utf-8"))
    fontes = pd.read_csv(DATA / "fontes.csv", dtype=str).fillna("")
    amostras = json.loads((DATA / "amostras.json").read_text(encoding="utf-8"))
    mun = pd.read_csv(DATA / "municipios.csv", dtype={"cod": str})
    nomes = pd.read_csv(DATA / "municipios_nomes.csv", dtype=str)
    nomes = {c[:6]: f"{n} ({u})" for c, n, u in zip(nomes["cod7"], nomes["nome"], nomes["uf"])}
    popproj = pd.read_csv(DATA / "pop_uf_projecao.csv")
    return perfil, fontes, amostras, mun, nomes, popproj


@st.cache_resource
def carregar_geo():
    uf = fig.orientar(json.loads((DATA / "uf.geojson").read_text(encoding="utf-8")))
    m = fig.orientar(json.loads((DATA / "municipios.geojson").read_text(encoding="utf-8")))
    sete = {f["properties"]["codarea"][:6]: f["properties"]["codarea"] for f in m["features"]}
    return uf, m, sete


perfil, fontes, amostras, mun, nomes, popproj = carregar()


# ------------------------------------------------------------------ formatação
def inteiro(n):
    return f"{int(round(n)):,}".replace(",", ".")


def decimal(n, casas=1):
    return f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def milhoes(n):
    return f"{decimal(n / 1e6)} milhões"


def ir(secao):
    st.session_state["secao"] = secao


def titulo(texto, sub):
    st.header(texto)
    st.markdown(f'<div class="sub">{sub}</div>', unsafe_allow_html=True)


def cartao(topo, numero, rodape, cor):
    st.markdown(f'<div class="cartao" style="--cor:{fig.COR[cor]}"><div class="topo">{topo}</div>'
                f'<div class="num">{numero}</div><div class="rodape">{rodape}</div></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ dados derivados
def total_por_ano(arq):
    return pd.Series({int(k): v for k, v in perfil[arq]["por_ano"].items()}).sort_index()


def serie_total(chave):
    """Total por ano de uma família. Internações no SUS são a soma dos municípios."""
    if chave == "sih":
        return mun[mun["base"] == "sih"].groupby("ano")["valor"].sum().sort_index()
    return total_por_ano(FAMILIAS[chave]["arq"])


def info_tabela(k):
    if k == "sih_atual":
        s = serie_total("sih")
        return {"ano_min": int(s.index.min()), "ano_max": int(s.index.max()), "anos_distintos": int(len(s))}
    return perfil[k]


def incompletos_chave(chave):
    """Meses faltantes por ano (só para as bases mensais)."""
    arq = "sihsus_internacoes.csv" if chave == "sih" else FAMILIAS[chave]["arq"]
    inc = incompletos(arq)
    return {a: n for a, n in inc.items() if a in serie_total(chave).index}


def incompletos(arq):
    """Anos com menos de 12 meses (só para as bases mensais)."""
    if arq == "sib_vinculos.csv":
        return {}
    return {int(a): int(n) for a, n in perfil[arq].get("meses_por_ano", {}).items() if n < 12}


def pop_uf():
    """População por estado (índice ano, código IBGE de 2 dígitos): projeção do IBGE por estado, uma série só, de 2000
    a 2070. As estimativas municipais de 2015 a 2021 são de outra revisão e diferem até 10% por estado."""
    p = popproj.copy()
    p["uf"] = p["uf"].map(SIGLA_COD)
    return p.groupby(["ano", "uf"])["pop"].sum()


def anos_municipais_com_populacao():
    return {int(a) for a in mun[mun["base"] == "ibge"]["ano"].unique()}


def valores_uf(chave, ano):
    """Total por estado em um ano (índice: código IBGE de 2 dígitos). Óbitos e vínculos vêm do agregado por
    estado; internações (SUS e planos) e população, da soma dos municípios."""
    if chave in ("tiss", "ibge", "sih"):
        t = mun[(mun["base"] == chave) & (mun["ano"] == ano)].copy()
        t["uf"] = t["cod"].str[:2]
        return t.groupby("uf")["valor"].sum()
    reg = pd.DataFrame(perfil[FAMILIAS[chave]["arq"]]["por_uf_ano"], columns=["ano", "uf", "valor"])
    reg = reg[reg["ano"] == ano]
    reg["uf"] = reg["uf"].map(lambda u: SIGLA_COD.get(u, u))
    return reg[reg["uf"].isin(UF)].groupby("uf")["valor"].sum()


def anos_com_taxa(chave, nivel):
    """Anos em que há contagem completa e população para dividir (a população muda com o nível)."""
    pop = {a for a, _ in pop_uf().index} if nivel == "Estados" else anos_municipais_com_populacao()
    return sorted(pop & (set(serie_total(chave).index) - set(incompletos_chave(chave))))


# ------------------------------------------------------------------ navegação
if "secao" not in st.session_state:
    st.session_state["secao"] = SECOES[0]
st.sidebar.radio("Seções", SECOES, key="secao")
secao = st.session_state["secao"]

# ------------------------------------------------------------------ início
if secao == SECOES[0]:
    st.title("Saúde no Brasil: dados públicos")
    st.markdown('<div class="sub">Óbitos, internações, planos de saúde e população: de onde vêm os dados, '
                'de quando são e onde no país eles estão.</div>', unsafe_allow_html=True)
    sim, sih, tiss = (serie_total(k) for k in ("sim", "sih", "tiss"))
    c = st.columns(5)
    with c[0]:
        cartao("Óbitos registrados", milhoes(sim.sum()), f"{sim.index.min()} a {sim.index.max()}", "obitos")
    with c[1]:
        cartao("Internações no SUS", milhoes(sih.sum()), f"{sih.index.min()} a {sih.index.max()}", "sus")
    with c[2]:
        cartao("Internações em planos de saúde", milhoes(tiss.sum()), f"{tiss.index.min()} a {tiss.index.max()}",
               "planos")
    with c[3]:
        v = total_por_ano("sib_vinculos.csv")
        cartao("Vínculos ativos em planos", milhoes(v.iloc[-1]), f"fotografia de {v.index[-1]}", "vinculos")
    with c[4]:
        p = total_por_ano("ibge_pop_municipio.csv")
        cartao("Habitantes (IBGE)", milhoes(p.iloc[-1]), f"estimativa de {p.index[-1]}", "pop")
    st.markdown("##### Por onde começar")
    b = st.columns(5)
    for col, s, txt in zip(b, SECOES[1:], ["De onde vêm?", "De quando são?", "Onde estão?", "Como é um registro?",
                                           "Como se cruzam?"]):
        col.button(txt, key=f"hub_{s}", on_click=ir, args=(s,), width="stretch")
    st.caption("Dados públicos do Ministério da Saúde, da ANS e do IBGE, sem resultado de análise. As internações em "
               "planos somam linhas do arquivo, não eventos distintos.")

# ------------------------------------------------------------------ 1. origem
elif secao == SECOES[1]:
    titulo(SECOES[1], "Cada base, a fonte oficial e o endereço de onde se baixa.")
    grupo = st.radio("Tipo de dado", ["Todos"] + sorted(fontes["grupo"].unique()), horizontal=True, key="origem_grupo")
    vis = fontes if grupo == "Todos" else fontes[fontes["grupo"] == grupo]
    base = st.selectbox("Base", vis["base"].tolist(), key="origem_base")
    f = vis[vis["base"] == base].iloc[0]
    cor = fig.COR[COR_DA_BASE.get(base, "outros")]
    st.markdown(
        f'<div class="ficha" style="--cor:{cor}"><h3>{f["base"]}</h3>{f["o_que_e"]}.'
        f'<div class="campo"><b>Fonte:</b> {f["fonte"]}</div>'
        f'<div class="campo"><b>Endereço:</b> <code>{f["link"]}</code></div>'
        f'<div class="campo"><b>Como se obtém:</b> {f["como_obtido"]}</div>'
        + (f'<div class="campo" style="color:#9aa4b2">{f["observacao"]}</div>' if f["observacao"] else "")
        + "</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ 2. período
elif secao == SECOES[2]:
    titulo(SECOES[2], "Do primeiro ao último ano de cada base, e quanto há em cada ano.")
    ks = list(TABELAS)
    it = {k: info_tabela(k) for k in ks}
    st.plotly_chart(fig.periodo([TABELAS[k][0] for k in ks], [it[k]["ano_min"] for k in ks],
                                [it[k]["ano_max"] for k in ks], [fig.COR[TABELAS[k][1]] for k in ks],
                                [it[k]["anos_distintos"] for k in ks]), width="stretch",
                    config={"responsive": True})
    buracos = [TABELAS[k][0] for k in ks
               if it[k]["anos_distintos"] < it[k]["ano_max"] - it[k]["ano_min"] + 1]
    if buracos:
        st.warning("Faltam anos dentro da faixa em: " + "; ".join(buracos) + ".")
    chave = st.radio("Quanto há em cada ano", ["sim", "sih", "tiss"], horizontal=True, key="serie_base",
                     format_func=lambda k: FAMILIAS[k]["nome"])
    fam = FAMILIAS[chave]
    pa = serie_total(chave)
    inc = incompletos_chave(chave)
    f2 = fig.serie_anual(pa.index, pa.values, fig.COR[fam["cor"]], inc, rotulo_y=fam["unidade"].capitalize())
    if chave == "sim":
        f2.add_vline(x=1996, line_dash="dot", line_color=fig.TEXTO_SUAVE, annotation_text="CID-10 (CID-9 até 1995)",
                     annotation_font_color=fig.TEXTO_SUAVE)
    st.plotly_chart(f2, width="stretch", config={"responsive": True})
    ult = pa.index[-1] if pa.index[-1] not in inc else pa.index[-2]
    st.success(f"{fam['nome']}: {inteiro(pa.iloc[0])} em {pa.index[0]} e {inteiro(pa.loc[ult])} em {ult}.")

# ------------------------------------------------------------------ 3. mapa
elif secao == SECOES[3]:
    titulo(SECOES[3], "Mapa por estado ou município, com os 10 maiores ao lado.")
    geo_uf, geo_mun, sete = carregar_geo()
    c1, c2, c3 = st.columns([3, 1.2, 1.5])
    chave = c1.radio("O que mostrar", list(FAMILIAS), horizontal=True, key="mapa_base",
                     format_func=lambda k: FAMILIAS[k]["nome"])
    fam = FAMILIAS[chave]
    nivel = c2.radio("Nível", ["Estados", "Municípios"], horizontal=True, key="mapa_nivel")
    medida = c3.radio("Medida", ["Total", "Por 100 mil habitantes"], horizontal=True, key="mapa_medida") \
        if fam["taxa"] else "Total"
    taxa = medida != "Total"
    if taxa:
        anos = anos_com_taxa(chave, nivel)
    elif nivel == "Estados" and chave in ("sim", "sib"):
        anos = sorted(int(a) for a in perfil[fam["arq"]]["por_ano"])
    else:
        anos = sorted(int(a) for a in mun[mun["base"] == chave]["ano"].unique())
    ano = anos[0] if len(anos) == 1 else st.select_slider("Ano", options=anos, value=anos[-1])
    cor = fig.COR[fam["cor"]]
    unidade = "por 100 mil habitantes" if taxa else fam["unidade"]
    pop = pop_uf()
    notas, poucos, fora = [], 0, 0.0

    if nivel == "Estados":
        v = valores_uf(chave, ano)
        brasil_total = float(v.sum())
        if taxa:
            v = (v / pop.xs(ano, level="ano").reindex(v.index) * 1e5).dropna()
        casas = 1 if taxa else 0
        txt = [f"{UF[c]}: {decimal(x, casas)}{' por 100 mil' if taxa else ''}" for c, x in v.items()]
        mapa = fig.mapa(geo_uf, geo_uf, v.index, v.values, txt, cor, titulo_barra=unidade, altura=680)
        top = v.sort_values(ascending=False).head(10)
        if taxa:
            brasil = brasil_total / float(pop.xs(ano, level="ano").sum()) * 1e5
            ref, ref_txt = brasil, f"Brasil: {decimal(brasil)}"
        else:
            ref, ref_txt = float(v.mean()), f"média dos estados: {inteiro(v.mean())}"
        rank = fig.barras([UF[c] for c in top.index], list(top.values), [decimal(x, casas) for x in top.values],
                          cor, ref, ref_txt)
        achado = (f"{len(v)} das 27 UFs com dado em {ano}. Maior valor: {UF[top.index[0]]}, "
                  f"{decimal(top.iloc[0], casas)} {unidade}.")
        rank_tit = f"Os 10 estados com mais {fam['unidade']}" + (" por 100 mil" if taxa else "")
        tabela = pd.DataFrame({"Estado": [UF[c] for c in v.index], unidade: v.values}).sort_values(unidade, ascending=False)
    else:
        casos = mun[(mun["base"] == chave) & (mun["ano"] == ano)].set_index("cod")["valor"]
        d = casos.copy()
        if taxa:
            pm = mun[(mun["base"] == "ibge") & (mun["ano"] == ano)].set_index("cod")["valor"]
            d = (d / pm.reindex(d.index) * 1e5).dropna()
        if chave != "ibge":
            poucos = int((casos < MIN_CASOS).sum())
            d = d[casos.reindex(d.index) >= MIN_CASOS]  # menos de 5: fica cinza, "poucos casos"
        d = d[d.index.isin(sete)]
        casas = 1 if taxa else 0
        txt = [f"{nomes.get(c, c)}: {decimal(x, casas)}{' por 100 mil' if taxa else ''}" for c, x in d.items()]
        mapa = fig.mapa(geo_mun, geo_uf, [sete[c] for c in d.index], d.values, txt, cor, usar_log=True,
                        titulo_barra=unidade, altura=760)
        if taxa:
            cand = d[d.index.isin(pm[pm >= 100_000].index)]
            rank_tit = f"Os 10 municípios com mais {fam['unidade']} por 100 mil (entre os de 100 mil habitantes ou mais)"
            brasil = float(casos.sum()) / float(pm.sum()) * 1e5
            ref, ref_txt = brasil, f"Brasil: {decimal(brasil)}"
        else:
            cand = d
            rank_tit = f"Os 10 municípios com mais {fam['unidade']}"
            ref, ref_txt = float(d.median()), f"mediana dos municípios: {inteiro(d.median())}"
        top = cand.sort_values(ascending=False).head(10)
        rank = fig.barras([nomes.get(c, c) for c in top.index], list(top.values), [decimal(x, casas) for x in top.values],
                          cor, ref, ref_txt)
        achado = f"{inteiro(len(d))} de {inteiro(len(geo_mun['features']))} municípios com dado em {ano}."
        tabela = pd.DataFrame({"Município": [nomes.get(c, c) for c in d.index], "Código IBGE": list(d.index),
                               unidade: d.values}).sort_values(unidade, ascending=False)
        total_ano = serie_total(chave).get(ano)
        if not taxa and total_ano:
            fora = max(float(total_ano) - float(casos[casos.index.isin(sete)].sum()), 0.0)
        notas.append("Cada tom a mais é 10 vezes maior. Cinza: sem dado" + ("." if chave == "ibge" else " ou poucos casos."))
        if poucos:
            notas.append(f"{inteiro(poucos)} municípios têm menos de {MIN_CASOS} casos.")
        if fora >= 1:
            notas.append(f"{inteiro(fora)} registros ficam fora do mapa por não ter município válido.")
    ca, cb = st.columns([2.3, 1])
    with ca:
        st.plotly_chart(mapa, width="stretch", config=fig.CONFIG_MAPA)
    with cb:
        st.markdown(f"**{rank_tit}, {ano}**")
        st.plotly_chart(rank, width="stretch", config={"responsive": True})
    st.success(achado)
    with st.expander("Ver os números deste mapa"):
        st.dataframe(tabela, hide_index=True, width="stretch", height=320)
        st.download_button("Baixar CSV", tabela.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{chave}_{nivel.lower()}_{ano}.csv", mime="text/csv")
    meses_ano = incompletos_chave(chave).get(int(ano))
    if meses_ano:
        notas.insert(0, f"{ano} está incompleto: só {meses_ano} meses de dado, então o total não é comparável com os anos fechados.")
    if chave == "tiss":
        notas.append("Vale o município onde o beneficiário mora, não onde o hospital fica.")
    if chave == "sib":
        notas.append("Fotografia mais recente; não foi verificado se inclui planos odontológicos.")
    if taxa:
        notas.append("Taxa bruta, sem ajustar por idade. Visão exploratória, não é um resultado validado. "
                     + ("População: projeção do IBGE por estado."
                        if nivel == "Estados" else
                        "População: estimativa municipal do IBGE; as de 2015 a 2021 e as de 2024 em diante são de "
                        "revisões diferentes, então não compare as duas fases."))
    if notas:
        st.caption(" ".join(notas))

# ------------------------------------------------------------------ 4. registro
elif secao == SECOES[4]:
    titulo(SECOES[4], "Uma linha real do arquivo de origem e a linha da tabela resumida em que ela se transforma.")
    ag = st.selectbox("Base", list(RESUMOS), format_func=lambda k: RESUMOS[k], key="linha_base")
    r = amostras["brutos"][BRUTO_DO_RESUMO[ag]]
    st.markdown(f"##### Arquivo de origem: {r['uma_linha_e']}")
    st.dataframe(pd.DataFrame(r["linhas"], columns=r["colunas"]), hide_index=True, width="stretch")
    st.caption(f"{r['arquivo']}, {r['n_colunas']} colunas (aqui só algumas, sem datas completas nem números de "
               f"identificação). {r['como_ler']}")
    st.markdown("##### Tabela resumida: uma linha por combinação de chaves")
    am = amostras["resumos"][ag]
    st.dataframe(pd.DataFrame(am["linhas"], columns=am["colunas"]), hide_index=True, width="stretch")
    st.caption(f"{inteiro(perfil[ag]['linhas'])} linhas no total. A última coluna é a contagem de registros que "
               f"têm exatamente aquelas chaves.")
    if ag == "tiss_cons_eventos.csv":
        st.warning("Neste resumo a contagem é de linhas do arquivo, não de eventos distintos.")
    if ag == "sib_vinculos.csv":
        st.warning("Só a fotografia mais recente, com vínculos ativos e inativos.")

# ------------------------------------------------------------------ 5. cruzamentos
else:
    titulo(SECOES[5], "Quais bases podem ser ligadas, por qual campo em comum e o que muda de uma para outra.")
    st.graphviz_chart(GRAFO)  # tamanho natural: esticar a largura escala o desenho além da altura da tela
    st.caption("Linha cheia: ligação feita neste painel (taxa por 100 mil habitantes no mapa). Pontilhada: os dois "
               "lados têm o campo em comum, mas a ligação não foi feita aqui. A cor da caixa é a da família do dado.")
    nome = st.radio("Detalhe da ligação", list(CRUZAMENTOS), horizontal=True, key="cruz_nome")
    situacao, chave, faz, atencao = CRUZAMENTOS[nome]
    st.markdown(f"**{nome}** · {situacao}  \n**Une por:** {chave}")
    st.markdown(faz)
    st.caption(atencao)
    st.markdown("##### Campo de município e de sexo em cada base")
    st.dataframe(pd.DataFrame(CAMPOS, columns=["Base", "Município", "Sexo", "Idade"]), hide_index=True,
                 width="stretch")
