import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json

# -----------------------------------------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
SPREADSHEET_ID = "1pwKuo_CANwxveC1sNxs98VMd4kUOP-JfRZnXoPSlJGU"

# Autenticação
@st.cache_resource
def get_google_sheets():
    with open("credenciais.json") as f:
        credentials_dict = json.load(f)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

try:
    planilha = get_google_sheets()
except Exception as e:
    st.error(f"Erro de conexão com a planilha: {e}")
    st.stop()

# Senhas
SENHA_ADMIN = "admin123"
SENHA_CONSULTA = "view123"

# -----------------------------------------------------------------------------
# LOGIN
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Controle de Estoque", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.nivel = None

if not st.session_state.autenticado:
    st.title("🔐 Controle de Estoque — Login")
    senha_digitada = st.text_input("Digite a senha:", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Entrar", use_container_width=True):
            if senha_digitada == SENHA_ADMIN:
                st.session_state.autenticado = True
                st.session_state.nivel = "admin"
                st.rerun()
            elif senha_digitada == SENHA_CONSULTA:
                st.session_state.autenticado = True
                st.session_state.nivel = "consulta"
                st.rerun()
            else:
                st.error("❌ Senha incorreta!")
    st.stop()

# -----------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------------------------------------
def ler_aba(nome_aba):
    try:
        aba = planilha.worksheet(nome_aba)
        dados = aba.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        st.warning(f"⚠️ Erro ao ler {nome_aba}: {e}")
        return pd.DataFrame()

def salvar_aba(nome_aba, df):
    try:
        aba = planilha.worksheet(nome_aba)
        aba.clear()
        if not df.empty:
            aba.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {e}")
        return False

def registrar_historico(tipo, produto, qtd, unidade, local, responsavel, obs="", id_prod=""):
    df_hist = ler_aba("Historico")
    nova_linha = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tipo": tipo,
        "produto": produto,
        "quantidade": qtd,
        "unidade": unidade,
        "local": local,
        "responsavel": responsavel,
        "observacao": obs,
        "id_produto": id_prod
    }
    df_hist = pd.concat([df_hist, pd.DataFrame([nova_linha])], ignore_index=True)
    salvar_aba("Historico", df_hist)

# -----------------------------------------------------------------------------
# MENU PRINCIPAL
# -----------------------------------------------------------------------------
st.title("📦 Controle de Estoque — Defensivos Agrícolas")
st.success(f"✅ Conectado como: {'Administrador' if st.session_state.nivel == 'admin' else 'Consulta'} | Dados salvos na Planilha Google")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📋 Estoque", "➕ Adicionar", "✏️ Saída/Editar", "📊 Histórico", "⚠️ Alertas"
])

# -----------------------------------------------------------------------------
# ABA 1 — ESTOQUE
# -----------------------------------------------------------------------------
with aba1:
    st.subheader("Lista de Produtos")
    df_prod = ler_aba("Produtos")
    
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True, hide_index=True)
        
        st.subheader("Resumo")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Itens", len(df_prod))
        with col2:
            total_qtd = pd.to_numeric(df_prod["quantidade"], errors="coerce").sum()
            st.metric("Quantidade Total", int(total_qtd) if total_qtd else 0)
        with col3:
            locais_unicos = df_prod["local"].nunique() if "local" in df_prod.columns else 0
            st.metric("Locais Diferentes", locais_unicos)
    else:
        st.info("📭 Nenhum produto cadastrado ainda. Vá em 'Adicionar Produto'")

# -----------------------------------------------------------------------------
# ABA 2 — ADICIONAR PRODUTO
# -----------------------------------------------------------------------------
with aba2:
    if st.session_state.nivel != "admin":
        st.warning("🔒 Apenas administrador pode adicionar produtos")
    else:
        st.subheader("Adicionar Novo Produto")
        
        df_locais = ler_aba("Locais")
        lista_locais = df_locais["nome"].dropna().tolist() if not df_locais.empty else []
        
        with st.form("form_adicionar"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome do Produto")
                categoria = st.text_input("Categoria")
                quantidade = st.number_input("Quantidade Inicial", min_value=0, step=1)
            with col2:
                unidade = st.selectbox("Unidade", ["Litro", "Kg", "Unidade", "Saco", "Lata", "Caixa", "Metro"])
                if lista_locais:
                    local = st.selectbox("Local de Armazenamento", lista_locais)
                else:
                    local = st.text_input("Local de Armazenamento")
                alerta_minimo = st.number_input("Alerta de Estoque Baixo", min_value=0, step=1, value=5)
            observacao = st.text_area("Observação (opcional)")
            responsavel = st.text_input("Responsável pelo Lançamento")
            
            if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True):
                if nome and responsavel:
                    df_prod = ler_aba("Produtos")
                    novo_id = str(len(df_prod) + 1) if not df_prod.empty else "1"
                    
                    novo_prod = {
                        "id": novo_id,
                        "nome": nome,
                        "categoria": categoria,
                        "quantidade": quantidade,
                        "unidade": unidade,
                        "local": local,
                        "alerta_minimo": alerta_minimo,
                        "observacao": observacao
                    }
                    
                    df_prod = pd.concat([df_prod, pd.DataFrame([novo_prod])], ignore_index=True)
                    if salvar_aba("Produtos", df_prod):
                        registrar_historico(
                            "ENTRADA", nome, quantidade, unidade, local, responsavel, observacao, novo_id
                        )
                        st.success(f"✅ *{nome}* cadastrado e salvo na planilha!")
                        st.rerun()
                else:
                    st.error("❌ Preencha o nome e o responsável")

# -----------------------------------------------------------------------------
# ABA 3 — SAÍDA / EDITAL
# -----------------------------------------------------------------------------
with aba3:
    if st.session_state.nivel != "admin":
        st.warning("🔒 Apenas administrador pode registrar saídas")
    else:
        st.subheader("Registrar Saída de Estoque")
        df_prod = ler_aba("Produtos")
        
        if not df_prod.empty:
            prod_selecionado = st.selectbox("Selecione o Produto", df_prod["nome"].tolist())
            dados_prod = df_prod[df_prod["nome"] == prod_selecionado].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"Estoque atual: *{dados_prod['quantidade']} {dados_prod['unidade']}*")
                qtd_saida = st.number_input("Quantidade de Saída", min_value=1, step=1, 
                                           max_value=int(dados_prod["quantidade"]))
            with col2:
                responsavel_saida = st.text_input("Quem está retirando?")
                obs_saida = st.text_area("Motivo/Observação")
            
            if st.button("📤 Registrar Saída", use_container_width=True):
                if responsavel_saida:
                    idx = df_prod[df_prod["nome"] == prod_selecionado].index[0]
                    qtd_anterior = int(df_prod.at[idx, "quantidade"])
                    df_prod.at[idx, "quantidade"] = qtd_anterior - int(qtd_saida)
                    
                    if salvar_aba("Produtos", df_prod):
                        registrar_historico(
                            "SAÍDA", prod_selecionado, qtd_saida, dados_prod["unidade"],
                            dados_prod["local"], responsavel_saida, obs_saida, dados_prod["id"]
                        )
                        st.success(f"✅ Saída registrada! Restam: {df_prod.at[idx, 'quantidade']} {dados_prod['unidade']} — atualizado na planilha!")
                        st.rerun()
                else:
                    st.error("❌ Informe quem está retirando")
        else:
            st.info("📭 Sem produtos cadastrados")

# -----------------------------------------------------------------------------
# ABA 4 — HISTÓRICO
# -----------------------------------------------------------------------------
with aba4:
    st.subheader("📊 Histórico de Movimentações")
    df_hist = ler_aba("Historico")
    
    if not df_hist.empty:
        st.dataframe(df_hist.sort_values("data", ascending=False), use_container_width=True, hide_index=True)
        csv = df_hist.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar Histórico", csv, "historico.csv", "text/csv", use_container_width=True)
    else:
        st.info("📭 Nenhuma movimentação registrada ainda")

# -----------------------------------------------------------------------------
# ABA 5 — ALERTAS
# -----------------------------------------------------------------------------
with aba5:
    st.subheader("⚠️ Produtos com Estoque Baixo")
    df_prod = ler_aba("Produtos")
    
    if not df_prod.empty:
        df_prod["quantidade"] = pd.to_numeric(df_prod["quantidade"], errors="coerce")
        df_prod["alerta_minimo"] = pd.to_numeric(df_prod["alerta_minimo"], errors="coerce")
        alerta = df_prod[df_prod["quantidade"] <= df_prod["alerta_minimo"]]
        
        if not alerta.empty:
            st.warning(f"🚨 {len(alerta)} produto(s) com estoque baixo!")
            st.dataframe(alerta[["nome", "quantidade", "alerta_minimo", "unidade", "local"]],
                        use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os produtos estão com estoque acima do limite de alerta")
    else:
        st.info("📭 Sem produtos cadastrados")

# -----------------------------------------------------------------------------
# RODAPÉ
# -----------------------------------------------------------------------------
st.divider()
if st.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.rerun()