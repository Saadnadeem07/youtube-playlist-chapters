<div align="center">

# 🧰 YouTube Playlist Toolkit

**Two tools, one local web app.** Paste a YouTube playlist once, then either
**download** the videos *or* **extract every video's chapters** into one clean
text file for an LLM — your choice, same server.

[![CI](https://github.com/Saadnadeem07/youtube-playlist-chapters/actions/workflows/ci.yml/badge.svg)](https://github.com/Saadnadeem07/youtube-playlist-chapters/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![No dependencies](https://img.shields.io/badge/python%20deps-none-success.svg)](#-requirements)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<img src="docs/preview.svg" alt="YouTube Playlist Toolkit UI preview" width="800">

</div>

---

This started as two separate projects — a **playlist downloader** and a
**chapters extractor** — now merged into a single, polished web app. Run one
command, open one page, and pick the tool you need from the tabs at the top.

Everything runs **on your machine** (binds to `127.0.0.1` only). It's a single
Python file using **only the standard library**, shelling out to the
battle-tested [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) binary (with
[`ffmpeg`](https://ffmpeg.org/) for merging).

## ✨ What's inside

### ⬇️ Download videos
- 🎚️ **Quality picker** — Best, 1080p, 720p, 480p, or **Audio only (MP3)**.
- ☑️ **Multi-select** with *Select all* and **Download selected**, or grab the whole list.
- 📊 **Live progress** — per-video %, speed & ETA, plus an overall batch bar.
- ✋ **Cancel** any queued or in-progress download.
- 📁 **Open folder** in your OS file manager (macOS, Windows, Linux).

### 📑 Extract chapters
- 🧾 Pulls **chapter timestamps** from every video into one consolidated text file.
- 🤝 Gracefully handles videos with no chapters (`No chapters found`).
- ⚡ Extracts in parallel with a live progress bar and per-video counts.
- 📋 **Copy** or **download `.txt`**, plus a built-in **LLM analysis prompt** to
  turn the playlist into a study roadmap (watch order, coverage, gaps).

### Shared
- 🔎 Instant filter, 🌗 light/dark theme (remembered), 🔔 toasts, responsive UI.
- 🪶 **Zero Python dependencies** — just the standard library + `yt-dlp`/`ffmpeg`.

## 📋 Requirements

- **Python 3.9+**
- [**yt-dlp**](https://github.com/yt-dlp/yt-dlp) on your `PATH`
- [**ffmpeg**](https://ffmpeg.org/) on your `PATH` (merges video+audio, makes MP3s)

| OS      | Install the two tools                        |
| ------- | -------------------------------------------- |
| macOS   | `brew install yt-dlp ffmpeg`                 |
| Windows | `winget install yt-dlp.yt-dlp Gyan.FFmpeg`   |
| Linux   | `sudo apt install yt-dlp ffmpeg`             |

> Prefer pip for the downloader? `pip install yt-dlp` also works.

## 🚀 Quick start

```bash
git clone https://github.com/Saadnadeem07/youtube-playlist-chapters.git
cd youtube-playlist-chapters
python3 app.py
```

Then open **<http://127.0.0.1:8000>** and:

1. Pick a tab — **⬇ Download videos** or **📑 Extract chapters**.
2. Paste a playlist (or single video) URL and click **Load**.
3. **Download:** choose a quality and download all / selected / individual videos.
   **Chapters:** click *Extract all chapters*, then **Copy** or **Download .txt**
   (and grab the **LLM prompt** from the result panel).

Downloads are saved to `./downloads/` as `.mp4` (best video+audio) or `.mp3`.
Stop the server with `Ctrl+C`.

## ⚙️ Configuration

| Variable | Default     | Description                                            |
| -------- | ----------- | ------------------------------------------------------ |
| `PORT`   | `8000`      | Port to serve on.                                      |
| `HOST`   | `127.0.0.1` | Bind address. Keep it local unless you know otherwise. |

```bash
PORT=9000 python3 app.py
```

## 🧩 How it works

```
Browser (tabbed HTML/CSS/JS UI)  ──fetch──▶  Python stdlib HTTP server  ──subprocess──▶  yt-dlp + ffmpeg
        ▲                                              │
        └────────────  polls /api/*/status  ◀──────────┘
```

- A `ThreadingHTTPServer` serves the UI and a small JSON API.
- **Download** jobs run on a single background worker (sequential, so YouTube
  isn't hammered), streaming `yt-dlp` progress back to the UI.
- **Chapters** extraction runs in a small thread pool, calling `yt-dlp -J` per
  video to read each video's `chapters` and assembling one ordered text file.

| Endpoint               | Purpose                                  |
| ---------------------- | ---------------------------------------- |
| `POST /api/playlist`   | List a playlist / single video           |
| `POST /api/download`   | Queue downloads (with quality)           |
| `POST /api/status`     | Poll download progress                   |
| `POST /api/cancel`     | Cancel a download                        |
| `POST /api/chapters/start`  | Start a chapters extraction job     |
| `POST /api/chapters/status` | Poll chapters progress + result     |

## 🗂️ Project structure

```
youtube-playlist-toolkit/
├── app.py            # the whole app: server + both tools + embedded UI
├── prompt.md         # LLM analysis prompt (also built into the UI)
├── requirements.txt  # notes the external tools (no Python deps)
├── docs/preview.svg  # UI preview used in this README
├── .github/          # CI workflow + issue/PR templates
└── downloads/        # your downloaded files (git-ignored)
```

## 🛠️ Troubleshooting

- **`yt-dlp not found on PATH`** — install it (see [Requirements](#-requirements)) and reopen your terminal.
- **Merging fails / no audio** — install `ffmpeg`; it's required to combine streams and make MP3s.
- **A download or extraction suddenly fails** — YouTube changes often; update:
  `yt-dlp -U` (or `brew upgrade yt-dlp` / `pip install -U yt-dlp`).
- **Port already in use** — run with a different port: `PORT=9000 python3 app.py`.

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE) © 2026 Saad Nadeem

## ⚖️ Disclaimer

For personal use. **Only download content you have the right to download**, and
respect YouTube's Terms of Service and creators' rights. The author is not
responsible for misuse.
