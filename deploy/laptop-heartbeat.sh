#!/bin/sh
# Main computer side of the failover (see failover-server.sh). Run every 30 seconds:
#   laptop-heartbeat.sh ubuntu@SERVER_IP ~/.ssh/KEY
# It tells the backup server "the site is being served here" only while that is true:
# the local website answers and this computer's tunnel is running.
# keep the admin switches the same on both computers
/usr/bin/python3 "$(dirname "$0")/sync-settings.py" "$1" "$2" "$(dirname "$0")/../data/settings.json" || true
curl -sf -o /dev/null --max-time 5 http://127.0.0.1:5050/ || exit 0
pgrep -qf "cloudflared.*config.yml.*run" || exit 0
# ServerAlive: give up on a connection that stops answering (a hung ssh would block every later run)
exec ssh -i "$2" -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 "$1" touch .laptop-alive
