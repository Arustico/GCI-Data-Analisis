"""
Modulo con funciones útiles para el análisis con biplot
─────────────────────────────────
    1. Normalización numérica de los valores/puntajes obtenidos por cada país
    2. Normaliza strings

"""
#─────────────────────────────────
# Librerías
#─────────────────────────────────
import unicodedata
import re
from pathlib import Path
import os
from dotenv import load_dotenv
import logging

import pandas as pd
import numpy as np
import matplotlib.pyplot as pl
import seaborn as sns

import plotly.express as px
import plotly.graph_objects as go
from pybiplots import *

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


def crear_biplot_interactivo(HJ: HJ_Biplot.fit,
                             groups=None, text_label=None,
                             axis_x=0, axis_y=1, arrow_color='gray',
                             arrow_head=2, marker_size=12, title=None) -> tuple(px.figure,np.array):
    """
    Crea un biplot interactivo. HJ puede ser también GH, JK.
    """

    # --- Datos base ---
    X = HJ.X
    ind = HJ.row_coordinates.reset_index()  # corresponden a los individuos
    vec = HJ.column_coordinates.copy()      # corresponden a los vectores

    # --- Nombres de ejes ---
    axis1_name = f'Axis {axis_x + 1} ({HJ.explained_variance[axis_x]:.2f}%)'
    axis2_name = f'Axis {axis_y + 1} ({HJ.explained_variance[axis_y]:.2f}%)'
    ind[axis1_name] = ind[f'Axis {axis_x + 1}']
    ind[axis2_name] = ind[f'Axis {axis_y + 1}']

  # --- Gráfico de individuos ---
    fig = px.scatter(
        ind, x=axis1_name, y=axis2_name,
        color=groups, text=text_label,
        title=title or "Biplot Interactivo"
    )
    fig.update_traces(textposition="bottom right", marker_size=marker_size)

    # --- Añadir autovectores ---
    for i in range(len(vec)):
        fig.add_trace(
        go.Scatter(
                x=[0, vec.iloc[i, axis_x]],
                y=[0, vec.iloc[i, axis_y]],
                mode='lines+text',
                line=dict(color=arrow_color, width=2),
                marker=dict(size=20,symbol="arrow-bar-up", angleref="previous",color="black"),
                text=[None, vec.index[i]],
                textposition="top center",
                showlegend=False,
                name=vec.index[i],
                hoverinfo='text',
                hovertext=f"{vec.index[i]}"
            )
        )

    # --- Layout base ---
    fig.update_layout(
        xaxis_title=axis1_name,
        yaxis_title=axis2_name,
        template="plotly_white",
        title_x=0.5
    )
    return fig, vec


def agregar_filtros_biplot(fig: px.Figure,
                           vec: np.array,
                           filter_cols: list,
                           num_previous_filters: int = 3) -> px.Figure:
    """
    Agrega filtros a la figura interactiva dash
    """
    n_vectores = len(vec)
    # muestra los elementos (false no los muestra)
    base_visibility = [True] + [True] * n_vectores  # puntos + vectores

    dropdowns = []
    x_pos = 0.15

    for filtro in filter_cols:
        if filtro not in vec.columns:
            logging.error(f"Error filtro: {filtro}, no existe columna")
            return None
        # valores únicos del filtro
        valores = sorted(vec[filtro].dropna().unique())
        buttons = [
        dict(
                label=f"{filtro}: Todos",
                method="update",
                args=[{"visible": base_visibility}]
            )
        ]
        for val in valores:
            visible_mask = num_previous_filters * [True] + vec[filtro].eq(val).tolist()
            buttons.append(
                dict(
                label=str(val),
                method="update",
                args=[{"visible": visible_mask}]
            ))
        #return val,visible_mask

        dropdowns.append(dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=x_pos,
            y=1.15,
            xanchor="left",
            yanchor="top",
            pad={"r": 10, "t": 10},
            active=0,
            name=filtro.capitalize()
        ))
        x_pos += 0.15  # separar menús visualmente

    fig.update_layout(
        updatemenus=dropdowns,
        margin=dict(t=100)
    )

    return fig
