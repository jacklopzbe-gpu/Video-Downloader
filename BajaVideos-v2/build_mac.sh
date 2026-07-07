#!/bin/bash
# Compilar BajaVideos.app en una Mac (alternativa a GitHub Actions).
# Uso: doble clic no funciona; abre Terminal, arrastra este archivo y Enter.
set -e
cd "$(dirname "$0")"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller pillow

# Icono .icns
rm -rf icon.iconset assets/icon.icns
mkdir icon.iconset
for s in 16 32 64 128 256 512; do
  sips -z $s $s assets/icon.png --out icon.iconset/icon_${s}x${s}.png >/dev/null
  sips -z $((s*2)) $((s*2)) assets/icon.png --out icon.iconset/icon_${s}x${s}@2x.png >/dev/null
done
iconutil -c icns icon.iconset -o assets/icon.icns
rm -rf icon.iconset

pyinstaller --noconfirm --windowed \
  --name "BajaVideos" \
  --icon assets/icon.icns \
  --collect-all customtkinter \
  --collect-all imageio_ffmpeg \
  --collect-all yt_dlp \
  --collect-all telegram \
  app.py

codesign --force --deep -s - "dist/BajaVideos.app"

echo ""
echo "✅ Listo: dist/BajaVideos.app"
echo "   Para compartirla, comprímela así (conserva permisos):"
echo "   ditto -c -k --keepParent dist/BajaVideos.app BajaVideos-Mac.zip"
