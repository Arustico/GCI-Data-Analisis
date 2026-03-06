"""
-------------------
Módulo para extraer y estructurar índices e indicadores desde los PDFs del
Informe de Competitividad Global (WEF) para los años 2014–2019.

Estrategia de extracción por año
─────────────────────────────────
Los PDFs del WEF cambiaron su maquetación entre ediciones. Hay dos formatos:

  FORMATO A — 2018/2019 (tabula, stream):
    Las tablas de índices son estructuras tabulares detectables por tabula-py.
    Columna 0 contiene strings "N.NN Descripción".

  FORMATO B — 2014/2015/2016 (pdftotext + regex):
    Los indicadores están en una columna de texto de doble página (layout a 2
    columnas). tabula no detecta tabla alguna porque no hay líneas de borde.
    Se extrae con `pdftotext -layout` y un parser de segmentos por línea que
    maneja DOS sub-formatos internos:
      B1) "N.NN Descripción"       → número y descripción en el mismo segmento
      B2) "N.NN" | "Descripción"   → separados por las múltiples columnas del layout
          (pilar 3 y pilares 11-12 presentan este comportamiento)

  FORMATO C — 2017 (tabula + transposición):
    Idéntico al Formato A pero la tabla está transpuesta; los indicadores se
    distribuyen en las filas 0 y 4 de la versión transpuesta.

Páginas correctas por PDF (confirmadas inspeccionando los PDFs reales)
────────────────────────────────────────────────────────────────────────
  Archivo (orden alfabético)                        Páginas  Método
  ────────────────────────────────────────────────────────────────────
  Global_Competitiveness_Report_2015-2016.pdf       57-58    pdftotext  ← CORREGIDO
  TheGlobalCompetitivenessReport2016-2017_FINAL     55-56    pdftotext  ← CORREGIDO
  TheGlobalCompetitivenessReport2017-2018           55       tabula
  TheGlobalCompetitivenessReport2018                70-71    tabula
  WEF_GlobalCompetitivenessReport_2014-15           65-67    pdftotext  ← CORREGIDO
  WEF_TheGlobalCompetitivenessReport2019            63-65    tabula

Requisitos de entorno (.env)
────────────────────────────
  PDF_FILES_PATH   → directorio con los PDFs
  FOLDER_PROCESSED → directorio donde se guarda el CSV de salida
  FOLDER_RAW       → (opcional) carpeta local de datos crudos
  LOG_LEVEL        → (opcional) nivel de logging; por defecto INFO

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

_folder_processed = os.getenv("FOLDER_PROCESSED")
if not _folder_processed:
    raise EnvironmentError(
        "La variable de entorno 'FOLDER_PROCESSED' no está definida. "
        "Agrégala en tu archivo .env antes de continuar."
    )
FOLDER_PROCESSED = Path(_folder_processed)

_pdf_path_env = os.getenv("PDF_FILES_PATH")
if not _pdf_path_env:
    raise EnvironmentError(
        "La variable de entorno 'PDF_FILES_PATH' no está definida. "
        "Agrégala en tu archivo .env antes de continuar."
    )
PDF_FILES_PATH = Path(_pdf_path_env)

# ── Páginas por PDF ────────────────────────────────────────────────────────────
# Orden: coincide con el orden ALFABÉTICO de los archivos en PDF_FILES_PATH.
# NOTA: actualizar esta lista si se agregan nuevos PDFs.
#
PAGES_PER_PDF: list[str] = ["57-58", "55-56", "55", "70-71", "65-67", "63-65"]

# ── Sets de años por método de extracción ─────────────────────────────────────
AÑOS_PDFTOTEXT = {"2014", "2015", "2016"}   # Formato B: pdftotext + regex
AÑOS_TABULA_A  = {"2018", "2019"}           # Formato A: tabula, columna 0
AÑOS_TABULA_C  = {"2017"}                   # Formato C: tabula + transposición

# ── Patrones de regex compilados ──────────────────────────────────────────────
# Número de índice exacto (todo el segmento): "1.01", "12.07"
_RE_NUMERO_SOLO = re.compile(r"^\d+\.\d+$")
# Número + descripción juntos en un segmento: "1.01 Property rights"
_RE_INDIC_COMPLETO = re.compile(r"^(\d+\.\d+)\s+([A-Z].+)")
# Número en inicio de cadena más larga (para filtros de candidatos tabula)
_RE_NUMERO_EN_CADENA = re.compile(r"^\d+\.\d+")

DEFAULT_DESCRIPTION_PATTERN = r"([A-Z])\w.+"

# ── Esquemas de columnas ──────────────────────────────────────────────────────
OUTPUT_COLUMNS = [
    "NUM_INDX", "DESCRIPCION_INDX", "DESCRIPCION_INDX_NORM",
    "PILAR", "SUBPILAR", "DESCRIPCION_PILAR",
    "AÑO", "CATEGORIA_INDX", "CATEGORIA_DESC", "FACTOR",
]

# ── Mapeos WEF ────────────────────────────────────────────────────────────────
MAP_CATEGORIAS = [
    {"CATEGORIA_INDX": "A", "CATEGORIA_DESC": "Requisitos Básicos",
     "FACTOR": 0.4, "PILAR": [1, 2, 3, 4]},
    {"CATEGORIA_INDX": "B", "CATEGORIA_DESC": "Impulsores de Eficiencia",
     "FACTOR": 0.5, "PILAR": [5, 6, 7, 8, 9, 10]},
    {"CATEGORIA_INDX": "C", "CATEGORIA_DESC": "Factores de Innovación y Sofisticación",
     "FACTOR": 0.1, "PILAR": [11, 12]},
]

MAP_DESCRIPCION_PILAR = {
    1: "Instituciones",
    2: "Infraestructura",
    3: "Adopción de Tecnologías de Información y Comunicación (TIC)",
    4: "Estabilidad Macroeconómica",
    5: "Salud",
    6: "Habilidades",
    7: "Mercado de Productos",
    8: "Mercado Laboral",
    9: "Sistema Financiero",
    10: "Tamaño del Mercado",
    11: "Dinamismo Empresarial",
    12: "Capacidad de Innovación",
}


# ─────────────────────────────────────────────
# Funciones auxiliares de texto
# ─────────────────────────────────────────────

def normalizar_texto(texto: str) -> str:
    """
    Normaliza una cadena para comparaciones y búsquedas:
      1. Elimina acentos (NFD + filtro categoría 'Mn').
      2. Convierte a minúsculas.
      3. Elimina caracteres que no sean letras, dígitos ni espacios.
      4. Colapsa espacios múltiples.

    Ejemplo:
        >>> normalizar_texto("Índice de Innovación (2019)")
        'indice de innovacion 2019'
    """
    texto = str(texto)
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9\s]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def extraer_indice_y_descripcion(
    cadena: str,
    patron_descripcion: str = DEFAULT_DESCRIPTION_PATTERN,
) -> tuple[str, str]:
    """
    Extrae (numero_indice, descripcion) de un string con formato
    "N.NN Descripción del indicador".

    Args:
        cadena: String ya limpio (sin puntos suspensivos ni rankings).
        patron_descripcion: Regex para capturar la descripción.

    Returns:
        Tupla (numero_indice, descripcion).

    Raises:
        ValueError: Si no se encuentra el índice o la descripción.
    """
    m_num = re.search(r"^\d+\.\d+", cadena)
    m_desc = re.search(patron_descripcion, cadena)
    if not m_num:
        raise ValueError(f"Sin número de índice en: '{cadena}'")
    if not m_desc:
        raise ValueError(f"Sin descripción en: '{cadena}'")
    return m_num.group(), m_desc.group()


def limpiar_descripcion_wef(raw: str) -> str:
    """
    Elimina sufijos de notas al pie de las descripciones WEF:
      - Asterisco y lo que sigue:  "Strength of investor protection*"  → "..."
      - Símbolo ½ y lo que sigue:  "Mobile subscriptions* ½"           → "..."
      - Fracción escrita "1/2" con espacio previo.

    No elimina letras de footnote pegadas (ej. "malariak") porque la
    distinción con letras propias de la palabra es ambigua. Estas letras
    son irrelevantes para normalizar_texto().
    """
    desc = re.sub(r"\s*[\*½].*$", "", raw)
    desc = re.sub(r"\s+1/2.*$", "", desc)
    return desc.strip()


# ─────────────────────────────────────────────
# Lectura de PDFs con tabula
# ─────────────────────────────────────────────

def leer_tablas_desde_pdfs(ruta_pdfs: Path) -> list[tuple]:
    """
    Lee tablas de todos los PDFs en *ruta_pdfs* con tabula-py.

    Para los años que usan pdftotext (2014/2015/2016), tabula puede devolver
    listas vacías; esto está previsto en `construir_dataframe_indices`.

    Returns:
        Lista de tuplas (nombre_archivo, periodo, año, lista_tablas).

    Raises:
        FileNotFoundError: Si el directorio no existe.
    """
    if not ruta_pdfs.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {ruta_pdfs}")

    archivos_pdf = sorted(ruta_pdfs.iterdir())

    if len(archivos_pdf) != len(PAGES_PER_PDF):
        logger.warning(
            "Hay %d PDFs pero PAGES_PER_PDF tiene %d entradas. "
            "Verifica la sincronización.",
            len(archivos_pdf), len(PAGES_PER_PDF),
        )

    resultados: list[tuple] = []
    for archivo, paginas in zip(archivos_pdf, PAGES_PER_PDF):
        nombre = archivo.name
        m = re.search(r"\d+[-_]\d+|\d+", nombre)
        if not m:
            logger.warning("Sin periodo en '%s'. Se omite.", nombre)
            continue

        periodo = m.group()
        año = re.split(r"[-_]", periodo)[0]

        logger.info("Leyendo: %-55s | páginas: %s", nombre, paginas)
        try:
            tablas = tabula.read_pdf(str(archivo), pages=paginas, multiple_tables=True)
            resultados.append((nombre, periodo, año, tablas))
            logger.debug("  → %d tabla(s).", len(tablas))
        except Exception as exc:
            logger.error("No se pudo leer '%s': %s", nombre, exc)

    return resultados


# ─────────────────────────────────────────────
# Extractores especializados por formato
# ─────────────────────────────────────────────

def _extraer_con_pdftotext(ruta_pdf: str, paginas: str, año: str) -> list[tuple]:
    """
    Extractor para años 2014/2015/2016 (Formato B).

    Estos PDFs presentan los indicadores en una estructura de dos columnas
    de texto sin bordes tabulares visibles, por lo que tabula no las detecta.
    Se usa `pdftotext -layout` que preserva el posicionamiento espacial,
    permitiendo separar las columnas por cantidad de espacios.

    Sub-formatos internos manejados:
      B1) Número y descripción en el mismo segmento de columna:
              "1.01 Property rights"
      B2) Número solo en un segmento, descripción en el siguiente
          (ocurre en pilar 3 y pilares 11-12):
              Seg[i]   = "3.01"
              Seg[i+1] = "Government budget balance*"

    Páginas correctas confirmadas inspeccionando los PDFs:
        2014 → 65-67  (pilar 3 en pág 65-66, pilares 11-12 en pág 67)
        2015 → 57-58
        2016 → 55-56

    Args:
        ruta_pdf: Ruta completa al archivo PDF.
        paginas:  Rango "inicio-fin" (ej. "65-67") o página sola ("55").
        año:      Año del informe.

    Returns:
        Lista de tuplas (NUM_INDX, DESCRIPCION, AÑO), deduplicada y ordenada.
    """
    primera, *resto = paginas.split("-")
    ultima = resto[0] if resto else primera

    proc = subprocess.run(
        ["pdftotext", "-f", primera, "-l", ultima, "-layout", ruta_pdf, "-"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        logger.error("[%s] pdftotext falló: %s", año, proc.stderr.strip())
        return []

    texto = proc.stdout
    vistos: set[str] = set()
    indicadores: list[tuple] = []

    for linea in texto.splitlines():
        # Dividir la línea por 4+ espacios → separa columnas del layout.
        segmentos = [s.strip() for s in re.split(r"\s{4,}", linea) if s.strip()]

        i = 0
        while i < len(segmentos):
            seg = segmentos[i]

            # ── Caso B1: "N.NN Descripción..." en el mismo segmento ─────────
            m = _RE_INDIC_COMPLETO.match(seg)
            if m:
                num = m.group(1)
                desc = limpiar_descripcion_wef(m.group(2))
                if desc and len(desc) >= 3 and num not in vistos:
                    vistos.add(num)
                    indicadores.append((num, desc, año))
                i += 1
                continue

            # ── Caso B2: "N.NN" solo → descripción en el segmento siguiente ─
            if _RE_NUMERO_SOLO.match(seg) and i + 1 < len(segmentos):
                siguiente = segmentos[i + 1]
                if re.match(r"^[A-Z]", siguiente):
                    num = seg
                    desc = limpiar_descripcion_wef(siguiente)
                    if desc and len(desc) >= 3 and num not in vistos:
                        vistos.add(num)
                        indicadores.append((num, desc, año))
                    i += 2
                    continue

            i += 1

    indicadores.sort(key=lambda x: [int(p) for p in x[0].split(".")])
    logger.info("[%s] %d indicadores extraídos (pdftotext).", año, len(indicadores))
    return indicadores


def _extraer_2018_2019(tablas: list, año: str) -> list[tuple]:
    """
    Extractor para 2018/2019 (Formato A).

    Concatena todas las tablas del PDF y toma la columna 0, que contiene
    strings con formato "N.NN Descripción".

    Corrección vs versión original: se usa `tablas` (el PDF actual) en lugar
    de `tablas_por_pdf[0][-1]` que siempre apuntaba al primer PDF cargado.
    """
    if not tablas:
        logger.warning("[%s] tabula no encontró tablas.", año)
        return []

    candidatos = pd.concat(tablas).iloc[:, 0].tolist()
    candidatos = [c for c in candidatos if _RE_NUMERO_EN_CADENA.search(str(c))]

    filas: list[tuple] = []
    for c in candidatos:
        try:
            num, desc = extraer_indice_y_descripcion(str(c))
            filas.append((num, desc, año))
        except ValueError as exc:
            logger.debug("[%s] Omitido: %s", año, exc)

    logger.info("[%s] %d indicadores extraídos (tabula).", año, len(filas))
    return filas


def _extraer_2017(tablas: list, año: str) -> list[tuple]:
    """
    Extractor para 2017 (Formato C — tabla transpuesta).

    La tabla del PDF está transpuesta: tras hacer `.T`, los indicadores se
    encuentran en las filas 0 y 4. Se valida la existencia de esas filas
    antes de acceder y se usa `.to_frame().T.iloc[0]` para re-indexar
    (igual que el notebook original), evitando errores de índice duplicado.
    """
    if not tablas:
        logger.warning("[%s] tabula no encontró tablas.", año)
        return []

    tabla_t = tablas[0].T
    n_filas = tabla_t.shape[0]

    if n_filas < 1:
        logger.warning("[%s] Tabla transpuesta vacía.", año)
        return []

    bloques = [tabla_t.iloc[0, :]]
    if n_filas >= 5:
        bloques.append(tabla_t.iloc[4, :])
    else:
        logger.warning(
            "[%s] Tabla transpuesta tiene %d fila(s); solo se usa fila 0.",
            año, n_filas,
        )

    candidatos = pd.concat(bloques).to_frame().T.iloc[0].tolist()
    candidatos = [c for c in candidatos if _RE_NUMERO_EN_CADENA.search(str(c))]

    filas: list[tuple] = []
    for c in candidatos:
        try:
            num, desc = extraer_indice_y_descripcion(str(c))
            filas.append((num, desc, año))
        except ValueError as exc:
            logger.debug("[%s] Omitido: %s", año, exc)

    logger.info("[%s] %d indicadores extraídos (tabula+T).", año, len(filas))
    return filas


# ─────────────────────────────────────────────
# Pipeline principal de extracción
# ─────────────────────────────────────────────

def construir_dataframe_indices(
    tablas_por_pdf: list[tuple],
    ruta_pdfs: Path,
) -> pd.DataFrame:
    """
    Consolida los índices de todos los PDFs en un único DataFrame intermedio.

    Despacha a la función de extracción correcta según el año:
        2014/2015/2016  →  _extraer_con_pdftotext()
        2017            →  _extraer_2017()
        2018/2019       →  _extraer_2018_2019()

    Args:
        tablas_por_pdf: Salida de `leer_tablas_desde_pdfs()`.
        ruta_pdfs:      Directorio con los PDFs (para localizar el archivo
                        al llamar a pdftotext).

    Returns:
        DataFrame con columnas: NUM_INDX, DESCRIPCION, AÑO, DESCRIPCION_INDX_NORM.

    Raises:
        ValueError: Si no se extrajo ningún indicador.
    """
    archivos_ordenados = sorted(ruta_pdfs.iterdir())
    filas_acumuladas: list[tuple] = []

    for nombre_archivo, periodo, año, tablas in tablas_por_pdf:
        logger.debug("Procesando: %s (año=%s)...", nombre_archivo, año)
        try:
            if año in AÑOS_PDFTOTEXT:
                # Localizar el índice de este PDF para obtener sus páginas
                idx = next(
                    i for i, f in enumerate(archivos_ordenados)
                    if f.name == nombre_archivo
                )
                paginas = PAGES_PER_PDF[idx]
                filas = _extraer_con_pdftotext(
                    str(ruta_pdfs / nombre_archivo), paginas, año
                )

            elif año in AÑOS_TABULA_A:
                filas = _extraer_2018_2019(tablas, año)

            elif año in AÑOS_TABULA_C:
                filas = _extraer_2017(tablas, año)

            else:
                logger.warning("Año '%s' sin extractor definido. Se omite.", año)
                continue

            filas_acumuladas.extend(filas)

        except Exception as exc:
            logger.error(
                "Error inesperado en año %s (%s): %s", año, nombre_archivo, exc
            )

    if not filas_acumuladas:
        raise ValueError(
            "No se extrajo ningún indicador. Revisa PDFs, PAGES_PER_PDF "
            "y los extractores por año."
        )

    df = pd.DataFrame(filas_acumuladas, columns=["NUM_INDX", "DESCRIPCION", "AÑO"])
    df["DESCRIPCION_INDX_NORM"] = df["DESCRIPCION"].apply(normalizar_texto)
    logger.info("DataFrame intermedio: %d filas.", len(df))
    return df


# ─────────────────────────────────────────────
# Enriquecimiento del DataFrame
# ─────────────────────────────────────────────

def agregar_pilar_y_subpilar(df: pd.DataFrame) -> pd.DataFrame:
    """Deriva PILAR y SUBPILAR desde NUM_INDX y ordena el DataFrame."""
    df = df.copy()
    df["PILAR"]   = df["NUM_INDX"].apply(lambda x: int(re.search(r"(^\d+)", x).group()))
    df["SUBPILAR"] = df["NUM_INDX"].apply(lambda x: int(re.search(r"(?<=\d\.)(\d+)", x).group()))
    df["AÑO"] = df["AÑO"].astype(int)
    return df.sort_values(["AÑO", "PILAR", "SUBPILAR"]).reset_index(drop=True)


def agregar_categorias(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna CATEGORIA_INDX, CATEGORIA_DESC y FACTOR según metodología WEF."""
    df = df.copy()
    for cat in MAP_CATEGORIAS:
        mask = df["PILAR"].isin(cat["PILAR"])
        df.loc[mask, "CATEGORIA_INDX"] = cat["CATEGORIA_INDX"]
        df.loc[mask, "CATEGORIA_DESC"] = cat["CATEGORIA_DESC"]
        df.loc[mask, "FACTOR"]         = cat["FACTOR"]
    return df


def agregar_descripcion_pilar(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna DESCRIPCION_PILAR según el mapeo oficial WEF."""
    df = df.copy()
    for pilar, descripcion in MAP_DESCRIPCION_PILAR.items():
        df.loc[df["PILAR"] == pilar, "DESCRIPCION_PILAR"] = descripcion
    return df


def construir_dataframe_final(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orquesta el enriquecimiento completo y retorna el DataFrame
    con el esquema de salida definido en OUTPUT_COLUMNS.
    """
    logger.info("Enriqueciendo DataFrame...")
    df = agregar_pilar_y_subpilar(df)
    df = agregar_categorias(df)
    df = agregar_descripcion_pilar(df)
    df = df.rename(columns={"DESCRIPCION": "DESCRIPCION_INDX"})
    df = df[OUTPUT_COLUMNS].copy()
    logger.info("DataFrame final: %d filas, %d columnas.", len(df), len(df.columns))
    return df


# ─────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────

def main() -> None:
    """
    Pipeline completo de extracción y exportación:
        1. Lee todos los PDFs con tabula (para años tabula) o pdftotext
           (para años 2014/2015/2016).
        2. Construye el DataFrame intermedio con indicadores y descripciones.
        3. Enriquece con pilares, categorías y descripciones.
        4. Exporta a CSV en FOLDER_PROCESSED.
    """
    logger.info("=" * 70)
    logger.info("Iniciando extracción de índices WEF.")
    logger.info("Directorio de PDFs: %s", PDF_FILES_PATH)
    logger.info("=" * 70)

    tablas_pdf = leer_tablas_desde_pdfs(PDF_FILES_PATH)
    logger.info("%d PDF(s) procesados por tabula.", len(tablas_pdf))

    df_indices = construir_dataframe_indices(tablas_pdf, PDF_FILES_PATH)

    print("\n" + "=" * 90)
    print("VISTA PREVIA — DataFrame intermedio (primeras 10 filas):")
    print(df_indices.head(10).to_string(index=False))
    print("=" * 90 + "\n")

    df_final = construir_dataframe_final(df_indices)

    print("\n" + "=" * 90)
    print("VISTA PREVIA — DataFrame final (primeras 10 filas):")
    print(df_final.head(10).to_string(index=False))
    print("=" * 90 + "\n")

    FOLDER_PROCESSED.mkdir(parents=True, exist_ok=True)
    ruta_salida = FOLDER_PROCESSED / "bd_diccionario_indices.csv"
    df_final.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    logger.info("Archivo guardado en: %s", ruta_salida)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
