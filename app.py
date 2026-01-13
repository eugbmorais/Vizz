import os
import json
import re
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from typing import Optional, Dict, Any, List
from huggingface_hub import InferenceClient

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Vizz – Transformando dados em decisões", 
    layout="wide", 
    initial_sidebar_state="expanded"
)
# ---------------- ESTILO CUSTOMIZADO ----------------
st.markdown("""
<style>
/* Estilo para os cards de métrica */
[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.stButton>button { border-radius: 8px; }
h1 { text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- LOGO PRINCIPAL CENTRALIZADO ---
col1, col2, col3 = st.columns([1, 2, 1]) 

with col2:
    st.image(
        "logo_vizz.png",  # Mude para o nome exato do seu ficheiro de logo
        use_container_width='auto' # Faz o logo preencher a coluna central
    )

# ---------------- HELP (ONBOARDING) ----------------
with st.expander("ℹ️ Como usar o Vizz – Guia rápido", expanded=False):
    st.markdown("""
    **Bem-vindo ao Vizz!** Transforme planilhas comuns em decisões poderosas.
    1. Envie sua planilha (.xlsx ou .csv) ou **use nossos dados de exemplo**.
    2. Abra os **Filtros Avançados** para refinar sua análise.
    3. Explore o **Dashboard** para ver seus KPIs e gráficos automáticos.
    4. Vá para **Ações com IA** para receber recomendações autônomas.
    """)

# ---------------- Funções utilitárias e de IA ----------------
def carregar_df(uploaded_file):
    """Lê xlsx ou csv de forma segura."""
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file)
        elif filename.endswith(".csv"):
            # tenta auto-detectar delimitador com engine python
            return pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            raise ValueError("Formato de arquivo não suportado.")
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None

@st.cache_data(show_spinner=False)
def hf_api_call(prompt: str, hf_token: str, model: str = "meta-llama/Llama-3.1-70B-Instruct") -> str:
    """Função genérica e cacheada para chamadas à API da Hugging Face."""
    if not hf_token:
        raise ValueError("Token da Hugging Face não fornecido.")
    try:
        client = InferenceClient(model=model, token=hf_token)
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages=messages, max_tokens=1024, temperature=0.1, stream=False)
        return response.choices[0].message.content.strip()
    except Exception as e:
        # repassa erro para o UI
        raise RuntimeError(f"Erro na API da Hugging Face: {e}")

def create_kpi_plan_prompt(df_schema: str, df_columns: List[str], col_valor: str) -> str:
    """Pede à IA para primeiro identificar o contexto e depois sugerir KPIs relevantes."""
    return f"""
    Você é um especialista em Business Intelligence. Sua primeira tarefa é analisar as colunas do dataframe para inferir o contexto do negócio (ex: Vendas, Finanças, Estoque, Marketing).
    Depois, sugira 3 KPIs que sejam altamente relevantes para esse contexto específico.

    COLUNAS DISPONÍVEIS: {df_columns}
    SCHEMA: {df_schema}

    Sua resposta deve ser APENAS uma lista de objetos JSON. Para cada KPI, forneça:
    1. 'title': Um título curto para o KPI.
    2. 'description': Uma explicação curta sobre por que este KPI é importante para o contexto identificado.
    3. 'calculation': Um objeto JSON descrevendo o cálculo com 'method' e 'params'.

    Métodos ('method') disponíveis: 'mean', 'sum', 'count', 'nunique', 'idxmax_groupby_sum'.
    A coluna principal de valor é '{col_valor}'.
    """
# --- NOVA FUNÇÃO DE FORMATAÇÃO UNIVERSAL ---
def format_brl(value):
    """Formata um número para o padrão de moeda brasileira (R$ 1.234,56)."""
    try:
        # Formata com separador de milhar americano, depois inverte os separadores
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value
    
# --- FUNÇÃO ATUALIZADA ---
def calculate_ai_kpi(df: pd.DataFrame, calculation: dict) -> Optional[str]:
    """Executa um cálculo de KPI com base em um plano, de forma 100% segura."""
    method = calculation.get('method')
    params = calculation.get('params', {})
    try:
        if method == 'mean':
            col = params['column']
            if col in df.columns: return format_brl(df[col].mean())
        elif method == 'sum':
            col = params['column']
            if col in df.columns: return format_brl(df[col].sum())
        elif method == 'count':
            col = params['column']
            if col in df.columns: return str(df[col].count())
        elif method == 'nunique':
            col = params['column']
            if col in df.columns: return str(df[col].nunique())
        elif method == 'idxmax_groupby_sum':
            groupby_col = params.get('groupby_column')
            agg_col = params.get('agg_column')
            if groupby_col in df.columns and agg_col in df.columns:
                if df.empty: return "N/A"
                return str(df.groupby(groupby_col)[agg_col].sum().idxmax())
        return None
    except Exception as e:
        print(f"DEBUG: Falha no cálculo do KPI. Método: {method}, Params: {params}, Erro: {e}")
        return None

    except Exception as e:
        print(f"DEBUG: Falha no cálculo do KPI. Método: {method}, Params: {params}, Erro: {e}")
        return None

def create_holistic_analysis_prompt(df_schema: str, df_head: str, kpis_gerais: List[Dict]) -> str:
    """Cria um prompt para a IA encontrar a maior oportunidade e o maior risco."""
    
    # Formata os KPIs gerais para dar mais contexto à IA
    kpi_summary = "\\n".join([f"- {kpi['label']}: {kpi['value']}" for kpi in kpis_gerais])

    return f"""
    Você é um consultor de negócios sênior e pragmático. Sua missão é analisar os dados de uma empresa e fornecer insights rápidos e acionáveis.

    Abaixo estão os KPIs gerais, a estrutura (schema) e as primeiras linhas de uma planilha:

    KPIs GERAIS:
    {kpi_summary}

    SCHEMA:
    {df_schema}

    PRIMEIRAS LINHAS:
    {df_head}

    Com base em TODAS as informações, responda de forma estruturada:
    1. **Principal Oportunidade:** Identifique e descreva em uma frase a maior oportunidade de crescimento ou ponto positivo evidente nos dados. Use um emoji 🚀.
    2. **Principal Risco:** Identifique e descreva em uma frase o maior risco, problema ou ponto de atenção que requer ação imediata. Use um emoji ⚠️.
    3. **Plano de Ação:** Liste 2 recomendações numeradas, uma para capitalizar na oportunidade e outra para mitigar o risco.
    """

def calcular_variacao_periodo(df: pd.DataFrame, col_data: str, col_valor: str) -> (Optional[float], Optional[float]):
    if col_data == "Nenhuma" or col_data not in df.columns or df[col_data].nunique() < 2: return None, None
    df_sorted = df.sort_values(by=col_data).reset_index(drop=True)
    midpoint_index = len(df_sorted) // 2
    periodo_anterior, periodo_atual = df_sorted.iloc[:midpoint_index], df_sorted.iloc[midpoint_index:]
    if periodo_anterior.empty or periodo_atual.empty: return None, None
    total_atual, total_anterior = periodo_atual[col_valor].sum(), periodo_anterior[col_valor].sum()
    if total_anterior == 0: return total_atual, None
    variacao = ((total_atual - total_anterior) / total_anterior) * 100
    return total_atual, variacao

def formatar_recomendacoes_ia(texto_ia: str) -> str:
    if not texto_ia: return "A IA não forneceu uma resposta."
    match = re.search(r'(.*?)(Recomendações de ação:|Recomendações:)(.*)', texto_ia, re.IGNORECASE | re.DOTALL)
    resumo_cru, recomendacoes_cruas = (match.group(1), match.group(3)) if match else (texto_ia, "")
    resumo_limpo = resumo_cru.replace("Resumo:", "").strip()
    recomendacoes_formatadas = ""
    if recomendacoes_cruas:
        linhas_rec = [rec.strip() for rec in re.split(r'\d+\.\s*', recomendacoes_cruas) if rec.strip()]
        if linhas_rec:
            recomendacoes_formatadas = "**Recomendações:**\n"
            for i, rec in enumerate(linhas_rec): recomendacoes_formatadas += f"{i+1}. {rec}\n"
    return f"**Resumo:** {resumo_limpo}\n\n{recomendacoes_formatadas}".strip()

# --- FUNÇÃO APRIMORADA COM EXPLICAÇÕES INTELIGENTES E LÓGICA PIZZA/ROSCA ---
def gerar_graficos_automaticos(
    df: pd.DataFrame,
    col_valor: str,
    col_data: str,
    colunas_cat: List[str],
    use_ia: bool = False,
    hf_token_input: Optional[str] = None
) -> List[Dict]:
    """Analisa os dados e gera uma lista de gráficos com explicações em linguagem natural."""
    graficos = []
    
    # --- NOVO: Sinalizador para alternar entre pizza e rosca ---
    pie_chart_created = False

    def gerar_explicacao_basica(tipo, titulo, df=None):
        """Gera um texto explicativo simples se IA não estiver habilitada."""
        if tipo == "temporal":
            return "Este gráfico mostra como o valor total evolui ao longo do tempo, ajudando a identificar períodos de alta ou queda."
        elif tipo == "histograma":
            return "Este gráfico mostra a distribuição dos valores, facilitando a identificação de faixas de preço ou volume mais comuns."
        elif tipo == "categoria_pizza":
            return f"O gráfico '{titulo}' mostra como o valor total está distribuído entre as categorias, destacando quais têm maior participação."
        elif tipo == "categoria_rosca":
            return f"O gráfico '{titulo}' (rosca) mostra a proporção de cada categoria, similar a um gráfico de pizza."
        elif tipo == "categoria_bar":
            return f"O gráfico '{titulo}' destaca os itens mais importantes da categoria, facilitando a análise de impacto."
        return "Gráfico gerado automaticamente com base nos dados enviados."

    def gerar_explicacao_ia(df_resumo: str, titulo: str) -> str:
        """Cria um prompt para a IA gerar explicação em linguagem natural sobre o gráfico."""
        if not use_ia or not hf_token_input:
            return None
        try:
            prompt = f"""
Você é um Analista de Bi especializado em Storytelling.
Analise o gráfico chamado '{titulo}' e escreva uma explicação **resumida e objetiva** (máximo de 3 linhas).

Sua explicação deve:
- Ser escrita em linguagem simples, como se falasse com alguém não técnico.
- Destacar **o principal padrão ou tendência** visível no gráfico.

Evite frases genéricas. Vá direto ao ponto e mantenha uma narrativa clara e fluida.

            Dados do gráfico:
            {df_resumo[:1500]}
            """
            resposta = hf_api_call(prompt, hf_token_input)
            return resposta.strip() if resposta else None
        except Exception:
            return None

    # 1. Gráfico de Série Temporal
    if col_data != "Nenhuma" and col_data in df.columns and df[col_data].nunique() > 1:
        serie = df.groupby(col_data)[col_valor].sum().reset_index()
        serie['texto_hover'] = serie[col_valor].apply(format_brl)
        fig = px.line(
            serie, x=col_data, y=col_valor,
            title=f"Evolução de '{col_valor}'", markers=True, custom_data=['texto_hover']
        )
        fig.update_layout(dragmode=False)
        fig.update_traces(hovertemplate='Data: %{x|%d/%m/%Y}<br>Valor: %{customdata[0]}<extra></extra>')
        fig.update_xaxes(tickformat='%d/%m/%Y')

        explicacao = gerar_explicacao_ia(serie.to_string(), f"Evolução de {col_valor}") or gerar_explicacao_basica("temporal", f"Evolução de {col_valor}")
        graficos.append({'title': "Análise Temporal", 'figure': fig, 'explicacao': explicacao})

    # 2. Histograma de Valores
    if col_valor in df.columns and pd.api.types.is_numeric_dtype(df[col_valor]):
        fig_hist = px.histogram(df, x=col_valor, title=f"Distribuição de Frequência de '{col_valor}'")
        fig_hist.update_layout(dragmode=False)
        fig_hist.update_traces(hovertemplate='Faixa de Valor: %{x}<br>Contagem: %{y}<extra></extra>')
        explicacao = gerar_explicacao_ia(df[col_valor].to_string(), f"Distribuição de {col_valor}") or gerar_explicacao_basica("histograma", f"Distribuição de {col_valor}")
        graficos.append({'title': "Distribuição de Valores", 'figure': fig_hist, 'explicacao': explicacao})

    # 3. Gráficos de Categoria
    cats_para_grafico = [
        c for c in colunas_cat if c in df.columns and 1 < df[c].nunique() < 50
    ][:2]

    for cat in cats_para_grafico:
        agrupado = df.groupby(cat)[col_valor].sum().sort_values(ascending=False).reset_index()
        agrupado['texto_hover'] = agrupado[col_valor].apply(format_brl)

        if len(agrupado) <= 7:
            # --- LÓGICA DE DECISÃO (PIZZA OU ROSCA) ---
            if not pie_chart_created:
                # O primeiro é um gráfico de Pizza
                titulo_grafico = f"Distribuição por '{cat}'"
                fig_cat = px.pie(agrupado, names=cat, values=col_valor,
                                 title=titulo_grafico, custom_data=['texto_hover'])
                tipo_explicacao = "categoria_pizza"
                pie_chart_created = True # Ativa o sinalizador
            else:
                # O segundo é um gráfico de Rosca (Donut)
                titulo_grafico = f"Distribuição (Rosca) por '{cat}'"
                fig_cat = px.pie(agrupado, names=cat, values=col_valor,
                                 title=titulo_grafico, custom_data=['texto_hover'],
                                 hole=0.4) # <-- A MÁGICA ACONTECE AQUI
                tipo_explicacao = "categoria_rosca"
            
            fig_cat.update_traces(hovertemplate='%{label}<br>Valor: %{customdata[0]}<br>Porcentagem: %{percent}<extra></extra>')
            # --- FIM DA LÓGICA DE DECISÃO ---
        else:
            titulo_grafico = f"Top 10 '{cat}' por '{col_valor}'"
            fig_cat = px.bar(agrupado.head(10), x=cat, y=col_valor,
                             title=titulo_grafico, custom_data=['texto_hover'])
            fig_cat.update_layout(dragmode=False)
            fig_cat.update_traces(hovertemplate=f'{cat.capitalize()}: %{{x}}<br>Valor: %{{customdata[0]}}<extra></extra>')
            tipo_explicacao = "categoria_bar"

        explicacao = gerar_explicacao_ia(agrupado.to_string(), titulo_grafico) or gerar_explicacao_basica(tipo_explicacao, titulo_grafico)
        graficos.append({'title': f"Análise de {cat}", 'figure': fig_cat, 'explicacao': explicacao})

    return graficos


# --- NOVO: Prompt para a IA gerar Alertas Inteligentes ---
def create_alerts_prompt(data_summary: str) -> str:
    """Cria um prompt para a IA identificar o insight mais crítico nos dados."""
    return f"""
    Você é um analista de dados sênior com a tarefa de encontrar o insight mais importante em um resumo estatístico.
    
    RESUMO DOS DADOS:
    {data_summary}

    Analise os dados e identifique o ponto mais notável, seja uma oportunidade (ex: um produto com valor médio muito alto) ou um risco (ex: uma categoria com poucas vendas).

    Sua resposta deve ser APENAS um objeto JSON com as chaves:
    1. 'alert_type': "success" para oportunidade, ou "warning" para risco.
    2. 'icon': Um emoji relevante (ex: "🚀" ou "⚠️").
    3. 'message': Uma frase curta e impactante descrevendo o insight.

    Exemplo:
    {{
      "alert_type": "warning",
      "icon": "⚠️",
      "message": "A categoria 'Acessórios' tem uma contagem de vendas muito baixa em comparação com as outras."
    }}
    """
# ---------------- Sessão e Upload ----------------
if "analises" not in st.session_state: st.session_state["analises"] = []
if "df" not in st.session_state: st.session_state["df"] = None

st.subheader("Comece sua análise")
col1, col2 = st.columns([2.5, 1])
with col1:
    # --- ALTERAÇÃO APLICADA AQUI ---
    # 1. Mudamos o 'label' para ser o texto de ação principal em português.
    # 2. Removemos 'label_visibility="collapsed"' para que o texto apareça.
    # 3. Adicionamos o 'help' com os requisitos em português.
    uploaded_file = st.file_uploader(
        "📥 **Clique para fazer o Upload do Arquivo** ou arraste-o para esta área",
        type=["xlsx", "xls", "csv"],
        help="Formatos permitidos: .xlsx, .xls ou .csv. Tamanho máximo: 200MB."
    )
    if st.button("🚀 Usar dados de exemplo", use_container_width=True):
        try:
            st.session_state["df"] = pd.read_excel("dados_exemplo.xlsx")
            st.rerun()
        except FileNotFoundError:
            st.error("Arquivo 'dados_exemplo.xlsx' não encontrado.")
if uploaded_file:
    st.session_state["df"] = carregar_df(uploaded_file)

# ---------------- Configurações e Histórico (Sidebar) ----------------
st.sidebar.title("Vizz")
use_ia = True
# pega token em secrets se configurado (evita erro se secrets malformado)
hf_token_input = None
try:
    if hasattr(st, "secrets") and "HF_TOKEN" in st.secrets:
        hf_token_input = st.secrets.get("HF_TOKEN")
except Exception:
    hf_token_input = None

if use_ia and not hf_token_input:
    st.sidebar.warning("Token da Hugging Face não configurado em .streamlit/secrets.toml.")

# ---------------- Processamento Principal ----------------
def create_context_id_prompt(df_columns: List[str]) -> str:
    """Pede à IA para analisar os nomes das colunas e identificar o tipo de planilha."""
    return f"""
    Você é um analista de negócios experiente. Sua tarefa é analisar a lista de colunas de uma planilha e identificar o seu propósito principal.

    COLUNAS DISPONÍVEIS: {df_columns}

    Com base nas colunas, responda APENAS com um objeto JSON com as seguintes chaves:
    1. 'business_context': Classifique a planilha como "Vendas", "Despesas", "Estoque", "Marketing" ou "Outro".
    2. 'value_column': Identifique a principal coluna numérica de valor (ex: 'total_da_venda', 'valor_pago', 'custo_total').
    3. 'date_column': Identifique a principal coluna de data (ex: 'data_da_venda', 'data_do_pagamento').

    Exemplo de resposta:
    {{
      "business_context": "Vendas",
      "value_column": "total_da_venda",
      "date_column": "data_da_venda"
    }}
    """
if st.session_state.get("df") is not None:
    df_original = st.session_state["df"].copy()
    df_original.columns = df_original.columns.str.strip().str.lower().str.replace(" ", "_")
    
    with st.expander("🔍 Filtros Avançados"):
        col_filt1, col_filt2 = st.columns(2)
        with col_filt1:
            # DETECÇÃO AUTOMÁTICA DE COLUNA DE DATA (se houver)
            col_data_sugerida = next((c for c in df_original.columns if "data" in c), None)
            if not col_data_sugerida:
                for c in df_original.columns:
                    try:
                        parsed = pd.to_datetime(df_original[c], errors="coerce")
                        non_null_ratio = parsed.notna().mean()
                        if non_null_ratio > 0.6:
                            col_data_sugerida = c
                            break
                    except Exception:
                        continue

            col_data_opts = ["Nenhuma"] + df_original.columns.tolist()
            default_idx_data = col_data_opts.index(col_data_sugerida) if col_data_sugerida in col_data_opts else 0
            col_data = st.selectbox("📅 Coluna de data", col_data_opts, index=default_idx_data)
            df = df_original.copy()
            if col_data != "Nenhuma" and col_data in df.columns:
                df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
                df.dropna(subset=[col_data], inplace=True)
                if not df.empty:
                    min_date, max_date = df[col_data].min(), df[col_data].max()
                    if pd.notnull(min_date) and pd.notnull(max_date):
                        data_ini, data_fim = st.date_input("Período da análise", value=(min_date.date(), max_date.date()), min_value=min_date.date(), max_value=max_date.date(), format="DD/MM/YYYY")
                        if data_ini and data_fim:
                            df = df[df[col_data].between(pd.to_datetime(data_ini), pd.to_datetime(data_fim))]
            colunas_num = df.select_dtypes(include="number").columns.tolist()
            ignorar = ['id', 'codigo', 'cpf', 'cnpj', 'registro', 'ano', 'mes', 'dia']
            colunas_valor = [c for c in colunas_num if all(i not in c for i in ignorar) and df[c].nunique() > 1]
            keywords_prioridade = ['valor', 'total', 'venda', 'faturamento', 'receita', 'price', 'amount']
            col_valor_sugerida = next((c for kw in keywords_prioridade for c in colunas_valor if kw in c), None)
            if not col_valor_sugerida and colunas_valor:
                try:
                    col_valor_sugerida = df[colunas_valor].sum().idxmax()
                except Exception:
                    col_valor_sugerida = colunas_valor[0] if colunas_valor else None
            col_valor_options = colunas_valor if colunas_valor else ["Nenhuma"]
            default_idx_val = col_valor_options.index(col_valor_sugerida) if (col_valor_sugerida and col_valor_sugerida in col_valor_options) else 0
            col_valor = st.selectbox("💰 Coluna de valores", col_valor_options, index=default_idx_val)
        with col_filt2:
            colunas_cat = df.select_dtypes(include="object").columns.tolist()
            for c in colunas_cat:
                opts = df[c].dropna().unique().tolist()
                if len(opts) > 1 and len(opts) < 100:
                    sel = st.multiselect(f"Filtrar {c}", opts)
                    if sel: df = df[df[c].isin(sel)]

    st.markdown("---")
    
    if col_valor == "Nenhuma" or col_valor not in df.columns:
        st.warning(f"👋 Para começar, selecione uma 'Coluna de valores' nos filtros acima.")
        st.stop()

        # --- NOVA SEÇÃO: QUALIDADE E TRATAMENTO DE DADOS ---
        st.markdown("---")
        st.markdown("##### Qualidade e Limpeza dos Dados")
        
        df_para_analise = df.copy() # Cria uma cópia para aplicar a limpeza
        
        # Diagnóstico de Nulos na coluna de valor
        if col_valor != "Nenhuma" and col_valor in df_para_analise.columns:
            nulos_valor = df_para_analise[col_valor].isnull().sum()
            if nulos_valor > 0:
                st.warning(f"⚠️ Encontradas **{nulos_valor} linhas** com valores em branco na coluna '{col_valor}'.")
                tratamento_valor = st.radio(
                    "Como lidar com estes valores?",
                    ("Remover as linhas", "Preencher com zero (0)"),
                    key="tratamento_valor", horizontal=True,
                    help="Escolha se deseja ignorar as linhas com dados faltantes ou considerá-las como zero."
                )
                if tratamento_valor == "Remover as linhas":
                    df_para_analise.dropna(subset=[col_valor], inplace=True)
                else:
                    df_para_analise[col_valor].fillna(0, inplace=True)
        
        # A variável 'df' final usada pelo resto do app agora é a versão limpa
        df = df_para_analise.copy()

    tab_dashboard, tab_acoes = st.tabs(["📊 Dashboard", "💡 Ações com IA"])
    
    with tab_dashboard:
        
        if use_ia and hf_token_input:
            with st.container(border=True):
                st.subheader("🚨 Alerta Inteligente da IA")
                try:
                    with st.spinner("IA está procurando por insights críticos..."):
                        # Usamos o describe() para dar um resumo estatístico para a IA
                        summary_str = df.describe(include='all').to_string()
                        alert_prompt = create_alerts_prompt(summary_str)
                        alert_response_str = hf_api_call(alert_prompt, hf_token_input)
                        
                        json_match = re.search(r'\{.*\}', alert_response_str, re.DOTALL)
                        if not json_match: raise ValueError("A IA não retornou um alerta JSON válido.")
                        
                        alert_data = json.loads(json_match.group(0))

                    # Exibe o alerta com o tipo e ícone corretos
                    if alert_data.get("alert_type") == "success":
                        st.success(f"{alert_data.get('icon', '✅')} **Oportunidade:** {alert_data.get('message')}")
                    else:
                        st.warning(f"{alert_data.get('icon', '⚠️')} **Ponto de Atenção:** {alert_data.get('message')}")

                except Exception as e:
                    # Se falhar, não quebra o app, apenas mostra uma mensagem sutil e loga o erro
                    st.info("Não foi possível gerar alertas inteligentes para os dados atuais.")
                    print(f"DEBUG: Falha na geração de Alertas: {e}")

        with st.container(border=True):
            st.subheader("Visão Geral")
            
            if not df.empty:
                # Calcula os KPIs básicos
                total_periodo_atual, variacao = calcular_variacao_periodo(df, col_data, col_valor)
                media = df[col_valor].mean()
                
                # Encontra a linha inteira do maior e menor valor
                linha_max = df.loc[df[col_valor].idxmax()]
                linha_min = df.loc[df[col_valor].idxmin()]
                
                # Procura por uma coluna de contexto (ex: produto, cliente) para exibir
                contexto_col = next((c for c in ['produto', 'cliente', 'descrição', 'nome_do_cliente'] if c in df.columns), None)

                c1, c2, c3 = st.columns(3)

                # Coluna 1: Total
                with c1:
                    if total_periodo_atual is not None:
                        delta_str = f"{variacao:.1f}%" if variacao is not None else None
                        st.metric("Total (Período Atual)", format_brl(total_periodo_atual), delta=delta_str, help="Comparado com a primeira metade do período selecionado.")
                    else:
                        st.metric("Total (Geral)", format_brl(df[col_valor].sum()))
                
                # Coluna 2:Máximo com Contexto
                with c2:
                    st.metric("Valor Máximo", format_brl(linha_max[col_valor]))
                    if contexto_col:
                        st.caption(f"Ref. a: **{str(linha_max[contexto_col])[:20]}**") # Limita o texto para caber

                # Coluna 3:Mínimo com Contexto
                with c3:
                    st.metric("Valor Mínimo", format_brl(linha_min[col_valor]))
                    if contexto_col:
                        st.caption(f"Ref. a: **{str(linha_min[contexto_col])[:20]}**") # Limita o texto para caber
            else:
                st.info("Não há dados para exibir com os filtros atuais.")
        
        if use_ia and hf_token_input:
            with st.container(border=True):
                st.subheader("Insights Aprofundados (KPIs Sugeridos pela IA)")
                try:
                    with st.spinner("IA está identificando KPIs..."):
                        from io import StringIO
                        buffer = StringIO(); df.info(buf=buffer); schema_str = buffer.getvalue()
                        kpi_prompt = create_kpi_plan_prompt(schema_str, df.columns.tolist(), col_valor)
                        plan_str = hf_api_call(kpi_prompt, hf_token_input)
                        json_match = re.search(r'\[.*\]', plan_str, re.DOTALL)
                        if not json_match: raise ValueError("A IA não retornou um plano JSON válido.")
                        kpi_plan = json.loads(json_match.group(0))
                    
                    if kpi_plan:
                        kpis_validos = []
                        for kpi in kpi_plan:
                            kpi_value = calculate_ai_kpi(df, kpi.get('calculation', {}))
                            if kpi_value:
                                kpis_validos.append({'title': kpi['title'], 'value': kpi_value, 'description': kpi['description']})
                        
                        if kpis_validos:
                            cols = st.columns(len(kpis_validos))
                            for i, kpi_valido in enumerate(kpis_validos):
                                with cols[i]:
                                    st.metric(label=kpi_valido['title'], value=kpi_valido['value'], help=kpi_valido['description'])
                except Exception as e:
                    print(f"DEBUG: Falha na geração de KPIs: {e}")

        with st.container(border=True):
            st.subheader("Visualizações Automáticas")
            # A variável é criada aqui
            graficos_gerados = gerar_graficos_automaticos(df, col_valor, col_data, colunas_cat, use_ia, hf_token_input)
    
    if not graficos_gerados:
        st.info("Não foi possível gerar gráficos. Verifique se sua planilha possui colunas de data e categoria.")
    else:
        # Divide a tela em duas colunas para organizar os gráficos
        col_graf1, col_graf2 = st.columns(2)

        # Loop pelos gráficos gerados
        for i, grafico in enumerate(graficos_gerados):
            # Alterna entre as duas colunas
            target_col = col_graf1 if i % 2 == 0 else col_graf2
            with target_col:
                # Título do gráfico
                st.markdown(f"### {grafico.get('title', 'Gráfico')}")
                
                # Exibe o gráfico interativo
                st.plotly_chart(grafico['figure'], use_container_width=True)

                # Se houver explicação (IA ou básica), mostra abaixo do gráfico
                if grafico.get('explicacao'):
                    st.markdown(f"💬 **Interpretação:** {grafico['explicacao']}")

                # Linha divisória entre gráficos
                st.markdown("---")
                        
        with st.container(border=True):
            st.subheader("Rankings Principais")
            for cat in colunas_cat:
                if cat in df.columns and df[cat].nunique() > 1 and df[cat].nunique() < 100:
                    st.markdown(f"##### Análise de **'{cat}'**")
                    
                    # --- MELHORIA: Título do Ranking Dinâmico ---
                    # Calcula o número de itens únicos na categoria
                    num_itens = df[cat].nunique()
                    # Define o "Top N" como 5 ou o número de itens, o que for menor
                    top_n = min(5, num_itens)

                    col1, col2 = st.columns(2)
                    with col1:
                        # Usa a variável top_n no título
                        st.markdown(f"**Top {top_n} por Valor**")
                        # Usa a variável top_n para pegar os maiores valores
                        top_valor = df.groupby(cat)[col_valor].sum().nlargest(top_n).reset_index()
                        try:
                            top_valor[col_valor] = top_valor[col_valor].apply(format_brl)
                        except Exception: pass
                        st.dataframe(top_valor, width='stretch', hide_index=True)
                        
                    with col2:
                        # Usa a variável top_n no título
                        st.markdown(f"**Top {top_n} por Quantidade**")
                        # Usa a variável top_n para pegar os valores mais frequentes
                        top_registros = df[cat].value_counts().nlargest(top_n).reset_index()
                        st.dataframe(top_registros, width='stretch', hide_index=True)

    with tab_acoes:
        st.subheader("🤖 Análise e Recomendações da IA")
        if not use_ia:
            st.info("Ative a 'Análise com IA' nas configurações.")
        elif not hf_token_input:
            st.error("Token da Hugging Face não configurado.")
        else:
            with st.container(border=True):
                st.markdown("Clique no botão para que a IA analise os dados e identifique oportunidades, riscos e um plano de ação.")
                
                # --- LÓGICA DE AÇÕES ATUALIZADA ---
                if st.button("🧠 Gerar Análise Estratégica", type="primary", use_container_width=True):
                    try:
                        with st.spinner("A IA está pensando como um consultor..."):
                            from io import StringIO
                            buffer = StringIO(); df.info(buf=buffer); schema_str = buffer.getvalue()
                            df_head_str = df.head().to_string()
                            
                            # Passa os KPIs gerais para a IA ter mais contexto
                            prompt = create_holistic_analysis_prompt(schema_str, df_head_str, st.session_state.get('kpis_gerais', []))
                            generated_text = hf_api_call(prompt, hf_token_input)
                        
                        if generated_text:
                            st.success("Análise gerada com sucesso!")
                            # Como o novo prompt já pede uma formatação boa, podemos não precisar da função de formatação
                            st.markdown(generated_text) 
                            st.session_state.analises.append({"timestamp": datetime.utcnow().isoformat(), "prompt": prompt, "response": generated_text})
                        else:
                            st.warning("A IA retornou um resultado vazio.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro durante a análise da IA: {e}")
else:
    st.info("👆 Envie uma planilha ou use os dados de exemplo para começar.")
    st.markdown("---")
    st.subheader("Transforme Seus Dados em Decisões Inteligentes")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📊 Insights Automáticos")
        st.write("Receba KPIs e gráficos gerados automaticamente com base na sua planilha.")
    with col2:
        st.markdown("#### 💡 Recomendações com IA")
        st.write("Obtenha um resumo e ações práticas geradas por inteligência artificial para melhorar seu negócio.")
    with col3:
        st.markdown("#### 📱 Acesso Fácil")
        st.write("Analise seus dados a qualquer hora, em qualquer lugar, direto do seu computador ou celular.")
