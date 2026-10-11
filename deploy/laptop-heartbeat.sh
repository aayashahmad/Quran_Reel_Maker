#!/bin/sh
# Main computer side of the failover (see failover-server.sh). Run every 15 seconds:
#   laptop-heartbeat.sh ubuntu@SERVER_IP ~/.ssh/KEY
# It tells the backup server "the site is being served here" only while that is true:
# the local website answers and this computer's tunnel is running.
# keep the admin switches the same on both computers
/usr/bin/python3 "$(dirname "$0")/sync-settings.py" "$1" "$2" "$(dirname "$0")/../data/settings.json" || true
curl -sf -o /dev/null --max-time 5 http://127.0.0.1:5050/ || exit 0
# the tunnel must be connected to Cloudflare, not just running: after sleep its process exists while its
# connections are dead (needs "metrics: 127.0.0.1:20241" in ~/.cloudflared/config.yml)
# A tunnel can also get stuck with no connections after a network drop, without exiting (so launchd never
# restarts it). If it has had none for 60 s while the internet works, restart it (at most every 2 minutes).
DOWN="$HOME/Library/Caches/quran-tunnel-down-since"
if ! curl -sf --max-time 3 http://127.0.0.1:20241/ready | grep -q '"readyConnections":[1-9]'; then
  now=$(date +%s)
  [ -f "$DOWN" ] || echo "$now" > "$DOWN"
  if [ $((now - $(cat "$DOWN"))) -ge 60 ] && curl -sf -o /dev/null --max-time 5 https://www.cloudflare.com/cdn-cgi/trace; then
    echo "$(date '+%F %T') tunnel had no connections for $((now - $(cat "$DOWN"))) s: restarting it"
    launchctl kickstart -k "gui/$(id -u)/com.quranreel.domain"
    echo $((now + 60)) > "$DOWN"         # give it time to connect before trying again
  fi
  exit 0
fi
rm -f "$DOWN"
# ServerAlive: give up on a connection that stops answering (a hung ssh would block every later run)
exec ssh -i "$2" -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 "$1" touch .laptop-alive
