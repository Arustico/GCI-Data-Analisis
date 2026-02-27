#-------------------
# Librerías
#-------------------
import pandas as pd
import numpy as np
import unicodedata

import re
import os
# para leer pdfs
import tabula

# Librerías
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración básica
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(f"{__name__}")

# Variables de configuración (asegúrate que están definidas en el entorno)
FOLDER_RAW_LOCAL = Path(os.getenv("FOLDER_RAW", "data/raw"))
PDF_FILES_PATH = Path(os.getenv("PDF_FILES_PATH"))

#-------------------
# Funciones
#-------------------
def find_indx_and_descrip(indicador_string: str, patron=None) -> list[str]:
  if not patron:
      patron = r"([A-Z])\w.+"
  indx = re.search(r"^\d+\.\d+",indicador_string).group()
  descrp = re.search(patron,indicador_string).group()
  return [indx, descrp]

def find_description(indice: str) -> list[str]:
    """
    Identifica la descripción del índice
    """
    indice = str(indice)
    frptron = r"^\s*(?:\d+(\.\d+)?\s+)?(.*?)\s+\.{2,}"
    ixptron = r"^\d+\.\d+"
    match_frs = re.search(frptron, indice)
    if match_frs:
        idx =  re.search(ixptron, indice).group()
        frase = match_frs.group(2)
        return [idx, frase]
    else:
        return indice

# Normaliza descripción de los índices
def normalizar_text(texto: str) -> str:
    """
    Noramliza el texto para poder trabajarlo
    """
    texto = str(texto)
    # Quitar acentos
    texto = ''.join(
    c for c in unicodedata.normalize('NFD', texto)
    if unicodedata.category(c) != 'Mn'
    )
    # Todo minúsculas
    texto = texto.lower()
    # eliminar puntuación, comas, asteriscos, etc.
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    # eliminar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def reading_tables_from_pdf(pthtopdfs: Path) -> list[str]:
    """
    Lectura de pdfs
    """
    pages2read = ['63-65','70-71','55','95','111','121'] # agregar páginas por pdf + periodos
    pthtopdfs_lst = [os.path.join(pthtopdfs,f) for f in os.listdir(pthtopdfs)]

    tables_pdf =  []
    for pdf,page in zip(pthtopdfs_lst,pages2read):
        print(f"Leyendo: {pdf}, pages: {page}\n")
        namefile = pdf.split('/')[-1]
        periodo = re.search(r"\d+[-_]\d+|\d+",pdf.split('/')[-1])[0]
        año = re.split("[-_]",periodo)[0]
        try:
            pdftable = tabula.read_pdf(pdf, pages=page, multiple_tables=True)
            tables_pdf.append([namefile,periodo,año,pdftable])
        except:
            print(f"NO SE LEYÓ: {pdf}")
    return tables_pdf


def index_df_creation(tables_pdf: list) -> pd.DataFrame:
    """
    Crea un dataframe con informaciones de los índices y su descripción
    """
    indicadores = []
    for table in tables_pdf:
        año = table[2]
        if año in ['2016','2017']: # 2017 tiene una sola tabla
            indic_rows = pd.concat([table[-1][0].T.iloc[0,:],table[-1][0].T.iloc[4,:]]).to_frame().T.iloc[0].tolist()
            indic_rows = [indx for indx in indic_rows if bool(re.search(r"^\d+\.\d+",str(indx)))]
            indic_rows = [find_indx_and_descrip(indx)+(año,) for indx in indic_rows]
        elif año in ['2018','2019']:
            indic_rows = pd.concat(tables_pdf[0][-1]).iloc[:,0].tolist()
            indic_rows = [indx for indx in indic_rows if bool(re.search(r"^\d+\.\d+",str(indx)))]
            indic_rows = [find_indx_and_descrip(indx)+(año,) for indx in indic_rows]
        elif año in ['2014','2015']:
            table = table[-1][0].T
            indic_rows = pd.concat([table.iloc[0,:],table.iloc[2,:].astype(str)+' '+table.iloc[3,:]]).tolist()
            indic_rows = [indx for indx in indic_rows if bool(re.search(r"^\d+\.\d+",str(indx)))]
            indic_rows = [re.split(r"\.{3}",str(indx))[0] for indx in indic_rows]
            indic_rows = [find_indx_and_descrip(indx)+(año,) for indx in indic_rows]
        indicadores.extend(indic_rows)
        indicadores = pd.DataFrame(indicadores,columns=["NUM_INDX","DESCRIPCION","AÑO"])
        indicadores['DESCRIPCION_INDX_NORM'] = indicadores['DESCRIPCION'].apply(lambda x: normalizar_text(x))
    return indicadores



logging.info(f"Leyendo pdfs de {PDF_FILES_PATH}/...")
tabula_pdfs = reading_tables_from_pdf(PDF_FILES_PATH)

print("="*90)
logging.info(f"Creando DataFrame ...")
df_index = index_df_creation(tabula_pdfs)

print(df_index)



