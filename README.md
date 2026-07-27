# 🎵 MELOXI - High-Fidelity Music Bot

MELOXI is a premium Discord music bot designed for the ultimate listening experience. Built with a focus on high-fidelity audio, AI-powered mood detection, and a robust social profile system.

## ✨ Features

- **🎧 High-Fidelity Audio**: Optimized streaming using `yt-dlp` and FFmpeg for crisp, lossless-quality sound.
- **📻 Spotify Radio Engine**: Pure algorithm-driven Auto-DJ powered by official Spotify Recommendations, Artist Radio, and Related Artist discovery.
- **🎯 1:1 Metadata Sync**: Strict similarity guards and duration audits ensure the displayed song info (Title, Artist, Album, Thumbnail) always perfectly matches the audio.
- **🚫 Zero-Repeat Engine**: Smart session-wide tracking ensures you never hear the same song twice.
- **🧠 AI Mood Engine**: Simply tell MELOXI how you feel (e.g., `/sad`, `/romantic`) and let the AI curate the perfect playlist.
- **👤 Profile & XP System**: Earn XP for every song you listen to. Level up, unlock exclusive badges, and climb the global leaderboard.
- **💎 Premium System**: Integrated Razorpay payments for unlocking "No-Prefix" mode, priority support, and special flair.
- **🛡️ Advanced Moderation**: Custom prefixes, channel locking (VC and Text), and detailed audit logging for server owners.
- **👑 Owner Dashboard**: Real-time system metrics (CPU/RAM) and global bot control for developers.

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- FFmpeg installed on your system
- A Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))

### Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/yassu9/meloxi.git
   cd meloxi
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   BOT_TOKEN=your_discord_token
   DATABASE_URL=sqlite:///meloxi.db
   OPENAI_API_KEY=your_openai_key
   RAZORPAY_KEY_ID=your_razorpay_id
   RAZORPAY_KEY_SECRET=your_razorpay_secret
   ```

4. **Run the Bot**:
   ```bash
   python bot.py
   ```

## 📜 Commands Summary

| Category | Commands |
| :--- | :--- |
| **Music** | `play`, `skip`, `stop`, `queue`, `loop`, `lyrics`, `autoplay`, `volume` |
| **Moods** | `sad`, `romantic`, `party`, `night`, `workout`, `lofi`, `mashup` |
| **Profile** | `profile`, `level`, `leaderboard`, `setbio` |
| **Admin** | `prefix`, `setchannel`, `setvoice`, `purge`, `setlog`, `features` |
| **Premium** | `premium`, `buy`, `rpsync` |

*For a full list of commands, use `/help` or refer to the [Command List](command_list.md).*

## 🛠️ Tech Stack
- **Language**: Python 3.12
- **Library**: `discord.py`
- **Database**: SQLAlchemy (SQLite/Postgres)
- **AI**: OpenAI GPT-3.5 API
- **Audio**: `yt-dlp`, FFmpeg & Spotify API
- **Payments**: Razorpay SDK

## 🚂 Railway Deployment

1. **GitHub Link**: Connect your repository to Railway.
2. **Database**: Add a **PostgreSQL** service in your Railway project.
3. **Environment Variables**:
   - `DATABASE_URL`: Railway will automatically provide this if you link the Postgres service.
   - `BOT_TOKEN`: Your bot token.
   - `OPENAI_API_KEY`: For AI moods.
4. **Build Config**: The `railway.toml` handles `ffmpeg` and dependencies automatically.

---
*Developed with ❤️ by yassu9*

---

## Web application (migration foundation)

The Discord bot remains intact. The web migration lives in `backend/` and
`frontend/`, and reuses the existing Spotify, JioSaavn, yt-dlp, and SmartLoader
modules without importing Discord commands into API routes.

Spotify links are used for catalogue metadata and matching; browser audio is
resolved through the existing source adapters rather than attempting to stream
Spotify's protected audio directly.

```bash
# 🚀 1-Click Launch (Runs Backend + Web App + Opens Browser)
python start.py
```

Or run manually:
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open `http://localhost:8000`. The FastAPI Swagger docs are available at `http://localhost:8000/docs`.

