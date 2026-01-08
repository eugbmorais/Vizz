# Vizz

Vizz é uma interface analítica que transforma planilhas (.xlsx / .csv) em insights acionáveis usando visualizações automáticas e recomendações com IA. O projeto foi pensado para analistas e pequenos negócios que querem gerar KPIs, gráficos e recomendações sem escrever código.

## Funcionalidades principais
- Upload de planilhas (.xlsx, .xls, .csv).
- Detecção automática de coluna de data, coluna de valor e colunas categóricas.
- Dashboard com KPIs básicos (total, média, máximo, mínimo) e variação por período.
- Geração automática de visualizações (séries temporais, histogramas, pizza/rosca, barras).
- Recomendações e alertas inteligentes usando a API da Hugging Face (opcional).
- Integração com Firebase para autenticação de usuários.
- Tratamento básico de qualidade de dados (remoção/preenchimento de nulos).

## Requisitos
- Python 3.10+ (testado em um devcontainer Linux).
- Dependências listadas em `requirements.txt`.
- Conta/Token da Hugging Face (opcional) para recursos de IA.
- Configuração do Firebase (opcional, para autenticação).

## Arquivos importantes
- `app.py` — aplicação principal (Streamlit).
- `requirements.txt` — dependências Python.
- `firebase_service_key.json` — chave/credenciais Firebase (se usada).
- `dados_exemplo.xlsx` — (opcional) arquivo de exemplo esperado pelo app.
- `logo_vizz.png` — logo exibida na interface.

## Instalação (local)
1. Crie e ative um ambiente virtual Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Configure variáveis sensíveis (veja a seção abaixo).

4. Execute a aplicação:

```bash
streamlit run app.py
```

## Configuração (Secrets / Firebase / HF)

1. Hugging Face
- Se quiser usar os recursos de IA, forneça um token da Hugging Face. No dev do Streamlit, coloque `HF_TOKEN` em `.streamlit/secrets.toml` ou configure `st.secrets` adequadamente.

Exemplo `.streamlit/secrets.toml`:

```toml
HF_TOKEN = "hf_xxx_your_token"
```

2. Firebase (opcional)
- Para ativar autenticação de usuários, configure as credenciais do Firebase em `st.secrets['firebase_credentials']` ou ajuste para carregar `firebase_service_key.json` conforme sua preferência. A aplicação espera um dicionário de configuração compatível com `pyrebase.initialize_app()`.

Campos típicos (exemplo resumido):

```toml
[firebase_credentials]
apiKey = "..."
authDomain = "..."
databaseURL = "..."
projectId = "..."
storageBucket = "..."
messagingSenderId = "..."
appId = "..."
```

3. Arquivos opcionais
- `dados_exemplo.xlsx` — se quiser testar com dados de exemplo sem fazer upload.

## Como usar
1. Abra a aplicação com `streamlit run app.py`.
2. Faça login (se Firebase configurado) ou use sem autenticação local, conforme a configuração.
3. Faça upload de um `.xlsx` / `.csv` ou clique em "Usar dados de exemplo".
4. Nos filtros avançados, selecione a `Coluna de data` (se houver) e a `Coluna de valores`.
5. Explore o Dashboard e a aba "Ações com IA" para recomendações e alertas.

Notas de uso
- O app tenta detectar automaticamente colunas de data/valor e sugere tratamentos para valores nulos.
- Quando o token da Hugging Face não estiver configurado, as funções de IA exibem aviso e permanecem desativadas.

## Observações técnicas
- Chamadas à IA: `hf_api_call()` usa `huggingface_hub.InferenceClient` com `chat_completion`.
- Cache: algumas chamadas usam `@st.cache_data` para reduzir custo de chamadas IA.
- Visualizações: a app usa `plotly.express` para gerar gráficos interativos.

## Soluções de problemas comuns
- Erro ao ler arquivo: verifique o formato e se a planilha não está corrompida.
- Token HF ausente: configure `HF_TOKEN` em `.streamlit/secrets.toml`.
- Firebase não inicializa: confirme o shape do dicionário de credenciais e a disponibilidade do serviço.

<<<<<<< HEAD

## Contribuições
- Sugestões e correções são bem-vindas. Abra issues descrevendo bug ou feature desejada.

=======
>>>>>>> ed1c65c17676a2973f739b829bb3747df4440ba8
## Segurança e privacidade
- Nunca comite tokens ou chaves em repositórios públicos. Use `st.secrets` ou variáveis de ambiente.

## Licença
- Atualmente não há licença explícita no repositório.
<<<<<<< HEAD
# Nudgi
=======
# Vizz
>>>>>>> ed1c65c17676a2973f739b829bb3747df4440ba8
