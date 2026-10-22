"""The visual theme of a hadith, from words in its translation, and the scene plan built from it.
These are creative moods (dawn for intention, water for patience...), never claims about the hadith's history.
No people, prophets or angels are ever drawn: the backgrounds are the site's own abstract animated scenes."""
import re

# id: (title, keywords, background styles, colour grade, camera, closing reflection - only shown if enabled)
THEMES = {
    "intention": ("On Intentions", r"intention|intend|sincer|for the sake of allah|show off",
                  ["rays", "aurora"], "dawn", "zoom-in", "Check your intention before you act: do it for Allah."),
    "patience": ("On Patience", r"patien|calamit|affliction|harm befalls|trial|grief|sorrow",
                 ["waves", "night"], "cool", "pan-up", "Hardship is not wasted: be patient and hope in Allah."),
    "charity": ("On Charity", r"charit|sadaqa|spend|give in|zakat|feed|poor|needy",
                ["lanterns", "particles"], "warm", "zoom-in", "Give, even a little: charity never decreases wealth."),
    "knowledge": ("On Knowledge", r"knowledge|learn|scholar|teach|understanding of the religion",
                  ["rosette", "rays"], "dawn", "pan-up", "Seek knowledge, act on it, and share it."),
    "mercy": ("On Mercy", r"merc|compassion|kind to|gentle|rifq",
              ["aurora", "waves"], "cool", "zoom-out", "Be merciful to others, and Allah will be merciful to you."),
    "prayer": ("On Prayer", r"\bprayer|salat|prostrat|mosque|wudu|ablution|night prayer",
               ["mosque", "arches"], "dawn", "zoom-in", "Guard your prayers: they are your meeting with Allah."),
    "honesty": ("On Truthfulness", r"truth|lie|lying|liar|honest|trust|betray|promise",
                ["waves", "stars"], "cool", "pan-up", "Speak the truth, even when it is hard."),
    "gratitude": ("On Gratitude", r"grateful|thank|gratitude|blessing|favour|favor",
                  ["rays", "desert"], "warm", "zoom-out", "Count your blessings and thank Allah for them."),
    "character": ("On Good Character", r"character|manners|smile|neighbou?r|guest|kinship|relatives|brother",
                  ["arches", "rosette"], "warm", "zoom-in", "Good character is among the heaviest deeds on the Scale."),
    "parents": ("On Parents", r"\bmother|\bfather|parents|dutiful",
                ["lanterns", "arches"], "warm", "zoom-out", "Honour your parents while you still can."),
    "dua": ("On Supplication", r"supplicat|invoke|\bdua\b|ask allah|remembrance|glorif|subhan",
            ["night", "stars"], "cool", "pan-up", "Call upon Allah: He is near and He answers."),
    "repentance": ("On Repentance", r"repent|forgive|forgiveness|sin",
                   ["aurora", "night"], "dawn", "zoom-in", "Turn back to Allah: His forgiveness is greater than any sin."),
    "hereafter": ("On the Hereafter", r"paradise|hell|\bfire\b|day of resurrection|grave|death|die",
                  ["desert", "night"], "cool", "zoom-out", "Prepare today for the life that does not end."),
    "faith": ("On Faith", r"faith|believ|iman|islam is|religion",
              ["stars", "rosette"], "dawn", "zoom-in", "Strengthen your faith with deeds, every day."),
    "fasting": ("On Fasting", r"fast|ramadan|suhur|iftar",
                ["lanterns", "night"], "warm", "pan-up", "Fasting is a shield: guard it with good words."),
    "quran": ("On the Quran", r"qur'?an|recit",
              ["rosette", "rays"], "dawn", "zoom-in", "Make the Quran part of every day."),
}
DEFAULT = ("Daily Hadith", "", ["particles", "stars"], "dawn", "zoom-in", "Learn it, live it, and share it.")
GRADES = {   # ffmpeg colour grade per mood (no flashing, gentle contrast)
    "dawn": "colorbalance=rs=.06:gs=.02:bs=-.05:rm=.05:bm=-.03,eq=saturation=1.05",
    "warm": "colorbalance=rs=.08:gs=.03:bs=-.07,eq=saturation=1.08",
    "cool": "colorbalance=rs=-.04:gs=.01:bs=.06,eq=saturation=1.0",
}


def detect(english):
    """The theme whose keywords appear most often in the translation (the default when none do)."""
    text = english.lower()
    best, hits = None, 0
    for tid, (_, words, *_rest) in THEMES.items():
        n = len(re.findall(words, text))
        if n > hits:
            best, hits = tid, n
    return best or "default"


def theme(tid):
    return THEMES.get(tid, DEFAULT)


def scene_plan(h, tid, segments, intro, outro):
    """A structured, readable plan of the video (also saved with it as JSON)."""
    title, _, styles, grade, camera, reflection = theme(tid)
    style = styles[h.number % len(styles)]                 # varies between hadith of the same theme
    plan = [{"scene": "opening", "description": f"{title}: the opening words of the hadith in Arabic",
             "background": style, "camera": camera, "lighting": grade, "animation": "fade in, soft halo text",
             "duration": intro, "captions": "hook (Arabic) + title", "transition": "fade from black"}]
    for i, s in enumerate(segments):
        plan.append({"scene": f"narration {i + 1}", "description": "Arabic shown; English read aloud, this part lit",
                     "background": style, "camera": camera, "lighting": grade, "animation": "caption highlight",
                     "duration": round(s["seconds"], 2), "captions": s["text"], "transition": "cut"})
    plan.append({"scene": "closing", "description": "reference, source link and invitation to share",
                 "background": style, "camera": camera, "lighting": grade, "animation": "fade out",
                 "duration": outro, "captions": h.citation, "transition": "fade to black"})
    return {"theme": tid, "title": title, "style": style, "grade": GRADES[grade], "camera": camera,
            "reflection": reflection, "scenes": plan}
