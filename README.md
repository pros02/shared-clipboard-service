# Shared Clipboard Service

Windows 11 と Ubuntu 26.04 間で、NAS共有フォルダを介して
テキスト・画像・ファイルを共有するクロスプラットフォームアプリ。

## Status

Phase 0: project scaffolding (package layout, local config loading,
logging). No clipboard, storage, or GUI functionality yet — see
[docs/design/requirements_review_v0.1.md](docs/design/requirements_review_v0.1.md)
for the full design review and phased implementation plan.

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

Run the current scaffolding (loads config, initializes logging; no GUI yet):

```bash
python -m cbs
```

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
