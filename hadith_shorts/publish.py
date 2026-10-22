"""YouTube title, description and tags, and the upload (YouTube Data API v3, the same OAuth login as the
Quran poster: token.json locally or the YT_TOKEN_JSON secret on GitHub). Uploads retry temporary errors;
a video is marked 'uploading' before the upload starts, so a crash never leads to a second copy."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from hadith_shorts import settings, source

HASHTAGS = "#SahihHadith #DailyHadith #Hadith #IslamicShorts #Sunnah #Islam #Shorts"


def metadata(h, title):
    yt_title = f"{title} | {h.citation} | Daily Sahih Hadith #Shorts"
    if len(yt_title) > 100:
        yt_title = f"{title} | {h.citation} #Shorts"[:100]
    lines = [f"{title}: an authentic hadith from {source.NAMES[h.collection]}.", "",
             h.english, "", h.arabic + (" (the Prophet's ﷺ words, from the full narration)" if h.arabic_is_excerpt else ""), "",
             f"Reference: {h.citation}" + (f", {h.book}" if h.book else ""),
             f"Source: {h.url}",
             f"English translation: {h.translator}. Arabic and English text: {source.DATASET}.",
             "Narration: AI voice (Microsoft Edge neural text-to-speech)." if settings.TTS_ENGINE == "edge" else "",
             "", "Learn it, live it, share it. This is the hadith as narrated, not a fatwa: for rulings ask a qualified scholar.",
             "", "Make your own Quran reels, free: https://quranreelmaker.xyz", "", HASHTAGS]
    desc = "\n".join(l for l in lines if l is not None)[:4900]
    tags = ["Sahih Hadith", "Daily Hadith", "Hadith", source.NAMES[h.collection], title.replace("On ", ""),
            "Hadith in English", "Islamic Shorts", "Sunnah", "Prophet Muhammad", "Islam"]
    return yt_title, desc, tags


def publish_at(day):
    """RFC 3339 time to publish (for a scheduled public video), or None to publish at once."""
    if not settings.PUBLISH_TIME or settings.YOUTUBE_PRIVACY_STATUS != "public":
        return None
    hh, mm = (int(x) for x in settings.PUBLISH_TIME.split(":"))
    tz = ZoneInfo(settings.TIMEZONE)
    when = datetime.fromisoformat(day).replace(hour=hh, minute=mm, tzinfo=tz)
    if when <= datetime.now(tz) + timedelta(minutes=15):
        return None
    return when.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def upload(path, title, desc, tags, thumbnail=None, when=None):
    """Upload and return the video id. Scheduled videos are uploaded private with publishAt (YouTube's rule)."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from youtube_upload import _creds

    status = {"privacyStatus": "private" if when else settings.YOUTUBE_PRIVACY_STATUS, "selfDeclaredMadeForKids": False}
    if when:
        status["publishAt"] = when
    yt = build("youtube", "v3", credentials=_creds(), cache_discovery=False)
    req = yt.videos().insert(part="snippet,status", media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True),
                             body={"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "27"},
                                   "status": status})
    resp = None
    while resp is None:
        _, resp = req.next_chunk(num_retries=5)       # retries 5xx and network errors with back-off
    vid = resp["id"]
    if thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg")).execute()
        except HttpError as e:
            print(f"Thumbnail not set (needs a phone-verified channel): {e.reason if hasattr(e, 'reason') else e}")
    return vid
