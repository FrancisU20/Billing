#!/usr/bin/env bash
# Construye el Lambda Layer con dependencias Python para Linux arm64 (Graviton2).
# Compatible con Mac arm64 (M-series), Linux arm64 y CI — sin Docker requerido.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INFRA="$ROOT/infra/lambda_layer"
BACKEND="$ROOT/backend"

echo "Limpiando layer anterior..."
rm -rf "$INFRA/core/python"
mkdir -p "$INFRA/core/python"

echo "Instalando core layer..."
pip install \
  --platform manylinux2014_aarch64 \
  --python-version 3.12 \
  --implementation cp \
  --only-binary=:all: \
  --upgrade --quiet \
  -r "$BACKEND/requirements-layer-core.txt" \
  --target "$INFRA/core/python"

echo ""
echo "Core layer: $(du -sh "$INFRA/core/python" | cut -f1)"
echo ""
echo "Lambda Layer listo para CDK deploy."
