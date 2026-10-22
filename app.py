import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta
import json
import io

# ================= CONFIGURAÇÕES DA PÁGINA =================
st.set_page_config(
    page_title="Controle de Estoque — Defensivos Agrícolas",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= ESTILOS E CORES =================
st.markdown("""
<style>
    :root {
        --fundo-escuro: #0e1113;
        --fundo-card: #1f2326;
        --verde-principal: #2ecc71;
        --amarelo-alerta: #f39c12;
        --vermelho-perigo: #e74c3c;
        --azul-info: #3498db;
        --cinza-texto: #bdc3c7;
        --branco: #ffffff;
    }
    
    .stApp { background-color: var(--fundo-escuro); }
    h1, h2, h3 { color: var(--branco) !important; }
    p, div { color: var(--cinza-texto); }
    
    .card-principal {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid var(--verde-principal);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .card-alerta {
        background: linear-gradient(135deg, #452a2a 0%, #1c1313 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid var(--vermelho-perigo);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .card-vencendo {
        background: linear-gradient(135deg, #453d2a 0%, #1c1a13 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid var(--amarelo-alerta);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .card-info {
        background: linear-gradient(135deg, #1e3a4a 0%, #0f1a24 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid var(--azul-info);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .card-local {
        background: linear-gradient(135deg, #1a2e2b 0%, #0f1f1d 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 4px solid var(--verde-principal);
        margin-bottom: 0.8rem;
    }
    .card-local-perigo {
        background: linear-gradient(135deg, #3d2424 0%, #1f1212 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 4px solid var(--vermelho-perigo);
        margin-bottom: 0.8rem;
    }
    .badge-vencido {
        background-color: var(--vermelho-perigo);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-vencendo {
        background-color: var(--amarelo-alerta);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-dia {
        background-color: var(--verde-principal);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .alerta-urgente {
        background: linear-gradient(90deg, #7b241c, #c0392b);
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e74c3c;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    [data-testid="stSidebar"] {
        background-color: #1a1c1e;
        border-right: 1px solid #2c3033;
    }
    .caixa-senha {
        background-color: var(--fundo-card);
        padding: 2rem;
        border-radius: 12px;
        max-width: 400px;
        margin: 0 auto;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
""", unsafe_allow_html=True)

# ================= INICIALIZAR SESSÃO =================
if 'acesso_autorizado' not in st.session_state:
    st.session_state.acesso_autorizado = False

SENHA_ADMIN = "admin123"

# ================= CONEXÃO COM GOOGLE SHEETS =================
@st.cache_resource(show_spinner="Conectando ao banco de dados...")
def conectar_planilha():
    try:
        secrets = st.secrets
        if "gcp_service_account" in secrets:
            creds = service_account.Credentials.from_service_account_info(
                dict(secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                "credenciais.json",
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
        gc = gspread.authorize(creds)
        PLANILHA_ID = "1pwKuo_CANwxveC1sNxs98VMd4kUOP-JfRZnXoPSlJGU"
        return gc.open_by_key(PLANILHA_ID)
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

planilha = conectar_planilha()

def ler_aba(nome_aba):
    if not planilha:
        return pd.DataFrame()
    try:
        aba = planilha.worksheet(nome_aba)
        dados = aba.get_all_records()
        return pd.DataFrame(dados)
    except:
        return pd.DataFrame()

def salvar_aba(nome_aba, df):
    if not planilha or not st.session_state.acesso_autorizado:
        return False
    try:
        aba = planilha.worksheet(nome_aba)
        aba.clear()
        aba.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except:
        return False

# ================= FUNÇÕES AUXILIARES =================
def dias_para_vencer(data_validade):
    if pd.isna(data_validade) or data_validade == "":
        return None
    try:
        if isinstance(data_validade, str):
            data_validade = datetime.strptime(data_validade, "%d/%m/%Y")
        return (data_validade - datetime.now()).days
    except:
        return None

def status_validade(dias):
    if dias is None:
        return "Sem data", "badge-dia"
    if dias < 0:
        return "VENCIDO", "badge-vencido"
    elif dias <= 15:
        return f"Vence em {dias} dias", "badge-vencendo"
    elif dias <= 30:
        return f"Vence em {dias} dias", "badge-vencendo"
    else:
        return "Em dia", "badge-dia"

# ================= ÁREA RESTRITA POR SENHA =================
def area_restrita(conteudo_funcao):
    if st.session_state.acesso_autorizado:
        conteudo_funcao()
    else:
        st.markdown("---")
        st.markdown("### 🔒 Área Restrita")
        st.info("Digite a senha para realizar alterações.")
        with st.form("form_senha"):
            senha_digitada = st.text_input("Senha de acesso", type="password")
            if st.form_submit_button("🔓 Desbloquear"):
                if senha_digitada == SENHA_ADMIN:
                    st.session_state.acesso_autorizado = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        st.markdown("---")

# ================= MENU LATERAL =================
with st.sidebar:
    st.markdown("## 🛡️ Controle de Estoque")
    st.markdown("### Defensivos Agrícolas")
    st.markdown("---")
    
    menu = st.radio(
        "Navegação",
        [
            "📊 Painel Geral",
            "📦 Estoque Total",
            "📅 Todas as Validades",
            "⏰ Controle de Validades",
            "🏷️ Todos os Produtos",
            "📍 Estoque por Local",
            "🔄 Produtos em Uso",
            "⚠️ Vencidos no Local Errado",
            "➕ Movimentação",
            "💰 Histórico de Gastos",
            "🔁 Transferência",
            "📋 Histórico Completo"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    if st.session_state.acesso_autorizado:
        st.success("✅ Modo Edição Ativo")
        if st.button("🔒 Sair"):
            st.session_state.acesso_autorizado = False
            st.rerun()
    else:
        st.info("🔒 Modo Visualização")

# ================= CARREGAR DADOS =================
df_produtos = ler_aba("Produtos")
df_historico = ler_aba("Histórico")
df_locais = ler_aba("Locais")

if df_produtos.empty:
    df_produtos = pd.DataFrame(columns=[
        "Produto", "Quantidade", "Unidade", "Validade", "Local", 
        "Lote", "ValorUnitario", "EmUso", "Observacoes"
    ])
if df_historico.empty:
    df_historico = pd.DataFrame(columns=[
        "DataHora", "Tipo", "Produto", "Quantidade", "Unidade", 
        "Validade", "Local", "Lote", "ValorUnitario", "Quem", "OrigemDestino"
    ])

# ================= PÁGINAS =================

# ---------- PAINEL GERAL ----------
if menu == "📊 Painel Geral":
    st.title("📊 Painel Geral")
    st.subheader("Resumo completo do estoque")
    
    total_produtos = len(df_produtos)
    total_lotes = df_produtos['Quantidade'].sum() if not df_produtos.empty else 0
    em_uso = len(df_produtos[df_produtos['EmUso'] == 'Sim']) if not df_produtos.empty else 0
    
    vencendo_15d = vencendo_30d = vencidos = local_errado = 0
    if not df_produtos.empty:
        for _, p in df_produtos.iterrows():
            d = dias_para_vencer(p['Validade'])
            if d is not None:
                if d < 0: vencidos += 1
                elif d <= 15: vencendo_15d += 1
                elif d <= 30: vencendo_30d += 1
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="card-info">', unsafe_allow_html=True)
        st.metric("📦 Produtos", total_produtos)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card-principal">', unsafe_allow_html=True)
        st.metric("📊 Lotes", f"{total_lotes:,}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card-info">', unsafe_allow_html=True)
        st.metric("🔄 Em Uso", em_uso)
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="card-alerta">', unsafe_allow_html=True)
        st.metric("🚨 Vencidos", vencidos)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="card-vencendo">', unsafe_allow_html=True)
        st.metric("⏰ Vence em até 15 dias", vencendo_15d)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="card-vencendo">', unsafe_allow_html=True)
        st.metric("⚠️ Vence em até 30 dias", vencendo_30d)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("✅ Sistema conectado à planilha do Google — dados salvos automaticamente!")
    st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ---------- ESTOQUE TOTAL ----------
elif menu == "📦 Estoque Total":
    st.title("📦 Estoque Total")
    st.subheader("Todo o estoque de cada produto")
    
    busca = st.text_input("🔍 Pesquisar produto...")
    if not df_produtos.empty:
        estoque_total = df_produtos.groupby(['Produto', 'Unidade']).agg({'Quantidade': 'sum'}).reset_index()
        if busca:
            estoque_total = estoque_total[estoque_total['Produto'].str.contains(busca, case=False)]
        st.dataframe(estoque_total, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum produto cadastrado. Vá em ➕ Movimentação!")

# ---------- TODAS AS VALIDADES ----------
elif menu == "📅 Todas as Validades":
    st.title("📅 Todas as Validades")
    filtro = st.radio("Filtrar:", ["Todas", "🚨 Vencidas", "⏰ 15 dias", "⚠️ 30 dias", "✅ Em dia"], horizontal=True)
    
    if not df_produtos.empty:
        df_exibir = df_produtos.copy()
        df_exibir['DiasParaVencer'] = df_exibir['Validade'].apply(dias_para_vencer)
        df_exibir['Status'], df_exibir['Badge'] = zip(*df_exibir['DiasParaVencer'].apply(status_validade))
        
        if filtro == "🚨 Vencidas": df_exibir = df_exibir[df_exibir['DiasParaVencer'] < 0]
        elif filtro == "⏰ 15 dias": df_exibir = df_exibir[(df_exibir['DiasParaVencer'] >= 0) & (df_exibir['DiasParaVencer'] <= 15)]
        elif filtro == "⚠️ 30 dias": df_exibir = df_exibir[(df_exibir['DiasParaVencer'] > 15) & (df_exibir['DiasParaVencer'] <= 30)]
        elif filtro == "✅ Em dia": df_exibir = df_exibir[df_exibir['DiasParaVencer'] > 30]
        
        for _, row in df_exibir.iterrows():
            st.markdown(f"""
            <div style="padding: 1rem; background: #1f2326; border-radius: 8px; margin-bottom: 0.5rem;">
                <strong>📦 {row['Produto']}</strong> — {row['Quantidade']} {row['Unidade']}<br>
                📅 Vence: {row['Validade']} • 📍 {row['Local']} • Lote: {row['Lote']}<br>
                <span class="{row['Badge']}">{row['Status']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum produto cadastrado.")

# ---------- CONTROLE DE VALIDADES ----------
elif menu == "⏰ Controle de Validades":
    st.title("⏰ Controle de Validades")
    
    if not df_produtos.empty:
        df_exibir = df_produtos.copy()
        df_exibir['DiasParaVencer'] = df_exibir['Validade'].apply(dias_para_vencer)
        
        st.markdown("### 🚨 PRODUTOS VENCIDOS")
        vencidos = df_exibir[df_exibir['DiasParaVencer'] < 0].sort_values('DiasParaVencer')
        if len(vencidos) > 0:
            for _, row in vencidos.iterrows():
                st.markdown(f"""
                <div style="padding: 1rem; background: #3d2424; border-radius: 8px; border-left: 4px solid #e74c3c; margin-bottom: 0.5rem;">
                    <strong>📦 {row['Produto']}</strong> — {row['Quantidade']} {row['Unidade']}<br>
                    ❌ Venceu em: {row['Validade']} — há {abs(row['DiasParaVencer'])} dias<br>
                    📍 {row['Local']} • Lote: {row['Lote']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Nenhum produto vencido!")
        
        st.markdown("---")
        st.markdown("### ⏰ VENCENDO NOS PRÓXIMOS 30 DIAS")
        vencendo = df_exibir[(df_exibir['DiasParaVencer'] >= 0) & (df_exibir['DiasParaVencer'] <= 30)].sort_values('DiasParaVencer')
        if len(vencendo) > 0:
            for _, row in vencendo.iterrows():
                st.markdown(f"""
                <div style="padding: 1rem; background: #453d2a; border-radius: 8px; border-left: 4px solid #f39c12; margin-bottom: 0.5rem;">
                    <strong>📦 {row['Produto']}</strong> — {row['Quantidade']} {row['Unidade']}<br>
                    ⚠️ Vence em: {row['Validade']} — faltam {row['DiasParaVencer']} dias<br>
                    📍 {row['Local']} • Lote: {row['Lote']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Nenhum produto vencendo nos próximos 30 dias!")
    else:
        st.info("Nenhum produto cadastrado.")

# ---------- TODOS OS PRODUTOS ----------
elif menu == "🏷️ Todos os Produtos":
    st.title("🏷️ Todos os Produtos")
    busca = st.text_input("🔍 Pesquisar...")
    
    if not df_produtos.empty:
        df_exibir = df_produtos.copy()
        if busca:
            df_exibir = df_exibir[
                df_exibir['Produto'].str.contains(busca, case=False) |
                df_exibir['Local'].str.contains(busca, case=False)
            ]
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum produto cadastrado.")

# ---------- ESTOQUE POR LOCAL ----------
elif menu == "📍 Estoque por Local":
    st.title("📍 Estoque por Local")
    
    if not df_produtos.empty:
        for local in sorted(df_produtos['Local'].unique()):
            df_local = df_produtos[df_produtos['Local'] == local]
            tem_vencido = any(df_local['Validade'].apply(lambda x: (dias_para_vencer(x) or 1) < 0))
            classe = "card-local-perigo" if tem_vencido else "card-local"
            
            st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)
            st.subheader(f"📍 {local}")
            st.write(f"*{len(df_local)} lotes* — Total: {df_local['Quantidade'].sum():,.2f}")
            for _, row in df_local.iterrows():
                d = dias_para_vencer(row['Validade'])
                if d and d < 0:
                    st.write(f"🚨 {row['Produto']} — {row['Quantidade']} {row['Unidade']} — VENCIDO")
                else:
                    st.write(f"✅ {row['Produto']} — {row['Quantidade']} {row['Unidade']} — Vence: {row['Validade']}")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhum produto cadastrado.")

# ---------- PRODUTOS EM USO ----------
elif menu == "🔄 Produtos em Uso":
    st.title("🔄 Produtos em Uso")
    
    if not df_produtos.empty:
        em_uso = df_produtos[df_produtos['EmUso'] == 'Sim']
        if len(em_uso) > 0:
            st.dataframe(em_uso, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum produto em uso no momento.")
    else:
        st.info("Nenhum produto cadastrado.")

# ---------- VENCIDOS NO LOCAL ERRADO ----------
elif menu == "⚠️ Vencidos no Local Errado":
    st.title("⚠️ Vencidos no Local Errado")
    st.markdown("""
    <div class="alerta-urgente">
        <h3>📌 REGRA IMPORTANTE</h3>
        <p>Produtos vencidos só podem ficar em:</p>
        <strong>• Córrego da Ponte - Quarto 01</strong><br>
        <strong>• Córrego da Ponte - Quarto 02</strong>
    </div>
    """, unsafe_allow_html=True)
    
    locais_permitidos = ["Córrego da Ponte - Quarto 01", "Córrego da Ponte - Quarto 02"]
    if not df_produtos.empty:
        df_exibir = df_produtos.copy()
        df_exibir['DiasParaVencer'] = df_exibir['Validade'].apply(dias_para_vencer)
        vencidos_fora = df_exibir[
            (df_exibir['DiasParaVencer'] < 0) &
            (~df_exibir['Local'].isin(locais_permitidos))
        ]
        if len(vencidos_fora) > 0:
            st.error(f"🚨 {len(vencidos_fora)} lote(s) vencido(s) no local ERRADO!")
            st.dataframe(vencidos_fora[['Produto', 'Quantidade', 'Local', 'Validade', 'Lote']], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Perfeito! Nenhum vencido no local errado!")
    else:
        st.info("Nenhum produto cadastrado.")

# ---------- MOVIMENTAÇÃO ----------
elif menu == "➕ Movimentação":
    st.title("➕ Movimentação")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Nova Entrada")
        with st.form("form_entrada"):
            novo_produto = st.text_input("Nome do Produto")
            nova_qtd = st.number_input("Quantidade", min_value=0.0, step=0.01)
            nova_und = st.selectbox("Unidade", ["Lts", "kg", "Un", "Lotes", "Sacos"])
            nova_data = st.text_input("Data de Validade (DD/MM/AAAA)")
            novo_local = st.text_input("Local de Armazenamento")
            novo_lote = st.text_input("Número do Lote")
            novo_valor = st.number_input("Valor Unitário R$", min_value=0.0, step=0.01)
            novo_quem = st.text_input("Quem cadastrou")
            
            if st.form_submit_button("✅ Registrar Entrada", type="primary"):
                def registrar():
                    global df_produtos, df_historico
                    if not novo_produto or nova_qtd <= 0:
                        st.error("Preencha os campos obrigatórios!")
                        return
                    
                    nova_linha = {
                        "Produto": novo_produto,
                        "Quantidade": nova_qtd,
                        "Unidade": nova_und,
                        "Validade": nova_data,
                        "Local": novo_local,
                        "Lote": novo_lote,
                        "ValorUnitario": novo_valor,
                        "EmUso": "Não",
                        "Observacoes": ""
                    }
                    df_produtos = pd.concat([df_produtos, pd.DataFrame([nova_linha])], ignore_index=True)
                    
                    linha_hist = {
                        "DataHora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Tipo": "ENTRADA",
                        "Produto": novo_produto,
                        "Quantidade": nova_qtd,
                        "Unidade": nova_und,
                        "Validade": nova_data,
                        "Local": novo_local,
                        "Lote": novo_lote,
                        "ValorUnitario": novo_valor,
                        "Quem": novo_quem,
                        "OrigemDestino": ""
                    }
                    df_historico = pd.concat([df_historico, pd.DataFrame([linha_hist])], ignore_index=True)
                    
                    if salvar_aba("Produtos", df_produtos) and salvar_aba("Histórico", df_historico):
                        st.success(f"✅ {nova_qtd} {nova_und} de {novo_produto} cadastrado!")
                        st.rerun()
                    else:
                        st.error("❌ Erro — verifique a senha de edição.")
                area_restrita(registrar)
    
    with col2:
        st.subheader("📤 Saída / Aplicação")
        if not df_produtos.empty:
            lista_prod = sorted(df_produtos['Produto'].unique().tolist())
            prod_saida = st.selectbox("Produto", [""] + lista_prod)
            if prod_saida:
                opcoes_local = df_produtos[df_produtos['Produto'] == prod_saida]['Local'].unique().tolist()
                local_saida = st.selectbox("Local", opcoes_local)
                opcoes_lote = df_produtos[
                    (df_produtos['Produto'] == prod_saida) &
                    (df_produtos['Local'] == local_saida)
                ]['Lote'].unique().tolist()
                lote_saida = st.selectbox("Lote", opcoes_lote)
                qtd_saida = st.number_input("Quantidade a retirar", min_value=0.0, step=0.01)
                quem_saida = st.text_input("Quem retirou/aplicou")
                obs_saida = st.text_area("Observações")
                
                if st.button("✅ Registrar Saída"):
                    def registrar_saida():
                        global df_produtos, df_historico
                        mascara = (
                            (df_produtos['Produto'] == prod_saida) &
                            (df_produtos['Local'] == local_saida) &
                            (df_produtos['Lote'] == lote_saida)
                        )
                        idx = df_produtos[mascara].index
                        if len(idx) == 0:
                            st.error("Produto não encontrado!")
                            return
                        
                        qtd_atual = df_produtos.loc[idx[0], 'Quantidade']
                        if qtd_saida > qtd_atual:
                            st.error(f"Estoque insuficiente! Disponível: {qtd_atual}")
                            return
                        
                        df_produtos.loc[idx[0], 'Quantidade'] -= qtd_saida
                        if df_produtos.loc[idx[0], 'Quantidade'] <= 0:
                            df_produtos = df_produtos.drop(idx)
                        
                        linha_hist = {
                            "DataHora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Tipo": "SAÍDA",
                            "Produto": prod_saida,
                            "Quantidade": qtd_saida,
                            "Unidade": df_produtos.loc[idx[0], 'Unidade'] if idx[0] in df_produtos.index else "",
                            "Validade": df_produtos.loc[idx[0], 'Validade'] if idx[0] in df_produtos.index else "",
                            "Local": local_saida,
                            "Lote": lote_saida,
                            "ValorUnitario": df_produtos.loc[idx[0], 'ValorUnitario'] if idx[0] in df_produtos.index else 0,
                            "Quem": quem_saida,
                            "OrigemDestino": obs_saida
                        }
                        df_historico = pd.concat([df_historico, pd.DataFrame([linha_hist])], ignore_index=True)
                        
                        if salvar_aba("Produtos", df_produtos) and salvar_aba("Histórico", df_historico):
                            st.success(f"✅ Saída de {qtd_saida} registrada!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar.")
                    area_restrita(registrar_saida)
        else:
            st.info("Cadastre um produto primeiro")

# ---------- HISTÓRICO DE GASTOS ----------
elif menu == "💰 Histórico de Gastos":
    st.title("💰 Histórico de Gastos")
    
    if not df_historico.empty:
        df_exibir = df_historico.copy()
        df_exibir['DataHora'] = pd.to_datetime(df_exibir['DataHora'], format="%d/%m/%Y %H:%M", errors='coerce')
        df_exibir['ValorTotal'] = df_exibir['Quantidade'] * df_exibir['ValorUnitario']
        
        st.subheader("📋 Lançamentos Mais Recentes")
        st.dataframe(df_exibir.sort_values('DataHora', ascending=False), use_container_width=True, hide_index=True)
        
        st.subheader("📊 Por Produto")
        gastos_prod = df_exibir.groupby('Produto').agg({
            'Quantidade': 'sum',
            'ValorTotal': 'sum',
            'Tipo': 'count'
        }).reset_index()
        gastos_prod.columns = ['Produto', 'Quantidade Total', 'Valor Total R$', 'Nº Lançamentos']
        st.dataframe(gastos_prod, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum lançamento registrado ainda.")

# ---------- TRANSFERÊNCIA ----------
elif menu == "🔁 Transferência":
    st.title("🔁 Transferência entre Locais")
    
    if not df_produtos.empty:
        lista_prod = sorted(df_produtos['Produto'].unique().tolist())
        prod_origem = st.selectbox("Produto", [""] + lista_prod)
        
        if prod_origem:
            opcoes_local_origem = sorted(df_produtos[df_produtos['Produto'] == prod_origem]['Local'].unique().tolist())
            local_origem = st.selectbox("De — Local de Origem", opcoes_local_origem)
            
            opcoes_lote = df_produtos[
                (df_produtos['Produto'] == prod_origem) &
                (df_produtos['Local'] == local_origem)
            ]['Lote'].unique().tolist()
            lote_transf = st.selectbox("Lote", opcoes_lote)
            
            qtd_disponivel = df_produtos[
                (df_produtos['Produto'] == prod_origem) &
                (df_produtos['Local'] == local_origem) &
                (df_produtos['Lote'] == lote_transf)
            ]['Quantidade'].sum()
            st.info(f"📦 Disponível: *{qtd_disponivel}*")
            
            qtd_transf = st.number_input("Quantidade a transferir", min_value=0.0, max_value=float(qtd_disponivel), step=0.01)
            
            todos_locais = sorted(df_produtos['Local'].unique().tolist())
            locais_destino = [l for l in todos_locais if l != local_origem]
            local_destino = st.selectbox("Para — Local de Destino", [""] + locais_destino)
            
            quem_transf = st.text_input("Quem transferiu")
            
            if st.button("✅ Confirmar Transferência", type="primary"):
                def fazer_transf():
                    global df_produtos, df_historico
                    if not local_destino or qtd_transf <= 0:
                        st.error("Preencha todos os campos!")
                        return
                    
                    mascara_origem = (
                        (df_produtos['Produto'] == prod_origem) &
                        (df_produtos['Local'] == local_origem) &
                        (df_produtos['Lote'] == lote_transf)
                    )
                    idx_origem = df_produtos[mascara_origem].index
                    
                    if len(idx_origem) == 0:
                        st.error("Produto não encontrado!")
                        return
                    
                    df_produtos.loc[idx_origem[0], 'Quantidade'] -= qtd_transf
                    
                    # Adicionar ao destino
                    mascara_destino = (
                        (df_produtos['Produto'] == prod_origem) &
                        (df_produtos['Local'] == local_destino) &
                        (df_produtos['Lote'] == lote_transf)
                    )
                    if len(df_produtos[mascara_destino]) > 0:
                        df_produtos.loc[mascara_destino, 'Quantidade'] += qtd_transf
                    else:
                        linha_nova = df_produtos.loc[idx_origem[0]].copy()
                        linha_nova['Quantidade'] = qtd_transf
                        linha_nova['Local'] = local_destino
                        df_produtos = pd.concat([df_produtos, pd.DataFrame([linha_nova])], ignore_index=True)
                    
                    # Remover se zerou
                    if df_produtos.loc[idx_origem[0], 'Quantidade'] <= 0:
                        df_produtos = df_produtos.drop(idx_origem)
                    
                    # Histórico
                    linha_hist = {
                        "DataHora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Tipo": "TRANSFERÊNCIA",
                        "Produto": prod_origem,
                        "Quantidade": qtd_transf,
                        "Unidade": df_produtos.loc[idx_origem[0], 'Unidade'] if idx_origem[0] in df_produtos.index else "",
                        "Validade": df_produtos.loc[idx_origem[0], 'Validade'] if idx_origem[0] in df_produtos.index else "",
                        "Local": local_destino,
                        "Lote": lote_transf,
                        "ValorUnitario": df_produtos.loc[idx_origem[0], 'ValorUnitario'] if idx_origem[0] in df_produtos.index else 0,
                        "Quem": quem_transf,
                        "OrigemDestino": f"{local_origem} → {local_destino}"
                    }
                    df_historico = pd.concat([df_historico, pd.DataFrame([linha_hist])], ignore_index=True)
                    
                    if salvar_aba("Produtos", df_produtos) and salvar_aba("Histórico", df_historico):
                        st.success(f"✅ Transferência de {qtd_transf} realizada!")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar.")
                area_restrita(fazer_transf)
    else:
        st.info("Cadastre um produto primeiro")

# ---------- HISTÓRICO COMPLETO ----------
elif menu == "📋 Histórico Completo":
    st.title("📋 Histórico Completo")
    st.subheader("Todas as movimentações — entrada, saída e transferência")
    
    if not df_historico.empty:
        df_exibir = df_historico.copy()
        df_exibir['DataHora'] = pd.to_datetime(df_exibir['DataHora'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos"] + sorted(df_exibir['Tipo'].unique().tolist()))
        if filtro_tipo != "Todos":
            df_exibir = df_exibir[df_exibir['Tipo'] == filtro_tipo]
        
        df_exibir = df_exibir.sort_values('DataHora', ascending=False).reset_index(drop=True)
        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
        st.markdown(f"*Total de {len(df_exibir)} registros encontrados*")
    else:
        st.info("Nenhum lançamento registrado ainda.")
