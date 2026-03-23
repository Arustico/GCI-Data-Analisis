"""
Módulo para la creación de biplots interactivos usando Plotly.
Incluye soporte para múltiples ejes, filtros dinámicos por menú desplegable
y exportación responsiva a HTML (compatible con móviles).

Funciones principales:
    - normalizar_puntajes: Normalización numérica de los valores/puntajes obtenidos por cada país
    - savefig: Guardados de figuras
    - savetable: guardados de tablas
    - crear_biplot_interactivo : genera la figura base del biplot.
    - agregar_filtros_biplot   : incorpora menús desplegables de filtrado.
    - exportar_html_responsivo : exporta la figura a HTML adaptable a móviles.

Dependencias:
    pip install plotly pandas numpy unicodedata

"""
#─────────────────────────────────
# Librerías estandar
#─────────────────────────────────
from __future__ import annotations


import re
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# ─────────────────────────────────────────────
# Librerías de terceros
# ─────────────────────────────────────────────
import unicodedata
import pandas as pd
import numpy as np
import matplotlib.pyplot as pl
import seaborn as sns

import plotly.express as px
import plotly.graph_objects as go
from pybiplots import *
from typing import Optional


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

#─────────────────────────────────
# Variables de entorno
#─────────────────────────────────
FIG_FOLDER = Path(os.getenv("FIG_FOLDER"))
TABLE_FOLDER = Path(os.getenv("TABLE_FOLDER"))


#─────────────────────────────────
# Funciones
#─────────────────────────────────

def normalizar_puntajes(values: pd.Series) -> pd.Series:
    """
    Normaliza puntajes de paises acorde a la fórmula de la metodología 4.0 del WEF
    """
    values = values[~values.isna()].copy()
    wpi = values.min()
    frontera = values.max()
    return (values-wpi)/(frontera-wpi) * 100


def savefig(fig: pl.fig,
            name: str,
            folder: Path = FIG_FOLDER) -> None:
    """
    Guarda las figuras en folder, para ser utilizadas en docs
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"{folder}/{name}.png"
    fig.savefig(filename,dpi=300,bbox_inches='tight')
    logging.info(f"Figura guardada en: {filename}")


def savetableview(df: pd.DataFrame,
                  name: str,
                  folder: Path = TABLE_FOLDER) -> None:
    """
    Guarda tablas para análisis y muestras en formato excel.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"{folder}/{name}.xlsx"
    df.to_excel(filename,index=False)
    logging.info(f"Tabla guardada en: {filename}")


# FUNCIONES DE PLOTLY
# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES Y VALORES POR DEFECTO
# ══════════════════════════════════════════════════════════════════════════════

# Color y tamaño de los vectores (autovectores / loadings)
DEFAULT_ARROW_COLOR   = "gray"
DEFAULT_ARROW_HEAD    = 2          # tamaño de la cabeza de flecha
DEFAULT_MARKER_SIZE   = 12         # tamaño de los puntos de individuos
DEFAULT_VECTOR_WIDTH  = 2          # grosor de la línea del vector

# Separación horizontal entre menús desplegables
DROPDOWN_X_STEP  = 0.18
DROPDOWN_X_START = 0.0
DROPDOWN_Y       = 1.18            # posición vertical sobre el gráfico

# Template visual de Plotly
DEFAULT_TEMPLATE = "plotly_white"


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN 1 — CREAR BIPLOT INTERACTIVO
# ══════════════════════════════════════════════════════════════════════════════

def crear_biplot_interactivo(
    hj_biplot,
    *,
    groups: Optional[pd.Series | str]  = None,
    text_label: Optional[str]          = None,
    axis_x: int                        = 0,
    axis_y: int                        = 1,
    arrow_color: str                   = DEFAULT_ARROW_COLOR,
    arrow_head: int                    = DEFAULT_ARROW_HEAD,
    marker_size: int                   = DEFAULT_MARKER_SIZE,
    title: Optional[str]               = None,
    meta_bool: Optional[bool]          = False,
    filters: list[str]             = ["Pilar","Anio"]
) -> tuple[go.Figure, pd.DataFrame]:
    """
    Genera un biplot interactivo con Plotly a partir de un objeto HJ_Biplot
    (o equivalente GH / JK).

    El biplot combina dos capas:
      1. **Individuos** → scatter plot coloreado por grupo.
      2. **Vectores**   → flechas que representan las variables (loadings).

    Parameters
    ----------
    hj_biplot : HJ_Biplot.fit
        Objeto ajustado que expone los atributos:
          - ``X``                  : DataFrame con los datos originales.
          - ``row_coordinates``    : DataFrame de coordenadas de individuos.
          - ``column_coordinates`` : DataFrame de coordenadas de variables.
          - ``explained_variance`` : array con varianza explicada por eje (%).
    groups : pd.Series | str | None
        Variable de agrupamiento para colorear los puntos.
        Puede ser el nombre de una columna de ``row_coordinates`` o una Serie.
    text_label : str | None
        Nombre de la columna en ``row_coordinates`` a mostrar como etiqueta.
    axis_x : int
        Índice del eje a representar en el eje horizontal (0-based). Default 0.
    axis_y : int
        Índice del eje a representar en el eje vertical (0-based).   Default 1.
    arrow_color : str
        Color CSS de las líneas de los vectores. Default 'gray'.
    arrow_head : int
        Tamaño de la cabeza de la flecha. Default 2.
    marker_size : int
        Tamaño de los marcadores de individuos. Default 12.
    title : str | None
        Título del gráfico. Si es None se usa 'Biplot Interactivo'.
    meta_bool: bool | False
        Variable para determinar si escribe o no ``meta_dict``
    filters: list | [Pilar, Anio]
        Filtros para escribir meta_dict

    Returns
    -------
    fig : go.Figure
        Figura Plotly lista para mostrar o exportar.
    vec : pd.DataFrame
        Coordenadas de las variables (columnas), útil para agregar filtros.

    Raises
    ------
    ValueError
        Si ``axis_x`` o ``axis_y`` están fuera del rango disponible.
    AttributeError
        Si ``hj_biplot`` no tiene los atributos esperados.

    Examples
    --------
    >>> fig, vec = crear_biplot_interactivo(modelo, groups='Region', title='GCI 2019')
    >>> fig.show()
    """
    # Validación de indices y ejes
    n_ejes = len(hj_biplot.explained_variance)
    for nombre, valor in (("axis_x", axis_x), ("axis_y", axis_y)):
        if not (0 <= valor < n_ejes):
            raise ValueError(
                f"'{nombre}={valor}' fuera de rango. "
                f"El modelo tiene {n_ejes} ejes (0–{n_ejes - 1})."
            )

    # Prepararación de datos
    # row_coordinates: coordenadas de los individuos (filas del biplot)
    ind = hj_biplot.row_coordinates.reset_index()

    # column_coordinates: coordenadas de las variables (vectores del biplot)
    vec = hj_biplot.column_coordinates.copy()

    if meta_bool: # el primary key es: pilar - año
        vec = vec.reset_index().rename(columns={"index":"primarykey"})
        vec[filters] = pd.DataFrame(vec["primarykey"].str.split("-").to_list(),columns=[f"key-{filter}"for filter in filters])

    vec = vec.set_index("primarykey")
    # Nombrar ejes con varianza explicada
    # Incluir el % de varianza facilita la interpretación del gráfico.
    axis1_label = _nombre_eje(hj_biplot, axis_x)
    axis2_label = _nombre_eje(hj_biplot, axis_y)

    # Renombrar columnas para que px.scatter use los nombres enriquecidos
    ind = ind.rename(columns={
        f"Axis {axis_x + 1}": axis1_label,
        f"Axis {axis_y + 1}": axis2_label,
    })

    # Scatter de individuos
    fig = px.scatter(
        ind,
        x=axis1_label,
        y=axis2_label,
        color=groups,
        text=text_label,
        title=title or "Biplot Interactivo",
        template=DEFAULT_TEMPLATE,
    )
    fig.update_traces(
        textposition="bottom right",
        marker_size=marker_size,
    )

    # ── 5. Añadir vectores (loadings) ─────────────────────────────────────────
    # Cada variable se representa como una flecha desde el origen (0,0)
    # hasta sus coordenadas en el espacio reducido.
    for nombre_var, fila in vec.iterrows():
        x_fin = fila.iloc[axis_x]
        y_fin = fila.iloc[axis_y]
        if meta_bool:
            meta_dict = {col: str(fila[col]) for col in filters}
        else:
            meta_dict = None
        fig.add_trace(
            go.Scatter(
                x=[0, x_fin],
                y=[0, y_fin],
                mode="lines+text+markers",
                line=dict(color=arrow_color, width=DEFAULT_VECTOR_WIDTH),
                marker=dict(
                    size=arrow_head * 5,          # escalar para visibilidad
                    symbol="arrow-bar-up",
                    angleref="previous",
                    color="black",
                ),
                text=[None, str(nombre_var)],
                textposition="top center",
                showlegend=False,
                name=str(nombre_var),
                hoverinfo="text",
                hovertext=str(nombre_var),
                meta = meta_dict,
            )
        )

    #logger.debug("Biplot creado: %d individuos, %d vectores.", len(ind), len(vec))
    print("Biplot creado: %d individuos, %d vectores.", len(ind), len(vec))
    # ── 6. Layout base ────────────────────────────────────────────────────────
    fig.update_layout(
        xaxis_title=axis1_label,
        yaxis_title=axis2_label,
        title_x=0.5,                   # centrar título
        margin=dict(t=80, b=50),       # margen superior para filtros
    )

    return fig, vec



# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN 2 — AGREGAR FILTROS AL BIPLOT
# ══════════════════════════════════════════════════════════════════════════════

def agregar_filtros_biplot(
    fig: go.Figure,
    vec: pd.DataFrame,
    filter_cols: list[str],
    num_traces_previos: int = 1,
) -> go.Figure:
    """
    Agrega menús desplegables (dropdowns) a la figura del biplot para filtrar
    los vectores según columnas categóricas de ``vec``.

    Cada menú desplegable controla la visibilidad de los vectores asociados
    a una categoría. La opción 'Todos' restaura la visibilidad completa.

    Parameters
    ----------
    fig : go.Figure
        Figura Plotly generada por ``crear_biplot_interactivo``.
    vec : pd.DataFrame
        DataFrame de coordenadas de variables, con columnas adicionales
        que contienen los atributos de filtrado.
    filter_cols : list[str]
        Lista de columnas de ``vec`` a usar como filtros. Cada columna
        genera un menú desplegable independiente.
    num_traces_previos : int
        Número de trazas que preceden a los vectores en la figura
        (scatter de individuos + otras capas fijas). Default 1.

    Returns
    -------
    go.Figure
        Figura con los menús desplegables incorporados.

    Raises
    ------
    ValueError
        Si alguna columna de ``filter_cols`` no existe en ``vec``.

    Notes
    -----
    La visibilidad de cada traza se controla con una máscara booleana:
      - Las primeras ``num_traces_previos`` trazas siempre están visibles.
      - Las siguientes ``len(vec)`` trazas corresponden a los vectores.

    Examples
    --------
    >>> fig = agregar_filtros_biplot(fig, vec, filter_cols=['Pilar', 'Categoria'])
    >>> fig.show()
    """
    # ── 1. Validar columnas de filtro ─────────────────────────────────────────
    columnas_invalidas = [c for c in filter_cols if c not in vec.columns]
    if columnas_invalidas:
        raise ValueError(
            f"Las siguientes columnas no existen en 'vec': {columnas_invalidas}. "
            f"Columnas disponibles: {list(vec.columns)}"
        )

    n_vectores = len(vec)

    # Visibilidad base: todos los traces visibles
    # Estructura: [traces_previos..., vector_1, vector_2, ..., vector_n]
    visibilidad_total = [True] * num_traces_previos + [True] * n_vectores

    # ── 2. Construir menús desplegables ───────────────────────────────────────
    dropdowns = []
    x_actual  = DROPDOWN_X_START

    for columna in filter_cols:
        valores_unicos = sorted(vec[columna].dropna().unique())

        # Botón "Todos": restaura visibilidad completa
        botones = [
            dict(
                label=f"Todos",
                method="update",
                args=[{"visible": visibilidad_total}],
            )
        ]

        # Un botón por cada valor único del filtro
        for valor in valores_unicos:
            # Las trazas previas siempre visibles; los vectores solo si coinciden
            mascara_vectores = vec[columna].eq(valor).tolist()
            mascara_total    = [True] * num_traces_previos + mascara_vectores

            botones.append(
                dict(
                    label=str(valor),
                    method="update",
                    args=[{"visible": mascara_total}],
                )
            )

        dropdowns.append(
            dict(
                buttons=botones,
                direction="down",
                showactive=True,
                x=x_actual,
                y=DROPDOWN_Y,
                xanchor="left",
                yanchor="top",
                pad={"r": 10, "t": 10},
                active=0,
                bgcolor="white",
                bordercolor="#cccccc",
                font=dict(size=12),
            )
        )

        x_actual += DROPDOWN_X_STEP    # separar menús horizontalmente

    # ── 3. Aplicar layout con los menús ───────────────────────────────────────
    # Se amplía el margen superior para que los dropdowns no tapen el gráfico.
    fig.update_layout(
        updatemenus=dropdowns,
        margin=dict(t=120),            # espacio para los menús
    )

    logger.debug(
        "Filtros agregados: %d menús desplegables para columnas %s.",
        len(dropdowns),
        filter_cols,
    )

    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN 3 — EXPORTAR A HTML RESPONSIVO (NUEVA)
# ══════════════════════════════════════════════════════════════════════════════

def exportar_html_responsivo(
    fig: go.Figure,
    ruta_salida: str,
    ancho_figura: int   = 1100,
    alto_figura: int    = 620,
    titulo_html: str    = "Biplot Interactivo",
) -> None:
    """
    Exporta la figura Plotly a un archivo HTML con soporte responsivo.

    El HTML generado incluye un script que redimensiona el gráfico
    automáticamente según el ancho de la ventana del navegador,
    lo que soluciona el problema de visualización en móviles.

    Parameters
    ----------
    fig : go.Figure
        Figura Plotly a exportar.
    ruta_salida : str
        Ruta completa del archivo HTML de salida (ej. 'diagrams/biplot.html').
    ancho_figura : int
        Ancho base de la figura en píxeles (usado como referencia de escala).
    alto_figura : int
        Alto base de la figura en píxeles.
    titulo_html : str
        Título de la pestaña del navegador.

    Notes
    -----
    La estrategia de responsividad usa ``config={'responsive': True}`` de
    Plotly junto con ``autosize=True`` en el layout. Esto permite que el
    gráfico se adapte al contenedor HTML, que a su vez puede ser controlado
    con CSS en el sitio web que lo incluye vía iframe.

    Examples
    --------
    >>> exportar_html_responsivo(fig, 'diagrams/biplot_gci.html')
    """
    # Activar autosize para que Plotly respete el contenedor
    fig.update_layout(
        autosize=True,
        width=None,        # anular dimensión fija
        height=None,       # anular dimensión fija
    )

    # Configuración de Plotly: responsive=True instruye a Plotly.js
    # a redimensionar el SVG cuando cambia el tamaño del contenedor.
    config = {
        "responsive": True,
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": titulo_html.lower().replace(" ", "_"),
            "width": ancho_figura,
            "height": alto_figura,
            "scale": 2,            # alta resolución al descargar
        },
    }

    # Exportar con include_plotlyjs para que sea autónomo
    html_content = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn",    # CDN reduce el tamaño del archivo
        config=config,
        default_width="100%",      # ancho relativo al contenedor
        default_height="100%",
    )

    # Inyectar meta viewport y estilos base para responsividad móvil
    meta_viewport = (
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<style>\n'
        '  html, body { margin: 0; padding: 0; width: 100%; height: 100%; }\n'
        '  .plotly-graph-div { width: 100% !important; height: 100% !important; }\n'
        '</style>\n'
    )
    # Insertar justo después de <head>
    html_content = html_content.replace("<head>", f"<head>\n{meta_viewport}", 1)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info("Figura exportada en: %s", ruta_salida)


def exportar_figure_json(fig: go.Figure, filename: str) -> Path:
    """
    Configura el layout para compatibilidad con el frontend responsivo
    y exporta la figura a JSON.

    Args:
        fig:      Figura de Plotly ya construida.
        filename: Path del archivo de salida con extension .json.

    Returns:
        Path del archivo generado.
    """
    # autosize=True es FUNDAMENTAL: permite que Plotly.js ajuste el gráfico
    fig.update_layout(
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    output_path = Path(filename)
    fig.write_json(filename, pretty=False, remove_uids=False)
    print(f"✓ Exportado: {output_path}  ({output_path.stat().st_size / 1024:.1f} KB)")
    return output_path


import json

def inject_js_filters(
    fig: go.Figure,
    vec: pd.DataFrame,
    filter_columns: list[str],
    num_traces_previos: Optional[int] = 0,
    filepath:Optional[Path] = None,
    return_html:bool = False):
    """
    Inyecta filtros combinables vía JavaScript en una figura Plotly.

    Parameters
    ----------
    fig : go.Figure
    vec : pd.DataFrame
        DataFrame con columnas de filtrado.
    filter_columns : list[str]
    num_traces_previos : int
        Trazas que siempre permanecen visibles.
    """

    # Validación fuerte
    for col in filter_columns:
        if col not in vec.columns:
            raise ValueError(f"Columna '{col}' no existe en vec.")

    # Obtener valores únicos por filtro
    unique_values = {
        col: sorted(vec[col].dropna().sort_values().astype(str).unique().tolist())
        for col in filter_columns
    }

    unique_values_json = json.dumps(unique_values)
    print(f"Valores filtros: {unique_values_json}")
    js_code = f"""
            window.addEventListener("DOMContentLoaded", function() {{

                const graphDiv = document.querySelector(".plotly-graph-div");
                if (!graphDiv) {{
                    console.error("Plotly graph no encontrado");
                    return;
                }}
                const filters = {unique_values_json};

                let selected = {{}};

                // Crear contenedor
                const container = document.createElement("div");
                container.style.marginBottom = "20px";

                // Crear dropdowns dinámicamente
                Object.keys(filters).forEach(col => {{

                    selected[col] = null;

                    const label = document.createElement("label");
                    label.innerHTML = col + ": ";
                    label.style.marginRight = "8px";

                    const select = document.createElement("select");
                    select.style.marginRight = "20px";

                    const optAll = document.createElement("option");
                    optAll.value = "";
                    optAll.text = "Todos";
                    select.appendChild(optAll);

                    filters[col].forEach(val => {{
                        const opt = document.createElement("option");
                        opt.value = val;
                        opt.text = val;
                        select.appendChild(opt);
                    }});

                    select.addEventListener("change", function(e) {{
                        selected[col] = e.target.value || null;
                        applyFilters();
                    }});

                    container.appendChild(label);
                    container.appendChild(select);
                }});

                graphDiv.parentNode.insertBefore(container, graphDiv);

                function applyFilters() {{

                    const visibility = graphDiv.data.map((trace, i) => {{

                        if (i < {num_traces_previos}) return true;

                        if (!trace.meta) return true;

                        for (let key in selected) {{
                           if (
                                selected[key] !== null &&
                                String(trace.meta[key]) !== selected[key]
                            ){{
                                return false;
                            }}
                        }}

                        return true;
                    }});

                    Plotly.restyle(graphDiv, {{ visible: visibility }});
                }}

            }});
            """
    fig.add_layout_image(dict())  # hack para forzar render completo
    if not filepath:
        filepath = "output.html"

    if return_html:
        return fig.to_html(
            full_html=False,
            include_plotlyjs="cdn",
            post_script=js_code,
            )
    else:
        fig.write_html(
            filepath,
            include_plotlyjs="cdn",
            post_script=js_code,
            full_html=True,
            auto_open=False,
        )
        return fig

# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES INTERNAS
# ══════════════════════════════════════════════════════════════════════════════

def _nombre_eje(hj_biplot, axis_idx: int) -> str:
    """
    Genera el nombre de un eje incluyendo su varianza explicada.

    Parameters
    ----------
    hj_biplot : objeto con atributo ``explained_variance`` (array-like).
    axis_idx  : índice del eje (0-based).

    Returns
    -------
    str
        Cadena con formato 'Axis N (X.XX%)'.
    """
    varianza = hj_biplot.explained_variance[axis_idx]
    return f"Axis {axis_idx + 1} ({varianza:.2f}%)"
