from fastapi import FastAPI, File, UploadFile, Form
import pandas as pd
from io import BytesIO

app = FastAPI()

# Função para lidar com múltiplos ISSNs e remover traços e espaços
def normalizar_issn(issn: str) -> list:
    """Converte uma string de ISSNs separados por vírgula em uma lista normalizada."""
    issn_list = [i.strip().replace("-", "") for i in issn.split(',')]
    return issn_list

# Novo endpoint para obter o SJR e o Best Quartile com base no ISSN
@app.post("/sjr/")
async def obter_sjr(issn: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()

    # Carregar o arquivo CSV do SJR
    try:
        sjr_df = pd.read_csv(BytesIO(contents), delimiter=';', on_bad_lines='skip', engine='python')
    except pd.errors.ParserError as e:
        return {"error": f"Erro ao processar o CSV: {str(e)}"}

    # Expandir e normalizar os ISSNs no dataframe
    sjr_df['ISSN_list'] = sjr_df['Issn'].apply(normalizar_issn)

    # Limpar o ISSN fornecido
    issn_cleaned = issn.replace("-", "").strip()

    # Procurar o ISSN na lista expandida
    sjr_row = sjr_df[sjr_df['ISSN_list'].apply(lambda x: issn_cleaned in x)]

    if sjr_row.empty:
        return {"message": "ISSN não encontrado no arquivo SJR."}

    # Extrair SJR e SJR Best Quartile
    sjr_value = sjr_row.iloc[0]['SJR']
    best_quartile = sjr_row.iloc[0]['SJR Best Quartile']

    return {
        "issn": issn,
        "sjr": sjr_value,
        "best_quartile": best_quartile
    }
