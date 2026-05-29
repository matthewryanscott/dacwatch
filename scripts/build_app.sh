#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$PROJECT_ROOT/dist/DaCWatch.app"
CONTENTS="$APP_DIR/Contents"

echo "Building DaCWatch.app..."

# Clean previous build
rm -rf "$APP_DIR"

# Create directory structure
mkdir -p "$CONTENTS/MacOS"
mkdir -p "$CONTENTS/Resources"

# --- Info.plist ---
cat > "$CONTENTS/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>DaCWatch</string>
    <key>CFBundleDisplayName</key>
    <string>DaCWatch</string>
    <key>CFBundleIdentifier</key>
    <string>com.versafeed.dacwatch</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleExecutable</key>
    <string>dacwatch</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

# --- Launcher script ---
# Forwards any extra args (e.g. --kroki-base) passed via `open --args`.
cat > "$CONTENTS/MacOS/dacwatch" << 'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail

# Resolve project root from .app location.
# .app is at <project>/dist/DaCWatch.app, launcher is in Contents/MacOS/
APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_ROOT="$(cd "$APP_DIR/../.." && pwd)"

# Use the project's uv venv.
PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    osascript -e "display alert \"DaCWatch\" message \"Could not find Python venv at $PROJECT_ROOT/.venv. Run uv sync first.\" as critical"
    exit 1
fi

exec "$PYTHON" -m dacwatch.main --serve "$@"
LAUNCHER
chmod +x "$CONTENTS/MacOS/dacwatch"

# --- Icon ---
ICON_SRC="$PROJECT_ROOT/resources/icon.png"
if [ -f "$ICON_SRC" ]; then
    ICONSET_DIR=$(mktemp -d)/icon.iconset
    mkdir -p "$ICONSET_DIR"

    # Generate required icon sizes
    for size in 16 32 128 256 512; do
        sips -z $size $size "$ICON_SRC" --out "$ICONSET_DIR/icon_${size}x${size}.png" > /dev/null 2>&1
        double=$((size * 2))
        sips -z $double $double "$ICON_SRC" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" > /dev/null 2>&1
    done

    iconutil -c icns "$ICONSET_DIR" -o "$CONTENTS/Resources/icon.icns"
    rm -rf "$(dirname "$ICONSET_DIR")"
    echo "Icon converted from $ICON_SRC"
else
    echo "Warning: No icon found at $ICON_SRC — app will use default icon"
fi

echo "Built: $APP_DIR"
echo ""
echo "The .app expects the project venv at $PROJECT_ROOT/.venv"
echo "Make sure you've run: uv sync"
