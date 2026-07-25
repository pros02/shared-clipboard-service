#!/usr/bin/env bash
# Simple installer for Ubuntu: sets up a dedicated venv, installs the app
# into it, and registers a desktop entry so it shows up in the app menu.
# Run from anywhere; it locates the repo relative to this script.
#
#   chmod +x packaging/linux/install.sh
#   ./packaging/linux/install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_DIR="$HOME/.local/share/shared-clipboard-service"
VENV_DIR="$INSTALL_DIR/venv"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "Installing Shared Clipboard Service from $REPO_DIR"

if ! python3 -c "import venv" >/dev/null 2>&1; then
    echo "python3-venv is required. Install it first with: sudo apt install python3-venv"
    exit 1
fi

mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install "$REPO_DIR"

mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/shared-clipboard-service.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Shared Clipboard Service
Exec=$VENV_DIR/bin/cbs
Terminal=false
Categories=Utility;
EOF

echo ""
echo "Installed. Launch it from your application menu, or run:"
echo "  $VENV_DIR/bin/cbs"
echo ""
echo "To start automatically at login, use the app's own Settings dialog"
echo "(no need to configure this separately)."
echo ""
echo "If the app fails to start with a Qt platform plugin error, install"
echo "the missing system library it names, e.g.: sudo apt install libxcb-cursor0"
