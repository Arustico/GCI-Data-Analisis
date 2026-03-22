#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Renderiza el sitio Quarto y lo publica en GitHub Pages
#
# Uso:
#   ./deploy.sh              → renderiza y sube con mensaje automático
#   ./deploy.sh "mi mensaje" → renderiza y sube con mensaje personalizado
#
# Requisitos:
#   - Archivo .env en la misma carpeta con PORTFOLIO_DIR y GCI_SUBFOLDER
#   - quarto instalado y en el PATH
#   - git configurado con acceso al repositorio del portafolio
# =============================================================================

set -euo pipefail

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✔]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✘]${NC} $1"; exit 1; }

# ── Cargar .env ───────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="../.env" # está en la raiz

[ -f "$ENV_FILE" ] || error "No se encontró .env en $SCRIPT_DIR\n  revisar ubicación de .env"

# Cargar solo las variables definidas en .env, ignorando comentarios y líneas vacías
set -a   # exportar automáticamente todas las variables que se definan
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# ── Validar variables requeridas ──────────────────────────────────────────────
[ -n "${PORTFOLIO_DIR:-}" ] || error "PORTFOLIO_DIR no está definido en .env"
[ -n "${GCI_SUBFOLDER:-}" ] || error "GCI_SUBFOLDER no está definido en .env"

#COMMIT_MSG="${1:-"Actualiza análisis GCI: $(date '+%Y-%m-%d %H:%M')"}"
COMMIT_MSG="Actualización Website del Análisis GCI: $(date '+%Y-%m-%d %H:%M')"

# ── Verificaciones previas ────────────────────────────────────────────────────
info "Verificando requisitos..."
command -v quarto &>/dev/null || error "quarto no está instalado o no está en el PATH"
command -v git    &>/dev/null || error "git no está instalado"
command -v rsync  &>/dev/null || error "rsync no está instalado"

[ -f "$SCRIPT_DIR/_quarto.yml" ] || \
    error "No se encontró _quarto.yml. Ejecuta el script desde la raíz del proyecto."
[ -d "$PORTFOLIO_DIR" ] || \
    error "No se encontró el directorio del portafolio: $PORTFOLIO_DIR"
[ -d "$PORTFOLIO_DIR/.git" ] || \
    error "$PORTFOLIO_DIR no es un repositorio git"

# ── Paso 1: Renderizar ────────────────────────────────────────────────────────
info "Renderizando sitio Quarto..."
cd "$SCRIPT_DIR"
poetry run quarto render || error "poetry run quarto render falló. Revisa los errores arriba."
info "Sitio renderizado en _site/"

# ── Paso 2: Copiar a portafolio ───────────────────────────────────────────────
DEST="$PORTFOLIO_DIR/src/$GCI_SUBFOLDER" # se agrega src/ que es donde queremos copiar los archivos y desde ahi copiarlos a dist
info "Copiando archivos a $DEST ..."
mkdir -p "$DEST"
rsync -av --delete _site/ "$DEST/" || error "Error al copiar archivos."

# ── Paso 3: Commit y push ─────────────────────────────────────────────────────
info "Publicando en GitHub Pages..."
cd "$PORTFOLIO_DIR"

if git diff --quiet && git diff --staged --quiet; then
    warning "No hay cambios nuevos. Nada que publicar."
    exit 0
fi
info "Estado del Git..."
git status
info "Agregando cambios..."
git add .
git commit -m "$COMMIT_MSG"
git push || error "git push falló. Verifica tu conexión y permisos."

# ── Listo ─────────────────────────────────────────────────────────────────────
echo ""
info "¡Publicado exitosamente!"
info "URL: https://arustico.github.io/arielnunezsalinas.github.io/$GCI_SUBFOLDER/"
