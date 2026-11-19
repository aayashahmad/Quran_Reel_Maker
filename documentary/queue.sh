#!/bin/bash
# Daily (launchd com.quranreel.documentary, 13:45 IST): post the next two Seerah documentary videos, then show them on
# the site. Stops by itself when every episode is up. Stop it early with:
#   launchctl bootout gui/$(id -u)/com.quranreel.documentary
set -u
cd "$(dirname "$0")/.." || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib:/opt/homebrew/lib"
export YOUTUBE_PRIVACY_STATUS=public
echo "$(date) documentary queue"
git pull -q --rebase --autostash || echo "$(date) git pull failed (uploading anyway)"
.venv/bin/python -m documentary.upload_queue 2
git add documentary/published.json
git commit -qm "Documentary: next episodes on YouTube" -- documentary/published.json || exit 0
git pull -q --rebase --autostash && git push -q || echo "$(date) push failed"
(cd "$HOME/quran-reel-site" && git pull -q --rebase --autostash) || echo "$(date) site pull failed"
curl -s -o /dev/null "https://api.indexnow.org/indexnow?url=https://quranreelmaker.xyz/seerah/documentary&key=591cf659eeb874507d48e077c1a3e769"
