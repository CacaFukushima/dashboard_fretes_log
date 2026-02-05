import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ==============================================================================
# 1. CONFIGURAÇÃO (VISUAL ORIGINAL QUE VOCÊ GOSTOU)
# ==============================================================================
st.set_page_config(layout="wide", page_title="Dashboard Logístico")

st.title("🚛 Dashboard de Decisão Logística")
st.markdown("Sistema de Pontuação de Eficiência (Nota 0 a 100).")

# --- BARRA LATERAL ---
st.sidebar.header("⚖️ Painel de Controle")

prioridade_usuario = st.sidebar.slider(
    "Defina a Prioridade:",
    min_value=0, max_value=100, value=50, step=10, format="%d%%",
    help="0% = Foco Total em PRAZO | 100% = Foco Total em PREÇO"
)

peso_preco = prioridade_usuario / 100
peso_prazo = 1.0 - peso_preco

st.sidebar.write(f"💰 Importância do Custo: **{peso_preco*100:.0f}%**")
st.sidebar.write(f"⏱️ Importância do Prazo: **{peso_prazo*100:.0f}%**")

# ==============================================================================
# 2. CARREGAMENTO DOS DADOS (SEM DICIONÁRIOS FIXOS!)
# ==============================================================================
nome_arquivo_pc = 'COTAÇÃO DE FRETE.xlsx'
nome_arquivo_nuvem = 'dados.xlsx'

@st.cache_data
def carregar_dados():
    # Detecta onde o arquivo está
    if os.path.exists(nome_arquivo_nuvem): arquivo = nome_arquivo_nuvem
    elif os.path.exists(nome_arquivo_pc): arquivo = nome_arquivo_pc
    else: return None

    try:
        xls = pd.ExcelFile(arquivo)
        
        # --- LENDO VALORES E PAGAMENTO DIRETO DO EXCEL ---
        df_v = pd.read_excel(xls, 'DADOS 1')
        
        # Limpeza básica de valores
        df_v['VALOR'] = pd.to_numeric(df_v['VALOR'], errors='coerce')
        df_v = df_v.dropna(subset=['VALOR', 'TRANSPORTADORA'])
        df_v = df_v[df_v['VALOR'] > 0]
        
        # PROCURA A COLUNA DE PAGAMENTO AUTOMATICAMENTE
        # (Aceita 'PAGAMENTO', 'CONDICAO', 'PAGTO', etc.)
        coluna_pagamento = None
        for col in df_v.columns:
            if 'PAG' in col.upper() or 'COND' in col.upper():
                coluna_pagamento = col
                break
        
        # Se achou, renomeia para o padrão. Se não, cria vazia.
        if coluna_pagamento:
            df_v.rename(columns={coluna_pagamento: 'PAGAMENTO'}, inplace=True)
        else:
            df_v['PAGAMENTO'] = '-' # Preenche com traço se não achar
            
        # --- LENDO PRAZOS ---
        df_p_raw = pd.read_excel(xls, 'DADOS 3', header=None)
        df_p = df_p_raw[pd.to_numeric(df_p_raw[1], errors='coerce').notna()].copy()
        df_p = df_p[[0, 1]]
        df_p.columns = ['TRANSPORTADORA', 'PRAZO']
        
        # Padroniza Nomes (Remove espaços traidores)
        df_v['TRANSPORTADORA'] = df_v['TRANSPORTADORA'].astype(str).str.strip()
        df_p['TRANSPORTADORA'] = df_p['TRANSPORTADORA'].astype(str).str.strip()
        
        # Junta as tabelas
        df = pd.merge(df_v, df_p, on='TRANSPORTADORA', how='inner')
        return df
    except:
        return None

df = carregar_dados()

# Se não carregar, mostra erro simples (sem travar tudo com código feio)
if df is None or df.empty:
    st.error("⚠️ Erro ao carregar. Verifique se o Excel está fechado e se os nomes das empresas são iguais nas abas.")
    st.stop()

# ==============================================================================
# 3. CÁLCULO (LÓGICA CORRETA 0 a 100)
# ==============================================================================
min_valor = df['VALOR'].min()
min_prazo = df['PRAZO'].min()

# Evita divisão por zero
if min_valor == 0: min_valor = 1
if min_prazo == 0: min_prazo = 1

# Calcula Notas
df['NOTA_PRECO'] = (min_valor / df['VALOR']) * 100
df['NOTA_PRAZO'] = (min_prazo / df['PRAZO']) * 100

# Score Final
df['SCORE_FINAL'] = (df['NOTA_PRECO'] * peso_preco) + (df['NOTA_PRAZO'] * peso_prazo)

# Ordena do Melhor para o Pior
df = df.sort_values('SCORE_FINAL', ascending=False)

campea = df.iloc[0]['TRANSPORTADORA']

# --- TEXTO DA IA (SIMPLES E DIRETO) ---
def gerar_texto_ia(df, campea_nome, peso_preco):
    row = df[df['TRANSPORTADORA'] == campea_nome].iloc[0]
    media_v = df['VALOR'].mean()
    media_p = df['PRAZO'].mean()
    diff_v = media_v - row['VALOR']
    diff_p = media_p - row['PRAZO']
    
    txt = f"**Análise de Decisão:** A transportadora **{campea_nome}** é a recomendação (Eficiência {row['SCORE_FINAL']:.1f}).\n\n"
    
    if peso_preco >= 0.6:
        txt += "🎯 **Motivo:** Foco em **Redução de Custos**. "
        if diff_v > 0: txt += f"Economia de **R$ {diff_v:,.2f}** vs média."
    elif peso_preco <= 0.4:
        txt += "🎯 **Motivo:** Foco em **Agilidade**. "
        if diff_p > 0: txt += f"Entrega **{int(diff_p)} dias** mais rápida que a média."
    else:
        txt += "🎯 **Motivo:** Melhor **Custo-Benefício** (Equilíbrio ideal)."
    return txt

st.success(f"🏆 Melhor Escolha: **{campea}**")
st.info(gerar_texto_ia(df, campea, peso_preco), icon="🤖")

# Cores (Verde para campeã, Azul para o resto)
cores = ['#00C851' if t == campea else '#1f77b4' for t in df['TRANSPORTADORA']]

# ==============================================================================
# 4. VISUALIZAÇÃO (VOLTANDO AO LAYOUT ORIGINAL)
# ==============================================================================
fig = make_subplots(
    rows=2, cols=2,
    column_widths=[0.5, 0.5],
    row_heights=[0.5, 0.5],
    specs=[[{"type": "bar"}, {"type": "bar"}], 
           [{"type": "table", "colspan": 2}, None]], 
    subplot_titles=("Comparativo de Custos (R$)", "Comparativo de Prazos (Dias)", "Tabela Detalhada")
)

# Gráfico 1: Barras de Custo
fig.add_trace(go.Bar(
    x=df['TRANSPORTADORA'], y=df['VALOR'],
    text=df['VALOR'].apply(lambda x: f"R$ {x:,.0f}"), 
    textposition='auto',
    marker_color=cores,
    name='Custo'
), row=1, col=1)

# Gráfico 2: Barras de Prazo
fig.add_trace(go.Bar(
    x=df['TRANSPORTADORA'], y=df['PRAZO'],
    text=df['PRAZO'].apply(lambda x: f"{int(x)} dias"),
    textposition='auto',
    marker_color=cores,
    name='Prazo'
), row=1, col=2)

# Tabela (Agora com a coluna PAGAMENTO real do Excel!)
fig.add_trace(go.Table(
    header=dict(
        values=['TRANSPORTADORA', 'VALOR', 'PRAZO', 'PAGAMENTO', 'NOTA FINAL'],
        fill_color='black', font=dict(color='white', size=12), align='left'
    ),
    cells=dict(
        values=[
            df['TRANSPORTADORA'],
            df['VALOR'].apply(lambda x: f"R$ {x:,.2f}"),
            df['PRAZO'].apply(lambda x: f"{int(x)} dias"),
            df['PAGAMENTO'], # <--- Aqui entra o dado real do seu Excel
            df['SCORE_FINAL'].apply(lambda x: f"{x:.1f}")
        ],
        fill_color=[['#1c4d32' if t == campea else '#2c2c2c' for t in df['TRANSPORTADORA']] * 5],
        font=dict(color='white', size=11), align='left', height=30
    )
), row=2, col=1)

fig.update_layout(template="plotly_dark", height=700, showlegend=False)
st.plotly_chart(fig, use_container_width=True)
