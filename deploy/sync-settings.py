"""Keep data/settings.json (the admin switches) the same on the laptop and the backup server.
Run by laptop-heartbeat.sh:  sync-settings.py ubuntu@SERVER_IP ~/.ssh/KEY ~/quran-reel-site/data/settings.json
The copy with the newer "updated" time is copied over the other one."""
import json
import os
import pathlib
import subprocess
import sys

host, key, local = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
REMOTE = "quran-reel-site/data/settings.json"
ssh = ["ssh", "-i", key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host]


def updated(text):
    try:
        return float(json.loads(text).get("updated", 0))
    except (ValueError, AttributeError, TypeError):
        return -1.0                      # damaged: never wins


got = subprocess.run(ssh + [f"cat {REMOTE} 2>/dev/null"], capture_output=True, text=True, timeout=30)
if got.returncode == 255:                # server not reachable: try again next time
    sys.exit(0)
remote = got.stdout if got.returncode == 0 else ""
mine = local.read_text() if local.exists() else ""
r, m = (updated(remote) if remote else 0.0), (updated(mine) if mine else 0.0)
if r > m:
    tmp = local.with_suffix(".tmp")
    tmp.write_text(remote)
    os.replace(tmp, local)
elif m > r:
    subprocess.run(ssh + [f"cat > {REMOTE}.tmp && mv {REMOTE}.tmp {REMOTE}"], input=mine, text=True, timeout=30, check=True)
