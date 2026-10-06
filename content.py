"""Titles, descriptions, tags and card text for a reel."""
from config import RECITER_NAME, URDU_NAME, URDU_AUDIO_NAME


def reel_info(items, part, parts, full):
    f, l = items[0], items[-1]
    rng = f"{f['ayah']}" if f is l else f"{f['ayah']}-{l['ayah']}"
    return {
        "surah": f["surah"], "surah_en": f["surah_en"], "surah_ar": f["surah_ar"],
        "first": f["ayah"], "last": l["ayah"], "range": rng,
        "full": full, "part": part, "parts": parts,
        "label": f"Full Surah  •  {len(items)} Ayat" if full else
                 (f"Ayah {rng}" if f is l else f"Ayat {rng}"),
        "part_label": f"Part {part} of {parts}" if parts > 1 else "",
        "ref": f"{f['surah']}:{rng}",
    }


def metadata(items, info, read_urdu=True):
    en, ar, rng = info["surah_en"], info["surah_ar"], info["range"]
    tag = "".join(ch for ch in en if ch.isalnum())

    if info["full"]:
        title = f"Surah {en} Full | Urdu Tarjuma | {ar} #Shorts"
    elif info["parts"] > 1:
        title = f"Surah {en} Part {info['part']}/{info['parts']} (Ayat {rng}) | Urdu Tarjuma #Shorts"
    else:
        title = f"Surah {en} {info['ref']} | Urdu Tarjuma | Quran Recitation #Shorts"
    if len(title) > 100:
        title = title.replace(" | Quran Recitation", "").replace(f" | {ar}", "")[:100]

    which = "Full Surah" if info["full"] else f"Ayat {rng}" + (
        f" (Part {info['part']} of {info['parts']})" if info["parts"] > 1 else "")
    head = (f"Surah {en} ({ar}) — Surah no. {info['surah']} — {which}\n"
            f"Quran recitation with Urdu translation (اردو ترجمہ).\n\n")
    credits = (f"\n\nRecitation: {RECITER_NAME}\nUrdu translation: {URDU_NAME}\n"
               + (f"Urdu audio: {URDU_AUDIO_NAME}\n" if read_urdu else "")
               + f"\n#Quran #QuranUrdu #Surah{tag} #UrduTarjuma #Tilawat #Islam #Shorts")
    body = ("\n".join(f"{x['ar']} ({x['ayah']})" for x in items) + "\n\nاردو ترجمہ:\n"
            + "\n".join(f"{x['ur']} ({x['ayah']})" for x in items))
    room = 4900 - len(head) - len(credits)
    if len(body) > room:
        body = body[:room - 2].rsplit("\n", 1)[0] + "\n…"
    desc = head + body + credits

    tags = ["Quran", "Quran with Urdu translation", "Quran Urdu tarjuma", "Urdu tarjuma",
            f"Surah {en}", f"Surah {en} Urdu", f"Surah {en} full" if info["full"] else f"Surah {en} {rng}",
            "Tilawat", "Quran recitation", "Mishary Alafasy", "Islamic shorts", "Quran shorts",
            "قرآن", "اردو ترجمہ", "تلاوت"]
    out, total = [], 0
    for t in tags:                      # YouTube allows about 500 characters of tags
        if total + len(t) + 1 > 480:
            break
        out.append(t)
        total += len(t) + 1
    return title, desc, out
