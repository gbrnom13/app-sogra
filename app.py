import streamlit as st
import pandas as pd
import json
import os

# --- CONFIGURAÇÃO INICIAL (Valores Padrão) ---
ARQUIVO_DADOS = 'despensa.json'
VALOR_HORA_SUGERIDO = 16.00
VALOR_HORA_FORNO_SUGERIDO = 2.50

# --- FUNÇÕES DE BANCO DE DADOS (JSON) ---
def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        # Cria um banco inicial se não existir
        dados_iniciais = [
            {"item": "Leite Condensado (395g)", "preco": 6.50, "qtd_emb": 395, "unidade": "g"},
            {"item": "Farinha de Trigo (1kg)", "preco": 5.00, "qtd_emb": 1000, "unidade": "g"},
            {"item": "Ovos (Dúzia)", "preco": 12.00, "qtd_emb": 12, "unidade": "un"},
            {"item": "Manteiga (200g)", "preco": 10.00, "qtd_emb": 200, "unidade": "g"},
            {"item": "Chocolate em Pó (50%)", "preco": 18.00, "qtd_emb": 200, "unidade": "g"}
        ]
        salvar_dados(dados_iniciais)
        return pd.DataFrame(dados_iniciais)
    
    with open(ARQUIVO_DADOS, 'r') as f:
        return pd.DataFrame(json.load(f))

def salvar_dados(dados):
    # Se for DataFrame, converte para lista de dicts
    if isinstance(dados, pd.DataFrame):
        dados = dados.to_dict(orient='records')
    
    with open(ARQUIVO_DADOS, 'w') as f:
        json.dump(dados, f, indent=4)

# --- INTERFACE DO APLICATIVO ---
st.set_page_config(page_title="Precificação - Padoca da Nane", page_icon="🍰")

st.title("🍰 Precificação - Padoca da Nane")

# Carrega a despensa
df_despensa = carregar_dados()

# Abas para separar as funcionalidades
aba_calc, aba_despensa, aba_config = st.tabs(["🧮 Calcular Receita", "📦 Minha Despensa", "⚙️ Configurações"])

# --- ABA 1: CALCULADORA ---
with aba_calc:
    st.header("Nova Precificação")
    
    # Seleção de Ingredientes
    ingredientes_selecionados = st.multiselect(
        "Selecione os ingredientes usados:", 
        df_despensa['item'].tolist()
    )
    
    custo_insumos = 0.0
    detalhes_insumos = []

    if ingredientes_selecionados:
        st.subheader("Quanto usou de cada?")
        for item in ingredientes_selecionados:
            # Busca dados do item no DF
            dados_item = df_despensa[df_despensa['item'] == item].iloc[0]
            
            # Input de quantidade usada
            col1, col2 = st.columns([3, 1])
            with col1:
                qtd_usada = st.number_input(
                    f"Qtd de {item} (em {dados_item['unidade']}):", 
                    min_value=0.0, step=1.0, key=f"qtd_{item}"
                )
            
            # Cálculo proporcional
            custo_item = (dados_item['preco'] / dados_item['qtd_emb']) * qtd_usada
            custo_insumos += custo_item
            
            with col2:
                st.write(f"R$ {custo_item:.2f}")

    st.divider()
    
    # Custos de Tempo (Mão de Obra e Gás)
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tempo_preparo = st.number_input("Tempo de Mão na Massa (minutos):", min_value=0, step=5)
    with col_t2:
        tempo_forno = st.number_input("Tempo de Forno (minutos):", min_value=0, step=5)

    # Pegando valores da config (session state ou padrão)
    valor_hora = st.session_state.get('valor_hora', VALOR_HORA_SUGERIDO)
    valor_gas = st.session_state.get('valor_gas', VALOR_HORA_FORNO_SUGERIDO)
    lucro_pct = st.session_state.get('lucro_pct', 30)

    # Matemática
    custo_mao_obra = (valor_hora / 60) * tempo_preparo
    custo_gas = (valor_gas / 60) * tempo_forno
    custo_total = custo_insumos + custo_mao_obra + custo_gas
    
    preco_venda = custo_total * (1 + (lucro_pct/100))
    lucro_reais = preco_venda - custo_total

    # Exibição do Resultado
    if st.button("Calcular Preço Final", type="primary"):
        st.success(f"💰 Preço Sugerido de Venda: R$ {preco_venda:.2f}")
        
        # Detalhamento Visual
        st.write("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Custo Ingredientes", f"R$ {custo_insumos:.2f}")
        c2.metric("Mão de Obra + Gás", f"R$ {custo_mao_obra + custo_gas:.2f}")
        c3.metric(f"Lucro ({lucro_pct}%)", f"R$ {lucro_reais:.2f}")

# --- ABA 2: DESPENSA (Gerenciamento) ---
with aba_despensa:
    st.header("Gerenciar Preços e Estoque")
    st.info("💡 Dica: Edite os preços diretamente na tabela abaixo se algo mudou.")

    # Tabela Editável (O "Pulo do Gato" para ela atualizar rápido)
    df_editado = st.data_editor(
        df_despensa, 
        num_rows="dynamic", # Permite adicionar linhas
        column_config={
            "preco": st.column_config.NumberColumn("Preço Pago (R$)", format="R$ %.2f"),
            "qtd_emb": st.column_config.NumberColumn("Tamanho da Emb.", format="%d"),
        },
        key="editor_despensa"
    )

    # Botão para salvar alterações
    if st.button("💾 Salvar Alterações na Despensa"):
        salvar_dados(df_editado)
        st.toast("Despensa atualizada com sucesso!", icon="✅")
        st.rerun()

# --- ABA 3: CONFIGURAÇÕES ---
with aba_config:
    st.header("Ajustes do Negócio")
    st.write("Defina aqui quanto vale o seu tempo.")
    
    st.session_state['valor_hora'] = st.number_input(
        "Valor da Hora de Trabalho (R$):", value=VALOR_HORA_SUGERIDO, step=0.50
    )
    st.session_state['valor_gas'] = st.number_input(
        "Custo do Forno por Hora (R$):", value=VALOR_HORA_FORNO_SUGERIDO, step=0.50
    )
    st.session_state['lucro_pct'] = st.slider(
        "Margem de Lucro Desejada (%)", 10, 100, 30
    )
