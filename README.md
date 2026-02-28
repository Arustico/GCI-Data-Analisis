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

Esto permite validar la coherencia del clustering, examinar la heterogeneidad de la estructura de los datos y permite dar interpretatibilidad a los resultados.
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

-   PC1 ≈ 80% variance explained
-   PC2 ≈ 5%

PC1 separates developed vs emerging economies.



### 5.3 HJ-Biplot

Based on Singular Value Decomposition (SVD).\
Allows simultaneous representation of countries and pillar-year
variables.

Key Finding: Structural rotations in pillars 3 and 10 during 2016 and
2018.


### 5.4 STATIS (Multi-table Analysis)

Each year treated as an independent table.\
RV coefficient used to measure similarity across yearly matrices.

Findings:

-   Strong coherence within 2014--2017.
-   Distinct structure in 2018--2019.
-   Methodological discontinuity confirmed.

------------------------------------------------------------------------

## 6. Main Findings

1.  Structural stability within homogeneous methodological periods.
2.  Clear structural break between GCI 3.0 and GCI 4.0.
3.  Pillars 3, 7, and 10 most sensitive to redesign.
4.  Developed economies show lower structural volatility.
5.  Multivariate geometry more informative than ranking positions.

------------------------------------------------------------------------

## 7. Repository Structure

    ├── data/
    ├── notebooks/
    ├── src/
    ├── figures/
    ├── README.md

------------------------------------------------------------------------

## 8. Reproducibilidad

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

------------------------------------------------------------------------

## 9. Consideraciones metodológicas

Los valores de GCI son comparables solo dentro de los periodos por separado:

-   2014--2017\
-   2018--2019

Una comparación directa a lo largo del cambio metodológico, es estadísticamente inválida sin ajustes estructurales.



