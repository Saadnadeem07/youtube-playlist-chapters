I'm sharing a file (`final_output.txt`) containing a DevOps YouTube playlist. Each entry has:
- Video Title
- Video URL
- Chapters (timestamps + topics), or "No chapters found"
- A `----` separator

I want to learn DevOps from scratch to production-ready. Analyze the chapters of every video and give me:

## 1. Recommended Watch Order
Reorder the videos from **first to watch → last to watch** based on learning dependencies (e.g., Linux before Docker, Docker before Kubernetes, Git before CI/CD, etc.). For each video, in 1–2 lines, explain **why it sits at that position** — what prerequisite knowledge it builds on and what it unlocks next.

## 2. Topic Coverage Assessment
For each video, based purely on the chapter titles, tell me:
- **Coverage score (0–100%)** — does it cover the topic comprehensively (beginner → advanced → production), or only parts?
- **What's covered well** (core strengths from the chapters)
- **What's missing or light** (gaps a learner would still need to fill from elsewhere)
- **Prerequisites** the viewer should already know before starting
- **Difficulty level**: Beginner / Intermediate / Advanced

## 3. Gap Analysis Across the Playlist
After analyzing all videos together:
- Which important DevOps topics are **not covered at all** by this playlist?
- Which topics are covered by **multiple videos** (overlap)?
- Suggest external topics/resources to fill the gaps so the playlist becomes a complete DevOps roadmap.

## 4. Final Roadmap
Give me a clean, numbered roadmap table:

| # | Video Title | Why Now | Coverage % | Difficulty | Est. Hours |

## Rules
- Do **not** skip any video — include all of them.
- If a video has "No chapters found", infer from the title only and mark coverage as "Unknown — title-based guess".
- Be honest about gaps; don't inflate coverage %.
- Keep reasoning concise and actionable — I want to start watching today.
