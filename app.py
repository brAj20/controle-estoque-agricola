import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json
import os

# -----------------------------------------------------------------------------
# CONFIGURAÇÕES PRINCIPAIS
# -----------------------------------------------------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
NOME_PLANILHA = "Controle de Estoque"

# Senhas de acesso
SENHA_ADMIN = "admin123"
SENHA_CONSULTA = "view123"

# Arquivos de cache para funcionar sem internet
PASTA_CACHE = "dados_cache"
os.makedirs(PASTA_CACHE, exist_ok=True)
CACHE_PRODUTOS = os.path.join(PASTA_CACHE, "produtos.json")
CACHE_HISTORICO = os.path.join(PASTA_CACHE, "historico.json")
CACHE_LOCAIS = os.path.join(PASTA_CACHE, "locais.json")

# -----------------------------------------------------------------------------
# FUNÇÕES DE CACHE — GUARDA DADOS PARA VER SEM INTERNET
# -----------------------------------------------------------------------------
def salvar_cache(dados, caminho):
    """Salva dados localmente para visualização offline"""
    try:
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, default=str)
        return True
    except:
        return False

def carregar_cache(caminho):
    """Carrega os últimos dados salvos quando não há internet"""
    try:
        if os.path.exists(caminho):
            with open(caminho, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return None

# -----------------------------------------------------------------------------
# CONEXÃO INTELIGENTE COM GOOGLE SHEETS
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Conectando ao sistema...")
def conectar_sistema():
    """Tenta conectar na nuvem, se não conseguir avisa que está offline"""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        cliente = gspread.authorize(creds)
        return cliente, True
    except Exception:
        return None, False

cliente, online = conectar_sistema()

# -----------------------------------------------------------------------------
# FUNÇÕES DE LEITURA E GRAVAÇÃO INTELIGENTES
# -----------------------------------------------------------------------------
def ler_dados(nome_aba, cache_arquivo):
    """Lê da nuvem se possível, senão mostra os últimos dados salvos"""
    if online:
        try:
            planilha = cliente.open(NOME_PLANILHA)
            aba = planilha.worksheet(nome_aba)
            dados = aba.get_all_records()
            salvar_cache(dados, cache_arquivo)
            return pd.DataFrame(dados) if dados else pd.DataFrame()
        except Exception:
            st.warning("⚠️ Usando dados salvos — mostrando última atualização")
    
    dados_salvos = carregar_cache(cache_arquivo)
    if dados_salvos:
        st.info("📴 Sem internet — mostrando dados da última vez que foi atualizado")
        return pd.DataFrame(dados_salvos)
    return pd.DataFrame()

def salvar_dados(nome_aba, df, cache_arquivo):
    """Salva na nuvem e sempre salva localmente como backup"""
    dados_lista = df.to_dict('records') if not df.empty else []
    salvar_cache(dados_lista, cache_arquivo)
    
    if online:
        try:
            planilha = cliente.open(NOME_PLANILHA)
            aba = planilha.worksheet(nome_aba)
            aba.clear()
            if not df.empty:
                aba.update([list(df.columns)] + df.values.tolist())
            return True, "✅ Salvo e sincronizado!"
        except Exception:
            return False, "⚠️ Salvo localmente — sincronizará quando voltar a internet"
    
    return False, "📴 Salvo no aparelho. Sincronização pendente."

def registrar_historico_completo(tipo, produto, qtd, unidade, local, resp, obs="", id_prod=""):
    """Registra movimentação com data e hora automáticas"""
    df_hist = ler_dados("Historico", CACHE_HISTORICO)
    nova_entrada = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tipo": tipo,
        "produto": produto,
        "quantidade": qtd,
        "unidade": unidade,
        "local": local,
        "responsavel": resp,
        "observacao": obs,
        "id_produto": id_prod
    }
    df_hist = pd.concat([df_hist, pd.DataFrame([nova_entrada])], ignore_index=True)
    salvar_dados("Historico", df_hist, CACHE_HISTORICO)

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Controle de Estoque", layout="wide", page_icon="📦")

# -----------------------------------------------------------------------------
# SISTEMA DE LOGIN COM LEMBRANÇA AUTOMÁTICA
# -----------------------------------------------------------------------------
def verificar_sessao():
    """Verifica se o usuário já entrou e se quer ser lembrado"""
    if "logado" in st.session_state and st.session_state.logado:
        return True
    return False

# TELA DE LOGIN
if not verificar_sessao():
    st.title("🔐 Controle de Estoque — Defensivos Agrícolas")
    st.subheader("Acesse o sistema")
    
    senha = st.text_input("Digite sua senha:", type="password")
    lembrar = st.checkbox("Lembrar meu acesso neste aparelho")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Entrar", use_container_width=True, type="primary"):
            if senha == SENHA_ADMIN:
                st.session_state.logado = True
                st.session_state.tipo = "admin"
                st.session_state.usuario = "Administrador"
                st.rerun()
            elif senha == SENHA_CONSULTA:
                st.session_state.logado = True
                st.session_state.tipo = "consulta"
                st.session_state.usuario = "Visualizador"
                st.rerun()
            else:
                st.error("❌ Senha incorreta! Tente novamente.")
    
    st.info("💡 Marque 'Lembrar meu acesso' para não precisar digitar senha na próxima vez")
    st.stop()

# -----------------------------------------------------------------------------
# ÁREA PRINCIPAL DO SISTEMA
# -----------------------------------------------------------------------------
st.title("📦 Controle de Estoque — Defensivos Agrícolas")

# Status da conexão
status = "✅ Online — dados atualizados em tempo real" if online else "📴 Modo offline — mostrando última atualização"
st.success(f"Conectado como: {st.session_state.usuario} | {status}")

# MENU DE ABAS
aba_estoque, aba_adicionar, aba_saida, aba_historico, aba_alertas = st.tabs([
    "📋 Estoque", "➕ Adicionar", "✏️ Saída", "📊 Histórico", "⚠️ Alertas"
])

# ═══════════════════════════════════════════════════════════════════════════
# ABA 1 — ESTOQUE GERAL
# ═══════════════════════════════════════════════════════════════════════════
with aba_estoque:
    st.subheader("Lista de Produtos")
    df_prod = ler_dados("Produtos", CACHE_PRODUTOS)
    
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True, hide_index=True)
        
        st.subheader("📊 Resumo Rápido")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Itens", len(df_prod))
        with col2:
            try:
                total = pd.to_numeric(df_prod["quantidade"], errors="coerce").sum()
                st.metric("Quantidade Total", f"{total:.0f}")
            except:
                st.metric("Quantidade Total", "-")
        with col3:
            st.metric("Última Atualização", datetime.now().strftime("%d/%m às %H:%M"))
    else:
        st.info("📭 Nenhum produto cadastrado ainda. Vá em 'Adicionar' para começar.")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 2 — ADICIONAR NOVO PRODUTO
# ═══════════════════════════════════════════════════════════════════════════
with aba_adicionar:
    if st.session_state.tipo != "admin":
        st.warning("🔒 Apenas administradores podem cadastrar produtos")
    else:
        st.subheader("➕ Cadastrar Novo Produto")
        df_locais = ler_dados("Locais", CACHE_LOCAIS)
        lista_locais = df_locais["nome"].dropna().tolist() if not df_locais.empty and "nome" in df_locais.columns else []
        
        with st.form("form_cadastro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_prod = st.text_input("Nome do Produto *")
                cat_prod = st.text_input("Categoria")
                qtd_prod = st.number_input("Quantidade Inicial *", min_value=0.0, step=0.5)
            with col2:
                uni_prod = st.selectbox("Unidade", ["Litro", "Kg", "Unidade", "Saco", "Caixa", "Lata"])
                if lista_locais:
                    local_prod = st.selectbox("Local de Armazenamento", lista_locais + ["— Outro —"])
                    if local_prod == "— Outro —":
                        local_prod = st.text_input("Digite o local")
                else:
                    local_prod = st.text_input("Local de Armazenamento *")
                alerta_prod = st.number_input("Avisar quando chegar em", min_value=0.0, step=0.5, value=5.0)
            obs_prod = st.text_area("Observação")
            
            if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True, type="primary"):
                if nome_prod and local_prod and qtd_prod >= 0:
                    df_atual = ler_dados("Produtos", CACHE_PRODUTOS)
                    novo_id = str(len(df_atual) + 1) if not df_atual.empty else "1"
                    
                    novo_item = {
                        "id": novo_id,
                        "nome": nome_prod,
                        "categoria": cat_prod or "",
                        "quantidade": qtd_prod,
                        "unidade": uni_prod,
                        "local": local_prod,
                        "alerta_minimo": alerta_prod,
                        "observacao": obs_prod or ""
                    }
                    
                    df_atual = pd.concat([df_atual, pd.DataFrame([novo_item])], ignore_index=True)
                    ok, mensagem = salvar_dados("Produtos", df_atual, CACHE_PRODUTOS)
                    registrar_historico_completo("ENTRADA", nome_prod, qtd_prod, uni_prod, 
                                                local_prod, st.session_state.usuario, obs_prod, novo_id)
                    st.success(f"✅ *{nome_prod}* cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Preencha os campos obrigatórios (*)")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 3 — REGISTRAR SAÍDA / CONSUMO
# ═══════════════════════════════════════════════════════════════════════════
with aba_saida:
    if st.session_state.tipo != "admin":
        st.warning("🔒 Apenas administradores podem registrar saídas")
    else:
        st.subheader("✏️ Registrar Saída / Consumo")
        df_prod = ler_dados("Produtos", CACHE_PRODUTOS)
        
        if not df_prod.empty and "nome" in df_prod.columns:
            produto_escolhido = st.selectbox("Selecione o Produto", df_prod["nome"].tolist())
            dados = df_prod[df_prod["nome"] == produto_escolhido].iloc[0]
            
            st.info(f"📦 Estoque atual: *{dados['quantidade']} {dados['unidade']}* | Local: {dados['local']}")
            
            with st.form("form_saida"):
                qtd_saida = st.number_input("Quantidade de Saída *", 
                                           min_value=0.01, 
                                           max_value=float(dados["quantidade"]), 
                                           step=0.5)
                motivo_saida = st.text_area("Motivo / Observação")
                
                if st.form_submit_button("📤 Confirmar Saída", use_container_width=True, type="primary"):
                    indice = df_prod[df_prod["nome"] == produto_escolhido].index[0]
                    df_prod.at[indice, "quantidade"] = float(df_prod.at[indice, "quantidade"]) - float(qtd_saida)
                    
                    ok, msg = salvar_dados("Produtos", df_prod, CACHE_PRODUTOS)
                    registrar_historico_completo("SAÍDA", produto_escolhido, qtd_saida, dados["unidade"],
                                                dados["local"], st.session_state.usuario, motivo_saida,
                                                str(df_prod.at[indice, "id"]))
                    st.success(f"✅ Saída registrada! Restam: *{df_prod.at[indice, 'quantidade']} {dados['unidade']}*")
                    st.rerun()
        else:
            st.info("📭 Sem produtos cadastrados ainda")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 4 — HISTÓRICO COMPLETO
# ═══════════════════════════════════════════════════════════════════════════
with aba_historico:
    st.subheader("📊 Histórico de Todas as Movimentações")
    df_hist = ler_dados("Historico", CACHE_HISTORICO)
    
    if not df_hist.empty:
        st.dataframe(df_hist.sort_values("data", ascending=False), use_container_width=True, hide_index=True)
        
        # Botão para baixar o histórico em Excel
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Histórico Completo", csv, "historico_estoque.csv", 
                          "text/csv", use_container_width=True)
    else:
        st.info("📭 Nenhuma movimentação registrada ainda")

# ═══════════════════════════════════════════════════════════════════════════
# ABA 5 — ALERTAS DE ESTOQUE BAIXO
# ═══════════════════════════════════════════════════════════════════════════
with aba_alertas:
    st.subheader("⚠️ Produtos com Estoque Baixo")
    df_prod = ler_dados("Produtos", CACHE_PRODUTOS)
    
    if not df_prod.empty and "quantidade" in df_prod.columns and "alerta_minimo" in df_prod.columns:
        df_prod["quantidade"] = pd.to_numeric(df_prod["quantidade"], errors="coerce")
        df_prod["alerta_minimo"] = pd.to_numeric(df_prod["alerta_minimo"], errors="coerce")
        
        produtos_com_alerta = df_prod[df_prod["quantidade"] <= df_prod["alerta_minimo"]]
        
        if not produtos_com_alerta.empty:
            st.warning(f"🚨 Atenção! {len(produtos_com_alerta)} produto(s) com estoque baixo")
            st.dataframe(produtos_com_alerta[["nome", "quantidade", "alerta_minimo", "unidade", "local"]],
                        use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os produtos estão com estoque acima do limite de alerta!")
    else:
        st.info("📭 Sem produtos para verificar ainda")

# -----------------------------------------------------------------------------
# RODAPÉ
# -----------------------------------------------------------------------------
st.divider()
st.caption(f"Sistema de Controle de Estoque | Última sincronização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

if st.button("🚪 Sair da conta", use_container_width=True):
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
    st.rerun()
