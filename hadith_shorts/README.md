# Daily Sahih Hadith Shorts

Two authentic hadith from Sahih al-Bukhari or Sahih Muslim a day: 12:00 IST in English (voice: Andrew) and 20:00 IST
in Urdu (voice: Asad, Urdu text from the dataset's Urdu edition); see SLOT_LANGS and VIDEOS_PER_DAY, as a 1080×1920 YouTube Short. It lives in the
same repository as quranreelmaker.xyz but is separate from the website: the site never imports it, and it only
reuses the shared hadith data, fonts, animated backgrounds and the YouTube login.

## How a video is made
1. **Choose**: the next unused reference from a fixed shuffled list of general-audience books (faith, knowledge,
   manners, supplication, heart-softening...), 18–95 English words, with a clear quote of the Prophet's ﷺ words.
2. **Verify**: the hadith's sunnah.com page is opened: the citation number and words of the English and Arabic must
   match. Failures are recorded and that hadith is never used. Any reference can be made by hand with `--ref`.
3. **Narrate**: the English is split into caption parts; each part is spoken into its own file, so every caption's
   timing comes from the real audio length. The Arabic is shown, not synthesised (see *Arabic audio*).
4. **Visuals**: a theme from the translation (intention, patience, charity...) picks one of the site's 11 procedural
   animated backgrounds, a camera move and a colour grade. No people, prophets or angels are ever drawn.
5. **Render** with FFmpeg: opening hook (Arabic + topic), the Arabic with the English lit part by part, and a closing
   card (reference, sunnah.com link, translator). H.264 + AAC, thumbnail and a metadata JSON with the scene plan.
6. **Check**: Arabic shaping (libraqm), source text, size, length, codecs and audio level.
7. **Upload** (only if `ENABLE_PUBLICATION=true`) with the configured privacy, optionally scheduled.

## Commands
```
DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python -m pip install -r hadith_shorts/requirements.txt  # once
.venv/bin/python -m hadith_shorts make --ref bukhari:1              # a video, no upload
.venv/bin/python -m hadith_shorts make --ref bukhari:1 --upload     # ... uploaded (privacy from settings)
.venv/bin/python -m hadith_shorts daily                             # the daily job
.venv/bin/python -m hadith_shorts status                            # recent videos and log
.venv/bin/python -m hadith_shorts resolve 2026-10-22 <id|none>      # settle an upload with an unknown result
.venv/bin/python -m pytest tests -q                                 # tests (RUN_NETWORK_TESTS=1 for sunnah.com)
```
On this Mac, prefix commands with `DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib:/opt/homebrew/lib` (Homebrew's Python
needs Homebrew's expat; without it pip and uv fail with "platform.mac_ver() returned an empty value").
`TTS_ENGINE=say` uses the Mac's own voice for quick tests without the internet.

## Settings
See `.env.example` in this folder. Important: `ENABLE_PUBLICATION` (default false), `YOUTUBE_PRIVACY_STATUS`
(private → unlisted → public), `PUBLISH_TIME` + `TIMEZONE` for scheduled public videos.

## YouTube login
The same OAuth login as the Quran poster (YouTube Data API v3, scope `youtube.upload`): `token.json` here, or the
`YT_TOKEN_JSON` GitHub secret. Never share your Google password; to log in again run `./run.sh auth`.
Uploads from an unaudited Google Cloud project may be forced to private until the YouTube API audit passes.

## Daily schedule
- **GitHub (recommended, runs with the laptop off):** `.github/workflows/hadith.yml`. Remove the `#`s before
  `schedule:` to turn it on. Repository variables: `HADITH_PUBLISH=true` to upload, `HADITH_PRIVACY`
  (private / unlisted / public), `HADITH_PUBLISH_TIME` (e.g. `18:00`). Each run keeps the video as a downloadable
  artifact for 14 days and commits `history.sqlite`.
- **macOS (launchd):** a LaunchAgent running `cd ~/quran-reel-site && .venv/bin/python -m hadith_shorts daily`
  with `StartCalendarInterval` Hour 12; it only runs while the Mac is awake.

## Database (`history.sqlite`, kept in git)
- `hadith(ref, citation, url, theme, verified, detail, checked_at)`: each source check and its result.
- `videos(id, day, ref, title, path, status, youtube_id, privacy, publish_at, error, created, updated)`:
  status `rendered → uploading → uploaded` (or `failed`). One `uploading/uploaded` video per day is enforced by a
  unique index, and a hadith that was uploaded is never chosen again.
- `log(at, level, ref, message)`.

Sample record: `videos: day=2026-10-22 ref=bukhari:1 title="On Intentions | Sahih al-Bukhari 1 | Daily Sahih Hadith #Shorts" status=rendered`.

## Safety and recovery
- Running `daily` twice does nothing the second time. If a run dies during an upload, the video stays `uploading`
  and the job stops until you check YouTube Studio and run `resolve` (no risk of a second copy).
- If the upload fails before reaching YouTube (e.g. expired login), the made video is kept and only the upload is
  retried next run.

## Sources, rights and limits
- **Text:** Arabic and English from fawazahmed0/hadith-api (described by its author as free to use). English
  translators: Dr. Muhammad Muhsin Khan (Bukhari), Abdul Hamid Siddiqui (Muslim), credited in every video. The
  printed translations have publishers; if you need certainty for a monetised channel, ask the publisher
  (Darussalam for Muhsin Khan) or use a translation with an explicit open licence.
- **Local:** rendering, backgrounds, checks, database. **Internet:** sunnah.com checks, edge-tts voices, YouTube.
- **edge-tts** uses Microsoft Edge's read-aloud service through an unofficial package: free, but it can change or
  stop without notice. The job then fails with a clear TTS error and nothing is published.
- **Arabic audio:** AI voices are not reliable for classical Arabic with full vowels, so Arabic is never synthesised.
  For `NARRATION_MODE=ar_en`, put an approved human recording at `arabic_audio/<collection>_<number>.mp3`.
- YouTube API quota: one upload ≈ 1,600 of the default 10,000 units a day.

## Troubleshooting
- *"libraqm is not available"*: install it (`brew install libraqm`, or `apt install libraqm0`).
- *"edge-tts failed"*: no internet or the service changed; try again, or `pip install -U edge-tts`.
- *"source check FAILED"*: sunnah.com shows a different text or number for that reference; it is skipped for good.
- *"invalid_grant"*: the YouTube login expired; run `./run.sh auth` and update the `YT_TOKEN_JSON` secret.
- *"an earlier upload's result is unknown"*: see Safety and recovery.
