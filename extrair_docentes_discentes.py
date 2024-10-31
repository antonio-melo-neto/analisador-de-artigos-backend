from fastapi import FastAPI, File, UploadFile
import pandas as pd
import json
import os

app = FastAPI()

# Lista de preposições a serem ignoradas
preposicoes = {"de", "do", "da", "dos", "das"}

def formatar_nome_autor(nome: str) -> dict:
    """
    Formata o nome do autor em múltiplos estilos: APA, ABNT e customizado.
    Exemplo: "Antonio Acacio de Melo Neto" -> "Melo Neto, A. A."
    """
    partes = nome.split()
    nome_principal = [parte for parte in partes[:-1] if parte.lower() not in preposicoes]  # Ignorar preposições
    sobrenome = partes[-1]  # Última parte é o sobrenome ou sufixo importante (Neto, Filho)

    # Verificar se há sufixos como "Neto", "Filho" que devem ser mantidos juntos
    if len(partes) > 1 and partes[-2].lower() not in preposicoes:
        sobrenome = f"{partes[-2]} {sobrenome}"

    # Construir as iniciais dos nomes
    iniciais = " ".join([p[0].upper() + "." for p in nome_principal])

    # Formatar nos diferentes estilos
    apa = f"{sobrenome}, {iniciais}"
    abnt = f"{sobrenome.upper()}, {' '.join(nome_principal).title()}"
    custom = f"{iniciais} {sobrenome.title()}"

    return {"APA": apa, "ABNT": abnt, "Custom": custom}

def salvar_em_arquivo_excel(dados, caminho):
    # Converter a lista de dicionários em DataFrame
    df = pd.DataFrame(dados)
    
    # Definir o caminho completo para salvar o arquivo
    caminho_completo = os.path.join(caminho, "docentes_discentes_formatados.xlsx")
    
    # Salvar em XLSX
    df.to_excel(caminho_completo, index=False, engine='openpyxl')
    return caminho_completo

@app.post("/upload/todos/")
async def upload_todos(docentes_file: UploadFile = File(...), discentes_file: UploadFile = File(...)):
    # Processar docentes
    docentes_contents = await docentes_file.read()
    docentes_xls = pd.read_excel(docentes_contents, engine='openpyxl')
    
    # Processar discentes
    discentes_contents = await discentes_file.read()
    discentes_json = json.loads(discentes_contents)
    
    # Lista final para armazenar todos os dados formatados
    todos_dados = []
    
    # Formatando os docentes permanentes e colaboradores
    docentes = docentes_xls[['NOME', 'CATEGORIA']].dropna()
    for _, row in docentes.iterrows():
        categoria = 'DP' if row['CATEGORIA'].lower() == 'permanente' else 'DC'
        nome_formatado = formatar_nome_autor(row['NOME'])
        todos_dados.append({
            "Nome Completo": row['NOME'],
            "Categoria": categoria,
            "APA": nome_formatado["APA"],
            "ABNT": nome_formatado["ABNT"],
            "Custom": nome_formatado["Custom"]
        })
    
    # Formatando os discentes
    for discente_nome in discentes_json:
        nome_formatado = formatar_nome_autor(discente_nome)
        todos_dados.append({
            "Nome Completo": discente_nome,
            "Categoria": 'DISC',
            "APA": nome_formatado["APA"],
            "ABNT": nome_formatado["ABNT"],
            "Custom": nome_formatado["Custom"]
        })

    # Definir caminho para salvar o arquivo
    caminho = "C:\\Users\\Decivil\\Dropbox\\PPGEC\\Indicadores\\chatgpt\\FastAPI"
    
    # Salvar os dados no arquivo XLSX
    arquivo_salvo = salvar_em_arquivo_excel(todos_dados, caminho)

    return {"mensagem": "Arquivo XLSX gerado com sucesso", "caminho": arquivo_salvo}
