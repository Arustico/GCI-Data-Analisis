"""
extraction_index.py
-------------------
Módulo para extraer y estructurar índices e indicadores desde archivos PDF
usando tabula-py. Genera un DataFrame consolidado con número de índice,
descripción normalizada y año de publicación.

Uso:
    python extraction_index.py
"""

# ─────────────────────────────────────────────
# Librerías estándar
# ─────────────────────────────────────────────
import os
import re
import logging
import unicodedata
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────
# Librerías de terceros
# ─────────────────────────────────────────────
import pandas as pd
import numpy as np
import tabula
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
FOLDER_RAW_LOCAL = Path(os.getenv("FOLDER_RAW", "data/raw"))

_pdf_path_env = os.getenv("PDF_FILES_PATH")
if not _pdf_path_env:
    raise EnvironmentError(
        "La variable de entorno 'PDF_FILES_PATH' no está definida. "
        "Agrégala en tu archivo .env antes de continuar."
    )
PDF_FILES_PATH = Path(_pdf_path_env)

# Páginas a leer por PDF (en el mismo orden que los archivos del directorio).
# NOTA: actualiza esta lista si se agregan nuevos PDFs o periodos.
PAGES_PER_PDF: list[str] = ["63-65", "70-71", "55", "95", "111", "121"]

# Patrón por defecto para capturar la descripción de un indicador
DEFAULT_DESCRIPTION_PATTERN = r"([A-Z])\w.+"

# Columnas del DataFrame final
OUTPUT_COLUMNS = ["NUM_INDX", "DESCRIPCION", "AÑO", "DESCRIPCION_INDX_NORM"]


# ─────────────────────────────────────────────
# Funciones auxiliares
# ─────────────────────────────────────────────

def normalizar_texto(texto: str) -> str:
    """
    Normaliza una cadena de texto para comparaciones y búsquedas:
      1. Elimina acentos (NFD + filtro de categoría 'Mn').
      2. Convierte a minúsculas.
      3. Elimina caracteres que no sean letras, dígitos ni espacios.
      4. Colapsa espacios múltiples en uno solo.

    Args:
        texto: Cadena a normalizar.

    Returns:
        Cadena normalizada.
    """
    texto = str(texto)
    # Paso 1 – quitar acentos
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    # Paso 2 – minúsculas
    texto = texto.lower()
    # Paso 3 – solo alfanuméricos y espacios
    texto = re.sub(r"[^a-z0-9\s]", "", texto)
    # Paso 4 – espacios múltiples
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def extraer_indice_y_descripcion(
    cadena_indicador: str,
    patron_descripcion: str = DEFAULT_DESCRIPTION_PATTERN,
) -> list[str]:
    """
    Extrae el número de índice y la descripción desde una cadena con formato:
        '1.2 Descripción del indicador ...'

    Args:
        cadena_indicador:   Cadena raw del PDF.
        patron_descripcion: Expresión regular para capturar la descripción.
                            Por defecto captura palabras que inician en mayúscula.

    Returns:
        Lista con dos elementos: [numero_indice, descripcion].

    Raises:
        ValueError: Si no se encuentran el índice o la descripción.
    """
    match_indice = re.search(r"^\d+\.\d+", cadena_indicador)
    match_descripcion = re.search(patron_descripcion, cadena_indicador)

    if not match_indice:
        raise ValueError(
            f"No se encontró un número de índice válido en: '{cadena_indicador}'"
        )
    if not match_descripcion:
        raise ValueError(
            f"No se encontró descripción con patrón '{patron_descripcion}' en: '{cadena_indicador}'"
        )

    return [match_indice.group(), match_descripcion.group()]


def extraer_descripcion_con_puntos(cadena_indice: str) -> list[str] | str:
    """
    Extrae el número y la descripción de un índice con formato de tabla de contenidos:
        '1.2  Nombre del indicador .....'

    Args:
        cadena_indice: Cadena raw del PDF con puntos suspensivos al final.

    Returns:
        Lista [numero_indice, descripcion] si hay coincidencia,
        o la cadena original si no se reconoce el formato.
    """
    cadena_indice = str(cadena_indice)
    patron_frase = r"^\s*(?:\d+(\.\d+)?\s+)?(.*?)\s+\.{2,}"
    patron_numero = r"^\d+\.\d+"

    match_frase = re.search(patron_frase, cadena_indice)
    if not match_frase:
        logger.debug("Formato de tabla de contenidos no reconocido: '%s'", cadena_indice)
        return cadena_indice

    match_numero = re.search(patron_numero, cadena_indice)
    if not match_numero:
        logger.debug("Número de índice no encontrado en: '%s'", cadena_indice)
        return cadena_indice

    return [match_numero.group(), match_frase.group(2)]


# ─────────────────────────────────────────────
# Funciones principales
# ─────────────────────────────────────────────

def leer_tablas_desde_pdfs(ruta_pdfs: Path) -> list[tuple]:
    """
    Lee tablas de los PDFs ubicados en *ruta_pdfs* usando tabula-py.

    Cada PDF se empareja con la página correspondiente en PAGES_PER_PDF
    (se asume que el orden del sistema de archivos coincide con el orden
    de las páginas declaradas).

    Args:
        ruta_pdfs: Directorio que contiene los archivos PDF.

    Returns:
        Lista de tuplas con estructura:
            (nombre_archivo, periodo, año, lista_de_DataFrames)

    Raises:
        FileNotFoundError: Si el directorio no existe.
    """
    if not ruta_pdfs.exists():
        raise FileNotFoundError(f"El directorio de PDFs no existe: {ruta_pdfs}")

    archivos_pdf = sorted(ruta_pdfs.iterdir())  # orden consistente entre SO
    if len(archivos_pdf) != len(PAGES_PER_PDF):
        logger.warning(
            "Se encontraron %d archivos PDF pero hay %d entradas en PAGES_PER_PDF. "
            "Verifica que la lista de páginas esté actualizada.",
            len(archivos_pdf),
            len(PAGES_PER_PDF),
        )

    resultados: list[tuple] = []

    for archivo, paginas in zip(archivos_pdf, PAGES_PER_PDF):
        nombre_archivo = archivo.name
        # Extrae el periodo del nombre de archivo (ej. "2016-01", "2018")
        match_periodo = re.search(r"\d+[-_]\d+|\d+", nombre_archivo)
        if not match_periodo:
            logger.warning("No se pudo extraer el periodo de '%s'. Se omite.", nombre_archivo)
            continue

        periodo = match_periodo.group()
        año = re.split(r"[-_]", periodo)[0]

        logger.info("Leyendo: %s  |  páginas: %s", nombre_archivo, paginas)
        try:
            tablas = tabula.read_pdf(str(archivo), pages=paginas, multiple_tables=True)
            resultados.append((nombre_archivo, periodo, año, tablas))
        except Exception as exc:  # tabula puede lanzar varios tipos de error
            logger.error("No se pudo leer '%s': %s", nombre_archivo, exc)

    return resultados


def construir_dataframe_indices(
    tablas_por_pdf: list[tuple],
) -> pd.DataFrame:
    """
    Consolida los índices extraídos de todos los PDFs en un único DataFrame.

    Lógica por año:
      - 2016 / 2017: tabla transpuesta; índices en filas 0 y 4.
      - 2018 / 2019: concatenación de todas las tablas; índices en columna 0.
      - 2014 / 2015: tabla transpuesta con descripción compuesta (filas 2 y 3).
        Los índices siguen el formato de tabla de contenidos (puntos al final).

    Args:
        tablas_por_pdf: Salida de `leer_tablas_desde_pdfs`.

    Returns:
        DataFrame con columnas: NUM_INDX, DESCRIPCION, AÑO, DESCRIPCION_INDX_NORM.

    Raises:
        ValueError: Si el DataFrame resultante está vacío.
    """
    patron_numero_indice = r"^\d+\.\d+"
    filas_acumuladas: list[tuple] = []

    for nombre_archivo, periodo, año, tablas in tablas_por_pdf:
        logger.debug("Procesando año %s (%s)...", año, nombre_archivo)
        filas_año: list[tuple] = []

        try:
            if año in {"2016", "2017"}:
                # Las tablas de 2016-2017 tienen una sola tabla con índices en
                # las filas 0 y 4 de su versión transpuesta.
                tabla_t = tablas[0].T
                candidatos = pd.concat([tabla_t.iloc[0, :], tabla_t.iloc[4, :]]).tolist()
                candidatos = [
                    c for c in candidatos
                    if re.search(patron_numero_indice, str(c))
                ]
                filas_año = [
                    (*extraer_indice_y_descripcion(c), año)
                    for c in candidatos
                ]

            elif año in {"2018", "2019"}:
                # BUG ORIGINAL: usaba `tablas_por_pdf[0]` (siempre el primer PDF)
                # en lugar de `tablas` (el PDF actual). Corregido ↓
                candidatos = pd.concat(tablas).iloc[:, 0].tolist()
                candidatos = [
                    c for c in candidatos
                    if re.search(patron_numero_indice, str(c))
                ]
                filas_año = [
                    (*extraer_indice_y_descripcion(c), año)
                    for c in candidatos
                ]

            elif año in {"2014", "2015"}:
                # Descripción compuesta: fila 2 (código) + fila 3 (texto)
                tabla_t = tablas[0].T
                descripcion_compuesta = (
                    tabla_t.iloc[2, :].astype(str) + " " + tabla_t.iloc[3, :]
                )
                candidatos = pd.concat([tabla_t.iloc[0, :], descripcion_compuesta]).tolist()
                candidatos = [
                    c for c in candidatos
                    if re.search(patron_numero_indice, str(c))
                ]
                # Eliminar los puntos suspensivos del formato tabla de contenidos
                candidatos = [re.split(r"\.{3,}", str(c))[0] for c in candidatos]
                filas_año = [
                    (*extraer_indice_y_descripcion(c), año)
                    for c in candidatos
                ]

            else:
                logger.warning("Año '%s' no tiene lógica de extracción definida. Se omite.", año)

        except Exception as exc:
            logger.error(
                "Error al procesar el año %s (%s): %s", año, nombre_archivo, exc
            )

        filas_acumuladas.extend(filas_año)

    if not filas_acumuladas:
        raise ValueError(
            "No se extrajeron índices. Revisa los PDFs, las páginas configuradas "
            "y la lógica de extracción por año."
        )

    df = pd.DataFrame(filas_acumuladas, columns=["NUM_INDX", "DESCRIPCION", "AÑO"])
    df["DESCRIPCION_INDX_NORM"] = df["DESCRIPCION"].apply(normalizar_texto)

    logger.info("DataFrame construido: %d registros, %d columnas.", len(df), len(df.columns))
    return df[OUTPUT_COLUMNS]


# ─────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────

def main() -> None:
    logger.info("Iniciando extracción de índices desde: %s", PDF_FILES_PATH)

    tablas_pdf = leer_tablas_desde_pdfs(PDF_FILES_PATH)
    logger.info("%d PDF(s) leídos correctamente.", len(tablas_pdf))

    df_indices = construir_dataframe_indices(tablas_pdf)

    # Muestra un resumen en consola (útil en desarrollo)
    print("\n" + "=" * 90)
    print(df_indices.to_string(index=False))
    print("=" * 90 + "\n")

    # Opcional: exportar a CSV en la carpeta raw local
    ruta_salida = FOLDER_RAW_LOCAL / "indices_extraidos.csv"
    FOLDER_RAW_LOCAL.mkdir(parents=True, exist_ok=True)
    df_indices.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    logger.info("Archivo guardado en: %s", ruta_salida)


if __name__ == "__main__":
    main()
