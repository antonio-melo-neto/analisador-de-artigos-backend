from fastapi import FastAPI, File, UploadFile
import zipfile
import os
import pandas as pd
from io import BytesIO
import xml.etree.ElementTree as ET

app = FastAPI()

def formatar_issn(issn: str) -> str:
    """Formata o ISSN no formato XXXX-XXXX."""
    issn = issn.replace("-", "").strip()
    if len(issn) == 8:
        return f"{issn[:4]}-{issn[4:]}"
    return issn  # Retorna o original se não for válido

def formatar_doi(doi: str) -> str:
    """Formata o DOI no formato http://dx.doi.org/xxxxxxxx."""
    if doi.lower().startswith("http://") or doi.lower().startswith("https://"):
        return doi.strip()
    return f"http://dx.doi.org/{doi.strip()}"

# Função para descompactar o ZIP e processar o XML
def processar_zip(contents, temp_folder):
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

# Função para processar o XML e extrair os dados
def processar_xml(xml_path, ano_inicio, ano_fim):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        artigos = []
        for artigo in root.findall('.//ARTIGO-PUBLICADO'):
            titulo = artigo.find('DADOS-BASICOS-DO-ARTIGO').get('TITULO-DO-ARTIGO', 'Sem Título')
            ano = int(artigo.find('DADOS-BASICOS-DO-ARTIGO').get('ANO-DO-ARTIGO', '0'))
            if ano_inicio <= ano <= ano_fim:
                autores = ', '.join([autor.get('NOME-COMPLETO-DO-AUTOR') for autor in artigo.findall('AUTORES')])
                issn = formatar_issn(artigo.find('DETALHAMENTO-DO-ARTIGO').get('ISSN', 'Sem ISSN'))
                doi = formatar_doi(artigo.find('DADOS-BASICOS-DO-ARTIGO').get('DOI', 'Sem DOI'))

                artigos.append({
                    'Título': titulo,
                    'Autores': autores,
                    'Ano': ano,
                    'ISSN': issn,
                    'DOI': doi
                })

        df = pd.DataFrame(artigos)
        return df
    except Exception as e:
        print(f"Erro ao processar o XML: {e}")
        return pd.DataFrame()

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), ano_inicio: int = 2000, ano_fim: int = 2024):
    contents = await file.read()

    temp_folder = "./temp"
    os.makedirs(temp_folder, exist_ok=True)

    xml_path, msg = processar_zip(contents, temp_folder)
    if not xml_path:
        return {"message": msg}

    artigos_df = processar_xml(xml_path, ano_inicio, ano_fim)

    if artigos_df.empty:
        return {"message": "Nenhum artigo encontrado no período especificado."}

    return artigos_df.to_dict(orient="records")
