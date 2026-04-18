# YouTube Playlist Chapters Extractor <img src="https://upload.wikimedia.org/wikipedia/commons/0/09/YouTube_full-color_icon_%282017%29.svg" alt="YouTube" height="28" align="center">

Give it a YouTube playlist URL — get back a single clean text file containing every video's **title, URL, and chapter timestamps**. Useful for feeding learning playlists to LLMs (Claude, ChatGPT, etc.) to plan a watch order, assess topic coverage, or generate a study roadmap.

## Features

- Extracts all videos from a YouTube playlist in one command
- Pulls chapter timestamps for every video
- Gracefully handles videos without chapters (`No chapters found`)
- Deduplicates repeated videos in the playlist
- Single consolidated output file, ready to paste into any LLM
- Zero API keys — uses [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) under the hood

## Installation

```bash
git clone https://github.com/<your-username>/youtube-playlist-chapters.git
cd youtube-playlist-chapters

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Usage

`main.py` auto-detects whether you pass a **playlist URL** or a **single video URL**.

### Playlist mode

```bash
python main.py "https://www.youtube.com/playlist?list=PLlfy9GnSVerQjeoYfoYKEMS1yKl89NOvL"
```

Produces:

| File | Contents |
|------|----------|
| `playlist_videos.txt` | Title + URL for every video in the playlist |
| `final_output.txt`    | Title + URL + chapters for every video (main output) |

### Single video mode

```bash
python main.py "https://www.youtube.com/watch?v=z0BZDAtQa6E"
```

Produces `final_output.txt` with just that one video's title, URL, and chapters.

### Output format

```
Video Title
https://www.youtube.com/watch?v=...
00:00:00 - Intro
00:02:10 - Setup
00:15:40 - Advanced topic
----------------------------------------

Video Title 2
https://www.youtube.com/watch?v=...
No chapters found
----------------------------------------
```

## Using the output with an LLM

`prompt.md` contains a ready-to-use prompt. Paste its contents into Claude or ChatGPT along with `final_output.txt` to get:

1. A recommended watch order based on topic dependencies
2. A coverage assessment (what each video teaches well / what's missing)
3. A gap analysis across the full playlist
4. A final learning roadmap

## Project structure

```
.
├── main.py              # Orchestrator — takes the playlist URL, writes final_output.txt
├── fetch_playlist.py    # Extracts videos from a playlist
├── fetch_chapters.py    # Extracts chapters for a single video
├── prompt.md            # Prompt template for Claude / ChatGPT
├── requirements.txt
└── README.md
```

Each script is also runnable on its own:

```bash
python fetch_playlist.py "<playlist_url>" playlist_videos.txt
python fetch_chapters.py "<video_url>"
```

## Requirements

- Python 3.9+
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) (installed via `requirements.txt`)

## Troubleshooting

- **`externally-managed-environment` on macOS**: always use a virtual environment (see Installation).
- **Slow first run**: `yt-dlp` fetches metadata over the network — a ~15-video playlist typically takes 30–60 seconds.
- **Outdated yt-dlp**: YouTube changes often break older versions. Update with `pip install -U yt-dlp`.

## License

MIT — feel free to use, modify, and share.
