# =============================================================================
# analisis_statis.R
# -----------------------------------------------------------------------------
# Análisis multivariado mediante el método STATIS (ade4)
# sobre índices de competitividad global del WEF (2014–2019).
#
# Estructura del script:
#   1. Librerías
#   2. Carga y preparación de datos
#   3. Construcción del K-table (ktab)
#   4. Ejecución de STATIS
#   5. Extracción de resultados
#   6. Visualizaciones
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# 1. LIBRERÍAS
#   - readxl: Lectura de archivos Excel
#   - ade4: STATIS y gráficos multivariados
#   - FactorMiner: Métodos de reducción de dimensión complementarios
# ─────────────────────────────────────────────────────────────────────────────

library(renv) # instalación en environment seguro
librerias <- c("readxl","ade4","FactoMineR")

for (lbr in librerias) {
  if (!require(lbr, character.only = TRUE)) {
    renv::install(lbr)
    library(lbr, character.only = TRUE)
  }else{
    library(lbr, character.only = TRUE)
  }
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. CARGA Y PREPARACIÓN DE DATOS
# ─────────────────────────────────────────────────────────────────────────────

# 2.1 Directorio de trabajo y lectura del Excel

readRenviron("../.env")

FOLDER_PRJ <- Sys.getenv(c("FOLDER_PRJCT"))
FOLDER_PROCESSED <- Sys.getenv(c("FOLDER_PROCESSED"))
setwd(FOLDER_PRJ)

filename <- file.path(FOLDER_PROCESSED,"data_pivoted_2.csv") # países como índices
#filename <- file.path(FOLDER_PROCESSED,"data_pivoted.csv")    # pilares cómo índices
datos <- read.csv(filename)
datos <- as.data.frame(datos)

# 2.2 La columna PILAR pasa a ser el identificador de fila
#     (cada fila = combinación pilar-año, e.g. "1-2014")
rownames(datos) <- datos$PILAR
datos$PILAR     <- NULL

# 2.3 Conservar solo columnas numéricas (países)
datos <- datos[, sapply(datos, is.numeric)]

# 2.4 Eliminar columnas y filas completamente vacías (todo NA)
datos <- datos[, colSums(is.na(datos))  < nrow(datos)]   # columnas
datos <- datos[rowSums(is.na(datos))    < ncol(datos), ]  # filas

# 2.5 Imputar valores faltantes restantes con la media de cada columna
#     Esto preserva la escala de los datos y evita pérdida de filas/columnas.
for (j in seq_len(ncol(datos))) {
  idx_na <- is.na(datos[, j])
  if (any(idx_na)) {
    datos[idx_na, j] <- mean(datos[, j], na.rm = TRUE)
  }
}

# 2.6 Eliminar columnas de varianza cero (no aportan información al análisis)
datos <- datos[, apply(datos, 2, sd) > 0]

# 2.7 Recuperar metadatos desde los nombres de fila
#     Formato esperado: "PILAR-AÑO" → e.g. "3-2017"
nombres_filas <- rownames(datos)
pilar <- sub("-.*", "", nombres_filas)   # parte antes del guión
anio  <- sub(".*-", "", nombres_filas)   # parte después del guión


# ─────────────────────────────────────────────────────────────────────────────
# 3. CONSTRUCCIÓN DEL K-TABLE (ktab)
# ─────────────────────────────────────────────────────────────────────────────
#
# STATIS opera sobre un K-table: una lista de K matrices (una por "tabla"),
# todas con las mismas filas (pilares × año) pero con columnas propias.
# Aquí cada tabla corresponde a un país (columna del data.frame).
#
# Estructura resultante:
#   - Filas    : combinaciones pilar-año (unidad de observación)
#   - Columnas : una por país (variable de interés)
#   - Bloques  : uno por país (k = número de países)

tablas_por_pais <- lapply(colnames(datos), function(pais) {
  data.frame(valor = datos[[pais]], row.names = rownames(datos))
})
names(tablas_por_pais) <- colnames(datos)

ktab_paises <- ktab.list.df(
  obj      = tablas_por_pais,
  tabnames = names(tablas_por_pais),
  rownames = rownames(datos)
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. EJECUCIÓN DE STATIS
# ─────────────────────────────────────────────────────────────────────────────
#
# STATIS busca una "estructura de compromiso" (compromise) que resume de forma
# óptima la información común a todas las tablas. El coeficiente RV mide la
# similitud entre pares de tablas (varía entre 0 y 1).
#
# Parámetros:
#   scannf = FALSE  → no pedir número de ejes de forma interactiva
#   nf = 2          → retener 2 factores principales (plano factorial)

res.statis <- statis(ktab_paises, scannf = FALSE, nf = 2)

# Diagnóstico rápido del objeto resultado
# plot(res.statis)   # gráficos por defecto de ade4 (opcional)


# ─────────────────────────────────────────────────────────────────────────────
# 5. EXTRACCIÓN DE RESULTADOS CLAVE
# ─────────────────────────────────────────────────────────────────────────────

# 5.1 Matriz RV: similitud entre tablas (países)
#     Valores cercanos a 1 → estructuras muy similares entre países
rv_matrix <- res.statis$RV

# 5.2 Coordenadas de las tablas en el espacio RV
#     Permite identificar agrupamientos de países con estructuras similares
coord_paises_rv <- res.statis$RV.coo

# 5.3 Peso de cada tabla en el compromiso
#     Tablas con mayor peso dominan la estructura común
peso_paises <- res.statis$RV.tabw
names(peso_paises) <- res.statis$tab.names

# 5.4 Coordenadas de las observaciones en el compromiso
#     (combinaciones pilar-año proyectadas en el plano del compromiso)
coord_obs_compromiso <- res.statis$C.li

# 5.5 Coordenadas de las variables en el compromiso
#     (pilares x año proyectados como vectores)
coord_vars_compromiso <- res.statis$C.Co

# Imprimir resumen en consola
cat("\n===== MATRIZ RV (primeras 5×5) =====\n")
print(round(rv_matrix[1:min(5, nrow(rv_matrix)), 1:min(5, ncol(rv_matrix))], 3))

cat("\n===== PESO DE CADA TABLA EN EL COMPROMISO =====\n")
print(round(sort(peso_paises, decreasing = TRUE), 4))


# ─────────────────────────────────────────────────────────────────────────────
# 6. VISUALIZACIONES
# ─────────────────────────────────────────────────────────────────────────────

# ── 6.1 Mapa RV: similitud entre países ──────────────────────────────────────
#        Posición en el plano refleja qué tan similares son sus estructuras
#        de competitividad a través de los años analizados.

s.label(
  coord_paises_rv,
  clab = 1,
  sub  = "Mapa RV – Similitud entre Países (STATIS)",
  csub = 1.5
)


# ── 6.2 Importancia de cada país en el compromiso ────────────────────────────
#        Un mayor peso indica que ese país tiene una estructura más "central"
#        (más representativa de la tendencia común).

barplot(
  sort(peso_paises, decreasing = TRUE),
  las  = 2,
  main = "Peso de cada país en el compromiso STATIS",
  ylab = "Peso",
  col  = "steelblue"
)


# ── 6.3 Observaciones (pilar-año) en el plano del compromiso ─────────────────

s.label(
  coord_obs_compromiso,
  clab = 0.7,
  sub  = "Compromiso STATIS – Observaciones (Pilar × Año)",
  csub = 1.5
)


# ── 6.4 Variables (pilares × año) en el plano del compromiso ─────────────────

s.label(
  coord_vars_compromiso,
  clab = 0.6,
  sub  = "Compromiso STATIS – Variables (Pilares × Año)",
  csub = 1.5
)


# ── 6.5 Mapa RV destacando a Chile ───────────────────────────────────────────
#
# Objetivo: identificar visualmente la posición relativa de Chile
# respecto al resto de países en el espacio de similitud estructural.
#
# ⚠️  Ajustar `codigo_chile` si el identificador en los datos es distinto
#     (e.g., "Chile", "chile", "CHL").

if (grepl("data_pivoted_2.csv", filename, fixed=TRUE)){  
  codigo_chile <- "CHL"
  
  idx_chile <- which(rownames(coord_paises_rv) == codigo_chile)
  idx_otros <- setdiff(seq_len(nrow(coord_paises_rv)), idx_chile)
  
  # Verificar que Chile existe en los datos antes de graficar
  if (length(idx_chile) == 0) {
    warning(
      "El código '", codigo_chile, "' no se encontró en los datos. ",
      "Códigos disponibles: ",
      paste(rownames(coord_paises_rv), collapse = ", ")
    )
  } else {
  
    plot(
      coord_paises_rv[, 1], coord_paises_rv[, 2],
      type = "n",
      xlab = "Eje 1 (compromiso)",
      ylab = "Eje 2 (compromiso)",
      main = "Mapa RV – Países (Chile destacado)"
    )
  
    # Resto de países en gris
    points(
      coord_paises_rv[idx_otros, 1],
      coord_paises_rv[idx_otros, 2],
      pch = 16, col = "grey70", cex = 0.9
    )
    text(
      coord_paises_rv[idx_otros, 1],
      coord_paises_rv[idx_otros, 2],
      labels = rownames(coord_paises_rv)[idx_otros],
      pos = 3, col = "grey50", cex = 0.6
    )
  
    # Chile en rojo
    points(
      coord_paises_rv[idx_chile, 1],
      coord_paises_rv[idx_chile, 2],
      pch = 19, col = "red", cex = 1.8
    )
    text(
      coord_paises_rv[idx_chile, 1],
      coord_paises_rv[idx_chile, 2],
      labels = codigo_chile,
      pos = 3, col = "red", cex = 1.0, font = 2
    )
  }
}

# ── 6.6 Validaciones ───────────────────────────────────────────
# La matriz RV (entre tablas) se extraen los autovalores.
# La matriz de compromiso se justifica porque el primer autovalor es mucho más 
# grande que los demás, conservando la mayória de la variabilidad de la data
# y justificando que exista una interestructura coherente. 

# Autovalores
eig_rv <- res.statis$C.eig # autovalores
prop_var <- eig_rv / sum(eig_rv) # proporción explicada
round(prop_var,4)

barplot(
  prop_var,
  main = "Autovalores - Interestructura (Matriz RV)",
  ylab = "Proporción de varianza",
  xlab = "Ejes",
  col = "steelblue"
  )

# cos2
coord <- res.statis$C.li

# Distancia total al origen en el espacio completo
dist2_total <- rowSums(coord^2)

# Cos2 para eje 1 y 2
cos2_eje1 <- coord[,1]^2 / dist2_total
cos2_eje2 <- coord[,2]^2 / dist2_total
cos2_total <- cos2_eje1 + cos2_eje2


hist(cos2_total,
     main="Distribución Cos² – Observaciones",
     col="steelblue")


pie(peso_paises,
    main="Contribución de cada país al compromiso")


# Chequeo de diferencias estructurales en los pilares
scores_eje1 <- res.statis$C.li[,1]
compromise <- res.statis$C.li
# correlacion simple
cor_pilares_eje1 <- cor(compromise, scores_eje1)
round(cor_pilares_eje1, 3)


cols_pre  <- grep("2014|2015|2016|2017", colnames(compromise))
cols_post <- grep("2018|2019", colnames(compromise))

library(tidyr)
library(dplyr)

df <- as.data.frame(res.statis$C.li)
df$Pilar_Año <- rownames(df)

df <- df %>%
  separate(Pilar_Año, into = c("Pilar","Año"), sep = "-")

df$Año <- as.numeric(df$Año)

resumen <- df %>%
  group_by(Pilar) %>%
  summarise(
    pre  = mean(C1[Año <= 2017]),
    post = mean(C1[Año >= 2018])
  ) %>%
  mutate(
    delta_abs = abs(post - pre),
    delta_pct = delta_abs / abs(pre),
    delta_pct_perc = delta_pct * 100
  )

resumen <- resumen[order(-resumen$delta_pct),]

write.csv2(resumen, "./cache/cambios_pilares_compromiso.csv")
# res.statis$C.li -> correlación con el eje 1 y 2 de compromiso de cada pilar
# Pilar     2014      2019        menciones
#------------------------------------------------------------------------
#  3   -0.2319109 -0.3096154    -0.2001295 (2016)
# 10   -0.3448419 -0.1450796
# 7    -0.3173680 -0.3210835
