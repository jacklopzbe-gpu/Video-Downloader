"""
Historial persistente de descargas (reemplaza al history.db de la v1).

Se guarda como JSON junto a la configuración. Sirve para:
  - Retomar descargas pendientes al abrir la app (si se cerró a medias).
  - Saber si un link ya fue descargado antes (evitar repetidos).
"""

import json
import os
import threading
import time
import uuid

from settings import config_dir

HISTORY_FILE = os.path.join(config_dir(), "history.json")
_LOCK = threading.Lock()
MAX_ITEMS = 500


def _load() -> list:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _save(items: list) -> None:
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(items[-MAX_ITEMS:], f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def add(url: str, chat_id=None) -> str:
    """Registra un link como pendiente. Devuelve su id."""
    item_id = uuid.uuid4().hex[:12]
    with _LOCK:
        items = _load()
        items.append({
            "id": item_id,
            "url": url,
            "chat_id": chat_id,
            "status": "pending",       # pending | downloading | done | error
            "file": None,
            "error": None,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        _save(items)
    return item_id


def set_status(item_id: str, status: str, file_path=None, error=None) -> None:
    with _LOCK:
        items = _load()
        for it in items:
            if it.get("id") == item_id:
                it["status"] = status
                if file_path is not None:
                    it["file"] = file_path
                if error is not None:
                    it["error"] = str(error)[:300]
                break
        _save(items)


def pending() -> list:
    """Links que quedaron a medias (pendientes o descargando) de otras sesiones."""
    return [it for it in _load() if it.get("status") in ("pending", "downloading")]


def find_done(url: str):
    """Si este link ya se descargó antes y el archivo aún existe, lo devuelve."""
    for it in reversed(_load()):
        if it.get("url") == url and it.get("status") == "done":
            f = it.get("file")
            if f and os.path.exists(f):
                return it
    return None

