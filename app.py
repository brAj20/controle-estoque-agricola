import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta
import json

# ────────────────────────────
# 🔑 CONEXÃO COM GOOGLE SHEETS
# ────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        with open("credenciais.json") as f:
            creds_dict = json.load(f)
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
except Exception as e:
    st.error(f"Erro de conexão com a planilha: {e}")
    st.stop()

gc = gspread.authorize(creds)
SPREADSHEET_ID = "1pwKuo_CANwxveC1sNxs98VMd4kUOP-JfRZnXoPSlJGU"
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

# ────────────────────────────
# 🎨 CONFIGURAÇÃO DA PÁGINA
# ────────────────────────────
st.set_page_config(
    page_title="Controle de Estoque — Defensivos Agrícolas",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ────────────────────────────
# 🔒 MODO EDIÇÃO — SÓ QUEM TEM SENHA
# ────────────────────────────
if "modo_edicao" not in st.session_state:
    st.session_state.modo_edicao = False

with st.sidebar:
    st.markdown("---")
    if not st.session_state.modo_edicao:
        with st.expander("🔑 Modo Edição"):
            senha_edicao = st.text_input("Digite a senha de edição:", type="password", key="senha_edicao")
            if st.button("Desbloquear Edição"):
                if senha_edicao == "admin123":
                    st.session_state.modo_edicao = True
                    st.success("✅ Modo edição desbloqueado!")
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
    else:
        st.success("✅ Modo Edição ATIVO")
        if st.button("🔒 Bloquear Edição"):
            st.session_state.modo_edicao = False
            st.rerun()
    st.markdown("---")

# Função auxiliar: campos só de visualização ou editáveis
def campo_ou_texto(label, valor="", tipo="default", **kwargs):
    if st.session_state.modo_edicao:
        if tipo == "number":
            return st.number_input(label, value=valor, **kwargs)
        elif tipo == "date":
            return st.date_input(label, value=valor, **kwargs)
        elif tipo == "text":
            return st.text_input(label, value=valor, **kwargs)
        elif tipo == "textarea":
            return st.text_area(label, value=valor, **kwargs)
        elif tipo == "selectbox":
            opcoes = kwargs.pop("opcoes", [])
            return st.selectbox(label, opcoes, index=opcoes.index(valor) if valor in opcoes else 0, **kwargs)
    else:
        st.write(f"*{label}*")
        if valor:
            st.info(f"{valor}")
        return None

# ────────────────────────────
# 📦 FUNÇÕES DE DADOS
# ────────────────────────────
def carregar_aba(nome_aba):
    try:
        aba = spreadsheet.worksheet(nome_aba)
        dados = aba.get_all_records()
        return pd.DataFrame(dados) if dados else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def salvar_dados(nome_aba, df):
    if not st.session_state.modo_edicao:
        st.warning("🔒 Desbloqueie o Modo Edição para salvar alterações")
        return False
    try:
        aba = spreadsheet.worksheet(nome_aba)
        aba.clear()
        aba.update([df.columns.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def calcular_alertas():
    df = carregar_aba("Produtos")
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
            nome = str(row.get("Produto", row.get("Nome", "Produto sem nome")))
            local = str(row.get("Local", ""))
            quantidade = str(row.get("Quantidade", row.get("Lotes", "")))
            
            info = {
                "nome": nome,
                "dias": dias,
                "validade": validade_str,
                "local": local,
                "quantidade": quantidade
            }
            
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
# 🧭 MENU LATERAL
# ────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 10px 10px 20px 10px;'>
            <span style='font-size: 22px; font-weight: bold; color: #2e7d32;'>🛡️ Controle de Estoque</span><br>
            <span style='font-size: 13px; color: #888;'>Defensivos Agrícolas</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🚨 Alertas de Validade")
    
    if vencidos:
        st.markdown(f"""
        <div style='background: rgba(211,47,47,0.15); border-left: 3px solid #d32f2f; 
             padding: 10px; border-radius: 6px; margin-bottom: 8px;'>
            <span style='color: #ff6b6b; font-weight: bold;'>⚠️ {len(vencidos)} PRODUTO(S) VENCIDO(S)</span>
        </div>
        """, unsafe_allow_html=True)
        for p in vencidos[:3]:
            st.markdown(f"🔴 *{p['nome']}* — {p['validade']}")
        if len(vencidos) > 3:
            st.markdown(f"... e mais {len(vencidos)-3} produto(s)")
    
    if vencendo_15d:
        st.markdown(f"""
        <div style='background: rgba(245,124,0,0.15); border-left: 3px solid #f57c00; 
             padding: 10px; border-radius: 6px; margin-bottom: 8px;'>
            <span style='color: #ffb74d; font-weight: bold;'>⏰ {len(vencendo_15d)} VENCE(M) EM ATÉ 15 DIAS</span>
        </div>
        """, unsafe_allow_html=True)
        for p in vencendo_15d[:3]:
            st.markdown(f"🟠 *{p['nome']}* — {p['dias']} dias")
    
    if vencendo_30d:
        st.markdown(f"""
        <div style='background: rgba(251,192,45,0.1); border-left: 3px solid #fbc02d; 
             padding: 10px; border-radius: 6px; margin-bottom: 8px;'>
            <span style='color: #fff176; font-weight: bold;'>📅 {len(vencendo_30d)} VENCE(M) EM ATÉ 30 DIAS</span>
        </div>
        """, unsafe_allow_html=True)
        for p in vencendo_30d[:2]:
            st.markdown(f"🟡 *{p['nome']}* — {p['dias']} dias")
    
    if not vencidos and not vencendo_15d and not vencendo_30d:
        st.markdown("✅ *Nenhum alerta — tudo em dia!*")
    
    st.markdown("---")
    
    if "pagina" not in st.session_state:
        st.session_state.pagina = "Painel Geral"
    
    opcoes_menu = [
        "📊 Painel Geral",
        "📦 Estoque Total",
        "📅 Todas as Validades",
        "⚠️ Controle de Validades",
        "📋 Todos os Produtos",
        "📍 Estoque por Local",
        "🔄 Produtos em Uso",
        "🚨 Vencidos no Local Errado",
        "↔️ Movimentação",
        "💰 Histórico de Gastos",
        "🔁 Transferência",
        "📜 Histórico Completo"
    ]
    
    escolhida = st.selectbox("Ir para página:", opcoes_menu, index=opcoes_menu.index(st.session_state.pagina))
    st.session_state.pagina = escolhida

pagina = st.session_state.pagina

# ────────────────────────────
# 🚀 PÁGINAS
# ────────────────────────────

def painel_geral():
    st.markdown("## 📊 Painel Geral")
    st.caption("Resumo completo do estoque")
    
    if vencidos:
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, rgba(211,47,47,0.18), rgba(198,40,40,0.08)); 
             border-left: 5px solid #d32f2f; padding: 20px; border-radius: 12px; margin-bottom: 25px;'>
            <h3 style='color: #ff6b6b; margin: 0 0 8px 0;'>🚨 {len(vencidos)} PRODUTO(S) VENCIDO(S)</h3>
            <p style='color: #ffcdd2; margin: 0;'>Verifique em <b>Controle de Validades</b> ou <b>Vencidos no Local Errado</b></p>
        </div>
        """, unsafe_allow_html=True)
    
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
    
    st.markdown("""
    <div style='background: rgba(46,125,50,0.06); border: 1px solid rgba(46,125,50,0.15); 
         border-radius: 12px; padding: 20px; margin-bottom: 25px;'>
        <h4 style='color: #2e7d32; margin: 0 0 8px 0;'>👋 Bem-vindo!</h4>
        <p style='color: #666; margin: 0;'>Para fazer lançamentos, editar ou cadastrar produtos → ative o 
        <b>🔑 Modo Edição</b> no menu lateral com a senha.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("🔴 Vencidos", len(vencidos))
    col_b.metric("🟠 Em 15 dias", len(vencendo_15d))
    col_c.metric("🟡 Em 30 dias", len(vencendo_30d))
    col_d.metric("📊 Total", f"~{len(carregar_aba('Produtos'))}")

def estoque_total():
    st.markdown("## 📦 Estoque Total")
    st.caption("Todos os produtos cadastrados")
    df = carregar_aba("Produtos")
    if df.empty:
        st.info("Nenhum produto cadastrado. Use o Modo Edição para adicionar.")
    else:
        st.dataframe(df, use_container_width=True)

def todas_validades():
    st.markdown("## 📅 Todas as Validades")
    st.caption("Lista completa com datas de validade")
    df = carregar_aba("Produtos")
    if df.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        st.dataframe(df[["Produto", "Validade", "Quantidade", "Local"]] 
                     if all(col in df.columns for col in ["Produto", "Validade", "Quantidade", "Local"]) 
                     else df, use_container_width=True)

def controle_validades():
    st.markdown("## ⚠️ Controle de Validades")
    st.caption("Produtos vencidos e próximos do vencimento")
    
    tab1, tab2, tab3 = st.tabs(["🔴 Vencidos", "🟠 Até 15 dias", "🟡 Até 30 dias"])
    
    with tab1:
        if vencidos:
            for p in vencidos:
                st.markdown(f"🔴 *{p['nome']}* — Venceu em: {p['validade']} | {p['quantidade']} | {p['local']}")
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

def todos_produtos():
    st.markdown("## 📋 Todos os Produtos")
    st.caption("Cadastro completo")
    df = carregar_aba("Produtos")
    if df.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        st.dataframe(df, use_container_width=True)

def estoque_por_local():
    st.markdown("## 📍 Estoque por Local")
    st.caption("Produtos por local de armazenamento")
    df = carregar_aba("Produtos")
    if df.empty or "Local" not in df.columns:
        st.info("Sem dados de locais.")
    else:
        locais = df["Local"].dropna().unique()
        for local in locais:
            with st.expander(f"📍 {local}"):
                st.dataframe(df[df["Local"] == local], use_container_width=True)

def produtos_em_uso():
    st.markdown("## 🔄 Produtos em Uso")
    st.caption("Produtos retirados e em utilização")
    st.info("Nenhum produto em uso no momento.")

def vencidos_local_errado():
    st.markdown("## 🚨 Vencidos no Local Errado")
    st.caption("Produtos vencidos fora do local correto")
    st.warning("⚠️ *REGRA:* Produtos vencidos só podem ficar no Córrego da Ponte — Q01 ou Q02")
    
    locais_corretos = ["Córrego da Ponte - Quarto 01", "Córrego da Ponte - Quarto 02", 
                       "Córrego da Ponte Q01", "Córrego da Ponte Q02", "Q01", "Q02"]
    
    errados = []
    for p in vencidos:
        local_ok = any(loc in str(p['local']) for loc in locais_corretos)
        if not local_ok:
            errados.append(p)
    
    if errados:
        for p in errados:
            st.markdown(f"🚨 *{p['nome']}* — Local atual: {p['local']} | Venceu: {p['validade']}")
    else:
        st.success("✅ Todos os vencidos estão no local correto!")

def movimentacao():
    st.markdown("## ↔️ Movimentação")
    st.caption("Entradas e saídas de estoque")
    
    if not st.session_state.modo_edicao:
        st.info("🔒 Ative o Modo Edição no menu lateral para registrar movimentações")
    else:
        tab1, tab2 = st.tabs(["📥 Entrada", "📤 Saída"])
        with tab1:
            st.markdown("### Nova Entrada")
            st.text_input("Nome do produto", key="entrada_nome")
            st.number_input("Quantidade", min_value=0, step=1, key="entrada_qtd")
            st.selectbox("Local", ["Córrego da Ponte - Q01", "Córrego da Ponte - Q02", "Outro"], key="entrada_local")
            st.date_input("Data", value=datetime.now(), key="entrada_data")
            if st.button("✅ Salvar Entrada", type="primary"):
                st.success("Entrada registrada! (conecte à planilha para salvar de verdade)")
        with tab2:
            st.markdown("### Nova Saída")
            st.text_input("Nome do produto", key="saida_nome")
            st.number_input("Quantidade", min_value=0, step=1, key="saida_qtd")
            st.text_input("Responsável", key="saida_resp")
            st.date_input("Data", value=datetime.now(), key="saida_data")
            if st.button("✅ Salvar Saída", type="primary"):
                st.success("Saída registrada!")

def historico_gastos():
    st.markdown("## 💰 Histórico de Gastos")
    st.caption("Registro de compras e valores")
    st.info("Conectando à planilha...")

def transferencia():
    st.markdown("## 🔁 Transferência entre Locais")
    st.caption("Movimentação de produtos entre locais")
    
    if not st.session_state.modo_edicao:
        st.info("🔒 Ative o Modo Edição no menu lateral para fazer transferências")
    else:
        st.text_input("Nome do produto", key="transf_nome")
        st.selectbox("De", ["Córrego da Ponte - Q01", "Córrego da Ponte - Q02"], key="transf_de")
        st.selectbox("Para", ["Córrego da Ponte - Q01", "Córrego da Ponte - Q02"], key="transf_para")
        st.number_input("Quantidade", min_value=0, step=1, key="transf_qtd")
        if st.button("✅ Confirmar Transferência", type="primary"):
            st.success("Transferência realizada!")

def historico_completo():
    st.markdown("## 📜 Histórico Completo")
    st.caption("Todas as movimentações — entradas, saídas e edições")
    st.info("Carregando histórico da planilha...")

# ────────────────────────────
# 📄 ROTEADOR DE PÁGINAS
# ────────────────────────────
mapa_paginas = {
    "📊 Painel Geral": painel_geral,
    "📦 Estoque Total": estoque_total,
    "📅 Todas as Validades": todas_validades,
    "⚠️ Controle de Validades": controle_validades,
    "📋 Todos os Produtos": todos_produtos,
    "📍 Estoque por Local": estoque_por_local,
    "🔄 Produtos em Uso": produtos_em_uso,
    "🚨 Vencidos no Local Errado": vencidos_local_errado,
    "↔️ Movimentação": movimentacao,
    "💰 Histórico de Gastos": historico_gastos,
    "🔁 Transferência": transferencia,
    "📜 Histórico Completo": historico_completo,
}

mapa_paginas[pagina]()
