"""Short, modern "apply it to your life" reflections on chosen ayat, for social media
status/stories. Uses the Claude API (needs ANTHROPIC_API_KEY)."""
import json
import os

import anthropic

MODEL = "claude-opus-5-5"

LANGUAGES = {
    "roman": "Roman Urdu (Urdu written in English letters, the way young people in Pakistan and India text)",
    "urdu": "Urdu in Urdu script",
    "english": "simple English",
}

SYSTEM = """You write short reflections on Quran ayat for young Muslims (Gen Z) to share as a WhatsApp/Instagram status or story. The goal: help them connect the meaning to their own daily life today - studies, phones and social media, friends, family, stress, career, self-worth, honesty, patience, gratitude.

You are given the reference, the Arabic text and the Urdu translation by Fateh Muhammad Jalandhry. Base the reflection ONLY on what that translation says.

Rules - these matter more than style:
- This is a personal reflection, not tafsir. Do not claim to explain the "real" or hidden meaning, the reason of revelation, or scholarly interpretation.
- Never invent or quote hadith, scholars, stories, numbers or sources. Never give fatwas or religious rulings (halal/haram, how to pray, etc.).
- Never rewrite, paraphrase or present your words as if they were the Quran or the translation. Do not include Arabic Quran text in your output.
- Respectful at all times. Modern and warm is good; jokes, memes, sarcasm or slang about Allah, the Prophet or the Quran are not.
- Ayat about laws, punishment, war, other faiths or historical events: give a careful general lesson (justice, trust in Allah, keeping promises, etc.). Never apply them to current politics, groups or real people, and never encourage harm.
- If the ayat only name things or are disconnected letters (like Alif Lam Mim), reflect gently on the wider idea (e.g. the Quran as guidance) without guessing their meaning.
- Keep it short and concrete. No preaching or guilt-tripping; encourage instead."""

SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "Punchy hook, at most 8 words"},
        "reflection": {"type": "string", "description": "2-3 short sentences linking the ayat to everyday life today"},
        "action": {"type": "string", "description": "One small practical thing to do today, one sentence"},
        "caption": {"type": "string", "description": "Ready-to-post caption, 1-3 short lines, a few fitting emojis, ends with the reference like (Surah Name 2:153)"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "6-10 hashtags without the # sign"},
    },
    "required": ["headline", "reflection", "action", "caption", "hashtags"],
    "additionalProperties": False,
}


class ReflectionError(Exception):
    pass


def available():
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def generate(items, info, language="roman"):
    """items: the ayat (same surah). Returns dict with headline, reflection, action, caption, hashtags."""
    ayat = "\n\n".join(
        f"{info['surah_en']} {x['surah']}:{x['ayah']}\nArabic: {x['ar']}\nUrdu translation: {x['ur']}"
        for x in items)
    prompt = (f"Surah {info['surah_en']} ({info['surah_ar']}), {info['label']}.\n\n{ayat}\n\n"
              f"Write the reflection, action and caption in {LANGUAGES.get(language, LANGUAGES['roman'])}. "
              "The headline may be in the same language.")
    try:
        resp = anthropic.Anthropic().beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        raise ReflectionError("Claude API key is missing or invalid. Set ANTHROPIC_API_KEY and restart.")
    except anthropic.RateLimitError:
        raise ReflectionError("Too many requests right now. Try again in a minute.")
    except anthropic.APIStatusError as e:
        raise ReflectionError(f"Claude API error ({e.status_code}). Try again.")
    except anthropic.APIConnectionError:
        raise ReflectionError("Could not reach the Claude API. Check the internet connection.")

    if resp.stop_reason == "refusal":
        raise ReflectionError("No reflection was written for these ayat. Try other ayat.")
    if resp.stop_reason == "max_tokens":
        raise ReflectionError("The reflection was cut off. Try again.")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    data = json.loads(text)
    data["hashtags"] = [h.lstrip("#").replace(" ", "") for h in data["hashtags"]][:10]
    return data
