
"""
Modulo para extraer la bandera de un repositorio y crear distintos
objetos.

"""

#-------------------------------------------
# LIBRERÍAS
#-------------------------------------------
import requests
import os
from pathlib import Path
import logging
from dotenv import load_dotenv
import ijson
import json
from urllib.parse import urljoin

#-------------------------------------------
# Variables de entorno
#-------------------------------------------
load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL")
CACHE_DIR = Path(os.getenv("CACHE_FOLDER"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = CACHE_DIR / "repo_index.json"
# Para urls utilizar urljoin
INFO_URL = urljoin(BASE_URL, "data-contries.json")

# Otra info
PIXEL_SIZE_LIST = [1280,2560,320,40,80]

METHOD_DIC = {
    "ALPHA2":"iso-3166-1_alpha-2",
    "NAME":"country",
    "ALPHA3":"iso-3166-1_alpha-3",
    "ISONUM":"iso-numerically"
    }
#-------------------------------------------
# FUNCIONES
#-------------------------------------------
def ensure_local_info():
    if not INDEX_FILE.exists():
        resp = requests.get(INFO_URL, timeout=10)
        resp.raise_for_status()
        with open(INDEX_FILE, "wb") as f:
            f.write(resp.content)

def transform_index():

    method = METHOD_DIC["ALPHA3"]

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        data_str = f.read()
    data_str  = data_str.replace('"iso-numerically\' : "', '"iso-numerically": ""')
    data_json = json.loads(data_str)

    data_dic = {info[method].lower(): info for info in list(data_json)}
    _save_index(data_dic)



def get_info_repo(country: str, method="ALPHA3"):
    """

    """
    ensure_local_info()

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    obj_key = METHOD_DIC[method]

    for obj in data:
        if obj[obj_key].lower() == country.lower():
            return obj

    return None


def get_country_info(country: str):
    """

    """
    country_key = country.lower()
    index = _load_index()

    logging.info(f"Chequeando si existe Información local de {country}...")
    # Si ya está en caché
    if country_key in index:
        logging.info(f"Existe información para: {country}. Obteniendola")
        return index[country_key]

    logging.info(f"No hay información. Request a repositorio para {country}...")
    # Si no está, buscamos en streaming
    info = get_info_repo(country)

    if info:
        logging.info("Encontrada en repositorio. Guardando consulta en caché...")
        print(f"Información: {info}")
        index[country_key] = info
        _save_index(index)
        return info
    else: logging.error(f"No se encontró {country} en los repositorios")
    return None


def check_flag_path(country: str, pixel_size: int = 40) -> Path:
    filename = f"{country.lower().replace(" ", "-")}.webp"
    subfolder = Path(f"{CACHE_DIR}/{pixel_size}")
    filepath = Path(f"{subfolder}/{filename}")

    # CACHE real
    logging.info("Buscando bandera en caché...")
    if filepath.exists():
        logging.info(f"Bandera de {country} en caché. Proceso finalizado")
        return filepath # path donde esta descargado la imagen
    else:
        return None


#---------------------------------------------
# Funciones Auxiliares
#---------------------------------------------
def _load_index():
    if not INDEX_FILE.exists():
        return {}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)

    except json.JSONDecodeError:
        # Si está corrupto, lo reiniciamos
        return {}


def _save_index(index: dict):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _build_url_country(
    country_info: dict,
    pixel_size = 40
    ) -> str:
    """
    Construye url para descarga de flag

    ejemplo: https://github.com/oliv3ira40/bandeiras-paises/blob/master/country-flags/w1280-webp/ad.webp
    """
    # Chequeo de pixeles
    if pixel_size not in PIXEL_SIZE_LIST:
        logging.error("Error en pixel_size:")
        raise ValueError(f"pixel_size solo tiene las siguientes opciones: {PIXEL_SIZE_LIST}")

    folderrep = f"/w{pixel_size}-webp/"
    country_code = country_info['iso-3166-1_alpha-2'].lower()
    # Forma final
    country_url = urljoin(
        BASE_URL.rstrip("/") + "/",
        f"w{pixel_size}-webp/{country_code}.webp"
        )

    return country_url

def _download_flag(country, country_url: str, pixel_size: int = 40):
    """
    Descarga imagen a folder cache/pixel_size/
    """

    filename = f"{country.lower().replace(' ', '-')}.webp"
    subfolder = Path(CACHE_DIR) / str(pixel_size)
    subfolder.mkdir(parents=True, exist_ok=True) # la crea de ser necesario

    filepath = subfolder / filename

    # Caché físico
    if filepath.exists():
        return filepath

    resp = requests.get(country_url, timeout=10)

    if resp.status_code == 200:
        with open(filepath, "wb") as f:
            f.write(resp.content)
        return filepath
    else:
        print(f"No encontrada: {country} -> {resp.status_code}")
        return None

#-------------------------------------------
# TEST
#-------------------------------------------

#print(get_info_repo("Andorra"))

def get_flag(country,pixel_size=40):

    country_pth_image = check_flag_path(country,pixel_size=pixel_size)

    if country_pth_image:
        return country_pth_image
    else:

        country_info = get_country_info(country)
        country_url  = _build_url_country(country_info)

        logging.info(f"No se encontró imagen en caché. Descargando bandera desde: {country_url}")
        country_pth_image = _download_flag(country,country_url,pixel_size=pixel_size)
        logging.info(f"Imagen descargada en: {country_pth_image}")
        return country_pth_image


if __name__ == "__main__":
    #ensure_local_info()
    get_flag("CHL")
    #transform_index()
    #print(get_flag("CHL"))



