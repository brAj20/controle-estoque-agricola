import streamlit as st
import json
import os
from datetime import datetime, date

# ------------------- CONFIGURAÇÕES DE PÁGINA -------------------
st.set_page_config(
    page_title="Controle de Estoque — Defensivos Agrícolas",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------- ESTILO PERSONALIZADO -------------------
st.markdown("""
<style>
    :root {
        --primaria: #0E7C7B;
        --secundaria: #284B53;
        --alerta: #F4A261;
        --perigo: #E76F51;
        --sucesso: #2A9D8F;
        --fundo-escuro: #1D3557;
        --texto-claro: #F1FAEE;
    }
    
    .main-header {
        background: linear-gradient(135deg, #0E7C7B 0%, #284B53 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .card {
        background: white;
        padding: 1.25rem;
        border-radius: 10px;
        border-left: 4px solid var(--primaria);
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .card-alerta { border-left-color: var(--alerta); }
    .card-perigo { border-left-color: var(--perigo); background: #fff2f2; }
    .card-sucesso { border-left-color: var(--sucesso); background: #f0fdf4; }
    .card-escuro { background: var(--fundo-escuro); color: white; border-left: none; }
    
    .metric-card {
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: 500;
    }
    .metric-card h2 { margin: 0.5rem 0; font-size: 1.8rem; }
    .metric-card p { margin: 0; opacity: 0.9; font-size: 0.9rem; }
    
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-sucesso { background: #d1fae5; color: #065f46; }
    .badge-alerta { background: #fef3c7; color: #92400e; }
    .badge-perigo { background: #fee2e2; color: #991b1b; }
    .badge-info { background: #e0f2fe; color: #075985; }
    
    .produto-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.75rem;
        border: 1px solid #e5e7eb;
    }
    
    .btn-acao {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.4rem 0.7rem;
        border-radius: 6px;
        font-size: 0.85rem;
        cursor: pointer;
        border: none;
        transition: 0.2s;
    }
    .btn-acao:hover { transform: scale(1.05); }
    
    .alerta-urgente {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
        color: white;
        padding: 1.25rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .stButton>button { border-radius: 8px; font-weight: 500; }
    .stButton>button:hover { transform: translateY(-1px); transition: 0.2s; }
    
    hr { margin: 1.5rem 0; border: none; border-top: 1px solid #e5e7eb; }
    
    .sidebar .css-1d391kg { background: #f8fafc; }
    
    div[data-testid="stSidebarNav"] { display: none; }
    
    .filter-tag {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        margin: 0.25rem;
        cursor: pointer;
        border: 2px solid transparent;
    }
    .filter-tag.active {
        background: var(--primaria);
        color: white;
        border-color: var(--primaria);
    }
</style>
""", unsafe_allow_html=True)

# ------------------- ARQUIVOS DE DADOS -------------------
ARQUIVO_PRODUTOS = "produtos.json"
ARQUIVO_HISTORICO = "historico.json"
ARQUIVO_LOCAIS = "locais.json"
ARQUIVO_USO = "produtos_em_uso.json"

# ------------------- FUNÇÕES AUXILIARES -------------------
def carregar_dados(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_dados(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def dias_para_vencer(data_validade):
    try:
        venc = datetime.strptime(data_validade, "%d/%m/%Y").date()
        hoje = date.today()
        return (venc - hoje).days
    except:
        return None

def status_validade(dias):
    if dias is None: return ("❓", "badge-info", "Sem data")
    if dias < 0: return ("🔴", "badge-perigo", f"VENCIDO há {abs(dias)} dia(s)")
    if dias <= 15: return ("⚠️", "badge-perigo", f"Vence em {dias} dias")
    if dias <= 30: return ("⏳", "badge-alerta", f"Vence em {dias} dias")
    return ("✅", "badge-sucesso", f"Vence em {dias} dias")

# ------------------- LOGIN -------------------
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("""
    <div class='main-header'>
        <h1 style='text-align:center;'>🌿 Controle de Estoque — Defensivos Agrícolas</h1>
        <p style='text-align:center; opacity:0.9;'>Sistema de Gestão de Estoques da Propriedade</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("🔐 Acesso ao Sistema")
        senha = st.text_input("Senha de Acesso:", type="password", placeholder="Digite sua senha...")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔑 Entrar", type="primary", use_container_width=True):
                if senha == "admin123":
                    st.session_state.logado = True
                    st.session_state.usuario = "Administrador"
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        with col_b:
            if st.button("👁️ Visualizador", use_container_width=True):
                st.session_state.logado = True
                st.session_state.usuario = "Visualizador"
                st.rerun()
    st.stop()

# Carregar dados
produtos = carregar_dados(ARQUIVO_PRODUTOS)
historico = carregar_dados(ARQUIVO_HISTORICO)
locais = carregar_dados(ARQUIVO_LOCAIS)
produtos_em_uso = carregar_dados(ARQUIVO_USO)

if not locais:
    locais = ["Barracão", "Quarto 05", "Quarto 06", "Quarto 07", "Córrego da Ponte - Q01", "Córrego da Ponte - Q02"]
    salvar_dados(ARQUIVO_LOCAIS, locais)

# ------------------- MENU LATERAL -------------------
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0;'>
        <h2 style='margin:0; color: #0E7C7B;'>🌿 Defensivos Agrícolas</h2>
        <p style='color: #666; font-size:0.9rem;'>Controle de Estoque</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<p style='color:#666; font-size:0.85rem;'>👤 {st.session_state.usuario}</p>", unsafe_allow_html=True)
    st.divider()
    
    pagina = st.radio(
        "📂 Navegação",
        [
            "📊 Painel Geral",
            "📦 Estoque Total",
            "📅 Todas as Validades",
            "⚠️ Controle de Validades",
            "📍 Estoque por Local",
            "🔄 Produtos em Uso",
            "🚨 Vencidos no Local Errado",
            "✏️ Movimentação",
            "↔️ Transferência entre Locais",
            "📜 Histórico Completo",
            "💰 Histórico de Gastos"
        ],
        label_visibility="collapsed"
    )
    
    st.divider()
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

# ==================== FUNÇÕES REUTILIZÁVEIS ====================
def filtros_busca(lista_produtos, chave_nome="nome"):
    busca = st.text_input("🔍 Pesquisar por produto, local ou validade...", placeholder="Digite para buscar...")
    if not busca:
        return lista_produtos
    return [p for p in lista_produtos if 
            busca.lower() in p.get(chave_nome, "").lower() or
            busca.lower() in p.get("local", "").lower() or
            busca.lower() in p.get("validade", "").lower()]

def card_produto(produto, mostrar_acoes=True):
    nome = produto.get("nome", "Sem nome")
    qtd = produto.get("quantidade", 0)
    un = produto.get("unidade", "un")
    validade = produto.get("validade", "--/--/----")
    local = produto.get("local", "Não definido")
    lote = produto.get("lote", "-")
    dias = dias_para_vencer(validade)
    icone, classe, texto_status = status_validade(dias)
    
    st.markdown(f"""
    <div class='produto-card'>
        <h4 style='margin:0 0 0.5rem 0;'>📦 {nome}</h4>
        <p style='margin:0.25rem 0;'><strong>Quantidade:</strong> {qtd} {un} | <strong>Lote:</strong> {lote}</p>
        <p style='margin:0.25rem 0;'><strong>Validade:</strong> {validade} | <strong>Local:</strong> 📍 {local}</p>
        <p class='badge {classe}'>{icone} {texto_status}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if mostrar_acoes and st.session_state.usuario == "Administrador":
        col1, col2, col3, col4, col5 = st.columns(5)
        idx = produtos.index(produto) if produto in produtos else -1
        if idx >= 0:
            with col1:
                if st.button("↔️ Transferir", key=f"transf_{idx}", use_container_width=True):
                    st.session_state.transf_produto = idx
                    st.info("Vá em '↔️ Transferência entre Locais' para concluir")
            with col2:
                if st.button("🔄 Usar", key=f"usar_{idx}", use_container_width=True):
                    if produto not in produtos_em_uso:
                        produtos_em_uso.append(produto.copy())
                        salvar_dados(ARQUIVO_USO, produtos_em_uso)
                        st.success(f"'{nome}' marcado como em uso!")
                        st.rerun()
            with col3:
                if st.button("📤 Saída", key=f"saida_{idx}", use_container_width=True):
                    st.session_state.saida_produto = idx
                    st.info("Vá em '✏️ Movimentação' → Saída para registrar")
            with col4:
                if st.button("✏️ Editar", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.editar_produto = idx
                    st.info("Função em desenvolvimento")
            with col5:
                if st.button("🗑️ Excluir", key=f"del_{idx}", use_container_width=True):
                    st.session_state.excluir_produto = idx
                    st.warning("Confirmação necessária — recarregue para cancelar")

# ==================== PÁGINAS ====================

# --------------- PAINEL GERAL ---------------
if pagina == "📊 Painel Geral":
    st.title("📊 Painel Geral")
    st.subheader("Resumo Completo do Estoque")
    
    # Cálculos
    total_produtos = len(produtos)
    total_lotes = len(produtos)
    em_uso = len(produtos_em_uso)
    
    hoje = date.today()
    vencendo_15d = 0
    vencendo_30d = 0
    vencidos = 0
    estoque_baixo = 0
    
    for p in produtos:
        dias = dias_para_vencer(p.get("validade", ""))
        qtd = p.get("quantidade", 0)
        minimo = p.get("estoque_minimo", 0)
        if qtd <= minimo:
            estoque_baixo += 1
        if dias is not None:
            if dias < 0: vencidos += 1
            elif dias <= 15: vencendo_15d += 1
            elif dias <= 30: vencendo_30d += 1
    
    # Alerta urgente
    locais_errados = [p for p in produtos if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) < 0 and "Córrego da Ponte" not in p.get("local","")]
    if locais_errados:
        st.markdown(f"""
        <div class='alerta-urgente'>
            <h3 style='margin:0;'>⚠️ ALERTA URGENTE — VENCIDOS NO LOCAL ERRADO</h3>
            <p>Produtos vencidos só podem ficar no Córrego da Ponte - Q01 ou Q02</p>
            <strong>{len(locais_errados)} produto(s) precisam ser transferidos!</strong>
        </div>
        """, unsafe_allow_html=True)
    
    # Cards principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class='metric-card' style='background: linear-gradient(135deg, #0E7C7B 0%, #284B53 100%);'>
            <p>📦 LOTES</p>
            <h2>{}</h2>
            <p>Cadastrados</p>
        </div>
        """.format(total_lotes), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='metric-card' style='background: linear-gradient(135deg, #2A9D8F 0%, #40916c 100%);'>
            <p>🔄 EM USO</p>
            <h2>{}</h2>
            <p>Fora do estoque</p>
        </div>
        """.format(em_uso), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='metric-card' style='background: linear-gradient(135deg, #F4A261 0%, #E9C46A 100%);'>
            <p>⏳ VENCENDO</p>
            <h2>{}</h2>
            <p>Até 30 dias</p>
        </div>
        """.format(vencendo_15d + vencendo_30d), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class='metric-card' style='background: linear-gradient(135deg, #E76F51 0%, #d62828 100%);'>
            <p>🔴 VENCIDOS</p>
            <h2>{}</h2>
            <p>Precisam de atenção</p>
        </div>
        """.format(vencidos), unsafe_allow_html=True)
    
    st.divider()
    
    # Segunda linha
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        <div class='card card-escuro'>
            <h4>📊 ESTOQUE TOTAL</h4>
            <h2>{}</h2>
            <p>Produtos cadastrados</p>
        </div>
        """.format(total_produtos), unsafe_allow_html=True)
    
    with col_b:
        st.markdown("""
        <div class='card card-escuro'>
            <h4>⚠️ ESTOQUE BAIXO</h4>
            <h2>{}</h2>
            <p>Produtos abaixo do mínimo</p>
        </div>
        """.format(estoque_baixo), unsafe_allow_html=True)
    
    with col_c:
        st.markdown("""
        <div class='card card-escuro'>
            <h4>🏠 LOCAIS</h4>
            <h2>{}</h2>
            <p>Pontos de armazenamento</p>
        </div>
        """.format(len(locais)), unsafe_allow_html=True)
    
    st.divider()
    
    # Estoque baixo
    st.subheader("⚠️ Produtos com Estoque Baixo")
    baixos = [p for p in produtos if p.get("quantidade", 0) <= p.get("estoque_minimo", 5)]
    if baixos:
        for p in baixos[:5]:
            st.markdown(f"""
            <div class='card card-alerta'>
                <strong>{p.get('nome')}</strong> — {p.get('quantidade')} {p.get('unidade')} (mínimo: {p.get('estoque_minimo')})
                | 📍 {p.get('local')}
            </div>
            """, unsafe_allow_html=True)
        if len(baixos) > 5:
            st.info(f"...e mais {len(baixos)-5} produto(s). Vá em '📦 Estoque Total' para ver tudo.")
    else:
        st.success("✅ Nenhum produto com estoque baixo no momento!")

# --------------- ESTOQUE TOTAL ---------------
elif pagina == "📦 Estoque Total":
    st.title("📦 Todos os Produtos")
    st.subheader("Defensivos Agrícolas")
    
    col_filtro1, col_filtro2 = st.columns([2,1])
    with col_filtro1:
        filtro_status = st.selectbox("Filtrar por Status", ["Todos", "✅ Disponível", "⏳ Vencendo", "🔴 Vencido"])
    with col_filtro2:
        filtro_local = st.selectbox("Filtrar por Local", ["Todos"] + locais)
    
    busca = st.text_input("🔍 Pesquisar por produto, local ou validade...")
    
    # Aplicar filtros
    lista_filtrada = produtos.copy()
    if filtro_status == "✅ Disponível":
        lista_filtrada = [p for p in lista_filtrada if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) > 30]
    elif filtro_status == "⏳ Vencendo":
        lista_filtrada = [p for p in lista_filtrada if dias_para_vencer(p.get("validade","")) and 0 <= dias_para_vencer(p.get("validade","")) <= 30]
    elif filtro_status == "🔴 Vencido":
        lista_filtrada = [p for p in lista_filtrada if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) < 0]
    
    if filtro_local != "Todos":
        lista_filtrada = [p for p in lista_filtrada if p.get("local") == filtro_local]
    
    if busca:
        lista_filtrada = [p for p in lista_filtrada if 
            busca.lower() in p.get("nome","").lower() or
            busca.lower() in p.get("local","").lower() or
            busca.lower() in p.get("validade","").lower()]
    
    st.subheader(f"{len(lista_filtrada)} produto(s) encontrado(s)")
    
    if not lista_filtrada:
        st.info("📋 Nenhum produto encontrado. Vá em '✏️ Movimentação → Nova Entrada' para cadastrar!")
    else:
        for p in lista_filtrada:
            card_produto(p)

# --------------- TODAS AS VALIDADES ---------------
elif pagina == "📅 Todas as Validades":
    st.title("📅 Todas as Validades")
    st.subheader("Todas as datas de validade, em ordem alfabética")
    
    filtro = st.radio("Filtrar:", ["Todas", "🔴 Vencidas", "⚠️ 15 dias", "⏳ 30 dias", "✅ Em dia"], horizontal=True)
    busca = st.text_input("🔍 Pesquisar por produto ou local...")
    
    lista = produtos.copy()
    if filtro == "🔴 Vencidas":
        lista = [p for p in lista if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) < 0]
    elif filtro == "⚠️ 15 dias":
        lista = [p for p in lista if dias_para_vencer(p.get("validade","")) and 0 <= dias_para_vencer(p.get("validade","")) <= 15]
    elif filtro == "⏳ 30 dias":
        lista = [p for p in lista if dias_para_vencer(p.get("validade","")) and 15 < dias_para_vencer(p.get("validade","")) <= 30]
    elif filtro == "✅ Em dia":
        lista = [p for p in lista if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) > 30]
    
    if busca:
        lista = [p for p in lista if busca.lower() in p.get("nome","").lower() or busca.lower() in p.get("local","").lower()]
    
    lista.sort(key=lambda x: x.get("nome","").lower())
    
    for p in lista:
        dias = dias_para_vencer(p.get("validade",""))
        icone, classe, _ = status_validade(dias)
        st.markdown(f"""
        <div class='produto-card'>
            <h4 style='margin:0;'>{icone} {p.get('nome')}</h4>
            <p>Vence: <strong>{p.get('validade')}</strong> | {p.get('quantidade')} {p.get('unidade')}</p>
            <p>📍 {p.get('local')}</p>
            <p class='badge {classe}'>{texto_status if 'texto_status' in locals() else ''}</p>
        </div>
        """, unsafe_allow_html=True)

# --------------- CONTROLE DE VALIDADES ---------------
elif pagina == "⚠️ Controle de Validades":
    st.title("⚠️ Controle de Validades")
    st.subheader("O que vence em breve e o que já venceu")
    
    vencidos = [p for p in produtos if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) < 0]
    vencendo = [p for p in produtos if dias_para_vencer(p.get("validade","")) and 0 <= dias_para_vencer(p.get("validade","")) <= 30]
    
    st.markdown(f"<h3 style='color:#d62828;'>🔴 Produtos Vencidos ({len(vencidos)})</h3>", unsafe_allow_html=True)
    if vencidos:
        for p in vencidos:
            card_produto(p)
    else:
        st.success("✅ Nenhum produto vencido!")
    
    st.markdown(f"<h3 style='color:#f4a261;'>⏳ Produtos Vencendo em até 30 dias ({len(vencendo)})</h3>", unsafe_allow_html=True)
    if vencendo:
        for p in vencendo:
            card_produto(p)
    else:
        st.success("✅ Nenhum produto vencendo em breve!")

# --------------- ESTOQUE POR LOCAL ---------------
elif pagina == "📍 Estoque por Local":
    st.title("📍 Estoque por Local")
    st.subheader("Escolha um local para ver o que tem guardado lá")
    
    for local in locais:
        produtos_local = [p for p in produtos if p.get("local") == local]
        total_qtd = sum(p.get("quantidade", 0) for p in produtos_local)
        st.markdown(f"""
        <div class='card'>
            <h4>📍 {local}</h4>
            <p><strong>{len(produtos_local)}</strong> lote(s) | Total: <strong>{total_qtd:.2f}</strong> unidade(s)</p>
        </div>
        """, unsafe_allow_html=True)
        
        if produtos_local:
            for p in produtos_local:
                st.markdown(f"- *{p.get('nome')}*: {p.get('quantidade')} {p.get('unidade')} | Vence: {p.get('validade')}")
        st.divider()

# --------------- PRODUTOS EM USO ---------------
elif pagina == "🔄 Produtos em Uso":
    st.title("🔄 Produtos em Uso")
    st.subheader("O que está sendo usado — sai daqui para voltar depois")
    
    if not produtos_em_uso:
        st.markdown("""
        <div style='text-align:center; padding:3rem; color:#666;'>
            <p style='font-size:3rem;'>🔁</p>
            <p>Nenhum produto em uso no momento.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, p in enumerate(produtos_em_uso):
            st.markdown(f"""
            <div class='card card-sucesso'>
                <h4>🔄 {p.get('nome')}</h4>
                <p>Quantidade: {p.get('quantidade')} {p.get('unidade')} | Local de origem: {p.get('local')}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✅ Devolvido ao Estoque", key=f"devolver_{i}"):
                produtos_em_uso.pop(i)
                salvar_dados(ARQUIVO_USO, produtos_em_uso)
                st.success(f"'{p.get('nome')}' devolvido ao estoque!")
                st.rerun()

# --------------- VENCIDOS NO LOCAL ERRADO ---------------
elif pagina == "🚨 Vencidos no Local Errado":
    st.title("🚨 Vencidos no Local Errado")
    st.subheader("Produtos vencidos guardados fora do Córrego da Ponte")
    
    local_correto = ["Córrego da Ponte - Q01", "Córrego da Ponte - Q02"]
    vencidos_fora = [p for p in produtos if dias_para_vencer(p.get("validade","")) and dias_para_vencer(p.get("validade","")) < 0 and p.get("local") not in local_correto]
    
    if not vencidos_fora:
        st.markdown("""
        <div style='background:#e8f5e9; padding:2rem; border-radius:10px; text-align:center;'>
            <h3 style='color:#2d6a4f;'>✅ Tudo Certo!</h3>
            <p>Nenhum produto vencido no local errado.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='alerta-urgente'>
            <h3>⚠️ ALERTA URGENTE — {len(vencidos_fora)} LOTE(S) NO LOCAL ERRADO</h3>
            <p>Vencidos só podem ficar no Córrego da Ponte - Q01 ou Q02. Transfira agora!</p>
        </div>
        """, unsafe_allow_html=True)
        
        for p in vencidos_fora:
            st.markdown(f"""
            <div class='card card-perigo'>
                <h4>{p.get('nome')} — {p.get('quantidade')} {p.get('unidade')}</h4>
                <p>📍 Local atual: <strong>{p.get('local')}</strong> | Venceu em: {p.get('validade')}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"➡️ Transferir para Q01", key=f"transf_q01_{p.get('nome')}"):
                idx = produtos.index(p)
                produtos[idx]["local"] = "Córrego da Ponte - Q01"
                salvar_dados(ARQUIVO_PRODUTOS, produtos)
                st.success("✅ Transferido para Córrego da Ponte - Q01!")
                st.rerun()
            if st.button(f"➡️ Transferir para Q02", key=f"transf_q02_{p.get('nome')}"):
                idx = produtos.index(p)
                produtos[idx]["local"] = "Córrego da Ponte - Q02"
                salvar_dados(ARQUIVO_PRODUTOS, produtos)
                st.success("✅ Transferido para Córrego da Ponte - Q02!")
                st.rerun()

# --------------- MOVIMENTAÇÃO ---------------
elif pagina == "✏️ Movimentação":
    st.title("✏️ Movimentação")
    st.subheader("Tudo junto num lugar só — escolha o que registrar")
    
    col_entrada, col_saida = st.columns(2)
    
    with col_entrada:
        st.markdown("""
        <div style='background:#e8f5e9; padding:1.5rem; border-radius:10px; text-align:center;'>
            <h3>📥 NOVA ENTRADA</h3>
            <p>Produto chegando ao estoque</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_entrada", clear_on_submit=True):
            nome = st.text_input("Nome do Produto")
            col1, col2 = st.columns(2)
            with col1:
                quantidade = st.number_input("Quantidade", min_value=0.01, step=0.01)
                unidade = st.selectbox("Unidade", ["Lts", "kg", "Un", "Saco", "Balde"])
                local = st.selectbox("Local", locais)
            with col2:
                validade = st.text_input("Validade (DD/MM/AAAA)")
                lote = st.text_input("Lote")
                estoque_minimo = st.number_input("Estoque Mínimo", min_value=0.0, value=5.0, step=0.5)
            observacao = st.text_input("Observação / Responsável")
            
            if st.form_submit_button("✅ Registrar Entrada", type="primary", use_container_width=True):
                if nome and quantidade > 0:
                    # Verificar se produto já existe no mesmo local e lote
                    existente = next((i for i,p in enumerate(produtos) if 
                        p.get("nome") == nome and 
                        p.get("local") == local and 
                        p.get("lote") == lote), None)
                    
                    if existente is not None:
                        produtos[existente]["quantidade"] += quantidade
                        idx_hist = existente
                    else:
                        novo = {
                            "nome": nome,
                            "quantidade": quantidade,
                            "unidade": unidade,
                            "validade": validade,
                            "lote": lote,
                            "local": local,
                            "estoque_minimo": estoque_minimo,
                            "tipo": ""
                        }
                        produtos.append(novo)
                        idx_hist = len(produtos) - 1
                    
                    salvar_dados(ARQUIVO_PRODUTOS, produtos)
                    historico.insert(0, {
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "tipo": "ENTRADA",
                        "produto": nome,
                        "quantidade": quantidade,
                        "unidade": unidade,
                        "local": local,
                        "observacao": observacao
                    })
                    salvar_dados(ARQUIVO_HISTORICO, historico)
                    st.success(f"✅ Entrada registrada: {quantidade} {unidade} de {nome} em {local}")
                    st.rerun()
                else:
                    st.warning("⚠️ Preencha o nome e quantidade!")
    
    with col_saida:
        st.markdown("""
        <div style='background:#f3f4f6; padding:1.5rem; border-radius:10px; text-align:center;'>
            <h3>📤 SAÍDA / APLICAÇÃO</h3>
            <p>Produto utilizado na lavoura</p>
        </div>
        """, unsafe_allow_html=True)
        
        if produtos:
            nomes_prod = [f"{p.get('nome')} — {p.get('local')} (Disponível: {p.get('quantidade')} {p.get('unidade')})" for p in produtos]
            escolha = st.selectbox("Selecione o Produto", nomes_produtos)
            idx = nomes_produtos.index(escolha) if escolha else None
            
            if idx is not None:
                p = produtos[idx]
                qtd_atual = p.get("quantidade", 0)
                un = p.get("unidade", "un")
                st.info(f"📦 Disponível: *{qtd_atual} {un}* em {p.get('local')}")
                
                with st.form("form_saida", clear_on_submit=True):
                    qtd_saida = st.number_input("Quantidade Utilizada", min_value=0.01, step=0.01)
                    area = st.text_input("Área / Talhão Aplicado")
                    responsavel = st.text_input("Responsável")
                    
                    if st.form_submit_button("✅ Registrar Saída", type="primary", use_container_width=True):
                        if qtd_saida > qtd_atual:
                            st.error(f"❌ Estoque insuficiente! Só há {qtd_atual} {un} disponível.")
                        else:
                            produtos[idx]["quantidade"] = qtd_atual - qtd_saida
                            salvar_dados(ARQUIVO_PRODUTOS, produtos)
                            
                            historico.insert(0, {
                                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "tipo": "SAÍDA",
                                "produto": p.get("nome"),
                                "quantidade": qtd_saida,
                                "unidade": un,
                                "local": p.get("local"),
                                "area": area,
                                "responsavel": responsavel
                            })
                            salvar_dados(ARQUIVO_HISTORICO, historico)
                            st.success(f"✅ Saída registrada: {qtd_saida} {un} de {p.get('nome')}")
                            st.rerun()
        else:
            st.info("📋 Sem produtos cadastrados. Faça uma entrada primeiro!")

# --------------- TRANSFERÊNCIA ---------------
elif pagina == "↔️ Transferência entre Locais":
    st.title("↔️ Transferência entre Locais")
    st.subheader("Mova um lote de um local de armazenamento para outro")
    
    busca = st.text_input("🔍 Pesquisar por produto, local ou validade...")
    
    lista_transf = produtos.copy()
    if busca:
        lista_transf = [p for p in lista_transf if 
            busca.lower() in p.get("nome","").lower() or
            busca.lower() in p.get("local","").lower()]
    
    if not lista_transf:
        st.info("📋 Nenhum produto encontrado.")
    else:
        for i, p in enumerate(lista_transf):
            dias = dias_para_vencer(p.get("validade",""))
            icone, classe, _ = status_validade(dias)
            st.markdown(f"""
            <div class='produto-card'>
                <h4>{icone} {p.get('nome')}</h4>
                <p>📍 {p.get('local')} — {p.get('quantidade')} {p.get('unidade')} | Vence: {p.get('validade')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_de, col_para, col_btn = st.columns([2,2,1])
            with col_de:
                st.write(f"De: *{p.get('local')}*")
            with col_para:
                destino = st.selectbox("Para:", [l for l in locais if l != p.get("local")], 
                                       key=f"destino_{i}", label_visibility="collapsed")
            with col_btn:
                if st.button("➡️ Transferir", key=f"btn_transf_{i}", type="primary"):
                    idx_real = produtos.index(p)
                    local_anterior = produtos[idx_real]["local"]
                    produtos[idx_real]["local"] = destino
                    salvar_dados(ARQUIVO_PRODUTOS, produtos)
                    
                    historico.insert(0, {
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "tipo": "TRANSFERÊNCIA",
                        "produto": p.get("nome"),
                        "quantidade": p.get("quantidade"),
                        "unidade": p.get("unidade"),
                        "de": local_anterior,
                        "para": destino
                    })
                    salvar_dados(ARQUIVO_HISTORICO, historico)
                    st.success(f"✅ Transferido de {local_anterior} → {destino}!")
                    st.rerun()
            st.divider()

# --------------- HISTÓRICO COMPLETO ---------------
elif pagina == "📜 Histórico Completo":
    st.title("📜 Histórico Completo")
    st.subheader("Tudo que já aconteceu no estoque")
    
    col_filtro, col_busca = st.columns([1,3])
    with col_filtro:
        filtro_tipo = st.radio("Filtrar:", ["Tudo", "ENTRADA", "SAÍDA", "TRANSFERÊNCIA"], horizontal=True)
    with col_busca:
        busca_hist = st.text_input("🔍 Pesquisar por produto, local ou destino...")
    
    st.download_button("📄 Salvar / Imprimir como CSV", 
        data="Data;Tipo;Produto;Quantidade;Unidade;Local;Observação\n" + 
        "\n".join([f"{h.get('data','')};{h.get('tipo','')};{h.get('produto','')};{h.get('quantidade','')};{h.get('unidade','')};{h.get('local','')};{h.get('observacao','')}" for h in historico]),
        file_name=f"historico_estoque_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv")
    
    lista_hist = historico.copy()
    if filtro_tipo != "Tudo":
        lista_hist = [h for h in lista_hist if h.get("tipo") == filtro_tipo]
    if busca_hist:
        lista_hist = [h for h in lista_hist if 
            busca_hist.lower() in h.get("produto","").lower() or
            busca_hist.lower() in h.get("local","").lower()]
    
    if not lista_hist:
        st.info("📋 Nenhuma movimentação registrada ainda.")
    else:
        for h in lista_hist:
            tipo = h.get("tipo", "")
            if tipo == "ENTRADA":
                emoji = "📥"
                cor = "badge-sucesso"
            elif tipo == "SAÍDA":
                emoji = "📤"
                cor = "badge-perigo"
            elif tipo == "TRANSFERÊNCIA":
                emoji = "↔️"
                cor = "badge-info"
            else:
                emoji = "📝"
                cor = "badge-alerta"
            
            st.markdown(f"""
            <div class='card'>
                <p><span class='badge {cor}'>{emoji} {tipo}</span> — <strong>{h.get('data')}</strong></p>
                <p><strong>Produto:</strong> {h.get('produto')} | <strong>Quantidade:</strong> {h.get('quantidade')} {h.get('unidade','')}</p>
                <p><strong>Local:</strong> {h.get('local','')}</p>
                {f"<p style='color:#666; font-size:0.9rem;'>Obs: {h.get('observacao','')}</p>" if h.get('observacao') else ""}
                {f"<p style='color:#666; font-size:0.9rem;'>De: {h.get('de')} → Para: {h.get('para')}</p>" if tipo == "TRANSFERÊNCIA" else ""}
            </div>
            """, unsafe_allow_html=True)

# --------------- HISTÓRICO DE GASTOS ---------------
elif pagina == "💰 Histórico de Gastos":
    st.title("💰 Histórico de Gastos por Área")
    st.subheader("Por produto ou os mais recentes lançamentos")
    
    col_ordem, col_busca = st.columns([1,3])
    with col_ordem:
        ordem = st.radio("Ordenar por:", ["📦 Por Produto", "⏰ Mais Recentes"], horizontal=True)
    with col_busca:
        busca_gastos = st.text_input("🔍 Pesquisar por área ou produto...")
    
    saidas = [h for h in historico if h.get("tipo") == "SAÍDA"]
    
    if not saidas:
        st.info("📋 Nenhum consumo registrado ainda.")
    else:
        if ordem == "📦 Por Produto":
            st.subheader("TOTAL APLICADO POR PRODUTO (A-Z)")
            total_geral = 0
            produtos_agrupados = {}
            for h in saidas:
                nome = h.get("produto", "Desconhecido")
                qtd = h.get("quantidade", 0)
                un = h.get("unidade", "")
                if nome not in produtos_agrupados:
                    produtos_agrupados[nome] = {"qtd": 0, "un": un, "lancamentos": 0, "ultimo": ""}
                produtos_agrupados[nome]["qtd"] += qtd
                produtos_agrupados[nome]["lancamentos"] += 1
                produtos_agrupados[nome]["ultimo"] = h.get("data", "")
            
            for nome in sorted(produtos_agrupados.keys()):
                dados = produtos_agrupados[nome]
                st.markdown(f"""
                <div class='card'>
                    <h4>{nome}</h4>
                    <p style='font-size:1.1rem;'><strong>{dados['qtd']} {dados['un']}</strong></p>
                    <p style='color:#666; font-size:0.9rem;'>🕐 Último lançamento: {dados['ultimo']} | {dados['lancamentos']} lançamento(s)</p>
                </div>
                """, unsafe_allow_html=True)
                total_geral += dados["qtd"]
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #0E7C7B 0%, #284B53 100%); color:white; padding:1rem; border-radius:10px; text-align:center; margin-top:1.5rem;'>
                <h3>Total Geral Aplicado</h3>
                <h2>{total_geral:.2f} unidades</h2>
            </div>
            """, unsafe_allow_html=True)
        
        else:
            st.subheader("Últimas Saídas / Consumos")
            for h in saidas[:20]:
                st.markdown(f"""
                <div class='card'>
                    <p><strong>{h.get('data')}</strong> — {h.get('produto')}: {h.get('quantidade')} {h.get('unidade')}</p>
                    <p style='color:#666; font-size:0.9rem;'>📍 Área/Talhão: {h.get('area','Não informado')} | Responsável: {h.get('responsavel','Não informado')}</p>
                </div>
                """, unsafe_allow_html=True)

# ------------------- RODAPÉ -------------------
st.markdown("""
<div style='text-align:center; margin-top:2rem; padding:1rem; color:#888; font-size:0.85rem; border-top:1px solid #eee;'>
    🌿 Controle de Estoque — Defensivos Agrícolas | Atualizado em: {}
</div>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)