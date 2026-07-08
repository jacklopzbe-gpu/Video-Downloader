"""
BajaVideos v2 — Descargador de TikTok, Instagram y YouTube.

Dos formas de usarla:
  A) Telegram (recomendado): mándale el link a tu bot desde el celular y se
     descarga en tu compu al abrir la app (o al instante si ya está abierta).
  B) Manual: pega el link en la ventana y presiona Descargar.

Opcional: abre Resolume Alley al terminar (para convertir a DXV3).
"""

import os
import threading
import traceback

import customtkinter as ctk

import downloader
import settings
import history_store
from telegram_worker import TelegramBot

APP_TITLE = "BajaVideos"
VERSION = "2.0"

# ─ Identidad Balastra ─  (negro, rojo #EC2024, estilo técnico)
ACCENT = "#EC2024"
ACCENT_HOVER = "#C4181C"
OK_COLOR = "#4CAF7D"
ERR_COLOR = "#FF6B6E"
BG = ("#F5F5F5", "#000000")
CARD_BG = ("#ECECEC", "#0E0E0E")
CARD_BORDER = ("#DDDDDD", "#1A1A1A")
SUBTLE = ("#6B6B76", "#B3B3B3")

PLATFORM_EMOJI = {"TikTok": "🎵", "Instagram": "📸", "YouTube": "▶️", "Video": "🎬"}


class DownloadCard(ctk.CTkFrame):
    """Tarjeta de una descarga en la lista."""

    def __init__(self, master, url: str):
        super().__init__(master, fg_color=CARD_BG, corner_radius=6,
                         border_width=1, border_color=CARD_BORDER)
        self.url = url
        self.file_path = None
        self.chat_id = None  # chat de Telegram que pidió esta descarga

        plat = downloader.platform_name(url)
        emoji = PLATFORM_EMOJI.get(plat, "🎬")

        self.grid_columnconfigure(1, weight=1)

        self.icon = ctk.CTkLabel(self, text=emoji, font=("", 26), width=44)
        self.icon.grid(row=0, column=0, rowspan=2, padx=(12, 4), pady=12)

        short = url if len(url) <= 62 else url[:59] + "…"
        self.title = ctk.CTkLabel(
            self, text=f"{plat}  ·  {short}", anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.title.grid(row=0, column=1, sticky="ew", padx=4, pady=(12, 0))

        self.status = ctk.CTkLabel(
            self, text="En cola…", anchor="w",
            font=ctk.CTkFont(size=12), text_color=SUBTLE,
        )
        self.status.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 4))

        self.bar = ctk.CTkProgressBar(self, height=8, progress_color=ACCENT)
        self.bar.set(0)
        self.bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))

        self.action = ctk.CTkButton(
            self, text="📂", width=40, height=30, fg_color="transparent",
            hover_color=("#DCDCE4", "#33333D"), text_color=SUBTLE,
            command=self._reveal,
        )
        self.action.grid(row=0, column=2, rowspan=2, padx=(4, 12))
        self.action.configure(state="disabled")

    # — Actualizaciones (siempre desde el hilo principal via .after) —

    def set_progress(self, frac, text):
        if frac is None:
            self.bar.configure(mode="indeterminate")
            self.bar.start()
        else:
            self.bar.stop()
            self.bar.configure(mode="determinate")
            self.bar.set(frac)
        self.status.configure(text=f"⬇️  Descargando…  {text}", text_color=SUBTLE)

    def set_done(self, file_path):
        self.file_path = file_path
        self.bar.stop()
        self.bar.configure(mode="determinate", progress_color=OK_COLOR)
        self.bar.set(1)
        name = os.path.basename(file_path)
        if len(name) > 58:
            name = name[:55] + "…"
        self.status.configure(text=f"✅  Listo  ·  {name}", text_color=OK_COLOR)
        self.action.configure(state="normal", text_color=OK_COLOR)

    def set_error(self, message):
        self.bar.stop()
        self.bar.configure(mode="determinate", progress_color=ERR_COLOR)
        self.bar.set(1)
        short = message.splitlines()[0]
        if len(short) > 90:
            short = short[:87] + "…"
        self.status.configure(text=f"❌  Error: {short}", text_color=ERR_COLOR)

    def _reveal(self):
        if self.file_path:
            downloader.reveal_in_folder(self.file_path)


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict, on_save):
        super().__init__(master)
        self.title("Ajustes")
        self.geometry("560x560")
        self.resizable(False, False)
        self.cfg = cfg
        self.on_save = on_save
        self.transient(master)
        self.grab_set()

        pad = {"padx": 24, "pady": (18, 0)}

        ctk.CTkLabel(self, text="⚙️  Ajustes", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", **pad
        )

        # Carpeta de descargas
        ctk.CTkLabel(self, text="Carpeta donde se guardan los videos:", anchor="w").pack(
            fill="x", **pad
        )
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(6, 0))
        self.dir_var = ctk.StringVar(value=cfg["download_dir"])
        ctk.CTkEntry(row, textvariable=self.dir_var).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(row, text="Elegir…", width=90, command=self._pick_dir,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side="right")

        # Resolume
        self.resolume_var = ctk.BooleanVar(value=cfg["open_resolume"])
        ctk.CTkSwitch(
            self,
            text="Abrir Resolume Alley al terminar cada descarga (para convertir a DXV3)",
            variable=self.resolume_var, progress_color=ACCENT,
        ).pack(anchor="w", padx=24, pady=(22, 0))

        found = downloader.find_resolume(cfg.get("resolume_path", ""))
        hint = f"Resolume detectado: {found}" if found else (
            "Resolume Alley no se detectó. Si lo tienes instalado en otra ruta,\n"
            "igual puedes abrirlo tú y arrastrar el video."
        )
        ctk.CTkLabel(self, text=hint, text_color=SUBTLE, anchor="w",
                     font=ctk.CTkFont(size=11), justify="left").pack(fill="x", padx=24, pady=(6, 0))

        # Telegram
        ctk.CTkLabel(self, text="Bot de Telegram (token de @BotFather):", anchor="w").pack(
            fill="x", **pad
        )
        self.token_var = ctk.StringVar(value=cfg.get("telegram_token", ""))
        ctk.CTkEntry(self, textvariable=self.token_var, show="•").pack(
            fill="x", padx=24, pady=(6, 0)
        )
        ctk.CTkLabel(
            self, anchor="w", justify="left", text_color=SUBTLE,
            font=ctk.CTkFont(size=11),
            text="Si cambias el token, cierra y vuelve a abrir la app.\n"
                 "Déjalo vacío para no usar Telegram.",
        ).pack(fill="x", padx=24, pady=(4, 0))
        ctk.CTkButton(
            self, text="Cambiar dueño del bot", width=170, height=28,
            fg_color="transparent", border_width=1, border_color=SUBTLE,
            text_color=SUBTLE, hover_color=("#DCDCE4", "#33333D"),
            command=self._reset_owner,
        ).pack(anchor="w", padx=24, pady=(8, 0))

        # Tema
        ctk.CTkLabel(self, text="Apariencia:", anchor="w").pack(fill="x", **pad)
        self.theme_var = ctk.StringVar(value=cfg.get("appearance", "dark"))
        ctk.CTkSegmentedButton(
            self, values=["dark", "light", "system"], variable=self.theme_var,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        ).pack(anchor="w", padx=24, pady=(6, 0))

        ctk.CTkButton(
            self, text="Guardar", width=120, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._save,
        ).pack(pady=24)

    def _pick_dir(self):
        from tkinter import filedialog
        chosen = filedialog.askdirectory(initialdir=self.dir_var.get() or os.path.expanduser("~"))
        if chosen:
            self.dir_var.set(chosen)

    def _reset_owner(self):
        """El próximo chat que escriba al bot será el nuevo dueño."""
        self.cfg["owner_chat_id"] = 0
        settings.save(self.cfg)

    def _save(self):
        self.cfg["download_dir"] = self.dir_var.get().strip() or settings.DEFAULTS["download_dir"]
        self.cfg["open_resolume"] = bool(self.resolume_var.get())
        self.cfg["appearance"] = self.theme_var.get()
        new_token = self.token_var.get().strip()
        if new_token != self.cfg.get("telegram_token", ""):
            self.cfg["telegram_token"] = new_token
            self.cfg["telegram_skipped"] = not bool(new_token)
        settings.save(self.cfg)
        ctk.set_appearance_mode(self.cfg["appearance"])
        self.on_save()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = settings.load()
        ctk.set_appearance_mode(self.cfg.get("appearance", "dark"))
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_TITLE}")
        self.configure(fg_color=BG)
        self.geometry("760x640")
        self.minsize(620, 500)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ─ Encabezado ─
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 4))
        header.grid_columnconfigure(0, weight=1)
        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_row, text=APP_TITLE.upper(), text_color=ACCENT,
            font=ctk.CTkFont(size=30, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            title_row, text=".", text_color=("#111", "#FFF"),
            font=ctk.CTkFont(size=30, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="T I K T O K   ·   I N S T A G R A M   ·   Y O U T U B E",
            text_color=SUBTLE, font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=1, column=0, sticky="w")
        self.bot_status = ctk.CTkLabel(
            header, text="", text_color=SUBTLE, font=ctk.CTkFont(size=12),
        )
        self.bot_status.grid(row=2, column=0, sticky="w", pady=(2, 0))
        ctk.CTkButton(
            header, text="⚙️", width=44, height=36, fg_color="transparent",
            hover_color=CARD_BG, text_color=SUBTLE, font=("", 18),
            command=self._open_settings,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        # ─ Barra de entrada ─
        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.grid(row=1, column=0, sticky="ew", padx=28, pady=(16, 8))
        entry_row.grid_columnconfigure(0, weight=1)

        self.url_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(
            entry_row, textvariable=self.url_var, height=44,
            placeholder_text="https://www.tiktok.com/…   ·   pega aquí el link",
            font=ctk.CTkFont(size=13), corner_radius=10,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self._start_download())

        ctk.CTkButton(
            entry_row, text="📋 Pegar", width=90, height=44, corner_radius=10,
            fg_color=CARD_BG, hover_color=("#DCDCE4", "#33333D"),
            text_color=("#333", "#DDD"), command=self._paste,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            entry_row, text="⬇  DESCARGAR", width=150, height=44, corner_radius=6,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._start_download,
        ).grid(row=0, column=2)

        self.hint = ctk.CTkLabel(self, text="", text_color=ERR_COLOR,
                                 font=ctk.CTkFont(size=12))
        # (se muestra solo cuando hay un aviso)

        # ─ Lista de descargas ─
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(4, 0))
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="\n\nAquí van a aparecer tus descargas 🙂",
            text_color=SUBTLE, font=ctk.CTkFont(size=14),
        )
        self.empty_label.grid(row=0, column=0, pady=40)

        # ─ Pie ─
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=28, pady=(8, 16))
        footer.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            footer, text="📂  Abrir carpeta de descargas", height=34, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=SUBTLE,
            text_color=("#333", "#DDD"), hover_color=CARD_BG,
            command=self._open_folder,
        ).grid(row=0, column=0, sticky="w")
        credit = ctk.CTkFrame(footer, fg_color="transparent")
        credit.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(credit, text="POWERED BY ", text_color=SUBTLE,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(side="left")
        ctk.CTkLabel(credit, text="BALASTRA.", text_color=ACCENT,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(side="left")
        ctk.CTkLabel(credit, text=f" & JACKKLO   ·   v{VERSION}", text_color=SUBTLE,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(side="left")

        self.cards_count = 0
        self.entry.focus()

        # ─ Telegram ─
        self.bot = None
        self.setup_card = None
        self.active_urls = set()
        if self.cfg.get("telegram_token"):
            self._start_bot()
        elif not self.cfg.get("telegram_skipped"):
            self._show_telegram_setup()

        # Retoma descargas que quedaron a medias en sesiones anteriores
        self.after(500, self._resume_pending)

    def _resume_pending(self):
        for it in history_store.pending():
            self._add_download(it["url"], it.get("chat_id"), item_id=it["id"])

    # ─── Telegram ────────────────────────────────────────────────────────────

    def _start_bot(self):
        self.bot_status.configure(text="🟡 Conectando bot de Telegram…",
                                  text_color=SUBTLE)
        self.bot = TelegramBot(
            token=self.cfg["telegram_token"],
            on_status=lambda ok, d: self.after(0, self._bot_status_changed, ok, d),
            on_link=lambda url, chat: self.after(0, self._add_download, url, chat),
            get_owner=lambda: self.cfg.get("owner_chat_id", 0),
            set_owner=self._set_owner,
        )
        self.bot.start()

    def _set_owner(self, chat_id):
        self.cfg["owner_chat_id"] = chat_id
        settings.save(self.cfg)

    def _bot_status_changed(self, ok, detail):
        if ok:
            self.bot_status.configure(
                text=f"🟢 Bot conectado: {detail} — mándale links desde tu cel",
                text_color=OK_COLOR,
            )
        else:
            self.bot_status.configure(
                text=f"🔴 Telegram: {detail}", text_color=ERR_COLOR
            )

    def _show_telegram_setup(self):
        card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=6,
                            border_width=1, border_color=CARD_BORDER)
        card.grid(row=2, column=0, sticky="ew", padx=28, pady=(4, 8))
        self.setup_card = card

        ctk.CTkLabel(
            card, text="📱  Conecta tu bot de Telegram (recomendado)",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            card, justify="left", text_color=SUBTLE, font=ctk.CTkFont(size=12),
            text=(
                "Así puedes mandarle videos desde tu celular y se descargan aquí.\n"
                "1. En Telegram busca a @BotFather y escríbele:  /newbot\n"
                "2. Sigue los pasos (te pedirá un nombre para tu bot).\n"
                "3. Al final te da un TOKEN (código largo). Pégalo aquí:"
            ),
        ).pack(anchor="w", padx=16)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(8, 14))
        self.token_var = ctk.StringVar()
        ctk.CTkEntry(
            row, textvariable=self.token_var, height=38,
            placeholder_text="123456789:AAH_tu_token_aquí…",
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row, text="Conectar", width=110, height=38,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._connect_token,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row, text="Usar sin Telegram", width=130, height=38,
            fg_color="transparent", border_width=1, border_color=SUBTLE,
            text_color=SUBTLE, hover_color=("#DCDCE4", "#33333D"),
            command=self._skip_telegram,
        ).pack(side="left")

    def _connect_token(self):
        token = (self.token_var.get() or "").strip()
        if ":" not in token or len(token) < 30:
            self._show_hint("🤔 Ese token no se ve completo. Copia TODO el código que te dio @BotFather.")
            return
        self.cfg["telegram_token"] = token
        settings.save(self.cfg)
        if self.setup_card:
            self.setup_card.destroy()
            self.setup_card = None
        self._start_bot()

    def _skip_telegram(self):
        self.cfg["telegram_skipped"] = True
        settings.save(self.cfg)
        if self.setup_card:
            self.setup_card.destroy()
            self.setup_card = None

    # ─── Acciones ────────────────────────────────────────────────────────────

    def _paste(self):
        try:
            self.url_var.set(self.clipboard_get().strip())
        except Exception:
            pass

    def _open_settings(self):
        SettingsWindow(self, self.cfg, on_save=lambda: None)

    def _open_folder(self):
        os.makedirs(self.cfg["download_dir"], exist_ok=True)
        downloader.reveal_in_folder(self.cfg["download_dir"])

    def _show_hint(self, text):
        self.hint.configure(text=text)
        self.hint.grid(row=1, column=0, sticky="w", padx=32, pady=(64, 0))
        self.after(4000, self.hint.grid_forget)

    def _start_download(self):
        url = downloader.extract_url(self.url_var.get())
        if not url:
            self._show_hint("🤔 Ese link no parece de TikTok, Instagram o YouTube.")
            return
        self.url_var.set("")
        self._add_download(url)

    def _add_download(self, url, chat_id=None, item_id=None):
        """Crea la tarjeta y arranca la descarga (manual, Telegram o retomada)."""
        # ¿Ya se está descargando en esta sesión?
        if url in self.active_urls:
            if self.bot and chat_id:
                self.bot.notify(chat_id, "⚠️ Ese link ya está en proceso.")
            return

        if self.empty_label.winfo_ismapped():
            self.empty_label.grid_forget()

        card = DownloadCard(self.list_frame, url)
        card.chat_id = chat_id
        card.grid(row=1000 - self.cards_count, column=0, sticky="ew", pady=6, padx=4)
        self.cards_count += 1

        # ¿Ya se descargó antes y el archivo sigue ahí? No lo repite.
        done = history_store.find_done(url)
        if done:
            card.set_done(done["file"])
            if self.bot and chat_id:
                self.bot.notify(
                    chat_id,
                    "⚠️ Ese video ya estaba descargado:\n"
                    f"📁 {os.path.basename(done['file'])}",
                )
            return

        self.active_urls.add(url)
        if item_id is None:
            item_id = history_store.add(url, chat_id)

        thread = threading.Thread(
            target=self._worker, args=(url, card, item_id), daemon=True
        )
        thread.start()

    # ─── Descarga en segundo plano ───────────────────────────────────────────

    def _worker(self, url, card, item_id):
        def progress(frac, text):
            self.after(0, card.set_progress, frac, text)

        history_store.set_status(item_id, "downloading")
        try:
            path = downloader.download(url, self.cfg["download_dir"], progress)
        except Exception as e:
            traceback.print_exc()
            msg = str(e) or e.__class__.__name__
            # yt-dlp antepone "ERROR: " a sus mensajes
            msg = msg.replace("ERROR: ", "")
            history_store.set_status(item_id, "error", error=msg)
            self.active_urls.discard(url)  # permite reintentar
            self.after(0, card.set_error, msg)
            if self.bot and getattr(card, "chat_id", None):
                self.bot.notify(card.chat_id, f"❌ No se pudo descargar:\n{msg[:200]}")
            return

        history_store.set_status(item_id, "done", file_path=path)
        self.after(0, card.set_done, path)

        if self.bot and getattr(card, "chat_id", None):
            self.bot.notify(
                card.chat_id,
                f"✅ ¡Listo! Se descargó:\n📁 {os.path.basename(path)}",
            )

        if self.cfg.get("open_resolume"):
            downloader.open_resolume(self.cfg.get("resolume_path", ""))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
