#!/bin/bash

echo "Obteniendo entorno de Poetry..."
VENV_PATH=$(poetry env info --path)

if [ -z "$VENV_PATH" ]; then
  echo "No se encontró entorno Poetry. Ejecuta 'poetry install' primero."
  exit 1
fi

echo "Entorno encontrado: $VENV_PATH"

echo "Configurando reticulate en R..."

Rscript - <<EOF
if (!requireNamespace("reticulate", quietly = TRUE)) {
  install.packages("reticulate", repos="https://cloud.r-project.org")
}

library(reticulate)
use_virtualenv("$VENV_PATH", required = TRUE)

cat("R configurado con reticulate correctamente\n")

cat("Estableciendo el entorno actual por default\n")
writeLines(
  sprintf('RETICULATE_PYTHON="%s"', "$VENV_PATH"),
  ".Renviron"
)
cat("Listo\n")
EOF

echo "Proceso terminado."


