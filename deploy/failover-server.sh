#!/bin/bash
# Backup mode for a server set up with FAILOVER=1 server-setup.sh.
# The main computer touches ~/.laptop-alive on this server every 30 seconds (laptop-heartbeat.sh).
# While that heartbeat is fresh this server's tunnel stays off; when it is older than 50 seconds
# (main computer off, asleep or offline) the tunnel is started and this server serves the site.
# Run once:  bash failover-server.sh
set -euo pipefail
HB=$HOME/.laptop-alive

sudo tee /usr/local/bin/quran-failover >/dev/null <<SCRIPT
#!/bin/bash
while true; do
  age=\$(( \$(date +%s) - \$(stat -c %Y "$HB" 2>/dev/null || echo 0) ))
  if [ "\$age" -lt 50 ]; then
    systemctl is-active -q quran-tunnel && { echo "main computer is back: backup off"; systemctl stop quran-tunnel; }
  else
    systemctl is-active -q quran-tunnel || { echo "no heartbeat for \${age}s: backup on"; systemctl start quran-tunnel; }
  fi
  sleep 5
done
SCRIPT
sudo chmod +x /usr/local/bin/quran-failover

sudo tee /etc/systemd/system/quran-failover.service >/dev/null <<UNIT
[Unit]
Description=Serve quranreelmaker.xyz from this backup server while the main computer is offline
After=network-online.target quran-web.service

[Service]
ExecStart=/usr/local/bin/quran-failover
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now quran-failover
systemctl is-active quran-failover
