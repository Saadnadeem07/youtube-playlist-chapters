# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-24

Merged the **playlist downloader** and the **chapters extractor** into a single
web app — two tools, one server, switchable from tabs.

### Added
- 📑 **Chapters tool** in the web UI: extract chapter timestamps for a whole
  playlist (or selection) into one text file, with copy / download `.txt` and a
  built-in LLM analysis prompt.
- Tabbed interface to switch between **Download** and **Chapters** modes.
- Chapters extraction runs in a thread pool with live progress and per-video counts.
- New endpoints: `POST /api/chapters/start`, `POST /api/chapters/status`.

### Changed
- Reimplemented chapter extraction on top of the `yt-dlp` **binary** so the whole
  toolkit stays **zero-dependency** (the old chapters CLI required the `yt-dlp`
  Python package).
- Rebranded to **YouTube Playlist Toolkit**; refreshed README and UI preview.

## [1.0.0] - 2026-06-24

### Added
- Quality selector: **Best**, 1080p, 720p, 480p, and **Audio only (MP3)**.
- Multi-select with checkboxes plus **Download selected** and **Select all**.
- **Cancel** button for queued or in-progress downloads.
- Overall progress bar, live per-video search/filter.
- Light/dark theme toggle, toasts, animated progress UI.
- Cross-platform "Open folder" (macOS, Windows, Linux).

### Changed
- Redesigned the entire web UI for a cleaner, more interactive experience.
- `HOST` is now configurable via environment variable (still local-only default).

[2.0.0]: https://github.com/Saadnadeem07/youtube-playlist-chapters/releases/tag/v2.0.0
[1.0.0]: https://github.com/Saadnadeem07/youtube-playlist-chapters/releases/tag/v1.0.0
