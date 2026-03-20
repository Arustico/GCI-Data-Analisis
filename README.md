# Coherencia, Estabilidad y Discontinuidades del Índice de Competitividad Global (GCI)

Un estudio multivariante para el período 2014–2019 

Trabajo Final de Magíster
Universidad Bernardo O’Higgins
Santiago, Chile – 2025

Autor: Ariel Ignacio Núñez Salinas
------------------------------------------------------------------------

## 1. Descripción del Proyecto

Este proyecto analiza la estructura temporal de los 12 pilares del Índice de Competitividad Global (GCI) publicado por el World Economic Forum durante el período 2014–2019. Existieron 2 metodologías:

> GCI 3.0 → usado hasta 2017
>
> GCI 4.0 → introducida en 2018

Esta transisción modificó

- Definición de indicadores
- Normalización de la escala (1–7 → 0–100)
- Composición de pilares
- Logica de agrupamiento

El proyecto aborda el siguiente problema:
    
> Es el GCI comparable estructuralmente a lo largo del periodo 2014-2019, o la transición metodológica genera una discontinuidad estadística detectable?
    
Para abordar esto, se implementa un enfoque multivariante combinando:

- Análisis Descriptivo
- Agrupamiento Jerárquico
- PCA
- HJ-Biplot
- STATIS

El objetivo no es solo replicar rankings, sino evaluar coherencia estructural, estabilidad y discontinuidades internas del índice.
------------------------------------------------------------------------

## 2. Objetivos de análisis

1. Evaluar la consistencia temporal de los pilares.
2. Detectar pilares sensibles a cambios metodológicos o shocks económicos.
3. Clasificar países según perfiles competitivos.
4. Analizar estructura de correlaciones entre pilares.
5. Identificar rupturas estructurales entre GCI 3.0 y GCI 4.0.

## Metodología General

El pipeline sigue esta estructura lógica:

```mermaid
flowchart LR
    indexRaw[Indicadores Raw
             2014 - 2019]
    normalization[Normalización 0-100]
    getAverage[Cálculo de promedio por Pilar]
    getMatriz[Matrices País x Pilar x Año]
    makeAnalisis[Análisis Multivariante]
    indexRaw --> normalization
    normalization --> getAverage --> getMatriz
    getMatriz --> makeAnalisis
```
------------------------------------------------------------------------

## 3. Datos

**Fuente**: Reportes (pdf) del Foro Económico Mundial (2014 - 2019)

Características de la Data:
- 55 países
- 12 pilares
- Periodo 2014–2019

**N° de Indicadores por año**:
- 109 (2014–2017)
- 92 (2018)
- 98 (2019)

**Datos nulos < 4%**

**Principal limitante**:
>Sólo 5 indicadores permanecen constante a lo largo de los 6 años. Una comparación a nivel de indicadores es por lo tanto inestable estadísticamente.

------------------------------------------------------------------------

## 4. Principales desiciones

### 4.1 Normalización unificada (0–100)

**Problema**
El problema de las escalas por metodología:
> GCI 3.0: escala 1–7
>
> GCI 4.0: escala 0–100

**Desición**
> Todos los indicadores seran re-escalados utilizando la normalización 0 - 100 de la metodología GCI 4.0.

Esto asegura la homogenidad de la métrica. Previene variaciones artificiales de inflación, preserva la monotocidad y permite una comparación estructural a nivel de pilares.


### 4.2 Nivel de Agregación: Pillar > Indicador

**Problema**
>Las definiciones de los indicadores cambiaron a lo largo de los años, es un problema poder comparar a nivel de indicadores.

**Decision**

Cálculo de los puntajes (scores) a nivel de pilares, Se hizo mediante:

$$
    P_{k,j} = \frac{1}{n_j}\sum_{i \in j}{sc_{i,k}}
$$

Donde:
- $k$ es el país
- $j$ es el pilar
- $sc_{i,k}$ es el score del indicador normalizado

Esto reduce la inestabilidad dimensional, mejora la robustes de las técnicas PCA y STATIS y reduce el ruido de la relocalización de los indicadores.


### 4.3 Estrategia para datos nulos o perdidos

Pérdida de valores < 4%

**Decisión**
No se necesitaron imputaciones complejas.

De esta forma se mantuvo la data estable para análisis de clustering y PCA. Se evitó bias por inyección.

### 4.4 Enriquecimiento de Categorías

Se introdujeron 2 nuevas categorías: 
- **BLOK**: Región geográfica
- **ORG**: Organización mundial
    - OECD
    - BRICS

>Esto permite validar la coherencia del clustering, examinar la heterogeneidad de la estructura de los datos y permite dar interpretatibilidad a los resultados.

------------------------------------------------------------------------
## 5. Framework de Análisis
### 5.1 Análisis Exploratorio Descriptivo (EDA)

- Distribución de los indicadores respecto a lo que representan para cada pilar.
- Diagnóstico de valores perdidos
- Matriz de correlaciones entre los pilares
- Evolución temporal de los puntajes

### 5.2 Agrupamiento Jerárquico
-   Distance: Euclidean
-   Linkage: Ward's method
-   Validation: Cophenetic correlation coefficient

Distancia euclediana:
$$
    d(x,y) &= {\left\Vert{x−y}\right\Vert}^{2}\\
$$

**Resultado**: Clara seperación entre 2014--2017 y 2018--2019.


### 5.2 Principal Component Analysis (PCA)

-   PC1 ≈ 80% varianza explicada
-   PC2 ≈ 5%

El componente PC1 separa economías emergentes vs economías desarrolladas


### 5.3 HJ-Biplot

Basado en la Descomposición de valores singulares (SVD).\
Permite la representación simiultánea de los países (sujetos) y los pilares-años (variables)

>Principal hallazgo: Rotaciones estructurales en pilares 3 y 10 durante 2016 y 2018.

### 5.4 STATIS (Multi-table Analysis)

Cada año es tratada como una tabla independiente.\
Se utilizaron coeficientes RV para medir similitud a lo largo de las matrices anuales. 

> Hallazgos:
    > Fuerte coherencia entre 2014-2017.
    > Estructura distinta en 2018 - 2019.
    > Se confirma la discontuinidad metodológica.

------------------------------------------------------------------------

## 6. Principales hallazgos

1.  Estabilidad estructural dentro de los periodos metodológicos homogéneos.
2.  Clara discontinuidad estructural entre GCI 3.0 y GCI 4.0.
3.  Pilares 3,7 y 10 fueron más suceptibles a los cambios metodológicos y de diseño.
4.  Economías desrrolladas muestran menor volatilidad estructural.
5.  Las geometrías multivariantes entregan mayor información que la posición del ranking.

------------------------------------------------------------------------

## 7. Esctructura del trabajo
La estructura del proyecto se divide en 3 partes principales. Una parte es la ```data```, otra son los ```notebooks``` de análisis exploratorios y de testeo y otro corresponde al ```website```, que muestra los resultados de forma íntegra y lúdica. 

```
├── data
│   ├── processed
│   │   ├── bd_diccionario_indices.csv
│   │   ├── bd_indices_wef.csv
│   │   ├── data_pivoted_2.csv
│   │   └── data_pivoted.csv
│   └── raw
│       ├── bd_paises_info.csv
│       ├── pdf
│       ├── puntajes_paises_1.xlsx
│       └── puntajes_paises_2.xlsx
├── notebooks
│   ├── analisis_gci_py.qmd
│   ├── analisis_gci_r.qmd
│   └── analisis_indices_wef.ipynb
├── poetry.lock
├── pyproject.toml
├── README.md
├── renv/
├── renv.lock
├── reportes
│   ├── figures/
│   ├── tables/
│   ├── Presentación TFM.pdf
│   └── TMF_AN_MAMB_V1.3.pdf
├── src
│   ├── analisis_statis.R
│   ├── biplots_utils.py
│   ├── data_transformation.py
│   ├── extraction_index.py
│   ├── pybiplots
│   │   ├── GH_Biplot.py
│   │   ├── HJ_Biplot.py
│   │   ├── __init__.py
│   │   └── JK_Biplot.py
│   └── setup_r.sh
└── website
    ├── biplot.qmd
    ├── deploy.sh
    ├── eda.qmd
    ├── index.qmd
    ├── _quarto.yml
    ├── _site/
    ├── statis.qmd
    └── style.css
```

------------------------------------------------------------------------

## 8. Reproducibilidad
### Environments

- renv
- poetry

### Dependencias de Python

-   pandas
-   numpy
-   scipy
-   scikit-learn
-   seaborn
-   plotly

### Dependencias de R

-   ade4
-   FactoMineR
-   ggplot2

### Dependencias para website

- quarto 

------------------------------------------------------------------------

## 9. Consideraciones metodológicas

Los valores de GCI son comparables solo dentro de los periodos por separado:

-   2014--2017\
-   2018--2019

Una comparación directa a lo largo del cambio metodológico, es estadísticamente inválida sin ajustes estructurales.

## Fuentes

- Farris, J. S. (1969). On the Cophenetic Correlation Coefficient. *Systematic Zoology*, 18, 279. [DOI](https://doi.org/10.2307/2412324)
- Ferreira, E., Macedo, P., Fernandes, E., & Coelho, M.C. (2023). A combined framework of Biplots and Machine Learning for real-world driving volatility. *Sustainable Cities and Society*, 99, 104945. [DOI](https://doi.org/10.1016/j.scs.2023.104945)
- Galindo Villardón, M.P. (1986). Una alternativa de representación simultánea: HJ-Biplot. *Questiio*, 10, 13–23.
- Olczyk, M., Kuc-Czarnecka, M., & Saltelli, A. (2022). Changes in the GCI 4.0 Methodology. *Journal of Competitiveness*, 14, 118–135. [DOI](https://doi.org/10.7441/joc.2022.01.07)
- Raschka, S., & Mirjalili, V. (2017). *Python Machine Learning*. Packt Publishing.
- Toledo-San-Martín, Á., Ruff, C., & Vicente-Galindo, P. (2025). A multivariate framework for measuring international mobility in tertiary education. *Neutrosophic Sets and Systems*, 89, 333–356.
- Torres-Cubilla, C. (2020). *PyBiplots*. GitHub. [Repositorio](https://github.com/carlostorrescubila/PyBiplots)
- WEF (2015–2019). *The Global Competitiveness Report* (ediciones 2014-15 a 2019). World Economic Forum. [www.weforum.org/gcr](https://www.weforum.org/gcr)


