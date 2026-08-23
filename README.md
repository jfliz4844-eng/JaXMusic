# JaXMusic

Telegram bot to download audio (yt-dlp) and convert to mp3 (ffmpeg).

This repository contains:
- bot.py: the Telegram bot implementation (uses yt-dlp and ffmpeg)
- Dockerfile: container image that includes ffmpeg
- .github/workflows/ci.yml: manual workflow to build (and optionally push) the Docker image
- deploy_jaxmusic_vps.sh: example deploy script for a VPS (creates venv and systemd service)

Quick start (local, without Docker):
1. Install system ffmpeg and python3-venv
   sudo apt update && sudo apt install -y ffmpeg python3-venv git
2. Create and activate a venv
   python3 -m venv .venv
   source .venv/bin/activate
3. Install Python deps
   pip install --upgrade pip
   pip install -r requirements.txt
4. Run the bot (set TELEGRAM_TOKEN in env first)
   export TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
   python bot.py

Quick start (Docker):
1. Build image
   docker build -t jaxmusic:local .
2. Run container (pass TELEGRAM_TOKEN)
   export TELEGRAM_TOKEN="YOUR_REAL_TOKEN"
   docker run --rm -e TELEGRAM_TOKEN="$TELEGRAM_TOKEN" jaxmusic:local

VPS deploy (example):
- Clone the repo to your VPS (recommended path: /opt/jaxmusic)
- Create a secure env file on the VPS with TELEGRAM_TOKEN (e.g. /etc/jaxmusic.env, chmod 600)
- Run deploy_jaxmusic_vps.sh as sudo to create venv and systemd service
- Ensure the service created uses EnvironmentFile=/etc/jaxmusic.env (script does this)

Security:
- Do NOT commit TELEGRAM_TOKEN or any secret into the repository. Use GitHub Secrets for CI and secure files (/etc) on servers.
