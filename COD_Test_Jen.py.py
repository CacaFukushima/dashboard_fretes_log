import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(layout="wide", page_title="Dashboard Logístico")

st.title("🚛 DASHBOARD DE DECISÃO DA LOGÍSTICA")
st.markdown("Sistema de Pontuação de Eficiência (Nota 0 a 100).")

# --- BARRA LATERAL ---
st.sidebar.header("⚖️ Ajuste de Prioridade")

prioridade_usuario = st.sidebar.slider(
    "O que é mais importante?",
    min_value=0,
    max_value=100,
    value=50,
    step=10,
    format="%d%%",
    help="0% = Só importa PRAZO | 100% = Só importa PREÇO"
)

# Pesos (0.0 a 1.0)
peso_preco = prioridade_usuario / 100
peso_prazo = 1.0 - peso_preco

st.sidebar.write(f"💰 Peso Preço: **{peso_preco*100:.0f}%**")
st.sidebar.write(f"⏱️ Peso Prazo: **{peso_prazo*100:.0f}%**")

# ==============================================================================
# 2. CARREGAMENTO DOS DADOS
# ==============================================================================
variaveis_pagamento = {
    'BARRETOS TRANSPORTES': '15 DIAS (BOLETO)',
    'FIEZA CARGAS': 'Á VISTA',
    'GODI TRANSPORTES': '7 DIAS (BOLETO)'
}

try:
    diretorio_script = os.path.dirname(os.path.abspath(__file__))
except:
    diretorio_script = os.getcwd()

caminho_arquivo = os.path.join(diretorio_script, 'COTAÇÃO DE FRETE.xlsx')

@st.cache_data
def carregar_dados():
    if not os.path.exists(caminho_arquivo):
        return None
    xls = pd.ExcelFile(caminho_arquivo)
    
    # Valores
    df_v = pd.read_excel(xls, 'DADOS 1')
    df_v['VALOR'] = pd.to_numeric(df_v['VALOR'], errors='coerce')
    df_v = df_v.dropna(subset=['VALOR', 'TRANSPORTADORA'])
    df_v = df_v[df_v['VALOR'] > 10]
    
    # Prazos
    df_p_raw = pd.read_excel(xls, 'DADOS 3', header=None)
    df_p = df_p_raw[pd.to_numeric(df_p_raw[1], errors='coerce').notna()].copy()
    df_p = df_p[[0, 1]]
    df_p.columns = ['TRANSPORTADORA', 'PRAZO']
    
    # Merge
    df = pd.merge(df_v, df_p, on='TRANSPORTADORA', how='inner')
    df['TRANSPORTADORA'] = df['TRANSPORTADORA'].str.strip()
    df['PAGAMENTO'] = df['TRANSPORTADORA'].map(variaveis_pagamento).fillna('A Combinar')
    
    return df

df = carregar_dados()

if df is None:
    st.error(f"❌ Erro: Não achei o arquivo em: {caminho_arquivo}")
    st.stop()

# ==============================================================================
# 3. CÁLCULO DE SCORE (AGORA: MAIOR É MELHOR)
# ==============================================================================
# Lógica de Eficiência: (Melhor_Valor_Do_Mercado / Valor_Da_Empresa) * 100
# Se a empresa tem o menor preço, a conta dá 1 * 100 = 100.
# Se a empresa cobra o dobro, a conta dá 0.5 * 100 = 50.

min_valor = df['VALOR'].min()
min_prazo = df['PRAZO'].min()

df['NOTA_PRECO'] = (min_valor / df['VALOR']) * 100
df['NOTA_PRAZO'] = (min_prazo / df['PRAZO']) * 100

# Média Ponderada das Notas
df['SCORE_FINAL'] = (df['NOTA_PRECO'] * peso_preco) + (df['NOTA_PRAZO'] * peso_prazo)

# ORDENAÇÃO INVERTIDA: ascending=False (Do MAIOR para o MENOR)
df = df.sort_values('SCORE_FINAL', ascending=False)

# Campeã é a primeira da lista (Maior Nota)
campea = df.iloc[0]['TRANSPORTADORA']
nota_campea = df.iloc[0]['SCORE_FINAL']

st.success(f"🏆 Melhor Opção: **{campea}** (Eficiência: {nota_campea:.1f}/100)")

# Cores: Verde para a campeã, Cinza para as outras
cores_dinamicas = ["#002FFF" if t == campea else "#8a2929" for t in df['TRANSPORTADORA']]

# ==============================================================================
# 4. VISUALIZAÇÃO
# ==============================================================================
fig = make_subplots(
    rows=2, cols=2,
    column_widths=[0.5, 0.5],
    row_heights=[0.5, 0.5],
    specs=[[{"type": "bar"}, {"type": "bar"}], 
           [{"type": "table", "colspan": 2}, None]], 
    subplot_titles=(
        "Custo (R$)", 
        "Prazo (Dias)", 
        "Ranking de Eficiência (Nota 0 a 100 - Maior é Melhor)"
    )
)

# Gráfico 1: Custo
fig.add_trace(go.Bar(
    x=df['TRANSPORTADORA'], y=df['VALOR'],
    text=df['VALOR'].apply(lambda x: f"R$ {x:,.2f}"), textposition='auto',
    marker_color=cores_dinamicas,
    name='Custo'
), row=1, col=1)

# Gráfico 2: Prazo
fig.add_trace(go.Bar(
    x=df['TRANSPORTADORA'], y=df['PRAZO'],
    text=df['PRAZO'].apply(lambda x: f"{int(x)} dias"), textposition='auto',
    marker_color=cores_dinamicas,
    name='Prazo'
), row=1, col=2)

# Tabela (Com Score Formatado)
fig.add_trace(go.Table(
    header=dict(
        values=['TRANSPORTADORA', 'VALOR', 'PRAZO', 'PAGAMENTO', 'NOTA FINAL (0-100)'],
        fill_color='black', font=dict(color='white', size=14)
    ),
    cells=dict(
        values=[
            df['TRANSPORTADORA'],
            df['VALOR'].apply(lambda x: f"R$ {x:,.2f}"),
            df['PRAZO'].apply(lambda x: f"{int(x)} dias"),
            df['PAGAMENTO'],
            df['SCORE_FINAL'].apply(lambda x: f"Nota {x:.1f}") # Formatado como Nota
        ],
        fill_color=[
            ["#0002FF" if t == campea else "#181717" for t in df['TRANSPORTADORA']] * 5
        ],
        font=dict(color='white', size=12), height=30
    )
), row=2, col=1)

fig.update_layout(template="plotly_dark", height=750, showlegend=False)

st.plotly_chart(fig, use_container_width=True)
