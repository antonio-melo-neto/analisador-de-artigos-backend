from fastapi import FastAPI, File, UploadFile, Form
import pandas as pd
from io import BytesIO

app = FastAPI()

# Novo endpoint para obter o 2023 JIF e JIF Quartile com base no ISSN ou eISSN
@app.post("/jcr/")
async def obter_jcr(issn: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()

    # Carregar o arquivo Excel
    try:
        jcr_df = pd.read_excel(BytesIO(contents), engine='openpyxl')
    except Exception as e:
        return {"error": f"Erro ao processar o Excel: {str(e)}"}

    # Limpar o ISSN de entrada (remover traços e espaços)
    issn_cleaned = issn.replace("-", "").strip()

    # Normalizar as colunas ISSN e eISSN no dataframe para comparação
    jcr_df['ISSN'] = jcr_df['ISSN'].astype(str).str.replace("-", "").str.strip()
    jcr_df['eISSN'] = jcr_df['eISSN'].astype(str).str.replace("-", "").str.strip()

    # Procurar o ISSN ou eISSN no dataframe
    jcr_row = jcr_df[(jcr_df['ISSN'] == issn_cleaned) | (jcr_df['eISSN'] == issn_cleaned)]

    if jcr_row.empty:
        return {"message": "ISSN não encontrado no arquivo JCR."}

    # Extrair 2023 JIF e JIF Quartile
    jif_2023 = jcr_row.iloc[0]['2023 JIF']
    jif_quartile = jcr_row.iloc[0]['JIF Quartile']

    return {
        "issn": issn,
        "2023_jif": jif_2023,
        "jif_quartile": jif_quartile
    }
