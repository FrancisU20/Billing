#!/usr/bin/env bash
# Construye los dos Lambda Layers con dependencias Python para Linux.
# Ejecutar antes de CDK deploy local: make build-lambda-deps
#
# En CI (GitHub Actions = Linux) se ejecuta automáticamente en el workflow.
# En Mac se instalan los wheels del sistema actual — los paquetes puros funcionan,
# pero C extensions (psycopg, lxml, etc.) necesitan el deploy de CI para estar correcto.
#
# Para un deploy de producción siempre usar CI, no el script local.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INFRA="$ROOT/infra/lambda_layer"
BACKEND="$ROOT/backend"

echo "Limpiando layers anteriores..."
rm -rf "$INFRA/core/python" "$INFRA/batch/python"
mkdir -p "$INFRA/core/python" "$INFRA/batch/python"

echo "Instalando core layer (~130MB)..."
pip install -r "$BACKEND/requirements-layer-core.txt" \
  --target "$INFRA/core/python" \
  --quiet

echo "Instalando batch layer (~69MB)..."
pip install -r "$BACKEND/requirements-layer-batch.txt" \
  --target "$INFRA/batch/python" \
  --quiet

echo "Limpiando archivos innecesarios..."
for DIR in "$INFRA/core/python" "$INFRA/batch/python"; do
  find "$DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find "$DIR" -name "*.pyc" -delete 2>/dev/null || true
  find "$DIR" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
  find "$DIR" -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
  find "$DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
done

echo ""
echo "Core layer: $(du -sh "$INFRA/core/python" | cut -f1)"
echo "Batch layer: $(du -sh "$INFRA/batch/python" | cut -f1)"
echo ""
echo "Lambda Layers listos para CDK deploy."
