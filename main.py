from fastapi import FastAPI, File, UploadFile, Query, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import zipfile
import os
import pandas as pd
import io
from io import BytesIO, StringIO  # Para trabalhar com streams de arquivo
from openpyxl import Workbook
import xml.etree.ElementTree as ET
import unidecode
import math  # Para verificar valores fora do intervalo
import uuid
import shutil  # Para remover a pasta temporária após o uso
from pydantic import BaseModel
from typing import List, Optional

# Modelo de artigo
class Artigo(BaseModel):
    Título: str
    Autores: str
    Ano: int
    ISSN: Optional[str] = None
    Qualis: str
    DP: int
    DC: Optional[int] = 0
    DIS: Optional[int] = 0

# Inicialização do aplicativo FastAPI
app = FastAPI()

# Configuração de CORS para permitir requisições de diferentes origens
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Para desenvolvimento local
        "https://www.ppgec.com.br",  # Site WordPress
        "https://analisador-de-artigos-frontend.vercel.app"  # Frontend hospedado no Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Funções utilitárias
def formatar_issn(issn: str) -> str:
    """Formata o ISSN no formato XXXX-XXXX."""
    issn = issn.replace("-", "").strip()
    return f"{issn[:4]}-{issn[4:]}" if len(issn) == 8 else issn

def normalizar_issn(issn: str) -> list:
    """Converte múltiplos ISSNs em uma lista normalizada."""
    return [i.strip().replace("-", "") for i in issn.split(',')]

def formatar_doi(doi: str) -> str:
    """Formata o DOI no formato http://dx.doi.org/xxxxx."""
    return doi.strip() if doi.lower().startswith(("http://", "https://")) else f"http://dx.doi.org/{doi.strip()}"

def formatar_jif(jif: float) -> str:
    """Converte o ponto decimal para vírgula."""
    return f"{jif:.2f}".replace('.', ',')

def sanitize_float_values(data):
    """Substitui valores fora do intervalo (NaN, inf, -inf) por None."""
    if isinstance(data, dict):
        return {k: sanitize_float_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_float_values(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    return data

# Funções para processar arquivos
def processar_zip(contents, temp_folder):
    """Descompacta o ZIP e localiza o arquivo XML."""
    try:
        with zipfile.ZipFile(BytesIO(contents), 'r') as zip_ref:
            zip_ref.extractall(temp_folder)

        xml_files = [f for f in os.listdir(temp_folder) if f.endswith('.xml')]
        if not xml_files:
            return None, "Nenhum arquivo XML encontrado no ZIP."

        xml_path = os.path.join(temp_folder, xml_files[0])
        return xml_path, "Arquivo XML extraído com sucesso."
    except Exception as e:
        return None, f"Erro ao descompactar o arquivo ZIP: {e}"

def processar_xml(xml_path):
    """Extrai o nome da pessoa e os dados dos artigos do XML."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        nome_pessoa = root.find(".//DADOS-GERAIS").get("NOME-COMPLETO", "Nome não encontrado")
        artigos = []

        for artigo in root.findall('.//ARTIGO-PUBLICADO'):
            titulo = artigo.find('DADOS-BASICOS-DO-ARTIGO').get('TITULO-DO-ARTIGO', 'Sem Título')
            ano = int(artigo.find('DADOS-BASICOS-DO-ARTIGO').get('ANO-DO-ARTIGO', '0'))
            autores = '; '.join([autor.get('NOME-COMPLETO-DO-AUTOR') for autor in artigo.findall('AUTORES')])
            issn = formatar_issn(artigo.find('DETALHAMENTO-DO-ARTIGO').get('ISSN', 'Sem ISSN'))
            titulo_periodico = artigo.find('DETALHAMENTO-DO-ARTIGO').get('TITULO-DO-PERIODICO-OU-REVISTA', 'Sem Título do Periódico')
            doi = artigo.find('DADOS-BASICOS-DO-ARTIGO').get('DOI', 'Sem DOI')

            artigos.append({
                'Título': titulo,
                'Autores': autores,
                'Ano': ano,
                'ISSN': issn,
                'Título do Periódico': titulo_periodico,
                'DOI': doi
            })

        return nome_pessoa, pd.DataFrame(artigos).sort_values(by='Ano')

    except Exception as e:
        print(f"Erro ao processar o XML: {e}")
        return None, pd.DataFrame()

# Funções para buscar classificações (Qualis, JCR, SJR)
def buscar_qualis(issn, qualis_df):
    """Busca a classificação Qualis pelo ISSN."""
    issn_cleaned = issn.replace("-", "").strip()
    qualis_df['ISSN'] = qualis_df['ISSN'].str.replace("-", "").str.strip()
    qualis_row = qualis_df[qualis_df['ISSN'] == issn_cleaned]
    return qualis_row.iloc[0]['Estrato'] if not qualis_row.empty else "NP"

def buscar_jcr(issn, jcr_df):
    """Busca o JCR e Quartil pelo ISSN ou eISSN."""
    issn_cleaned = issn.replace("-", "").strip()
    jcr_df['ISSN'] = jcr_df['ISSN'].astype(str).str.replace("-", "").str.strip()
    jcr_df['eISSN'] = jcr_df['eISSN'].astype(str).str.replace("-", "").str.strip()
    jcr_row = jcr_df[(jcr_df['ISSN'] == issn_cleaned) | (jcr_df['eISSN'] == issn_cleaned)]
    if not jcr_row.empty:
        return formatar_jif(jcr_row.iloc[0]['2023 JIF']), jcr_row.iloc[0]['JIF Quartile']
    return "---", "---"

def buscar_sjr(issn, sjr_df):
    """Busca o SJR e Quartil pelo ISSN."""
    issn_cleaned = issn.replace("-", "").strip()
    sjr_df['ISSN_list'] = sjr_df['Issn'].apply(normalizar_issn)
    sjr_row = sjr_df[sjr_df['ISSN_list'].apply(lambda x: issn_cleaned in x)]
    if not sjr_row.empty:
        return sjr_row.iloc[0]['SJR'], sjr_row.iloc[0]['SJR Best Quartile']
    return "---", "---"

# Função para quantificar DP, DC e DIS comparando com múltiplos formatos de nomes
def quantificar_participantes(autores, docentes_discentes_df):
    """Compara os autores com os docentes/discentes e conta DP, DC e DIS."""
    dp_count, dc_count, dis_count = 0, 0, 0
    for autor in autores.split(';'):
        autor_normalizado = unidecode.unidecode(autor.strip().lower())
        match = docentes_discentes_df[
            (docentes_discentes_df['Nome Completo'].apply(lambda x: autor_normalizado in unidecode.unidecode(x.lower()))) |
            (docentes_discentes_df['APA'].apply(lambda x: autor_normalizado in unidecode.unidecode(x.lower()))) |
            (docentes_discentes_df['ABNT'].apply(lambda x: autor_normalizado in unidecode.unidecode(x.lower()))) |
            (docentes_discentes_df['Custom'].apply(lambda x: autor_normalizado in unidecode.unidecode(x.lower())))
        ]
        if not match.empty:
            categoria = match.iloc[0]['Categoria']
            if categoria == 'DP':
                dp_count += 1
            elif categoria == 'DC':
                dc_count += 1
            else:
                dis_count += 1
    return dp_count, dc_count, dis_count

# Função para calcular pontuação Qualis
def calcular_pontuacao_qualis(artigos_df):
    """Calcula a pontuação Qualis dos artigos agrupados por ano e dividida pelo número de DP."""
    pontuacao = {
        "A1": 1.0, "A2": 0.9, "A3": 0.75, "A4": 0.6,
        "B1": 0.4, "B2": 0.3, "B3": 0.15, "B4": 0.05,
        "C": 0, "NP": 0
    }

    def calcular_pontos_por_qualis(qualis, dp):
        return pontuacao.get(qualis, 0) / max(dp, 1)

    # Criar uma nova tabela de pontuações por ano
    pontuacao_anos = artigos_df.groupby('Ano').apply(
        lambda x: pd.Series({
            'A1': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'A1'),
            'A2': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'A2'),
            'A3': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'A3'),
            'A4': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'A4'),
            'B1': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'B1'),
            'B2': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'B2'),
            'B3': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'B3'),
            'B4': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'B4'),
            'C': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'C'),
            'NP': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] == 'NP'),
            'Total A': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] in ['A1', 'A2', 'A3', 'A4']),
            'Total B': sum(calcular_pontos_por_qualis(row['Qualis'], row['DP']) for _, row in x.iterrows() if row['Qualis'] in ['B1', 'B2', 'B3', 'B4']),
        })
    )

    # Adicionar os percentuais e evitar divisão por zero
    pontuacao_anos['Total'] = pontuacao_anos['Total A'] + pontuacao_anos['Total B']
    pontuacao_anos['% A'] = (pontuacao_anos['Total A'] / pontuacao_anos['Total']) * 100 if pontuacao_anos['Total'].sum() > 0 else 0
    pontuacao_anos['% B'] = (pontuacao_anos['Total B'] / pontuacao_anos['Total']) * 100 if pontuacao_anos['Total'].sum() > 0 else 0

    return pontuacao_anos.reset_index().to_dict(orient="records")

# Endpoints
@app.post("/upload/")
async def processar_artigos(file: UploadFile = File(...)):
    """Processa o XML com os artigos diretamente ou a partir de um arquivo ZIP."""
    contents = await file.read()
    
    # Cria uma pasta temporária única para o upload
    temp_folder = f"./temp/{uuid.uuid4()}"
    os.makedirs(temp_folder, exist_ok=True)

    try:
        # Verificar o tipo de arquivo
        if file.filename.endswith(".zip"):
            xml_path, msg = processar_zip(contents, temp_folder)
            if not xml_path:
                return {"message": msg}
        elif file.filename.endswith(".xml"):
            # Grava o XML diretamente na pasta temporária
            xml_path = os.path.join(temp_folder, "uploaded.xml")
            with open(xml_path, "wb") as f:
                f.write(contents)
            msg = "Arquivo XML carregado diretamente."
        else:
            return {"message": "Formato de arquivo não suportado. Envie um arquivo .zip ou .xml."}

        # Processar o XML extraído ou carregado
        nome_pessoa, artigos_df = processar_xml(xml_path)
        if artigos_df.empty:
            return {"message": "Nenhum artigo encontrado."}

        # Carregar arquivos fixos
        qualis_file = './data/Classificação Qualis 2017_2020.csv'
        jcr_file = './data/JCR tabelado.xlsx'
        sjr_file = './data/scimagojr 2023.csv'
        docentes_discentes_file = './data/docentes_discentes_formatados.xlsx'

        qualis_df = pd.read_csv(qualis_file, delimiter=',')
        jcr_df = pd.read_excel(jcr_file, engine='openpyxl')
        sjr_df = pd.read_csv(sjr_file, delimiter=';', on_bad_lines='skip', engine='python')
        docentes_discentes_df = pd.read_excel(docentes_discentes_file, engine='openpyxl')

        # Processar dados dos artigos
        artigos_df['Qualis'] = artigos_df['ISSN'].apply(lambda x: buscar_qualis(x, qualis_df))
        artigos_df[['2023 JIF', 'JIF Quartile']] = artigos_df['ISSN'].apply(lambda x: pd.Series(buscar_jcr(x, jcr_df)))
        artigos_df[['SJR', 'SJR Best Quartile']] = artigos_df['ISSN'].apply(lambda x: pd.Series(buscar_sjr(x, sjr_df)))
        artigos_df[['DP', 'DC', 'DIS']] = artigos_df['Autores'].apply(lambda x: pd.Series(quantificar_participantes(x, docentes_discentes_df)))

        # Calcular pontuação Qualis
        pontuacao_qualis = calcular_pontuacao_qualis(artigos_df)
        
        # Limpar valores incompatíveis com JSON
        artigos_df = artigos_df.replace([float("inf"), -float("inf")], float("nan")).fillna(0)
        pontuacao_qualis = sanitize_float_values(pontuacao_qualis)

        # Retornar resultados
        return {
            "nomePessoa": nome_pessoa,
            "artigos": artigos_df.to_dict(orient="records"),
            "pontuacaoQualis": pontuacao_qualis
        }
    finally:
        # Remove a pasta temporária após o processamento
        shutil.rmtree(temp_folder)

@app.post("/generate-csv/")
async def generate_csv(
    nomePessoa: str = Query(..., description="Nome do currículo"),
    pontuacaoQualis: list = Body(..., description="Dados da Tabela 2")
):
    """Gera um arquivo CSV com os dados da Tabela 2 e o nome do currículo."""
    
    # Converte pontuacaoQualis em DataFrame para CSV
    df = pd.DataFrame(pontuacaoQualis)
    
    # Cria um buffer em memória para o arquivo CSV
    output = io.StringIO()
    df.to_csv(
        output,
        index=False,
        sep=';',                  # Define ponto e vírgula como separador de coluna
        decimal=',',              # Define vírgula como separador decimal
        float_format='%.3f'       # Limita os números a 3 casas decimais
    )
    output.seek(0)  # Retorna o ponteiro para o início do arquivo

    # Nome do arquivo com o nome do currículo
    filename = f"{nomePessoa}_curriculo.csv"
    
    # Retornar o arquivo para download
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
