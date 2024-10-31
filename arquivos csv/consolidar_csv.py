from fastapi import FastAPI, UploadFile, File
import pandas as pd
from io import BytesIO

app = FastAPI()

# Função para processar o arquivo CSV e remover duplicatas
def processar_csv_eliminar_repeticoes(file: UploadFile):
    # Ler o conteúdo do arquivo
    contents = file.file.read()
    
    # Ler o CSV em um DataFrame
    df = pd.read_csv(BytesIO(contents))
    
    # Remover duplicatas com base em todas as colunas
    df_sem_repeticoes = df.drop_duplicates()
    
    # Converter o DataFrame de volta para CSV e retornar como bytes
    output = BytesIO()
    df_sem_repeticoes.to_csv(output, index=False)
    
    # Retornar o conteúdo do arquivo processado
    return output.getvalue()

# Endpoint para upload do arquivo CSV e eliminação de duplicatas
@app.post("/upload/eliminar_repeticoes/")
async def upload_csv(file: UploadFile = File(...)):
    # Processar o arquivo CSV e eliminar repetições
    csv_processado = processar_csv_eliminar_repeticoes(file)
    
    # Retornar o arquivo processado
    return {"message": "Arquivo processado com sucesso.", "csv_processado": csv_processado.decode('utf-8')}
