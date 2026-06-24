# LLM analysis prompt

The **Chapters** tool produces a single text file (`playlist_chapters.txt`) where
each entry has a video **title**, **URL**, and **chapter timestamps** (or
`No chapters found`). Paste that file into an LLM (Claude, ChatGPT, …) together
with the prompt below to turn a raw playlist into a study roadmap.

> This same prompt is built into the web UI — open the **Chapters** tab, extract,
> then switch the result panel to **🤖 LLM prompt** and copy it.

---

I'm sharing a text file containing a YouTube playlist. Each entry has:
- Video Title
- Video URL
- Chapters (timestamps + topics), or "No chapters found"
- A `----` separator

I want to learn this subject from scratch to an advanced / production-ready level.
Analyze the chapters of every video and give me:

## 1. Recommended Watch Order
Reorder the videos from first-to-watch → last-to-watch based on learning
dependencies. For each video, in 1–2 lines, explain why it sits at that position —
what prerequisite knowledge it builds on and what it unlocks next.

## 2. Topic Coverage Assessment
For each video, based purely on the chapter titles, tell me:
- **Coverage score (0–100%)** — comprehensive (beginner → advanced → production) or partial?
- **What's covered well**
- **What's missing or light**
- **Prerequisites** the viewer should already know
- **Difficulty**: Beginner / Intermediate / Advanced

## 3. Gap Analysis Across the Playlist
- Which important topics are **not covered at all**?
- Which topics are covered by **multiple videos** (overlap)?
- Suggest external topics/resources to fill the gaps into a complete roadmap.

## 4. Final Roadmap
A clean, numbered table: `| # | Video Title | Why Now | Coverage % | Difficulty | Est. Hours |`

## Rules
- Do **not** skip any video — include all of them.
- If a video has "No chapters found", infer from the title only and mark coverage
  as "Unknown — title-based guess".
- Be honest about gaps; don't inflate coverage %.
- Keep reasoning concise and actionable — I want to start watching today.
