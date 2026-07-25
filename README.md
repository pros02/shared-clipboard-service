# Shared Clipboard Service

Windows 11 と Ubuntu 26.04 間で、NAS共有フォルダを介して
テキスト・画像・ファイルを共有するクロスプラットフォームアプリ。

## Status

**v1.0** — Windows/Ubuntu間でのテキスト・画像・ファイルの送受信、自動受信、
履歴、起動時常駐、両OS向けパッケージングまで実機検証済み。既知の残課題は
設計レビュー文書の「プラットフォーム固有リスク」を参照。複数ファイル同時
送信や他のホームラボ関連アプリとの連携は今後の改訂版で検討予定。設計の
詳細は
[docs/design/requirements_review_v0.1.md](docs/design/requirements_review_v0.1.md)
を参照。

## Target Platforms

- Windows 11
- Ubuntu 26.04 LTS

## Technology

- Python 3.11+
- PySide6
- SMB shared folder (NAS)

## Development Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate   # Linux
pip install -e ".[dev]"
```

Run the tests:

```bash
pytest
```

Run the app:

```bash
python -m cbs
```

## Installing (end users)

### Windows

Build a standalone executable with PyInstaller (no Python install
required to run the result):

```powershell
pip install -e ".[build]"
pyinstaller packaging\cbs.spec
```

The executable is written to `dist\SharedClipboardService.exe`. Copy it
wherever you like and run it directly.

### Ubuntu

```bash
chmod +x packaging/linux/install.sh
./packaging/linux/install.sh
```

This creates a dedicated venv under `~/.local/share/shared-clipboard-service/`,
installs the app into it, and adds a desktop entry so it shows up in your
application menu. If it fails to start with a Qt platform plugin error,
install the missing system library it names (commonly
`sudo apt install libxcb-cursor0`).

Either way, use the app's own **設定** (Settings) dialog to enable
"ログイン時に自動起動する" (start on login) — no separate OS configuration
needed.

## Configuration

Local, per-machine settings are stored outside the repository:

- Windows: `%APPDATA%\SharedClipboardService\config.json`
- Linux: `$XDG_CONFIG_HOME/shared-clipboard-service/config.json` (defaults to `~/.config/...`)

A template listing all fields is checked in at
[config/config.example.json](config/config.example.json). The NAS shared
folder path is OS-specific, e.g.:

- Windows: `\\192.168.10.16\sharedclipboard`
- Ubuntu: `/mnt/networkstorage/sharedclipboard`

Logs are always written locally only, never to the NAS share:

- Windows: `%LOCALAPPDATA%\SharedClipboardService\logs`
- Linux: `$XDG_STATE_HOME/shared-clipboard-service/logs` (defaults to `~/.local/state/...`)
