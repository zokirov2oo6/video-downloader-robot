# Video Downloader Bot

Telegram orqali YouTube, Instagram, TikTok, Twitter/X, Facebook va 1000+ saytdan video/audio yuklab beruvchi bot (yt-dlp + python-telegram-bot).

## Render'ga bepul (Free Web Service) joylashtirish + UptimeRobot

Bot endi `PORT` portida kichik bir health-check server ochadi (`http.server` orqali), bu Render'ning Free Web Service health check talabini qondiradi va UptimeRobot uchun ping nuqtasi vazifasini bajaradi. Telegram polling shu bilan parallel, alohida threadda ishlayveradi.

1. Render dashboard → **New** → **Blueprint** → repo'ni tanlang. `render.yaml` avtomatik o'qiladi (`type: web`, `plan: free`, Docker orqali quriladi — ffmpeg ham o'rnatiladi).
   - Yoki qo'lda: **New** → **Web Service** → Environment: **Docker** → Dockerfile yo'li `./Dockerfile`.
2. **Environment** bo'limida `BOT_TOKEN`ni qo'shing (BotFather'dan olingan token).
3. Deploy tugagach, Render sizga ochiq URL beradi (masalan `https://video-downloader-bot.onrender.com`). Shu URL'ni [UptimeRobot](https://uptimerobot.com) (yoki shunga o'xshash xizmat)ga qo'shib, har 5 daqiqada ping qiladigan monitor o'rnating — shunda Render uni "harakatsiz" deb hisoblab uxlatib qo'ymaydi.

### Bilib qo'yish kerak bo'lgan cheklovlar

- UptimeRobot doim 100% kafolat bermaydi — ba'zida ping orasida bot baribir bir necha soniya/daqiqaga uxlab qolishi mumkin, foydalanuvchi xabar yuborganda javob biroz kechikishi mumkin.
- Free instance'da RAM atigi 512MB, CPU 0.1 — katta/uzun videolarni yuklashda sekinlik yoki xotira yetishmasligi bo'lishi mumkin.
- Bir nechta foydalanuvchi bir vaqtda video yuklasa, resurs cheklovlari sezilarli bo'lishi mumkin.
- Agar bot doim barqaror ishlashi muhim bo'lsa, kelajakda Background Worker (Starter, ~$7/oy) ga o'tish tavsiya qilinadi.

## Eslatma

- `nixpacks.toml` va `railway.toml` — Railway uchun, Render ularni e'tiborsiz qoldiradi.
- Fayl hajmi 50MB dan oshsa, Telegram orqali yuborib bo'lmaydi (Bot API cheklovi) — bot bunday holatda foydalanuvchiga pastroq sifat tanlashni so'raydi.

