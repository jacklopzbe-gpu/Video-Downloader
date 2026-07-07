"""
Configuración persistente de BajaVideos.

Se guarda como JSON en la carpeta de configuración del usuario:
  - Mac:     ~/Library/Application Support/BajaVideos/config.json
  - Windows: %APPDATA%/BajaVideos/config.json
  - Linux:   ~/.config/BajaVideos/config.json
"""

import json
import os
import sys

APP_NAME = "BajaVideos"


def config_dir() -> str:
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_FILE = os.path.join(config_dir(), "config.json")

DEFAULTS = {
    # Carpeta donde se guardan los videos
    "download_dir": os.path.join(os.path.expanduser("~"), "Downloads", APP_NAME),
    # Abrir Resolume Alley al terminar cada descarga
    "open_resolume": False,
    # Ruta manual a Resolume Alley (vacío = detectar automáticamente)
    "resolume_path": "",
    # Tema: "dark", "light" o "system"
    "appearance": "dark",
    # Token del bot de Telegram (lo da @BotFather). Vacío = sin Telegram.
    "telegram_token": "",
    # Chat del dueño del bot: el PRIMER chat que le escriba queda como dueño
    # y los demás se ignoran. 0 = aún sin dueño.
    "owner_chat_id": 0,
    # El usuario eligió usar la app sin Telegram (oculta la tarjeta de setup)
    "telegram_skipped": False,
}


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            data.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return data


def save(data: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
