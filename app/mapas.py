"""Figuras do painel em tema escuro: mapa, ranking, série anual e período.

Uma cor fixa por família de dado, a mesma em todas as figuras (paleta checada no modo escuro quanto à faixa
de luminosidade, à separação para daltonismo e ao contraste com o fundo).
Status (feito, pendente) nunca usa essas cores: usa estilo de linha.
"""
import numpy as np
import plotly.graph_objects as go

SUPERFICIE = "#0e1117"
TEXTO = "#e6edf3"
TEXTO_SUAVE = "#9aa4b2"
GRADE = "#232b3a"
CINZA_SEM_DADO = "#1d2430"
BORDA_UF = "#7d8795"

COR = {  # uma cor por família de dado
    "obitos": "#d9585a",
    "sus": "#3a88cc",
    "planos": "#2e9e66",
    "vinculos": "#bf8a24",
    "pop": "#8d6cc4",
    "outros": "#7d8795",
}
FUNDO_TRANSPARENTE = "rgba(0,0,0,0)"


def _hex(c):
    return np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def _misturar(a, b, t):
    m = _hex(a) * (1 - t) + _hex(b) * t
    return "#%02x%02x%02x" % tuple(int(round(x)) for x in m)


def rampa(cor):
    """Do escuro (cor misturada com o fundo) ao claro (cor misturada com branco), uma só matiz."""
    return [[0, _misturar(cor, SUPERFICIE, 0.78)], [0.45, _misturar(cor, SUPERFICIE, 0.25)],
            [0.8, cor], [1, _misturar(cor, "#ffffff", 0.6)]]


def orientar(geo):
    """A malha do IBGE vem com os anéis no sentido oposto ao que o plotly espera: sem inverter, cada
    polígono preenche o globo inteiro e o mapa vira um retângulo. Devolve cópia, sem alterar a original."""
    def inv(coords):
        return [list(reversed(anel)) for anel in coords]
    novo = {"type": geo["type"], "features": []}
    for f in geo["features"]:
        g = f["geometry"]
        c = inv(g["coordinates"]) if g["type"] == "Polygon" else [inv(p) for p in g["coordinates"]]
        novo["features"].append({"type": "Feature", "properties": f["properties"],
                                 "geometry": {"type": g["type"], "coordinates": c}})
    return novo


def _layout(fig, altura):
    fig.update_layout(template="plotly_dark", height=altura, paper_bgcolor=FUNDO_TRANSPARENTE,
                      plot_bgcolor=FUNDO_TRANSPARENTE, font=dict(color=TEXTO, size=13),
                      separators=",.", margin=dict(l=0, r=10, t=10, b=0))
    return fig


def mapa(geo_dados, geo_uf, locs, valores, hover, cor, usar_log=False, titulo_barra="", altura=600):
    """Mapa em coroplético. geo_dados e geo_uf já orientados. Camadas, de baixo para cima:
    estados em cinza (onde não há dado aparece cinza), os dados, e as bordas dos estados por cima.
    Com usar_log a cor segue log10, mas a barra e o texto do mouse mostram sempre o valor real."""
    valores = np.asarray(valores, dtype=float)
    z = np.log10(valores + 1) if usar_log else valores
    barra = dict(title=dict(text=titulo_barra, side="right"), thickness=12, len=0.9)
    zmin = zmax = None
    if usar_log and len(z):
        # a cor vai do percentil 2 ao 99,5 (os extremos não achatam o resto); o texto do mouse mostra o valor real
        zmin, zmax = float(np.nanpercentile(z, 2)), float(np.nanpercentile(z, 99.5))
        ticks = [k for k in range(0, int(np.ceil(zmax)) + 1) if zmin - 0.05 <= k <= zmax + 0.05]
        barra.update(tickvals=ticks, ticktext=[f"{10 ** k:,.0f}".replace(",", ".") for k in ticks])
    ufs = [f["properties"]["codarea"] for f in geo_uf["features"]]
    fig = go.Figure()
    fig.add_trace(go.Choropleth(geojson=geo_uf, featureidkey="properties.codarea", locations=ufs, z=[0] * len(ufs),
                                colorscale=[[0, CINZA_SEM_DADO], [1, CINZA_SEM_DADO]], showscale=False,
                                marker_line_width=0, hoverinfo="skip"))
    fig.add_trace(go.Choropleth(geojson=geo_dados, featureidkey="properties.codarea", locations=list(locs), z=z,
                                zmin=zmin, zmax=zmax, text=list(hover), colorscale=rampa(cor), colorbar=barra, marker_line_width=0,
                                hovertemplate="%{text}<extra></extra>"))
    fig.add_trace(go.Choropleth(geojson=geo_uf, featureidkey="properties.codarea", locations=ufs, z=[0] * len(ufs),
                                colorscale=[[0, FUNDO_TRANSPARENTE], [1, FUNDO_TRANSPARENTE]], showscale=False,
                                marker_line_width=0.7, marker_line_color=BORDA_UF, hoverinfo="skip"))
    # enquadramento fixo no Brasil (o ajuste automático deixava o mapa pequeno no meio da área)
    fig.update_geos(lonaxis_range=[-74.5, -33.5], lataxis_range=[-34.5, 5.8], visible=False,
                    bgcolor=FUNDO_TRANSPARENTE, domain=dict(x=[0, 1], y=[0, 1]))
    _layout(fig, altura)
    fig.update_layout(dragmode=False)  # sem arrastar nem zoom: a roda do mouse deve rolar a página, não o mapa
    return fig


# Configuração do componente de mapa: sem zoom pela roda do mouse e sem barra de ferramentas.
CONFIG_MAPA = {"responsive": True, "scrollZoom": False, "displayModeBar": False}


def barras(rotulos, valores, textos, cor, ref_valor=None, ref_texto="", altura=420):
    """Ranking: uma barra por item, um número no fim da barra, linha de referência rotulada."""
    ordem = np.argsort(valores)  # do menor ao maior; o plotly desenha de baixo para cima
    r = [rotulos[i] for i in ordem]
    v = [valores[i] for i in ordem]
    t = [textos[i] for i in ordem]
    fig = go.Figure(go.Bar(x=v, y=r, orientation="h", marker_color=cor, text=t, textposition="outside",
                           cliponaxis=False, hoverinfo="skip"))
    if ref_valor is not None:
        fig.add_vline(x=ref_valor, line_dash="dot", line_color=TEXTO_SUAVE, annotation_text=ref_texto,
                      annotation_position="top", annotation_font_color=TEXTO_SUAVE)
    fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(showgrid=False, automargin=True)
    _layout(fig, altura)
    fig.update_layout(margin=dict(l=0, r=70, t=30, b=10), showlegend=False)
    return fig


def serie_anual(anos, valores, cor, incompletos=None, rotulo_y=""):
    """Linha por ano. Anos incompletos saem em tracejado, com marcador vazado e o número de meses."""
    incompletos = incompletos or {}
    anos = list(anos)
    valores = list(valores)
    cheio = [i for i, a in enumerate(anos) if a not in incompletos]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[anos[i] for i in cheio], y=[valores[i] for i in cheio], mode="lines+markers",
                             line=dict(color=cor, width=2.5), marker=dict(size=6, color=cor),
                             hovertemplate="%{x}: %{y:,.0f}<extra></extra>", showlegend=False))
    for a, meses in incompletos.items():
        if a not in anos:
            continue
        i = anos.index(a)
        if i > 0:
            fig.add_trace(go.Scatter(x=[anos[i - 1], a], y=[valores[i - 1], valores[i]], mode="lines",
                                     line=dict(color=cor, width=2, dash="dot"), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=[a], y=[valores[i]], mode="markers+text", text=[f"só {meses} meses"],
                                 textposition="middle right", textfont=dict(color=TEXTO_SUAVE, size=12),
                                 marker=dict(size=9, color=SUPERFICIE, line=dict(color=cor, width=2)),
                                 hovertemplate="%{x} (incompleto): %{y:,.0f}<extra></extra>", showlegend=False))
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(gridcolor=GRADE, title=rotulo_y, rangemode="tozero", tickformat=",.0f")
    return _layout(fig, 340)


def periodo(nomes, inicio, fim, cores, anos_com_dado, altura=420):
    """Uma barra por tabela, do primeiro ao último ano, na cor da família do dado."""
    fig = go.Figure(go.Bar(y=nomes, x=[f - i + 1 for i, f in zip(inicio, fim)], base=inicio, orientation="h",
                           marker_color=cores, customdata=list(zip(inicio, fim, anos_com_dado)),
                           hovertemplate="%{y}<br>%{customdata[0]} a %{customdata[1]} "
                                         "(%{customdata[2]} anos com dado)<extra></extra>"))
    fig.update_xaxes(gridcolor=GRADE, title="")
    fig.update_yaxes(autorange="reversed", automargin=True)
    _layout(fig, altura)
    fig.update_layout(showlegend=False, bargap=0.35)
    return fig
