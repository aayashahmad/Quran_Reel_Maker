#!/bin/bash
# Sets up the website on an Ubuntu server (e.g. Oracle Cloud Always Free, Arm or x86).
# Run as the normal login user (ubuntu), after copying the Cloudflare tunnel files to ~/.cloudflared/:
#   bash server-setup.sh
# Afterwards the site runs as two services that start on boot and restart on failure:
#   quran-web     the website (gunicorn on 127.0.0.1:5050)
#   quran-tunnel  the Cloudflare tunnel that serves it at quranreelmaker.xyz
# With FAILOVER=1 the tunnel is installed but not started: this server is a backup that
# failover-server.sh switches on only while the main computer is offline.
set -euo pipefail

REPO=https://github.com/aayashahmad/Quran_Reel_Maker.git
APP=$HOME/quran-reel-site
TUNNEL_DIR=$HOME/.cloudflared

echo "== System packages"
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q ffmpeg libraqm0 libfribidi0 python3-venv git curl

echo "== Cloudflare tunnel program"
if ! command -v cloudflared >/dev/null; then
  arch=$(dpkg --print-architecture)       # arm64 on Oracle's free Ampere servers, amd64 otherwise
  curl -fsSL -o /tmp/cloudflared.deb \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$arch.deb"
  sudo dpkg -i /tmp/cloudflared.deb
fi

echo "== Website code"
if [ -d "$APP/.git" ]; then git -C "$APP" pull -q; else git clone -q "$REPO" "$APP"; fi
cd "$APP"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt gunicorn

echo "== Quran text and fonts (first time only, about a minute)"
.venv/bin/python -c "from quran_data import load_quran; load_quran(); import video; video.ensure_fonts()"

echo "== Tunnel settings"
cred=$(ls "$TUNNEL_DIR"/*.json 2>/dev/null | head -1 || true)
[ -n "$cred" ] || { echo "Copy the tunnel's .json credentials file to $TUNNEL_DIR first."; exit 1; }
cat > "$TUNNEL_DIR/config.yml" <<EOF
tunnel: $(basename "$cred" .json)
credentials-file: $cred
ingress:
  - hostname: quranreelmaker.xyz
    service: http://localhost:5050
  - hostname: www.quranreelmaker.xyz
    service: http://localhost:5050
  - service: http_status:404
EOF
cloudflared tunnel --config "$TUNNEL_DIR/config.yml" ingress validate

echo "== Services"
# Small servers (under 4 GB memory): keep ffmpeg to one thread so a render fits in memory
lowmem=""; [ "$(awk '/MemTotal/ {print int($2 / 1024)}' /proc/meminfo)" -lt 4000 ] && lowmem="Environment=FFMPEG_THREADS=1"
sudo tee /etc/systemd/system/quran-web.service >/dev/null <<EOF
[Unit]
Description=Quran Reel Maker website
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$APP
$lowmem
ExecStart=$APP/.venv/bin/gunicorn web:app --bind 127.0.0.1:5050 --workers 1 --threads 8 --timeout 0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/quran-tunnel.service >/dev/null <<EOF
[Unit]
Description=Cloudflare tunnel for quranreelmaker.xyz
After=network-online.target quran-web.service
Wants=network-online.target

[Service]
User=$USER
ExecStart=/usr/bin/cloudflared tunnel --no-autoupdate --config $TUNNEL_DIR/config.yml run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now quran-web
sudo systemctl restart quran-web
if [ "${FAILOVER:-0}" = 1 ]; then
  sudo systemctl disable --now quran-tunnel 2>/dev/null || true
else
  sudo systemctl enable --now quran-tunnel
  sudo systemctl restart quran-tunnel
fi

echo "== Check"
for i in $(seq 1 30); do curl -sf -o /dev/null http://127.0.0.1:5050/ && break; sleep 2; done
curl -s -o /dev/null -w "website: HTTP %{http_code}\n" http://127.0.0.1:5050/
systemctl is-active quran-web quran-tunnel || true
echo "Done. To update later:  cd $APP && git pull && sudo systemctl restart quran-web"
