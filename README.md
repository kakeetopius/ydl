# ydl

A simple command-line interface for downloading YouTube videos and audio, built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp). This tool provides an easier way to search, select, and download content from YouTube.

## Features

- Search YouTube by keywords and interactively select video to download.
- Download directly using a YouTube link (or any other video site that [yt-dlp](https://github.com/yt-dlp/yt-dlp) can download from).
- Server and client mode: run ydl as a download daemon on any machine and send download requests to it.
- Optional RabbitMQ queue for sending requests to a server that can't be reached directly.

## Requirements

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
- `-u, --url <url>`: Download from a direct url.
- `-U, --url-file <file>`: Download from a file containing URLs (one per line).
- `-k, --keyword-file <file>`: Download top Youtube result for each line of keywords in a file.
- `-n, --num-results <N>`: Number of search results to return (default: 5).
- `-p, --playlist`: Download Youtube playlist if link points to one.
- `-S, --server`: Run in server mode.
- `-c, --client`: Run in client mode.
- `--queue`: Send or receive download requests via a RabbitMQ queue.
- `-P, --port <port>`: Server port to listen on (server mode) or connect to (client mode).
- `-a, --addr <address>`: Server address to listen on (server mode) or connect to (client mode).
- `-h, --help`: Get help

</details>

### Example

Search for a video and select which to download from a menu.

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

## Server and Client Mode

ydl can run as a small download daemon that accepts requests and downloads them. It can run on another machine or just on your own computer (localhost).

All that is needed is to start ydl in server mode, then send it download requests using client mode. The client just posts the job and exits. The server adds it to an internal queue and downloads in the background.

Start the server:

```sh
ydl --server --music-dir ~/Music --video-dir ~/Videos
```

Send a request from a client:

```sh
ydl --client --url "https://www.youtube.com/watch?v=123xyz"
```

The client finds the server using the `server.address` and `server.port` values from your config file (see below), or you can pass `--addr` and `--port` directly.

> [!NOTE]
> The server has no authentication. Anyone who can reach its port can queue downloads, so only run it on a trusted network (or behind a firewall/VPN or use --addr as localhost to restrict to the local machine only).

### Using a RabbitMQ queue

If the machine running the ydl server can't be reached directly (for example it's behind a NAT or firewall), requests can be sent through a RabbitMQ queue instead. The queue can be anywhere, such as in the cloud.

With `--queue`, the client only publishes the request to RabbitMQ and never talks to the server directly. The server must also be started with `--queue` so that it subscribes to the queue and picks up the jobs.

```sh
# on the machine that downloads
ydl --server --queue

# on any other machine
ydl --client --queue --url "https://www.youtube.com/watch?v=123xyz"
```

Both sides need the RabbitMQ connection details in their config file.

## Configuration

ydl reads an optional config file named `ydl.toml` from your user config directory (on Linux this is `~/.config/ydl/ydl.toml`).  
All values are optional (apart from the RabbitMQ credentials that is if queuing is required). The defaults are shown below.

```toml
[server]
address = "localhost"   # address to listen on (server) or connect to (client)
port = 2210
queue = false           # set to true to always use the RabbitMQ queue

[rabbitmq]
address = "localhost"
port = 5672
vhost = ""
username = ""
password = ""
```

The `--addr`, `--port` and `--queue` command line options override the values in the config file.

## YouTube API Key

For search functionality, set your YouTube Data API v3 key in the environment variable:

```sh
export yt_api=YOUR_API_KEY
```

## License

[MIT](LICENSE)
