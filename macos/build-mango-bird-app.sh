#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"
APP_DIR="$DIST_DIR/mango-bird.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
MANGO_RESOURCES_DIR="$RESOURCES_DIR/MangoBird"
MODULE_CACHE_DIR="$PROJECT_DIR/.build/module-cache"

mkdir -p "$MACOS_DIR" "$MANGO_RESOURCES_DIR" "$MODULE_CACHE_DIR"

CLANG_MODULE_CACHE_PATH="$MODULE_CACHE_DIR" xcrun swiftc "$SCRIPT_DIR/MangoBirdApp.swift" \
  -framework Cocoa \
  -framework WebKit \
  -o "$MACOS_DIR/MangoBird"

cp "$SCRIPT_DIR/Info.plist" "$CONTENTS_DIR/Info.plist"
cp "$SCRIPT_DIR/MangoBird.icns" "$RESOURCES_DIR/MangoBird.icns"

cp "$PROJECT_DIR/mango-bird.html" "$MANGO_RESOURCES_DIR/"
cp "$PROJECT_DIR/mango-bird-server.py" "$MANGO_RESOURCES_DIR/"
cp "$PROJECT_DIR/time_parser.py" "$MANGO_RESOURCES_DIR/"
cp -R "$PROJECT_DIR/assets" "$MANGO_RESOURCES_DIR/"
cp -R "$PROJECT_DIR/new2" "$MANGO_RESOURCES_DIR/"

cat > "$MANGO_RESOURCES_DIR/.env.example" <<'ENV'
# Copy this file to ~/Library/Application Support/Mango Bird/.env.
# Supported providers: deepseek, glm.
MANGO_AI_PROVIDER=deepseek
MANGO_AI_API_KEY=sk-your-own-api-key
ENV

echo "Built: $APP_DIR"
