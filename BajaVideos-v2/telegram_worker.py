"""
Bot de Telegram corriendo en un hilo de fondo, integrado con la GUI.

Flujo:
  - El usuario le manda un link (TikTok/Instagram/YouTube) al bot desde el cel.
  - Si la app está abierta, se descarga al momento.
  - Si estaba cerrada, Telegram guarda los mensajes (~24 h) y se descargan
    en cuanto se abre la app (drop_pending_updates=False).

Seguridad: el PRIMER chat que le escriba al bot queda como "dueño";
mensajes de cualquier otra persona se ignoran.

Callbacks hacia la GUI (se llaman desde este hilo; la GUI debe usar .after):
  on_status(ok: bool, detail: str)   – conectado (detail=@usuario) o error
  on_link(url: str, chat_id: int)    – llegó un link para descargar
"""

import asyncio
import logging
import threading

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import downloader

log = logging.getLogger(__name__)

WELCOME = (
    "👋 ¡Hola! Soy tu descargador de videos.\n\n"
    "Mándame un link de TikTok, Instagram o YouTube y lo descargo "
    "en tu computadora (la app BajaVideos debe estar abierta, o se "
    "descargará cuando la abras)."
)

WELCOME_BACK = (
    "🟢 BajaVideos está abierta. Revisé los mensajes que mandaste "
    "mientras estaba cerrada y los estoy procesando.\n"
    "Los links nuevos se descargan al momento."
)


class TelegramBot(threading.Thread):
    def __init__(self, token: str, on_status, on_link, get_owner, set_owner):
        super().__init__(daemon=True, name="TelegramBot")
        self.token = token.strip()
        self.on_status = on_status
        self.on_link = on_link
        self.get_owner = get_owner      # () -> int  (0 = sin dueño)
        self.set_owner = set_owner      # (chat_id) -> None
        self.loop = None
        self.app = None
        self.connected = False

    # ─── Hilo del bot ─────────────────────────────────────────────────────────

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            app = Application.builder().token(self.token).build()
            app.add_handler(CommandHandler("start", self._cmd_start))
            app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
            )

            async def post_init(application):
                me = await application.bot.get_me()
                self.connected = True
                self.on_status(True, f"@{me.username}")
                # Avisa al dueño que la app ya está abierta (si ya hay dueño)
                owner = self.get_owner()
                if owner:
                    try:
                        await application.bot.send_message(owner, WELCOME_BACK)
                    except Exception:
                        pass

            app.post_init = post_init
            self.app = app
            # stop_signals=None → permite correr fuera del hilo principal
            # drop_pending_updates=False → recibe lo enviado con la app cerrada
            app.run_polling(
                stop_signals=None,
                close_loop=False,
                drop_pending_updates=False,
            )
        except Exception as e:
            self.connected = False
            name = e.__class__.__name__
            msg = str(e)
            if name == "Conflict" or "terminated by other getUpdates" in msg:
                msg = (
                    "Otro programa está usando este mismo bot "
                    "(¿sigue abierto el BotVideos viejo?). Ciérralo y "
                    "vuelve a abrir esta app."
                )
            elif name == "InvalidToken" or "Unauthorized" in msg:
                msg = "El token no es válido. Revísalo en ⚙️ Ajustes."
            elif name in ("NetworkError", "TimedOut") or "getaddrinfo" in msg:
                msg = "Sin conexión a internet. Se reintentará al reabrir la app."
            self.on_status(False, msg)

    # ─── Handlers ─────────────────────────────────────────────────────────────

    def _is_owner(self, chat_id: int) -> bool:
        owner = self.get_owner()
        if owner == 0:
            self.set_owner(chat_id)
            return True
        return chat_id == owner

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update.effective_chat.id):
            await update.message.reply_text("🔒 Este bot es privado.")
            return
        await update.message.reply_text(WELCOME)

    async def _on_message(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_owner(chat_id):
            await update.message.reply_text("🔒 Este bot es privado.")
            return

        url = downloader.extract_url(update.message.text or "")
        if not url:
            await update.message.reply_text(
                "🤔 No vi un link válido. Mándame uno de TikTok, "
                "Instagram o YouTube."
            )
            return

        await update.message.reply_text("✅ Recibido, descargando en tu compu…")
        self.on_link(url, chat_id)

    # ─── Para llamar DESDE la GUI (thread-safe) ──────────────────────────────

    def notify(self, chat_id: int, text: str) -> None:
        """Manda un mensaje al chat sin bloquear la GUI."""
        if not (self.connected and self.loop and self.app):
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.app.bot.send_message(chat_id=chat_id, text=text),
                self.loop,
            )
        except Exception as e:
            log.warning("No se pudo notificar por Telegram: %s", e)
