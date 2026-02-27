# Coherencia, Estabilidad y Discontinuidades del Índice de Competitividad Global (GCI)

Un estudio multivariante para el período 2014–2019 

Trabajo Final de Magíster
Universidad Bernardo O’Higgins
Santiago, Chile – 2025

Autor: Ariel Ignacio Núñez Salinas

## Descripción del Proyecto

Este proyecto analiza la estructura temporal de los 12 pilares del Índice de Competitividad Global (GCI) publicado por el World Economic Forum durante el período 2014–2019. Existieron 2 metodologías:

> GCI 3.0 → usado hasta 2017
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

## Objetivos de análisis

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
            (2014-2019)]
    normalization[Normalización 0-100]
    getAverage[Cálculo de promedio por Pilar]
    getMatriz[Matrices País x Pilar x Año]
    makeAnalisis[Análisis Multivariante]
    indexRaw --> normalization
    normalization --> getAverage --> getMatriz
    getMatriz --> makeAnalisis
```

