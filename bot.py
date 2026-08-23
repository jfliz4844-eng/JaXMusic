#!/usr/bin/env python3
# bot.py
# Minimal Telegram bot that:
# - downloads audio using yt-dlp
# - converts to mp3 with ffmpeg
# - sends the mp3 back to the user
#
# Requirements: python-telegram-bot>=20.x, yt-dlp
# Ensure ffmpeg is installed on the host (apt install ffmpeg or similar).
import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from yt_dlp import YoutubeDL
from telegram import __version__ as TG_VER

# python-telegram-bot v20+ uses asyncio; ensure compatible
try:
    from telegram import Update
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except Exception as e:
    raise RuntimeError(
        "Failed to import python-telegram-bot. "
        "Install python-telegram-bot>=20.x"
    ) from e

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

YTDL_OPTS = {
    "format": "bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    # you can add additional yt-dlp options here
}

URL_RE = re.compile(r"(https?://\S+)")


def blocking_download_and_convert(url: str, out_dir: str) -> str:
    """
    Blocking function to:
    - download best audio with yt-dlp into out_dir
    - convert the downloaded file to mp3 with ffmpeg
    - return path to mp3 file
    """
    logger.info("Starting blocking download for %s", url)
    os.makedirs(out_dir, exist_ok=True)
    ydl_opts = YTDL_OPTS.copy()
    ydl_opts["outtmpl"] = os.path.join(out_dir, "%(title)s.%(ext)s")
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # prepare_filename uses the extracted info to construct filename
        downloaded_path = ydl.prepare_filename(info)
        logger.info("Downloaded file path: %s", downloaded_path)

    # Ensure downloaded file exists
    if not os.path.exists(downloaded_path):
        # yt-dlp can sometimes store in different names; try to find files in out_dir
        candidates = list(Path(out_dir).glob("*"))
        if not candidates:
            raise FileNotFoundError("No file found after yt-dlp download")
        downloaded_path = str(candidates[0])
        logger.warning("Using candidate file: %s", downloaded_path)

    # Convert to mp3 using ffmpeg
    mp3_name = Path(downloaded_path).with_suffix(".mp3")
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        downloaded_path,
        "-vn",
        "-ab",
        "192k",
        "-ar",
        "44100",
        "-y",
        str(mp3_name),
    ]
    logger.info("Running ffmpeg command: %s", " ".join(ffmpeg_cmd))
    proc = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        logger.error("ffmpeg failed: %s", proc.stderr.decode(errors="ignore"))
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode(errors='ignore')}")
    logger.info("Converted to mp3: %s", mp3_name)

    # Optionally remove original downloaded file to save space
    try:
        if downloaded_path != str(mp3_name):
            os.remove(downloaded_path)
    except Exception:
        logger.exception("Failed to remove original downloaded file")

    return str(mp3_name)


async def download_and_convert(url: str) -> tuple[str, str]:
    """Run the blocking download/convert in a thread and return (mp3_path, tmpdir)."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        tmpdir = tempfile.mkdtemp(prefix="jaxmusic_")
        try:
            mp3_path = await loop.run_in_executor(
                pool, blocking_download_and_convert, url, tmpdir
            )
            return str(mp3_path), tmpdir
        except Exception:
            # cleanup on error
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise


def extract_url(text: str) -> str | None:
    if not text:
        return None
    m = URL_RE.search(text)
    if m:
        return m.group(1)
    return None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me a YouTube (or other supported) link or use /download <url> to fetch audio as mp3."
    )


async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Prefer arg passed to /download, otherwise take message text
    args = context.args
    if args:
        url = args[0]
    else:
        url = extract_url(update.message.text)
    if not url:
        await update.message.reply_text(
            "No URL detected. Usage: /download <url> or send a message containing a URL."
        )
        return

    status_msg = await update.message.reply_text("Starting download... (this can take a while)")
    try:
        mp3_path, tmpdir = await download_and_convert(url)
        await status_msg.edit_text("Uploading MP3...")

        # If file is large for Telegram upload, send as document instead of audio
        try:
            size = os.path.getsize(mp3_path)
        except Exception:
            size = 0

        MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB
        try:
            if size and size > MAX_AUDIO_BYTES:
                # send as document
                with open(mp3_path, "rb") as f:
                    await update.message.reply_document(document=f, filename=Path(mp3_path).name)
            else:
                with open(mp3_path, "rb") as f:
                    await update.message.reply_audio(audio=f, filename=Path(mp3_path).name)
            await status_msg.edit_text("Done! Uploaded MP3.")
        finally:
            # Cleanup temporary directory
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                logger.exception("Failed to remove temporary directory")
    except Exception as e:
        logger.exception("Error in download handler")
        await status_msg.edit_text(f"Failed: {e}")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If user sends just a URL, start the download automatically
    text = update.message.text or ""
    url = extract_url(text)
    if url:
        # call same logic as /download
        context.args = [url]
        await cmd_download(update, context)
    else:
        await update.message.reply_text(
            "Send a link (YouTube or other) or use /download <url>."
        )


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_TOKEN environment variable is not set. Set it and re-run the bot."
        )
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("download", cmd_download))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info("Bot started. Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
