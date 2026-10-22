"""Draws the text layers and puts the video together with FFmpeg: an animated background (the site's own
procedural loops, with a slow camera move and a colour grade per theme), the text layers timed to the narration,
and the narration audio. Output: 1080x1920 H.264 + AAC MP4, plus a thumbnail and a metadata JSON."""
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import backgrounds
import video
from video import font, shape, text_w, wrap, GOLD, GOLD2, WHITE, MUTED
from hadith_shorts import settings, themes, tts

W, H = settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT
AR_FONT, EN_FONT = "Amiri-Regular.ttf", "Amiri-Regular.ttf"
INTRO, OUTRO = 3.0, 4.0
DIMMED = (165, 185, 175)
FADE = 0.6


def _fit(text, fname, max_w, max_h, size, min_size, lh, rtl):
    while True:
        f = font(fname, size)
        lines = wrap(text, f, max_w, rtl, "ar" if rtl else None)
        if len(lines) * size * lh <= max_h or size <= min_size:
            return f, size, lines
        size -= 2


def _center(d, text, fname, size, y, color, rtl=False):
    f = font(fname, size)
    s = shape(text) if rtl else text
    w = text_w(f, s, rtl, "ar")
    d.text(((W - w) / 2, y), s, font=f, fill=color, **(dict(direction="rtl", language="ar") if rtl and video.RAQM else {}))


def _arabic(d, text, y, max_h, size=58, min_size=36, color=WHITE):
    f, size, lines = _fit(text, AR_FONT, W - 160, max_h, size, min_size, 1.85, True)
    for ln in lines:
        s = shape(ln)
        w = text_w(f, s, True, "ar")
        d.text(((W - w) / 2, y), s, font=f, fill=color, **(dict(direction="rtl", language="ar") if video.RAQM else {}))
        y += int(size * 1.85)
    return y


def _english(d, parts, lit, y, max_h):
    """The whole translation, the part being read in bright white, the rest dimmed."""
    text = " ".join(parts)
    f, size, _ = _fit(text, EN_FONT, W - 150, max_h, 46, 30, 1.45, False)
    space = text_w(f, " ", False)
    line_h = int(size * 1.45)
    words = [(w, i) for i, p in enumerate(parts) for w in p.split()]
    lines, cur, cur_w = [], [], 0
    for w, i in words:
        ww = text_w(f, w, False)
        if cur and cur_w + space + ww > W - 150:
            lines.append((cur, cur_w))
            cur, cur_w = [], 0
        cur_w += (space if cur else 0) + ww
        cur.append((w, i, ww))
    if cur:
        lines.append((cur, cur_w))
    for line, lw in lines:
        x = (W - lw) / 2
        for w, i, ww in line:
            d.text((x, y), w, font=f, fill=WHITE if i == lit else DIMMED if lit is not None else WHITE)
            x += ww + space
        y += line_h
    return y


def _layer():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _finish(img, path):
    video.brand(ImageDraw.Draw(img), W, H)
    video.shadowed(img).save(path)


def intro_layer(h, title, path):
    img, d = _layer()
    _center(d, "DAILY SAHIH HADITH", EN_FONT, 40, 420, GOLD)
    d.line([(W / 2 - 160, 490), (W / 2 + 160, 490)], fill=GOLD, width=2)
    hook = h.arabic.split("،")[0] if len(h.arabic.split("،")[0].split()) <= 8 else " ".join(h.arabic.split()[:6]) + " …"
    _arabic(d, hook, 600, 420, 84, 56, GOLD2)
    _center(d, title, EN_FONT, 72, 1130, WHITE)
    _center(d, h.citation, EN_FONT, 44, 1240, MUTED)
    _finish(img, path)


def main_layer(h, parts, lit, path):
    img, d = _layer()
    _center(d, "DAILY SAHIH HADITH", EN_FONT, 34, 150, GOLD)
    y = _arabic(d, h.arabic, 240, 640)
    if h.arabic_is_excerpt:
        _center(d, "(the Prophet's ﷺ words, from the full narration)", EN_FONT, 26, y + 2, MUTED)
        y += 40
    d.line([(W / 2 - 180, y + 24), (W / 2 + 180, y + 24)], fill=GOLD, width=2)
    _english(d, parts, lit, y + 64, H - (y + 64) - 330)
    _center(d, f"{h.citation}" + (f" · {h.book}" if h.book else ""), EN_FONT, 34, H - 250, GOLD)
    _finish(img, path)


def outro_layer(h, reflection, path):
    img, d = _layer()
    _center(d, h.citation, EN_FONT, 66, 520, GOLD2)
    if h.book:
        _center(d, f"Book of {h.book}" if not h.book.lower().startswith("the book") else h.book, EN_FONT, 38, 620, WHITE)
    _center(d, h.url.replace("https://", ""), EN_FONT, 36, 700, MUTED)
    _center(d, f"English: {h.translator}", EN_FONT, 30, 770, MUTED)
    if reflection:
        _center(d, "Reflection (not part of the hadith)", EN_FONT, 30, 950, GOLD)
        f, size, lines = _fit(reflection, EN_FONT, W - 200, 240, 44, 32, 1.4, False)
        y = 1000
        for ln in lines:
            w = text_w(f, ln, False)
            d.text(((W - w) / 2, y), ln, font=f, fill=WHITE)
            y += int(size * 1.4)
    _center(d, "Learn it · Live it · Share it", EN_FONT, 50, 1350, WHITE)
    _finish(img, path)


def thumbnail(h, title, style, path):
    frame = Path(path).with_suffix(".bg.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", str(backgrounds.loop(style)), "-frames:v", "1",
                    "-vf", "scale=1280:-2,crop=1280:720", str(frame)], check=True)
    img = Image.open(frame).convert("RGBA")
    frame.unlink()
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    hook = h.arabic.split("،")[0] if len(h.arabic.split("،")[0].split()) <= 8 else " ".join(h.arabic.split()[:6]) + " …"
    f = font(AR_FONT, 92)
    s = shape(hook)
    while text_w(f, s, True, "ar") > 1160 and f.size > 50:
        f = font(AR_FONT, f.size - 6)
    d.text(((1280 - text_w(f, s, True, "ar")) / 2, 150), s, font=f, fill=GOLD2,
           **(dict(direction="rtl", language="ar") if video.RAQM else {}))
    for text, size, y, color in (("DAILY SAHIH HADITH", 40, 60, GOLD), (title, 78, 420, WHITE), (h.citation, 46, 540, GOLD)):
        f = font(EN_FONT, size)
        d.text(((1280 - text_w(f, text, False)) / 2, y), text, font=f, fill=color)
    Image.alpha_composite(img, video.shadowed(over)).convert("RGB").save(path, "JPEG", quality=90)


def build(h, out_dir, log=print):
    """Narration, layers and video for one hadith. Returns a dict with the files and the scene plan."""
    out_dir = Path(out_dir)
    work = out_dir / "work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    tid = themes.detect(h.english)
    title = themes.theme(tid)[0]

    parts = tts.segments(h.english)
    log(f"Narrating {len(parts)} parts ({settings.TTS_ENGINE})")
    segs, audio = [], []
    arabic = tts.arabic_recording(h) if settings.NARRATION_MODE == "ar_en" else None
    if settings.NARRATION_MODE == "ar_en" and not arabic:
        log("No approved Arabic recording for this hadith: English narration only")
    for i, p in enumerate(parts):
        f = work / f"en{i}.mp3"
        segs.append({"text": p, "seconds": tts.speak(p, f) + settings.PAUSE_SECONDS, "file": f})

    plan = themes.scene_plan(h, tid, segs, INTRO, OUTRO)
    style = plan["style"]
    reflection = plan["reflection"] if settings.INCLUDE_REFLECTION else ""

    # text layers and their times
    layers = [(work / "intro.png", INTRO + (tts.duration(arabic) + 0.4 if arabic else 0))]
    intro_layer(h, title, layers[0][0])
    for i, s in enumerate(segs):
        p = work / f"main{i}.png"
        main_layer(h, parts, i, p)
        layers.append((p, s["seconds"]))
    p = work / "outro.png"
    outro_layer(h, reflection, p)
    layers.append((p, OUTRO))
    total = sum(sec for _, sec in layers)
    if total > settings.VIDEO_MAX_SECONDS:
        raise ValueError(f"the video would be {total:.0f}s, more than {settings.VIDEO_MAX_SECONDS:.0f}s")

    lst = work / "layers.txt"
    lst.write_text("".join(f"file '{p.name}'\nduration {sec:.3f}\n" for p, sec in layers) + f"file '{layers[-1][0].name}'\n")

    # audio: (Arabic recording) + English parts with pauses, placed at their layer times
    inputs, chains, t = [], [], INTRO - 0.4
    if arabic:
        inputs += ["-i", str(arabic)]
        chains.append(f"[{len(inputs) // 2 - 1 + 2}:a]adelay={int((INTRO - 0.4) * 1000)}|{int((INTRO - 0.4) * 1000)}[a0]")
        t = INTRO + tts.duration(arabic)
    for s in segs:
        inputs += ["-i", str(s["file"])]
        k = len(inputs) // 2 - 1 + 2
        chains.append(f"[{k}:a]aresample=44100,adelay={int(t * 1000)}|{int(t * 1000)}[a{len(chains)}]")
        t += s["seconds"]
    mix = "".join(f"[a{i}]" for i in range(len(chains)))
    zoom = {"zoom-in": "1+0.06*t/{T}", "zoom-out": "1.06-0.06*t/{T}", "pan-up": "1.06"}[plan["camera"]].format(T=total)
    bgf = (f"[0:v]scale={W}:{H},fps=30,scale=w='ceil({W}*({zoom})/2)*2':h='ceil({H}*({zoom})/2)*2':eval=frame,"
           f"crop={W}:{H}:x='(iw-{W})/2':y='{'(ih-%d)*(1-t/%f)' % (H, total) if plan['camera'] == 'pan-up' else '(ih-%d)/2' % H}',"
           f"{plan['grade']},vignette=PI/5,setsar=1[bg]")
    graph = ";".join([bgf, "[1:v]format=rgba[ov]",
                      f"[bg][ov]overlay=0:0:format=auto:eof_action=repeat,fade=t=in:st=0:d={FADE},"
                      f"fade=t=out:st={total - FADE:.3f}:d={FADE},format=yuv420p[v]"] + chains +
                     [f"{mix}amix=inputs={len(chains)}:normalize=0,apad,atrim=0:{total:.3f},"
                      f"afade=t=out:st={total - FADE:.3f}:d={FADE}[a]"])
    mp4 = out_dir / f"{h.collection}_{h.number}.mp4"
    log("Rendering the video")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(backgrounds.loop(style)),
           "-f", "concat", "-safe", "0", "-i", str(lst), *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
           "-t", f"{total:.3f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", str(mp4)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-800:]}")
    thumb = out_dir / f"{h.collection}_{h.number}_thumbnail.jpg"
    thumbnail(h, title, style, thumb)
    plan["captions"] = []
    t = layers[0][1]
    for s in segs:
        plan["captions"].append({"start": round(t, 3), "end": round(t + s["seconds"] - settings.PAUSE_SECONDS, 3), "text": s["text"]})
        t += s["seconds"]
    shutil.rmtree(work, ignore_errors=True)
    return {"video": mp4, "thumbnail": thumb, "seconds": total, "plan": plan, "theme": tid, "title": title}
