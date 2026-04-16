#!/bin/bash
# 下载默认 VRoid 女性素体模型到前端 public 目录
# 模型来源：hinzka/52blendshapes-for-VRoid-face (免费，含 52 BlendShapes)

set -e

URL="https://raw.githubusercontent.com/hinzka/52blendshapes-for-VRoid-face/main/VRoid_V110_Female_v1.1.3.vrm"
OUT_DIR="$(cd "$(dirname "$0")/../frontend/public/models" && pwd)"
OUT_FILE="$OUT_DIR/vroid_female.vrm"

mkdir -p "$OUT_DIR"

echo "Downloading VRoid female base model..."
echo "  From: $URL"
echo "  To:   $OUT_FILE"

curl -L -o "$OUT_FILE" "$URL"

echo "Done. ($OUT_FILE)"
