import os
import re
import asyncio
import logging
import tempfile
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise SystemExit(
        "❌ BOT_TOKEN muhit o'zgaruvchisi topilmadi. "
        "Render'da Environment bo'limiga BOT_TOKEN qo'shing (BotFather'dan olingan token)."
    )

url_store = {}

# Render Free Web Service portni tinglashni talab qiladi (health check uchun),
# va UptimeRobot ham shu manzilga ping yuborib botni "uyg'oq" tutadi.
# Telegram polling shu bilan parallel, alohida threadda ishlaydi.
PORT = int(os.environ.get("PORT", 10000))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot ishlamoqda ✅".encode("utf-8"))

    def do_HEAD(self):
        # UptimeRobot va boshqa monitoring xizmatlari ko'pincha
        # GET emas, HEAD so'rovi yuboradi. Agar bu metod bo'lmasa,
        # BaseHTTPRequestHandler avtomatik 501 Not Implemented qaytaradi
        # va monitor botni "Down" deb hisoblaydi.
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Render loglarini health-check so'rovlari bilan to'ldirmaslik uchun


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"Health-check server {PORT}-portda ishga tushdi")
    server.serve_forever()


MUSIC_KEYWORDS = ["music", "song", "audio", "musiqa", "track", "album", "official audio", "lyrics"]


def is_music_likely(url: str, info: dict) -> bool:
    categories = info.get("categories", []) or []
    tags = info.get("tags", []) or []
    title = (info.get("title") or "").lower()

    if any(kw in title for kw in MUSIC_KEYWORDS):
        return True
    if "Music" in categories:
        return True
    if any(kw in " ".join(tags).lower() for kw in MUSIC_KEYWORDS):
        return True
    return False


def detect_url(text: str):
    match = re.search(r'https?://[^\s]+', text)
    return match.group(0) if match else None


def get_ydl_opts_base():
    return {
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"],
            }
        },
    }


def get_video_info(url: str) -> dict:
    opts = get_ydl_opts_base()
    opts["skip_download"] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men Video Downloader botman!\n\n"
        "📹 Quyidagi platformalardan video yuklashim mumkin:\n"
        "• YouTube\n• Instagram\n• TikTok\n• Twitter/X\n• Facebook\n• Va boshqa 1000+ sayt!\n\n"
        "🔗 Faqat video havolasini yuboring!"
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    url = detect_url(text)

    if not url:
        await update.message.reply_text("❌ Havola topilmadi.")
        return

    status_msg = await update.message.reply_text("⏳ Tekshirilmoqda...")

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_video_info, url)

        title = info.get("title", "Noma'lum")
        duration = info.get("duration", 0)
        uploader = info.get("uploader", "Noma'lum")

        if duration:
            mins, secs = divmod(int(duration), 60)
            hrs, mins = divmod(mins, 60)
            duration_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
        else:
            duration_str = "Noma'lum"

        url_id = str(update.message.message_id)
        url_store[url_id] = url

        msg_text = (
            f"📹 *{title}*\n\n"
            f"👤 {uploader}\n"
            f"⏱ {duration_str}\n\n"
            f"Sifatni tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("🎬 360p", callback_data=f"v|360|{url_id}"),
                InlineKeyboardButton("🎬 720p", callback_data=f"v|720|{url_id}"),
            ],
            [
                InlineKeyboardButton("🎬 1080p", callback_data=f"v|1080|{url_id}"),
                InlineKeyboardButton("🎬 Best", callback_data=f"v|best|{url_id}"),
            ],
        ]

        if is_music_likely(url, info):
            keyboard.append([
                InlineKeyboardButton("🎵 MP3 yuklash", callback_data=f"a|mp3|{url_id}")
            ])
            msg_text += "\n\n🎵 *Qo'shiq bor! MP3 sifatida ham yuklab olish mumkin!*"

        keyboard.append([InlineKeyboardButton("❌ Bekor", callback_data="cancel")])

        await status_msg.edit_text(
            msg_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(
            "❌ Bu havola ishlamadi yoki video mavjud emas.\nBoshqa havola yuborib ko'ring."
        )


async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    parts = query.data.split("|", 2)
    if len(parts) != 3:
        await query.edit_message_text("❌ Xatolik.")
        return

    dl_type, quality, url_id = parts
    url = url_store.get(url_id)

    if not url:
        await query.edit_message_text("❌ Havola topilmadi. Qaytadan yuboring.")
        return

    await query.edit_message_text("⬇️ Yuklanmoqda... Kuting...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "%(title)s.%(ext)s")
            base_opts = get_ydl_opts_base()

            if dl_type == "a":
                ydl_opts = {
                    **base_opts,
                    "format": "bestaudio/best",
                    "outtmpl": output_path,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                }
            else:
                fmt_map = {
                    "360": "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360]",
                    "720": "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]",
                    "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]",
                    "best": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
                }
                ydl_opts = {
                    **base_opts,
                    "format": fmt_map.get(quality, "best"),
                    "outtmpl": output_path,
                    "merge_output_format": "mp4",
                }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

            files = list(Path(tmpdir).glob("*"))
            if not files:
                await query.edit_message_text("❌ Fayl yuklanmadi.")
                return

            file_path = str(files[0])
            file_size = os.path.getsize(file_path)

            if file_size > 50 * 1024 * 1024:
                await query.edit_message_text("❌ Fayl 50MB dan katta. Pastroq sifat tanlang.")
                return

            await query.edit_message_text("📤 Yuborilmoqda...")

            with open(file_path, "rb") as f:
                if dl_type == "a" or file_path.endswith(".mp3"):
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=f,
                        caption="🎵 Mana sizning qo'shig'ingiz!"
                    )
                else:
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=f,
                        caption="🎬 Mana sizning videongiz!",
                        supports_streaming=True
                    )

            await query.edit_message_text("✅ Yuborildi!")
            url_store.pop(url_id, None)

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(
            "❌ Yuklab olishda xatolik.\nBoshqa sifat tanlang yoki qaytadan urinib ko'ring."
        )


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(download_callback))

    logger.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
