#!/bin/bash
# Backup mode for a server set up with FAILOVER=1 server-setup.sh.
# The main computer touches ~/.laptop-alive on this server every 30 seconds (laptop-heartbeat.sh).
# When the heartbeat is older than 50 seconds (main computer off, asleep or offline) the tunnel is started
# and this server serves the site. It stops again only after the heartbeat has been steady for 60 seconds,
# so a sleeping laptop's brief background wake-ups don't switch the site to a computer that is about to sleep.
# Run once:  bash failover-server.sh
set -euo pipefail
HB=$HOME/.laptop-alive

sudo tee /usr/local/bin/quran-failover >/dev/null <<SCRIPT
#!/bin/bash
steady_since=0                       # when the current unbroken run of fresh heartbeats began
while true; do
  now=\$(date +%s)
  age=\$(( now - \$(stat -c %Y "$HB" 2>/dev/null || echo 0) ))
  if [ "\$age" -lt 50 ]; then
    [ "\$steady_since" -eq 0 ] && steady_since=\$now
    if [ \$(( now - steady_since )) -ge 60 ]; then
      systemctl is-active -q quran-tunnel && { echo "main computer back and steady: backup off"; systemctl stop quran-tunnel; }
    fi
  else
    steady_since=0
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
