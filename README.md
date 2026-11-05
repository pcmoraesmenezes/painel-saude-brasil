# Saúde no Brasil: painel de dados públicos

Painel em Streamlit com dados públicos de mortalidade, internações no SUS, internações em planos de saúde,
vínculos com planos e população: de onde vêm, de quando são e onde estão no país (estados e municípios).
Não traz resultados de análise.

## Como rodar

```
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Testes (exercitam cada seção, seletor e combinação de mapa):

```
python3 -m pytest tests
python3 tests/render_mapas.py SAIDA_DIR   # gera imagens dos mapas; precisa do pacote kaleido
```

## Publicar (Streamlit Community Cloud)

O painel só lê arquivos de `data/`, sem segredo nem variável de ambiente.

1. Em share.streamlit.io, entrar com a conta do GitHub dona do repositório e escolher "New app".
2. Escolher este repositório, branch `main`, arquivo principal `app/streamlit_app.py`.
3. O tema escuro vem de `.streamlit/config.toml`.

## O que há em cada pasta

- `app/`: o painel (`streamlit_app.py`) e as figuras (`mapas.py`).
- `data/`: tudo que o painel lê. Todo número da tela é calculado destes arquivos.
  - `perfil_agregados.json`: linhas, anos, totais por ano e por estado de cada tabela.
  - `municipios.csv`: total por município e ano (base, ano, código IBGE de 6 dígitos, valor) de óbitos,
    internações no SUS, internações em planos, vínculos com planos e população.
  - `pop_uf_projecao.csv`: projeção de população por estado, 2000 a 2070.
  - `fontes.csv`: de onde vem cada base.
  - `amostras.json`: linhas reais do arquivo de origem (sem datas completas nem números de identificação) e da
    tabela resumida.
  - `uf.geojson`, `municipios.geojson`, `municipios_nomes.csv`: malha e nomes do IBGE.
- `tests/`: testes do app e dos dados.

## Notas sobre os dados

- Óbitos: os arquivos de 2022 e 2023 vêm sem linha de cabeçalho; os nomes das colunas vêm de 2021 e de 2024.
  Antes de 1996 o código do município tem 7 dígitos; códigos terminados em 0000 são município ignorado.
- Internações no SUS: no arquivo de origem cada internação aparece uma vez por diagnóstico; só o diagnóstico
  principal conta a internação. Ficam de fora as internações de longa permanência.
- Taxas por 100 mil habitantes são brutas (sem ajuste por idade) e exploratórias. A taxa por estado usa a
  projeção do IBGE por estado. A taxa por município usa a estimativa municipal e só existe em 2015 a 2021 e 2024
  em diante (revisões diferentes do IBGE; não há estimativa municipal para 2022 e 2023).
- Municípios com menos de 5 casos aparecem em cinza. A soma dos municípios fica entre 96% e 100% do total por
  estado, conforme a base e o ano; o restante são códigos de município sem polígono na malha atual.
- Fontes: Ministério da Saúde (DATASUS), ANS, IBGE, OMS, ONU, IHME, Society of Actuaries e Susep; endereços em
  `data/fontes.csv`.
