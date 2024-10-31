from fastapi import FastAPI, File, UploadFile, Form
import pandas as pd
from io import BytesIO

app = FastAPI()

# Novo endpoint para obter a classificação Qualis com base no ISSN
@app.post("/qualis/")
async def obter_qualis(issn: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()

    # Converter os bytes em um objeto que pandas pode ler
    qualis_df = pd.read_csv(BytesIO(contents), delimiter=',')

    # Limpar o ISSN (remover traços, espaços extras etc.)
    issn_cleaned = issn.replace("-", "").strip()
    
    # Normalizar o ISSN no dataframe para comparação
    qualis_df['ISSN'] = qualis_df['ISSN'].str.replace("-", "").str.strip()

    # Encontrar o Qualis correspondente
    qualis_row = qualis_df[qualis_df['ISSN'] == issn_cleaned]
    
    if qualis_row.empty:
        return {"message": "ISSN não encontrado no arquivo Qualis."}
    
    # Retornar o estrato Qualis
    estrato = qualis_row.iloc[0]['Estrato']
    
    return {"issn": issn, "qualis": estrato}
