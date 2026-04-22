# ydl

A simple command-line interface for downloading YouTube videos and audio, built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp). This tool provides an easier, interactive way to search, select, and download content from YouTube.

## Features

- Search YouTube by keywords and interactively select videos to download.
- Download by direct YouTube link or batch file of links.
- Download top results for keywords from a file.
- Choose to download audio, video, or both.
- Interactive selection of download formats and output directories.
- List available yt-dlp formats for a video.
- Supports playlist downloads.

## Requirments

- uv: The python package and project manager used. It can be downloaded from any package manager.

## Installation

Clone the repository:

```sh
git clone https://github.com/kakeetopius/ydl.git
cd ydl
```

Install dependencies:

```sh
uv sync
```

Install to path:

```sh
uv tool install .
```

## Usage

```sh
ydl [OPTIONS]
```

<details>
<summary>Common Options</summary>

- `-s, --search <keywords>`: Search YouTube for videos.
- `-u, --url <url>`: Download from a direct YouTube link.
- `-U, --url-file <file>`: Download from a file containing YouTube URLs (one per line).
- `-k, --keyword-file <file>`: Download top result for each line of keywords in a file.
- `-n, --num-results <N>`: Number of search results to return (default: 5).
- `-p, --playlist`: Download playlist if link points to one.
- `-S, --subtitles`: Add subtitles to video(s) if available.
- `-h, --help`: Get help

</details>

### Example

Search for a video and select one to download from an interactive menu.

```sh
ydl --search "wrong places - joshua baraka"
```

Download from a link:

```sh
ydl --url "https://www.youtube.com/watch?v=123xyz"
```

Batch download from a file:

```sh
ydl --url-file urls.txt
```

## YouTube API Key

For search functionality, set your YouTube Data API v3 key in the environment:

```sh
export yt_api=YOUR_API_KEY
```

## License

MIT
