# Qissa story videos

Paper-collage story videos (1:30–3:00, 1080×1920) about prophets and events from the Quran and sahih hadith, in
English (voice: Andrew) and Hinglish (voice: Madhur). Separate from the website and the daily hadith job.

- Scripts: `qissa/stories/<id>.json` (references only for every ayah/hadith; text comes from the verified data).
- Rules: `qissa/STYLE.md`. Owner's changes over time: `qissa/LEARNINGS.md`.
- Agent: `.claude/agents/qissa-writer.md`. In Claude Code, ask e.g. "use the qissa-writer agent to make the
  story of Yusuf (AS)"; it writes the script, checks it, renders both languages, and records your feedback.

```
DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib:/opt/homebrew/lib .venv/bin/python -m qissa list
... -m qissa check yunus
... -m qissa make yunus --lang all        # output/qissa/yunus_en.mp4, yunus_hi.mp4
```
Fonts Anton and Courier Prime (SIL Open Font License) are downloaded into fonts/ from github.com/google/fonts.
