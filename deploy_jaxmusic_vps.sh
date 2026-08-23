#!/usr/bin/env bash
# Example deploy script for a VPS (Ubuntu)
# USAGE: Run on the VPS as a user with sudo privileges.
set -euo pipefail

APP_DIR="/opt/jaxmusic"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="jaxmusic.service"

echo "Creating application directory..."
sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

echo "Copy files to $APP_DIR (you should scp or git clone the repo here)..."
# Example: git clone https://github.com/<owner>/JaXMusic.git "$APP_DIR"
# Or copy files manually.

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg

echo "Creating venv..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Installing requirements..."
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

deactivate

echo "Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME > /dev/null <<EOF
[Unit]
Description=JaXMusic Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=TELEGRAM_TOKEN=PUT_YOUR_TOKEN_IN_SYSTEMD_ENV_OR_USE_ENV_FILE
ExecStart=$VENV_DIR/bin/python $APP_DIR/bot.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE_NAME

echo "Done. Check logs with: sudo journalctl -u $SERVICE_NAME -f"
