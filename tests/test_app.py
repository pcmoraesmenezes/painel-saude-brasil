"""Exercita cada seção e cada seletor do painel (AppTest headless)."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
APP = str(RAIZ / "app" / "streamlit_app.py")
SECOES = ["Início", "1. De onde vêm os dados?", "2. De quando são?", "3. Onde estão no país?",
          "4. Como é um registro?", "5. Como as bases se cruzam?"]
BASES_MAPA = ["sim", "sih", "tiss", "sib", "ibge"]


def novo(secao=None):
    at = AppTest.from_file(APP, default_timeout=120)
    if secao:
        at.session_state["secao"] = secao
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_inicio_e_botoes_do_hub():
    at = novo()
    for i in range(5):
        at = novo()
        at.button[i].click().run()
        assert not at.exception
        assert at.session_state["secao"] == SECOES[i + 1]


def test_origem_cada_base_e_grupo():
    at = novo(SECOES[1])
    for g in at.radio(key="origem_grupo").options:
        at.radio(key="origem_grupo").set_value(g).run()
        assert not at.exception
        for b in at.selectbox(key="origem_base").options:
            at.selectbox(key="origem_base").set_value(b).run()
            assert not at.exception, b


def test_periodo_cada_serie():
    at = novo(SECOES[2])
    for o in ["sim", "sih", "tiss"]:
        at.radio(key="serie_base").set_value(o).run()
        assert not at.exception, o


def test_registro_cada_base():
    at = novo(SECOES[4])
    for k in ["sim_obitos.csv", "sihsus_internacoes.csv", "tiss_cons_eventos.csv", "sib_vinculos.csv"]:
        at.selectbox(key="linha_base").set_value(k).run()
        assert not at.exception, k


def test_registro_sem_identificadores():
    """A amostra pública não pode trazer número de AIH, CNES, IDs de plano nem datas completas."""
    amostras = json.loads((RAIZ / "data" / "amostras.json").read_text(encoding="utf-8"))
    proibidas = {"N_AIH", "CNES", "DT_INTER", "DT_SAIDA", "DTNASC", "DTOBITO", "CODESTAB", "ID_PLANO",
                 "ID_EVENTO_ATENCAO_SAUDE", "CD_PLANO_RPS"}
    for k, v in amostras["brutos"].items():
        assert not proibidas & set(v["colunas"]), k


def test_cruzamentos_cada_um():
    at = novo(SECOES[5])
    for o in at.radio(key="cruz_nome").options:
        at.radio(key="cruz_nome").set_value(o).run()
        assert not at.exception, o


def test_mapa_todas_as_combinacoes():
    """Base x nível x medida x anos (amostra de anos), sempre com uma frase-achado calculada."""
    at = novo(SECOES[3])
    for base in BASES_MAPA:
        for nivel in ["Estados", "Municípios"]:
            at.radio(key="mapa_base").set_value(base).run()
            at.radio(key="mapa_nivel").set_value(nivel).run()
            medidas = ["Total", "Por 100 mil habitantes"] if base in ("sim", "sih") else ["Total"]
            for medida in medidas:
                if base in ("sim", "sih"):
                    at.radio(key="mapa_medida").set_value(medida).run()
                assert not at.exception, (base, nivel, medida)
                assert len(at.success) == 1, (base, nivel, medida)
                if at.select_slider:
                    ops = at.select_slider[0].options
                    for ano in ops[:: max(1, len(ops) // 4)] + [ops[-1]]:
                        at.select_slider[0].set_value(ano).run()
                        assert not at.exception, (base, nivel, medida, ano)


def _anos(at):
    return [str(o) for o in at.select_slider[0].options]  # no AppTest as opções vêm como texto


def test_taxa_por_estado_cobre_2022_e_2023_e_exclui_ano_incompleto():
    at = novo(SECOES[3])
    for base, ultimo in (("sim", "2024"), ("sih", "2025")):
        at.radio(key="mapa_base").set_value(base).run()
        at.radio(key="mapa_medida").set_value("Por 100 mil habitantes").run()
        anos = _anos(at)
        assert {"2000", "2022", "2023", ultimo} <= set(anos), base
        assert "2026" not in anos, base          # 2026 do SIH tem só 7 meses


def test_ano_incompleto_do_sih_avisa_no_mapa():
    at = novo(SECOES[3])
    at.radio(key="mapa_base").set_value("sih").run()
    at.select_slider[0].set_value(2026).run()
    assert not at.exception
    assert any("2026 está incompleto" in c.value and "7 meses" in c.value for c in at.caption)
    at.select_slider[0].set_value(2024).run()
    assert not any("incompleto" in c.value for c in at.caption)
