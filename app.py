import streamlit as st
import os
import json
from datetime import datetime, date

# ════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Controle de Estoque Agrícola",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════
# SENHAS DE ACESSO
# ════════════════════════════════════════════════════════
SENHAS_ADMIN = ["admin123", "senha2", "senha3"]
SENHA_VISUALIZADOR = "visualizar"

# ════════════════════════════════════════════════════════
# FUNÇÕES DE SALVAR E CARREGAR DADOS
# ════════════════════════════════════════════════════════
ARQUIVO_PRODUTOS = "produtos.json"
ARQUIVO_HISTORICO = "historico.json"
ARQUIVO_LOCAIS = "locais.json"

def carregar_dados(arquivo, padrao):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

def salvar_dados(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_locais():
    padrao = ["Quarto 01", "Quarto 02", "Quarto 03", "Quarto 04", 
              "Quarto 05", "Quarto 06", "Quarto 07", "Depósito Central",
              "Córrego da Ponte Q01", "Córrego da Ponte Q02"]
    return carregar_dados(ARQUIVO_LOCAIS, padrao)

# ════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ════════════════════════════════════════════════════════
def dias_para_vencer(data_validade_str):
    try:
        hoje = date.today()
        dia, mes, ano = map(int, data_validade_str.split('/'))
        validade = date(ano, mes, dia)
        return (validade - hoje).days
    except:
        return -999

def verificar_alerta_local(produto):
    vencido = dias_para_vencer(produto["validade"]) < 0
    local_restrito = ["Córrego da Ponte Q01", "Córrego da Ponte Q02"]
    return vencido and produto["local"] not in local_restrito

# ════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.eh_admin = False

if not st.session_state.logado:
    st.title("🛡️ Controle de Estoque Agrícola")
    st.subheader("Faça seu acesso")
    
    senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
    
    if st.button("🔑 Entrar"):
        if senha_digitada in SENHAS_ADMIN:
            st.session_state.logado = True
            st.session_state.eh_admin = True
            st.success("✅ Acesso liberado — Administrador")
            st.rerun()
        elif senha_digitada == SENHA_VISUALIZADOR or senha_digitada == "":
            st.session_state.logado = True
            st.session_state.eh_admin = False
            st.info("👀 Modo visualização — Sem alterações permitidas")
            st.rerun()
        else:
            st.error("❌ Senha incorreta — contate o administrador")
    
    st.info("💡 Sem senha = apenas visualização | Senha de administrador = acesso total")
    st.stop()

# ════════════════════════════════════════════════════════
# CARREGAR DADOS
# ════════════════════════════════════════════════════════
produtos = carregar_dados(ARQUIVO_PRODUTOS, [])
historico = carregar_dados(ARQUIVO_HISTORICO, [])
locais = carregar_locais()

# ════════════════════════════════════════════════════════
# MENU LATERAL
# ════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🛡️ Controle de Estoque")
    st.subheader("DEFENSIVOS AGRÍCOLAS")
    st.divider()
    
    if st.session_state.eh_admin:
        st.success("🔑 Você é Administrador")
        pagina = st.radio(
            "Navegação",
            ["📋 Estoque", "➕ Adicionar Produto", "✏️ Editar/Saída", "📊 Histórico", "⚠️ Alertas"]
        )
    else:
        pagina = st.radio(
            "Navegação",
            ["📋 Estoque", "📊 Histórico", "⚠️ Alertas"]
        )
    
    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()

# ════════════════════════════════════════════════════════
# PÁGINA: ESTOQUE
# ════════════════════════════════════════════════════════
if pagina == "📋 Estoque":
    st.header("📋 Lista de Produtos em Estoque")
    
    if not produtos:
        st.info("📭 Nenhum produto cadastrado ainda.")
    else:
        filtro_local = st.selectbox("Filtrar por local:", ["Todos"] + locais)
        filtro_nome = st.text_input("🔍 Buscar por nome do produto:")
        
        st.divider()
        
        for i, prod in enumerate(produtos):
            mostrar = True
            if filtro_local != "Todos" and prod["local"] != filtro_local:
                mostrar = False
            if filtro_nome and filtro_nome.lower() not in prod["nome"].lower():
                mostrar = False
            
            if mostrar:
                dias = dias_para_vencer(prod["validade"])
                if dias < 0:
                    cor = "🔴"
                elif dias <= 90:
                    cor = "🟡"
                else:
                    cor = "🟢"
                
                with st.expander(f"{cor} {prod['nome']} — {prod['quantidade']} {prod['unidade']}"):
                    st.write(f"*Princípio Ativo:* {prod.get('principio_ativo', '-')}")
                    st.write(f"*Lote:* {prod.get('lote', '-')}")
                    st.write(f"*Validade:* {prod['validade']} — {dias} dias")
                    st.write(f"*Local:* {prod['local']}")
                    st.write(f"*Observação:* {prod.get('observacao', '-')}")

# ════════════════════════════════════════════════════════
# PÁGINA: ADICIONAR PRODUTO
# ════════════════════════════════════════════════════════
elif pagina == "➕ Adicionar Produto" and st.session_state.eh_admin:
    st.header("➕ Adicionar Novo Produto")
    
    with st.form("form_adicionar"):
        nome = st.text_input("Nome do Produto")
        principio_ativo = st.text_input("Princípio Ativo")
        lote = st.text_input("Número do Lote")
        quantidade = st.number_input("Quantidade", min_value=0.0, step=0.01)
        unidade = st.selectbox("Unidade", ["Litro", "Kg", "Saco", "Unidade", "Pacote"])
        validade = st.text_input("Data de Validade (DD/MM/AAAA)")
        local = st.selectbox("Local de Armazenamento", locais)
        observacao = st.text_area("Observações")
        
        if st.form_submit_button("✅ Cadastrar Produto"):
            if nome and quantidade > 0:
                novo_produto = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "nome": nome,
                    "principio_ativo": principio_ativo,
                    "lote": lote,
                    "quantidade": quantidade,
                    "unidade": unidade,
                    "validade": validade,
                    "local": local,
                    "observacao": observacao,
                    "data_cadastro": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                produtos.append(novo_produto)
                salvar_dados(ARQUIVO_PRODUTOS, produtos)
                
                historico.insert(0, {
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "tipo": "ENTRADA",
                    "produto": nome,
                    "quantidade": quantidade,
                    "unidade": unidade,
                    "local": local,
                    "lote": lote
                })
                salvar_dados(ARQUIVO_HISTORICO, historico)
                
                st.success(f"✅ {nome} cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Preencha o nome e a quantidade corretamente.")

# ════════════════════════════════════════════════════════
# PÁGINA: EDITAR / SAÍDA
# ════════════════════════════════════════════════════════
elif pagina == "✏️ Editar/Saída" and st.session_state.eh_admin:
    st.header("✏️ Saída ou Edição de Produto")
    
    if not produtos:
        st.info("📭 Nenhum produto cadastrado.")
    else:
        lista_nomes = [f"{p['nome']} ({p['local']})" for p in produtos]
        escolha = st.selectbox("Selecione o produto:", lista_nomes)
        indice = lista_nomes.index(escolha)
        prod = produtos[indice]
        
        st.info(f"*Estoque atual:* {prod['quantidade']} {prod['unidade']}")
        
        acao = st.radio("Tipo de Movimento", ["📤 Saída de Uso", "✏️ Editar Dados"])
        
        if acao == "📤 Saída de Uso":
            with st.form("form_saida"):
                qtd_saida = st.number_input("Quantidade retirada", min_value=0.01, max_value=prod["quantidade"], step=0.01)
                motivo = st.text_input("Motivo da saída / Observação")
                
                if st.form_submit_button("✅ Registrar Saída"):
                    produtos[indice]["quantidade"] -= qtd_saida
                    salvar_dados(ARQUIVO_PRODUTOS, produtos)
                    
                    historico.insert(0, {
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "tipo": "SAÍDA",
                        "produto": prod["nome"],
                        "quantidade": qtd_saida,
                        "unidade": prod["unidade"],
                        "local": prod["local"],
                        "lote": prod.get("lote", "-"),
                        "motivo": motivo
                    })
                    salvar_dados(ARQUIVO_HISTORICO, historico)
                    
                    st.success(f"✅ Saída registrada! Restante: {produtos[indice]['quantidade']} {prod['unidade']}")
                    st.rerun()
        
        else:
            with st.form("form_editar"):
                novo_nome = st.text_input("Nome", value=prod["nome"])
                novo_qtd = st.number_input("Quantidade", min_value=0.0, value=prod["quantidade"], step=0.01)
                novo_local = st.selectbox("Local", locais, index=locais.index(prod["local"]) if prod["local"] in locais else 0)
                nova_validade = st.text_input("Validade (DD/MM/AAAA)", value=prod["validade"])
                nova_obs = st.text_area("Observação", value=prod.get("observacao", ""))
                
                if st.form_submit_button("✅ Salvar Alterações"):
                    produtos[indice]["nome"] = novo_nome
                    produtos[indice]["quantidade"] = novo_qtd
                    produtos[indice]["local"] = novo_local
                    produtos[indice]["validade"] = nova_validade
                    produtos[indice]["observacao"] = nova_obs
                    salvar_dados(ARQUIVO_PRODUTOS, produtos)
                    st.success("✅ Produto atualizado!")
                    st.rerun()

# ════════════════════════════════════════════════════════
# PÁGINA: HISTÓRICO
# ════════════════════════════════════════════════════════
elif pagina == "📊 Histórico":
    st.header("📊 Histórico de Movimentações")
    
    if not historico:
        st.info("📭 Nenhuma movimentação registrada ainda.")
    else:
        st.subheader(f"Total de registros: {len(historico)}")
        st.divider()
        
        for mov in historico:
            if mov["tipo"] == "ENTRADA":
                st.success(f"📥 *{mov['data']}* | {mov['tipo']} | {mov['produto']} — {mov['quantidade']} {mov['unidade']} | {mov['local']}")
            else:
                st.warning(f"📤 *{mov['data']}* | {mov['tipo']} | {mov['produto']} — {mov['quantidade']} {mov['unidade']} | {mov['local']}")

# ════════════════════════════════════════════════════════
# PÁGINA: ALERTAS
# ════════════════════════════════════════════════════════
elif pagina == "⚠️ Alertas":
    st.header("⚠️ Produtos com Validade Próxima ou Vencida")
    
    vencidos = []
    a_vencer = []
    
    for p in produtos:
        dias = dias_para_vencer(p["validade"])
        if dias < 0:
            vencidos.append(p)
        elif dias <= 90:
            a_vencer.append(p)
    
    if vencidos:
        st.error(f"🔴 PRODUTOS VENCIDOS — {len(vencidos)} item(is)")
        for p in vencidos:
            st.write(f"🔴 *{p['nome']}* — Venceu em {p['validade']} | {p['local']}")
        st.divider()
    
    if a_vencer:
        st.warning(f"🟢 A vencer em até 90 dias — {len(a_vencer)} item(is)")
        for p in a_vencer:
            dias = dias_para_vencer(p["validade"])
            st.write(f"🟡 *{p['nome']}* — Vence em {dias} dias ({p['validade']}) | {p['local']}")
        st.divider()
    
    if not vencidos and not a_vencer:
        st.success("✅ Todos os produtos estão dentro do prazo de validade!")

# ════════════════════════════════════════════════════════
# RODAPÉ
# ════════════════════════════════════════════════════════
st.divider()
st.caption("🛡️ Sistema de Controle de Estoque Agrícola • Atualizado em: " + datetime.now().strftime("%d/%m/%Y %H:%M"))