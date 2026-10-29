# Qissa style guide (read before writing any story)

## What a Qissa is
A 1:30–3:00 vertical story video about a prophet, a Companion, or an event from the Quran / sahih hadith, told in
short scenes with paper-collage visuals, big headings and verified ayah/hadith cards. One story per JSON file in
`qissa/stories/<id>.json`, with English (`en`) and Hinglish (`hi`) in the same file.

## Truth rules (never break)
1. Only what the **Quran** or **Sahih al-Bukhari / Sahih Muslim** say. No Isra'iliyyat, no popular tales, no
   invented dialogue, numbers, names of places, or durations that are not in these sources (e.g. no "40 days in
   the fish", no town name unless the source names it).
2. Every card quotes a **reference only** (`{"ayah": "37:142"}`, `{"hadith": "bukhari:3416"}`): the text is
   pulled from the verified data, never typed into the script.
3. Narration may paraphrase the cited ayah/hadith of that scene in simple words, but must not add meaning.
   Where scholars differ, say less, not more.
4. Fact cards (`{"fact": "100,000+", ...}`) need a `ref` pointing to where the fact is stated.
5. Never depict or describe the appearance of prophets, Companions or angels. Art is only nature, sea, ships,
   fish, towns, plants, sky (see `art` names in qissa/art.py).
6. Every new story has `"status": "draft: to be checked by a scholar before public release"` until a qualified
   person has approved it; only then change it to `"approved by <name>, <date>"`.

## Shape of a story (12–16 scenes)
1. **Hook** (no label): the paradox or the stakes in 3–6 words. "ONE PROPHET | *THREE DARKNESSES*".
2. **Who**: label THE MAN / THE PEOPLE…, the person and an ayah card that introduces them.
3. **The events**, one per scene, each with its ayah card.
4. **The turning point**: the dua / the decision, with its ayah card.
5. **The answer / outcome.**
6. **A sahih hadith** that honours or explains (optional but preferred).
7. **For you**: the lesson turned to the viewer, in second person. "WHEN IT GETS DARK, | *REMEMBER THIS*".
8. **Share**: "SEND THIS TO SOMEONE | *…*".

## Length and parts
A video must stay under 3 minutes (YouTube Shorts). A story longer than about 14 scenes or 2:40 is split with
`"parts": [[1, 8], [9, 16]]` (scene numbers); each part should end on a natural pause and part 2+ should open with
a scene that reminds the viewer where the story is. The queue publishes parts in order.

## Footage
Scenes show real footage from Pexels for their `art` (see qissa/footage.py QUERIES), or a scene's own
`"footage": "<search words>"`. Only people-free subjects (sea, sky, rain, desert, mountains, boats, old towns, plants,
animals the story mentions). `"art": "paper"` scenes stay plain paper (cards, duas, hadith).

## Writing
- Headings: CAPITALS, 2–6 words per line, at most 2 lines split by `|`; the key phrase in `*stars*` (shown red).
- Labels: 1–3 words, CAPITALS ("THE SHIP", "FOR YOU").
- Narration: 1–3 short sentences per scene, spoken calmly; English plain and warm; **Hinglish** = everyday
  Roman Hindi/Urdu as people text it ("Unhone apni qaum ko Allah ki taraf bulaya"), Islamic words in their usual
  spelling (Allah, Quran, dua, imaan, sabr, qayamat, rasool, sallallahu alaihi wasallam).
- Say "peace be upon him" / "sallallahu alaihi wasallam" after **every** mention of the Prophet ﷺ in narration
  (also "Muhammad", "the Prophet's ..."; `check` flags a missing one), "alaihis salam" (AS) for prophets.
- Vary `art` from scene to scene; dark arts for trials, dawn / town-dawn for relief.

## Checks before handing over
`python -m qissa check <id>` must print `ready` (both languages, valid art, every ayah exists, every hadith passes
the sunnah.com check). Then `python -m qissa make <id> --lang all` and look at the video.
