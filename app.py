import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from io import StringIO

# --- CONFIGURAÇÃO INICIAL ---
VALOR_HORA_SUGERIDO = 16.00
VALOR_HORA_FORNO_SUGERIDO = 2.50

st.set_page_config(page_title="Precificação da Sogra", page_icon="🍰")
st.title("🍰 Calculadora de Doces")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Cria a conexão
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    # 1. Pega a resposta do Google (que vem como <Response [200]>)
    response = conn.read(worksheet="Dados", ttl=0)
    
    # 2. O truque: Pega o TEXTO de dentro da resposta e transforma em tabela
    # O StringIO faz o texto parecer um arquivo para o Pandas ler
    tabela = pd.read_csv(StringIO(response.text))
    
    return tabela

def salvar_dados(df_novo):
    # Atualiza a planilha no Google
    conn.update(worksheet="Dados", data=df_novo)
    st.cache_data.clear() # Limpa cache do Streamlit

# Abas
aba_calc, aba_despensa, aba_config = st.tabs(["🧮 Calcular Receita", "📦 Minha Despensa", "⚙️ Configurações"])

# Carrega dados iniciais
try:
    df_despensa = carregar_dados()
    # Garante que as colunas numéricas sejam números
    df_despensa['preco'] = pd.to_numeric(df_despensa['preco'])
    df_despensa['qtd_emb'] = pd.to_numeric(df_despensa['qtd_emb'])
except Exception as e:
    st.error(f"Erro ao ler a planilha. Verifique se o cabeçalho está correto (item, preco, qtd_emb, unidade). Erro: {e}")
    st.stop()

# --- ABA 1: CALCULADORA ---
with aba_calc:
    st.header("Nova Precificação")
    
    if df_despensa.empty:
        st.warning("Sua despensa está vazia! Cadastre itens na aba 'Minha Despensa'.")
    else:
        ingredientes_selecionados = st.multiselect(
            "Selecione os ingredientes usados:", 
            df_despensa['item'].tolist()
        )
        
        custo_insumos = 0.0
        
        if ingredientes_selecionados:
            st.subheader("Quanto usou de cada?")
            for item in ingredientes_selecionados:
                dados_item = df_despensa[df_despensa['item'] == item].iloc[0]
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    qtd_usada = st.number_input(
                        f"Qtd de {item} (em {dados_item['unidade']}):", 
                        min_value=0.0, step=1.0, key=f"qtd_{item}"
                    )
                
                # Cálculo proporcional
                preco_base = float(dados_item['preco'])
                qtd_base = float(dados_item['qtd_emb'])
                
                if qtd_base > 0:
                    custo_item = (preco_base / qtd_base) * qtd_usada
                else:
                    custo_item = 0
                
                custo_insumos += custo_item
                
                with col2:
                    st.write(f"R$ {custo_item:.2f}")

        st.divider()
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tempo_preparo = st.number_input("Tempo de Mão na Massa (minutos):", min_value=0, step=5)
        with col_t2:
            tempo_forno = st.number_input("Tempo de Forno (minutos):", min_value=0, step=5)

        valor_hora = st.session_state.get('valor_hora', VALOR_HORA_SUGERIDO)
        valor_gas = st.session_state.get('valor_gas', VALOR_HORA_FORNO_SUGERIDO)
        lucro_pct = st.session_state.get('lucro_pct', 30)

        custo_mao_obra = (valor_hora / 60) * tempo_preparo
        custo_gas = (valor_gas / 60) * tempo_forno
        custo_total = custo_insumos + custo_mao_obra + custo_gas
        
        preco_venda = custo_total * (1 + (lucro_pct/100))
        lucro_reais = preco_venda - custo_total

        if st.button("Calcular Preço Final", type="primary"):
            st.success(f"💰 Preço Sugerido: R$ {preco_venda:.2f}")
            st.write("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingredientes", f"R$ {custo_insumos:.2f}")
            c2.metric("Mão de Obra/Gás", f"R$ {custo_mao_obra + custo_gas:.2f}")
            c3.metric(f"Lucro ({lucro_pct}%)", f"R$ {lucro_reais:.2f}")

# --- ABA 2: DESPENSA (Google Sheets) ---
with aba_despensa:
    st.header("Gerenciar Preços (Google Sheets)")
    st.info("As alterações aqui salvam direto na sua planilha do Google!")

    # Editor de dados
    df_editado = st.data_editor(
        df_despensa, 
        num_rows="dynamic",
        column_config={
            "preco": st.column_config.NumberColumn("Preço (R$)", format="%.2f"),
            "qtd_emb": st.column_config.NumberColumn("Qtd Emb.", format="%d"),
        },
        key="editor_despensa"
    )

    if st.button("💾 Salvar Alterações na Planilha"):
        with st.spinner("Salvando no Google..."):
            salvar_dados(df_editado)
        st.success("Salvo com sucesso! Pode fechar o app que não perde nada.")
        st.rerun()

# --- ABA 3: CONFIGURAÇÕES ---
with aba_config:
    st.header("Ajustes")
    st.session_state['valor_hora'] = st.number_input("Valor Hora (R$):", value=VALOR_HORA_SUGERIDO)
    st.session_state['valor_gas'] = st.number_input("Valor Forno/h (R$):", value=VALOR_HORA_FORNO_SUGERIDO)
    st.session_state['lucro_pct'] = st.slider("Lucro (%)", 10, 100, 30)
