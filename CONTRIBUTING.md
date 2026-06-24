# Contributing

Thanks for your interest in improving **YouTube Playlist Downloader**! 🎉

This is a small, single-file project, so contributing is intentionally simple.

## Getting set up

```bash
git clone https://github.com/saadnadeem/yt-playlist-downloader.git
cd yt-playlist-downloader

# External tools (only these are required to run):
brew install yt-dlp ffmpeg        # macOS — see README for Windows/Linux

python3 app.py                    # http://127.0.0.1:8000
```

There are **no Python dependencies** — the app uses only the standard library.

## Before opening a pull request

- Keep it a single zero-dependency file. New Python packages should be avoided
  unless there's a strong reason; that simplicity is the whole point.
- Make sure it still byte-compiles:
  ```bash
  python -m py_compile app.py
  ```
- Lint with [ruff](https://docs.astral.sh/ruff/) (matches CI):
  ```bash
  pipx run ruff check .
  ```
- Test the UI manually: load a playlist, download one video, download a
  selection, cancel an in-progress download, and try the quality options.

## Commit & PR style

- Write clear, present-tense commit messages (e.g. "Add quality selector").
- One focused change per pull request is easier to review.
- Describe **what** changed and **why** in the PR body; screenshots help for
  any UI change.

## Reporting bugs / ideas

Open an [issue](https://github.com/saadnadeem/yt-playlist-downloader/issues)
using the templates. For download failures, include your `yt-dlp --version`
and the exact URL/error where possible.

By contributing, you agree your contributions are licensed under the
[MIT License](LICENSE).
