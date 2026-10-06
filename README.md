# Quran Reels Auto-Poster + Reel Maker website

Posts 2 YouTube Shorts (reels) every day, going through the whole Quran surah by surah, and includes a local website to make your own reels and status/story images.

## What each reel contains
- **Surah by surah.** A short surah becomes one full reel. A long surah is split into even parts (Part 1 of 6, ...), each at most 3 minutes, which YouTube counts as a Short. Parts end at **ruku** boundaries whenever possible, so each part is a complete section.
- A **title card** (surah name, ayat, part), then **Bismillah** as its own frame (not for Surah At-Tawbah, and in Al-Fatiha it is ayah 1), then one frame per ayah.
- Arabic text (Amiri Quran font, with the numbered end-of-ayah sign), plus the **Urdu translation** by Fateh Muhammad Jalandhry on screen.
- **Word-by-word highlighting:** the Arabic word being recited lights up in gold, using Quran.com's word timings for this recitation. While the Urdu is read, the Urdu text brightens and the Arabic dims.
- Audio: recitation by **Mishary Rashid Alafasy**, then the Urdu translation read aloud by **Shamshad Ali Khan** (turn this off with `READ_URDU = False` in `config.py`).
- Sajdah ayat are marked "آیتِ سجدہ" (22:77 is marked "عند الشافعی").
- A **thumbnail**, title, description and tags are made for each reel. Uploads progress in order, and `state.json` remembers where it stopped.
- Posts at **8:00 AM and 8:00 PM IST** (change the times in `.github/workflows/post.yml`).

## One-time setup on this Mac
Already done on this computer: Homebrew `ffmpeg`, `libraqm`, `fribidi`, `expat`, `python@3.12`, and a `.venv` with `requirements.txt` installed. Always run through `./run.sh`; it sets the libraries correctly.

Optional settings go in a `.env` file in this folder (never commit it):
```
ANTHROPIC_API_KEY=sk-ant-...     # for status/story reflections on the website
CHANNEL_TAG=@yourchannel         # shown at the bottom of videos and stories
```

## YouTube login
1. Go to https://console.cloud.google.com and create a project.
2. Enable **YouTube Data API v3**.
3. APIs & Services, then Credentials, then Create OAuth client ID, type **Desktop app**. Download the JSON and save it here as `client_secret.json`.
4. OAuth consent screen: add your own Google account as a **Test user**.
5. Run `./run.sh auth`. A browser opens; log in to your channel. This creates `token.json`.

Notes:
- Uploads from a new, unaudited API project may be forced to *private*. Submit the project for the YouTube API audit (free, takes a few days), or use `YT_PRIVACY=private` and publish by hand until then.
- Custom thumbnails need a phone-verified YouTube channel. Without it the video still uploads; only the thumbnail is skipped.

## Free daily posting with GitHub Actions
1. Create a **private** GitHub repo and push this folder. `client_secret.json`, `token.json` and `.env` are in `.gitignore`; keep it that way.
2. Repo, Settings, Secrets and variables, Actions:
   - New **secret** `YT_TOKEN_JSON`: the full contents of `token.json`
   - Optional new **variable** `CHANNEL_TAG`: e.g. `@yourchannel`
3. Repo, Actions, run **Post Quran Short** once by hand to test.

It then posts twice a day, even when your computer is off.

## Commands
```
./run.sh run --dry-run    # make the next reel only (output/ folder), no upload
./run.sh run --count 1    # make and upload the next reel now
./run.sh status           # show progress
./run.sh web              # start the website at http://localhost:5050
```

## Website
`./run.sh web`, then open http://localhost:5050.
- **Reel:** pick a surah and From/To ayah (or "Full surah"), then Generate video. Preview it, then download the video and thumbnail and copy the title, description and tags.
- **Status / story:** pick up to 3 ayat and a language (Roman Urdu, Urdu or English). You get a 9:16 image with the ayat, the Urdu translation and a short reflection on living it today, plus a ready caption with hashtags. This needs `ANTHROPIC_API_KEY`.

The reflections are written by AI (Claude) from the translation. It is told not to give tafsir, rulings or hadith and to stay respectful, and every image says "reflection, not tafsir". Still, read each one before posting.

## Settings (`config.py`)
- `URDU_EDITION`: `ur.jalandhry` (if you change it, the spoken Urdu audio may no longer match the text)
- `RECITATION_ID`: Quran.com recitation (7 = Alafasy). Another reciter only works if Quran.com has word timings for it.
- `READ_URDU`, `MAX_REEL_SECONDS`, `INTRO_SECONDS`

## Please check
- Have a knowledgeable person (hafiz/aalim) check the first reels for text, translation and audio, especially that the spoken Urdu matches the on-screen Jalandhry translation.
- A single very long ayah (like 2:282 with its Urdu) can be longer than 3 minutes. That one uploads as a normal video, not a Short.
