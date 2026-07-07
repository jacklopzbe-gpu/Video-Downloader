"""
Descarga de videos (TikTok, Instagram, YouTube) con yt-dlp.

Expone:
  - extract_url(texto)  -> primer link soportado o None
  - platform_name(url)  -> "TikTok" | "Instagram" | "YouTube"
  - download(url, carpeta, on_progress) -> ruta del MP4 final
  - open_resolume(ruta_manual)          -> abre Resolume Alley (Mac/Windows)
  - reveal_in_folder(ruta)              -> muestra el archivo en Finder/Explorador
"""

import os
import re
import subprocess
import sys

import yt_dlp

URL_RE = re.compile(
    r"(https?://)?(www\.|vm\.|vt\.|m\.)?"
    r"(tiktok\.com|instagram\.com|instagr\.am|youtube\.com|youtu\.be)"
    r"/[^\s]*",
    re.IGNORECASE,
)


def extract_url(text: str):
    match = URL_RE.search(text or "")
    if not match:
        return None
    url = match.group(0).rstrip(").,]>\"'")
    return url if url.lower().startswith("http") else "https://" + url


def platform_name(url: str) -> str:
    u = (url or "").lower()
    if "tiktok" in u:
        return "TikTok"
    if "instagram" in u or "instagr.am" in u:
        return "Instagram"
    if "youtube" in u or "youtu.be" in u:
        return "YouTube"
    return "Video"


def _ffmpeg_path():
    """Ruta al ffmpeg incluido con la app (imageio-ffmpeg), o None."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def download(url: str, download_dir: str, on_progress=None) -> str:
    """
    Descarga el video y devuelve la ruta del archivo final.

    on_progress(fraccion, texto) se llama durante la descarga:
      fraccion: 0.0 a 1.0 (o None si no se conoce)
      texto:    estado legible, ej. "45%  ·  2.1 MB/s"
    """
    os.makedirs(download_dir, exist_ok=True)
    out_template = os.path.join(download_dir, "%(title).80s.%(ext)s")

    final_path = {"value": None}

    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            frac = (done / total) if total else None
            speed = d.get("speed")
            speed_txt = f"{speed / 1_048_576:.1f} MB/s" if speed else ""
            pct_txt = f"{frac * 100:.0f}%" if frac is not None else "…"
            if on_progress:
                on_progress(frac, f"{pct_txt}  ·  {speed_txt}".strip(" ·"))
        elif status == "finished":
            final_path["value"] = d.get("filename")
            if on_progress:
                on_progress(1.0, "Procesando…")

    ffmpeg = _ffmpeg_path()

    ydl_opts = {
        # Mejor video+audio; si no hay ffmpeg, el mejor archivo ya combinado
        "format": (
            "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b[ext=mp4]/b"
            if ffmpeg
            else "b[ext=mp4]/b"
        ),
        "outtmpl": out_template,
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "progress_hooks": [hook],
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    }
    if ffmpeg:
        ydl_opts["ffmpeg_location"] = ffmpeg

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    # yt-dlp puede cambiar la extensión al hacer merge
    candidates = [filename, os.path.splitext(filename)[0] + ".mp4"]
    if final_path["value"]:
        candidates.insert(0, final_path["value"])
        candidates.insert(1, os.path.splitext(final_path["value"])[0] + ".mp4")
    for ext in (".mkv", ".webm", ".mov"):
        candidates.append(os.path.splitext(filename)[0] + ext)

    for c in candidates:
        if c and os.path.exists(c):
            return c

    raise FileNotFoundError("No se encontró el archivo descargado.")


# ─── Integraciones con el sistema ────────────────────────────────────────────

_RESOLUME_MAC = [
    "/Applications/Resolume Alley.app",
    os.path.expanduser("~/Applications/Resolume Alley.app"),
]
_RESOLUME_WIN = [
    r"C:\Program Files\Resolume Alley\Alley.exe",
    r"C:\Program Files (x86)\Resolume Alley\Alley.exe",
]


def find_resolume(manual_path: str = "") -> str:
    """Devuelve la ruta de Resolume Alley, o '' si no se encuentra."""
    if manual_path and os.path.exists(manual_path):
        return manual_path
    paths = _RESOLUME_MAC if sys.platform == "darwin" else _RESOLUME_WIN
    for p in paths:
        if os.path.exists(p):
            return p
    return ""


def open_resolume(manual_path: str = "") -> bool:
    """Abre Resolume Alley. Devuelve True si se pudo."""
    path = find_resolume(manual_path)
    if not path:
        return False
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen([path])
        return True
    except Exception:
        return False


def reveal_in_folder(path: str) -> None:
    """Muestra el archivo (o abre la carpeta) en Finder / Explorador."""
    try:
        if sys.platform == "darwin":
            if os.path.isfile(path):
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["open", path])
        elif sys.platform == "win32":
            if os.path.isfile(path):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                os.startfile(os.path.normpath(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path)])
    except Exception:
        pass
