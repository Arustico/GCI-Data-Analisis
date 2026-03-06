"""
Modulo para realizar transformaciones a la data.
Los archivos puntajes_paises_**.xlsx contienen los puntajes por año y por países, extraidos de forma manual de los informes.
Este módulo lee estos puntajes y los transforma en una base de datos tratable para posteriormente ser analizada.
"""

# ─────────────────────────────────────────────
# Librerías estándar
# ─────────────────────────────────────────────
import os
import re
import subprocess
import logging
import unicodedata
from pathlib import Path

# ─────────────────────────────────────────────
# Librerías de terceros
# ─────────────────────────────────────────────
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Configuración de entorno y logging
# ─────────────────────────────────────────────
load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Variables de configuración
# ─────────────────────────────────────────────
FOLDER_RAW_LOCAL = Path(os.getenv("FOLDER_RAW"))
FOLDER_PROCESSED = Path(os.getenv("FOLDER_PROCESSED"))

# Información de datos
_files_name = ["puntajes_paises_1.xlsx", "puntajes_paises_2.xlsx"]
files = [f"{FOLDER_RAW_LOCAL}/{f}" for f in _files_name]

file_paises_info = f"{FOLDER_RAW_LOCAL}/bd_paises_info.csv"
file_indices_info = f"{FOLDER_PROCESSED}/bd_diccionario_indices.csv"


# ─────────────────────────────────────────────
# Funciones
# ─────────────────────────────────────────────


def creacion_df_list(files: list[Path]) -> list[pd.DataFrame]:
    """
    Crea lee los archivos y crea dataframe
    """
    bd_score = []
    colnames = []

    for f in files:
        logger.info(f"Lectura: {f}")
        bdaux = pd.read_excel(f, sheet_name=None) # None lee todos las hojas
        periods = list(bdaux.keys())
        for sheet,df in bdaux.items(): # El nombre de la hoja es el periodo
            df['PERIODO'] = sheet
            bd_score.append(df)
            colnames.append((len(df.columns.tolist()),sheet, df.columns.tolist()))
    return bd_score


def transformacion_datos_dfscore(dflist: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Tranformacion de los Datos
    Por cada conjunto de valores (paises + valores de indicadores) hay un año y un conjunto de indicadores.
    """
    df_score = []
    for df in dflist:
        año = int(list(set(df['PERIODO'].tolist()))[0].split("-")[0])
        df = df.dropna(subset=['Países'])
        df = df.rename(columns={'Países':'PAIS_COD'})
        # Unión
        df_melt = df.melt(
            id_vars=['PAIS_COD','PERIODO'],
            var_name='NUM_INDX',
            value_name='VALOR_INDICE'
        )
        df_melt['AÑO'] = año
        df_score.append(df_melt)

    df_score = pd.concat(df_score)
    df_score['NUM_INDX'] = df_score['NUM_INDX'].str.replace("P-","")
    return df_score


def add_info_pais(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lee información de paises y luego agrega la información a los índices
    """
    # Lectura de información paises
    logger.info(f"Leyendo informacion de países: {file_paises_info}")
    try:
        df_countries_info = pd.read_csv(file_paises_info)
    except Exception as exc:
        logger.error("No se pudo leer '%s': %s", file_paises_info, exc)

    logger.info("Agregando nueva información ...")
    try:
        df_melt = df.merge(df_countries_info, left_on = "PAIS_COD", right_on="PAIS_COD",how="left")
    except Exception as exc:
        logger.error("No se pudo llevar a cabo la operación:\n '%s'",exc)
        return df
    return df_melt


def add_indices_info(df:pd.DataFrame) -> pd.DataFrame:
    """
    Agrega información de los indicadores presentes en la data
    """
    print("="*90)
    logger.info(f"\nLeyendo información de indicadores: {file_indices_info}")
    try:
        df_indicadores = pd.read_csv(file_indices_info)
    except Exception as exc:
        logger.error("No se leyó datos: %s",exc)
    # Arreglos
    df_indicadores['NUM_INDX'] = df_indicadores['NUM_INDX'].astype(str)

    # chequeo de dtypes y consistencia años
    #print(df_indicadores['AÑO'].dtype == bd_indx_fil['AÑO'].dtype)
    #print(df_indicadores['AÑO'].unique() == bd_indx_fil['AÑO'].unique())
    print("="*90)
    logger.info(f"Agregando información...\n")
    # Agregamos los pilares
    usedcols = ['NUM_INDX', 'DESCRIPCION_INDX','DESCRIPCION_INDX_NORM', 'PILAR', 'SUBPILAR',
                'DESCRIPCION_PILAR', 'CATEGORIA_INDX', 'CATEGORIA_DESC','FACTOR']
    df_merged = []
    for año,df in df.groupby('AÑO'):
        indicadores = df_indicadores[df_indicadores['AÑO']==año]
        try:
            indicadores = indicadores[usedcols]
        except Exception as exc:
            logger.warning("Revisar columnas: %s",exc)

        df = df.merge(indicadores,on='NUM_INDX',how='inner')
        df_merged.append(df)

    df_merged = pd.concat(df_merged)

    # todos con descrpición
    nodescrip = df_merged[df_merged['DESCRIPCION_INDX'].isna()]
    if len(nodescrip)>0:
        logger.warning(f"Indicadores sin descripción: {nodescrip}")
    else:
        logger.info("Todos indicadores con descripción: OK\n")

    #% de nan en valores de índice
    missed_values = df_merged['VALOR_INDICE'].isna().sum()/len(df_merged)*100
    missed_values = np.round(missed_values,2)
    logger.warning(f"Valores nulos: {missed_values}%")
    #indicadores['DESCRIPCION_INDX'].unique()
    return df_merged

# ─────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────
def main() -> None:

    df_scores_list = creacion_df_list(files)
    df_score = transformacion_datos_dfscore(df_scores_list)

    df_score = add_info_pais(df_score)
    df_score = add_indices_info(df_score)
    print("\n" + "=" * 90)
    print("VISTA PREVIA — DataFrame intermedio (primeras 10 filas):")
    print(df_score.head(10).to_string(index=False))
    print("=" * 90 + "\n")

    file_data = f"{FOLDER_PROCESSED}/bd_indices_wef.csv"
    df_score.to_csv(file_data, index=False)
    logging.info(f"Datos guardados datos en: {file_data}")


if __name__ == "__main__":
    main()

