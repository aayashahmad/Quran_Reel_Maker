#!/bin/bash
# The daily hadith Shorts, made on time by the Mac: 09:00 and 21:00 English (UK voice), 15:00 Urdu in the Hayatus
# Sahaba narrator's voice (OmniVoice, every sentence checked with Whisper). launchd (com.quranreel.hadith) runs this
# every 20 minutes from its own clone (~/hadith-bot); it does nothing unless a video is due. If the Mac is off or
# asleep, GitHub makes the video 90 minutes late instead (Urdu then in the Asad voice). History is shared with GitHub
# through hadith_shorts/history.sqlite in git.
set -u
cd "$(dirname "$0")/.." || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib:/opt/homebrew/lib"
export RUNNER=laptop URDU_ENGINE=omni ENABLE_PUBLICATION=true YOUTUBE_PRIVACY_STATUS=public
export SLOT_TIMES="09:00,15:00,21:00" LAPTOP_SLOTS="1,2,3" SLOT_LANGS="en,ur,en" VIDEOS_PER_DAY=3
[ -f "$HOME/.quranreel-pexels" ] && export PEXELS_API_KEY="$(cat "$HOME/.quranreel-pexels")"

PY="$PWD/.venv/bin/python"
git pull -q --rebase || { echo "$(date) git pull failed"; exit 1; }
"$PY" hadith_shorts/due.py | grep -q "due=true" || exit 0
echo "$(date) making the Mac's hadith video"
"$PY" -m hadith_shorts daily
git add hadith_shorts/history.sqlite
git commit -qm "hadith history (Mac)" && { git pull -q --rebase && git push -q || echo "$(date) push failed"; }
