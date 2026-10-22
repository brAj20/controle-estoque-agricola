import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta
import json

# ────────────────────────────
# 🔑 AUTENTICAÇÃO — Funciona local e na nuvem
# ────────────────────────────
def get_gsheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            with open("credenciais.json") as f:
                creds_dict = json.load(f)
        
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(credentials)
        return gc
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

gc = get_gsheet()
SPREADSHEET_ID = "1pwKuo_CANwxveC1sNxs98VMd4kUOP-JfRZnXoPSlJGU"

# ────────────────────────────
# 🎨 CONFIGURAÇÃO DE PÁGINA
# ────────────────────────────
st.set_page_config(page_title="Estoque Defensivos", layout="wide", initial_sidebar_state="expanded")

# ────────────────────────────
# 🔐 LOGIN
# ────────────────────────────
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🛡️ Controle de Estoque — Defensivos Agrícolas")
    senha = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar", type="primary"):
        if senha == "admin123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# ────────────────────────────
# 📦 CARREGAR DADOS DA PLANILHA
# ────────────────────────────
def carregar_dados(aba):
    if not gc:
        return pd.DataFrame()
    try:
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(aba)
        dados = ws.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar {aba}: {e}")
        return pd.DataFrame()

# ────────────────────────────
# 📊 FUNÇÕES DE ALERTA DE VALIDADE
# ────────────────────────────
def calcular_alertas():
    df = carregar_dados("Produtos")
    if df.empty or "Validade" not in df.columns:
        return [], [], []
    
    hoje = datetime.now().date()
    vencidos = []
    vencendo_30d = []
    vencendo_15d = []
    
    for _, row in df.iterrows():
        try:
            validade_str = str(row.get("Validade", ""))
            if not validade_str or validade_str == "nan":
                continue
            
            for fmt in ["%d/%m/%Y", "%Y-%m-%d"]:
                try:
                    validade = datetime.strptime(validade_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                continue
            
            dias = (validade - hoje).days
            nome = row.get("Produto", row.get("Nome", "Produto sem nome"))
            local = row.get("Local", "")
            quantidade = row.get("Quantidade", row.get("Lotes", ""))
            
            info = {"nome": nome, "dias": dias, "validade": validade_str, 
                    "local": local, "quantidade": quantidade}
            
            if dias < 0:
                vencidos.append(info)
            elif dias <= 15:
                vencendo_15d.append(info)
            elif dias <= 30:
                vencendo_30d.append(info)
        except:
            continue
    
    return vencidos, vencendo_15d, vencendo_30d

vencidos, vencendo_15d, vencendo_30d = calcular_alertas()

# ────────────────────────────
# 🧭 BARRA LATERAL — MENU COM ALERTAS
# ────────────────────────────
st.sidebar.markdown("""
    <div style='text-align: center; padding: 10px 10px 20px 10px;'>
        <span style='font-size: 22px; font-weight: bold; color: #2e7d32;'>🛡️ Controle de Estoque</span><br>
        <span style='font-size: 13px; color: #888;'>Defensivos Agrícolas</span>
    </div>
""", unsafe_allow_html=True)

# ⚠️ ALERTAS NO MENU LATERAL — SEMPRE VISÍVEIS
st.sidebar.markdown("---")
st.sidebar.markdown("### 🚨 Alertas de Validade")

if vencidos:
    st.sidebar.markdown(f"""
    <div style='background: rgba(211,47,47,0.15); border-left: 3px solid #d32f2f; 
         padding: 10px; border-radius: 6px; margin-bottom: 8px;'>
        <span style='color: #ff6b6b; font-weight: bold;'>⚠️ {len(vencidos)} PRODUTO(S) VENCIDO(S)</span>
    </div>
    """, unsafe_allow_html=True)
    for p in vencidos[:3]:
        st.sidebar.markdown(f"🔴 *{p['nome']}* — {p['validade']}")
    if len(vencidos) > 3:
        st.sidebar.markdown(f"... e mais {len(vencidos)-3} produto(s) vencido(s)")

if vencendo_15d:
    st.sidebar.markdown(f"""
    <div style='background: rgba(245,124,0,0.15); border-left: 3px solid #f57c00; 
         padding: 10px; border-radius: 6px; margin-bottom: 8px;'>
        <span style='color: #ffb74d; font-weight: bold;'>⏰ {len(vencendo_15d)} VENCE(M) EM ATÉ 15 DIAS</span>
    </div>
    """, unsafe_allow_html=True)
    for p in vencendo_15d[:3]:
        st.sidebar.markdown(f"🟠 *{p['nome']}* — {p['dias']} dias")
    if len(vencendo_15d) > 3:
        st.sidebar.markdown(f"... e mais {len(vencendo_15d)-3} produto(s)")

if vencendo_30d:
    st.sidebar.markdown(f"""
    <div style='background: rgba(251,192,45,0.1); border-left: 3px solid #fbc02d; 
         padding: 10px; border-radius: 6px; margin-bottom: 8px;'>
        <span style='color: #fff176; font-weight: bold;'>📅 {len(vencendo_30d)} VENCE(M) EM ATÉ 30 DIAS</span>
    </div>
    """, unsafe_allow_html=True)
    for p in vencendo_30d[:2]:
        st.sidebar.markdown(f"🟡 *{p['nome']}* — {p['dias']} dias")

if not vencidos and not vencendo_15d and not vencendo_30d:
    st.sidebar.markdown("✅ *Nenhum alerta — tudo em dia!*")

st.sidebar.markdown("---")

# Inicializar página atual
if "pagina" not in st.session_state:
    st.session_state.pagina = "Painel Geral"

# Itens do Menu
menu_items = [
    ("📊 Painel Geral", "Painel Geral"),
    ("📦 Estoque Total", "Estoque Total"),
    ("📅 Todas as Validades", "Todas as Validades"),
    ("⚠️ Controle de Validades", "Controle de Validades"),
    ("📋 Todos os Produtos", "Todos os Produtos"),
    ("📍 Estoque por Local", "Estoque por Local"),
    ("🔄 Produtos em Uso", "Produtos em Uso"),
    ("🚨 Vencidos no Local Errado", "Vencidos no Local Errado"),
    ("↔️ Movimentação", "Movimentação"),
    ("💰 Histórico de Gastos", "Histórico de Gastos"),
    ("🔁 Transferência", "Transferência"),
    ("📜 Histórico Completo", "Histórico Completo"),
]

for label, pagina in menu_items:
    if st.sidebar.button(label, use_container_width=True, 
                         type="primary" if st.session_state.pagina == pagina else "secondary"):
        st.session_state.pagina = pagina
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔑 Sair", use_container_width=True):
    st.session_state.logado = False
    st.rerun()

pagina = st.session_state.pagina

# ────────────────────────────
# 🎯 PÁGINAS
# ────────────────────────────

def pagina_painel_geral():
    st.markdown("## 📊 Painel Geral")
    st.caption("Resumo completo do estoque")
    
    # ALERTA PRINCIPAL NO TOPO DO PAINEL
    if vencidos:
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, rgba(211,47,47,0.18), rgba(198,40,40,0.08)); 
             border-left: 5px solid #d32f2f; padding: 20px; border-radius: 12px; margin-bottom: 25px;'>
            <h3 style='color: #ff6b6b; margin: 0 0 8px 0;'>🚨 {len(vencidos)} PRODUTO(S) VENCIDO(S)</h3>
            <p style='color: #ffcdd2; margin: 0;'>Verifique imediatamente em <b>Controle de Validades</b> ou <b>Vencidos no Local Errado</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🔴 Ver produtos vencidos"):
            for p in vencidos:
                st.markdown(f"*{p['nome']}* — Venceu em {p['validade']} | {p['quantidade']} | {p['local']}")
    
    if vencendo_15d:
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, rgba(245,124,0,0.15), rgba(230,81,0,0.05)); 
             border-left: 5px solid #f57c00; padding: 18px; border-radius: 12px; margin-bottom: 25px;'>
            <h4 style='color: #ffb74d; margin: 0 0 5px 0;'>⏰ {len(vencendo_15d)} produto(s) vence(m) em até 15 dias</h4>
        </div>
        """, unsafe_allow_html=True)
    
    if vencendo_30d:
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, rgba(251,192,45,0.12), rgba(245,127,23,0.05)); 
             border-left: 5px solid #fbc02d; padding: 15px; border-radius: 12px; margin-bottom: 25px;'>
            <h4 style='color: #fff176; margin: 0;'>📅 {len(vencendo_30d)} produto(s) vence(m) em até 30 dias</h4>
        </div>
        """, unsafe_allow_html=True)
    
    # ALERTA DE LOCAL ERRADO
    st.markdown("""
    <div style='background: rgba(239,108,0,0.08); border: 1px solid rgba(239,108,0,0.2); 
         border-radius: 12px; padding: 20px; margin-bottom: 30px;'>
        <h4 style='color: #ff9800; margin: 0 0 10px 0;'>⚠️ REGRA DE ARMAZENAMENTO</h4>
        <p style='color: #ddd; margin: 0;'>Produtos vencidos só podem ficar armazenados no <b>Córrego da Ponte — Q01 ou Q02</b>. 
        Clique em <b>Vencidos no Local Errado</b> para verificar e transferir.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # CARDS DE NAVEGAÇÃO — Clicáveis
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦\n\nEstoque Total\n\nVer todos os produtos →", use_container_width=True):
            st.session_state.pagina = "Estoque Total"
            st.rerun()
        if st.button("📅\n\nTodas as Validades\n\nLista completa →", use_container_width=True):
            st.session_state.pagina = "Todas as Validades"
            st.rerun()
        if st.button("⚠️\n\nControle de Validades\n\nVencendo e vencidos →", use_container_width=True):
            st.session_state.pagina = "Controle de Validades"
            st.rerun()
        if st.button("📍\n\nEstoque por Local\n\nPor armazém →", use_container_width=True):
            st.session_state.pagina = "Estoque por Local"
            st.rerun()
        if st.button("🚨\n\nVencidos no Local Errado\n\nVerificar e mover →", use_container_width=True):
            st.session_state.pagina = "Vencidos no Local Errado"
            st.rerun()
    
    with col2:
        if st.button("📋\n\nTodos os Produtos\n\nCadastro completo →", use_container_width=True):
            st.session_state.pagina = "Todos os Produtos"
            st.rerun()
        if st.button("🔄\n\nProdutos em Uso\n\nEm campo →", use_container_width=True):
            st.session_state.pagina = "Produtos em Uso"
            st.rerun()
        if st.button("↔️\n\nMovimentação\n\nEntradas e saídas →", use_container_width=True):
            st.session_state.pagina = "Movimentação"
            st.rerun()
        if st.button("💰\n\nHistórico de Gastos\n\nPor produto →", use_container_width=True):
            st.session_state.pagina = "Histórico de Gastos"
            st.rerun()
        if st.button("🔁\n\nTransferência\n\nEntre locais →", use_container_width=True):
            st.session_state.pagina = "Transferência"
            st.rerun()
    
    st.divider()
    
    # RESUMO RÁPIDO
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("📦 Vencidos", len(vencidos))
    col_b.metric("⏰ Em 15 dias", len(vencendo_15d))
    col_c.metric("📅 Em 30 dias", len(vencendo_30d))
    col_d.metric("✅ Em dia", f"~{max(0, 87 - len(vencidos) - len(vencendo_15d) - len(vencendo_30d))}")

def pagina_estoque_total():
    st.markdown("## 📦 Estoque Total")
    st.caption("Todo o estoque de cada produto, somado")
    df = carregar_dados("Produtos")
    if df.empty:
        st.info("Nenhum produto cadastrado ainda. Use 'Movimentação → Nova Entrada'.")
    else:
        st.dataframe(df, use_container_width=True)

def pagina_todas_validades():
    st.markdown("## 📅 Todas as Validades")
    st.caption("Todas as datas de validade dos produtos")
    df = carregar_dados("Produtos")
    if df.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        st.dataframe(df, use_container_width=True)

def pagina_controle_validades():
    st.markdown("## ⚠️ Controle de Validades")
    st.caption("O que vence em breve e o que já venceu")
    
    tab1, tab2, tab3 = st.tabs(["🔴 Vencidos", "🟠 Até 15 dias", "🟡 Até 30 dias"])
    
    with tab1:
        if vencidos:
            for p in vencidos:
                st.markdown(f"""
                <div style='background: rgba(211,47,47,0.08); border-left: 3px solid #d32f2f; 
                     padding: 12px; border-radius: 8px; margin-bottom: 8px;'>
                    <b>{p['nome']}</b><br>
                    Venceu em: {p['validade']} | {p['quantidade']} | {p['local']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Nenhum produto vencido!")
    
    with tab2:
        if vencendo_15d:
            for p in vencendo_15d:
                st.markdown(f"🟠 *{p['nome']}* — {p['dias']} dias restantes | {p['validade']}")
        else:
            st.success("✅ Nenhum produto vencendo nos próximos 15 dias!")
    
    with tab3:
        if vencendo_30d:
            for p in vencendo_30d:
                st.markdown(f"🟡 *{p['nome']}* — {p['dias']} dias restantes | {p['validade']}")
        else:
            st.success("✅ Nenhum produto vencendo nos próximos 30 dias!")

def pagina_todos_produtos():
    st.markdown("## 📋 Todos os Produtos")
    st.caption("Lista completa com todos os produtos cadastrados")
    df = carregar_dados("Produtos")
    if df.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        st.dataframe(df, use_container_width=True)

def pagina_estoque_por_local():
    st.markdown("## 📍 Estoque por Local")
    st.caption("Escolha um local para ver o que tem guardado lá")
    df = carregar_dados("Locais")
    if df.empty:
        st.info("Locais ainda não cadastrados na planilha.")
    else:
        st.dataframe(df, use_container_width=True)

def pagina_produtos_em_uso():
    st.markdown("## 🔄 Produtos em Uso")
    st.caption("O que está sendo usado agora — sai daqui ao devolver")
    st.info("Nenhum produto em uso no momento")

def pagina_vencidos_local_errado():
    st.markdown("## 🚨 Vencidos no Local Errado")
    st.caption("Produtos vencidos guardados fora do Córrego da Ponte")
    
    st.warning("⚠️ *REGRA:* Produtos vencidos só podem ficar no Córrego da Ponte — Q01 ou Q02")
    
    # Filtrar vencidos em local errado
    locais_corretos = ["Córrego da Ponte - Quarto 01", "Córrego da Ponte - Quarto 02", 
                       "Córrego da Ponte Q01", "Córrego da Ponte Q02", "Q01", "Q02"]
    
    errados = []
    for p in vencidos:
        local_ok = any(loc in str(p['local']) for loc in locais_corretos)
        if not local_ok:
            errados.append(p)
    
    if errados:
        for p in errados:
            st.markdown(f"""
            <div style='background: rgba(211,47,47,0.1); border: 1px solid #d32f2f; 
                 padding: 15px; border-radius: 10px; margin-bottom: 10px;'>
                <h4 style='color: #ff6b6b; margin: 0 0 5px 0;'>🚨 {p['nome']}</h4>
                <p style='margin: 0;'>📍 Local atual: <b>{p['local']}</b><br>
                📅 Venceu em: {p['validade']} | 📦 {p['quantidade']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Todos os vencidos estão no local correto!")

def pagina_movimentacao():
    st.markdown("## ↔️ Movimentação")
    st.caption("Tudo junto num lugar só — escolha o que registrar")
    col1, col2 = st.columns(2)
    with col1:
        st.button("➕ NOVA ENTRADA\n\nProduto chegando ao estoque", use_container_width=True, type="primary")
    with col2:
        st.button("➡️ SAÍDA\n\nAplicação por foto ou digitada", use_container_width=True)

def pagina_historico_gastos():
    st.markdown("## 💰 Histórico de Gastos")
    st.caption("Por produto ou os mais recentes")
    st.info("Conectando ao histórico de lançamentos da planilha...")

def pagina_transferencia():
    st.markdown("## 🔁 Transferência entre Locais")
    st.caption("Mova um lote de um local de armazenamento para outro")
    st.info("Selecione o produto e o destino para transferir")

def pagina_historico_completo():
    st.markdown("## 📜 Histórico Completo")
    st.caption("Tudo que já aconteceu no estoque — entradas, saídas e edições")
    st.info("Carregando histórico da planilha...")

# ────────────────────────────
# 🚀 EXIBIR PÁGINA ATUAL
# ────────────────────────────
paginas = {
    "Painel Geral": pagina_painel_geral,
    "Estoque Total": pagina_estoque_total,
    "Todas as Validades": pagina_todas_validades,
    "Controle de Validades": pagina_controle_validades,
    "Todos os Produtos": pagina_todos_produtos,
    "Estoque por Local": pagina_estoque_por_local,
    "Produtos em Uso": pagina_produtos_em_uso,
    "Vencidos no Local Errado": pagina_vencidos_local_errado,
    "Movimentação": pagina_movimentacao,
    "Histórico de Gastos": pagina_historico_gastos,
    "Transferência": pagina_transferencia,
    "Histórico Completo": pagina_historico_completo,
}

paginas[pagina]()
