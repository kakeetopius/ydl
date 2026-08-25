import ipaddress
import os
import argparse
import yt_downloader.downloader as downloader
from platformdirs import user_config_dir
from pathlib import Path
from dynaconf import Dynaconf
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator, PathValidator
from yt_downloader.youtube import YTClient

CONFIG_FILE = Path(user_config_dir(appname="ydl", ensure_exists=True)) / "ydl.toml"


def get_args_and_settings() -> tuple[argparse.Namespace, Dynaconf]:
    """
    Function get_args_and_settings gets command line arguments and settings.
    """

    settings = Dynaconf(
        envvar_prefix="YDL",
        settings_files=[str(CONFIG_FILE)],
    )

    description = "A python script to search youtube for any video with keywords and then download audio or video."

    argparser = argparse.ArgumentParser(description=description)
    argparser.add_argument(
        "-s",
        "--search",
        type=str,
        help="The keywords to use for the search",
        dest="search",
    )
    argparser.add_argument(
        "-u", "--url", type=str, help="A direct url for the youtube video", dest="url"
    )
    argparser.add_argument(
        "-k",
        "--keyword-file",
        type=str,
        help="Path to a file with keywords for the videos, each line describing a single video (Should be detailed because the top result is downloaded)",
        dest="kwfile",
    )
    argparser.add_argument(
        "-U",
        "--url-file",
        type=str,
        help="Path to a file with youtube urls. One per line",
        dest="url_file",
    )
    argparser.add_argument(
        "-r",
        "--resolution",
        type=str,
        help="Desired video quality eg 420p, 720p, 1080p etc",
        default="",
        dest="resolution",
    )
    argparser.add_argument(
        "-f",
        "--format",
        type=str,
        help="Raw yt-dlp format to use. Overrides the resolution setting (video only).",
        dest="format",
    )
    argparser.add_argument(
        "-M",
        "--music-dir",
        type=str,
        help="The directory to save downloaded audio files",
        default="",
        dest="music_dir",
    )
    argparser.add_argument(
        "-V",
        "--video-dir",
        type=str,
        help="The directory to save downloaded video files",
        default="",
        dest="video_dir",
    )
    argparser.add_argument(
        "-n",
        "--num-results",
        type=int,
        help="The number of results to retrieve for the video if keywords are used to search. (Default is 5)",
        dest="num_results",
        default=5,
    )
    argparser.add_argument(
        "-F",
        "--list-formats",
        action="store_true",
        help="List yt-dlp formats for the video instead of downloading.",
        dest="list_formats",
    )
    argparser.add_argument(
        "-p",
        "--playlist",
        action="store_true",
        help="Download playlist if link points to one.",
        dest="playlist",
    )
    argparser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed progress information.",
        dest="verbose",
    )

    content_type = argparser.add_mutually_exclusive_group(required=False)
    content_type.add_argument(
        "--audio", action="store_true", help="Download audio only", dest="audio"
    )
    content_type.add_argument(
        "--video", action="store_true", help="Download video only", dest="video"
    )
    content_type.add_argument(
        "--both",
        action="store_true",
        help="Download both video and audio",
        dest="both",
    )

    argparser.add_argument(
        "-S",
        "--server",
        action="store_true",
        help="Run in server mode and listen for download jobs over HTTP",
        dest="server_mode",
    )
    argparser.add_argument(
        "-c",
        "--client",
        action="store_true",
        help="Run in client mode and send download jobs to a server over HTTP",
        dest="client_mode",
    )
    argparser.add_argument(
        "--no-queue",
        action="store_true",
        help="Send or receive download requests directly to the server or from the client, not via a rabbitmq queue",
        dest="noqueue",
        default=settings.get("server.noqueue"),
    )
    argparser.add_argument(
        "-P",
        "--port",
        type=int,
        help="The server port to listen on in server mode or connect to in client mode.",
        dest="port",
        default=settings.get("server.port"),
    )
    argparser.add_argument(
        "-a",
        "--addr",
        type=str,
        help="The server address to listen on in server mode or connect to in client mode.",
        dest="address",
        default=settings.get("server.address"),
    )

    args = argparser.parse_args()

    settings.update(
        {
            "server": {
                "address": args.address,
                "port": args.port,
                "noqueue": args.noqueue,
            }
        }
    )

    return args, settings


def get_opts_from_arguments(
    options: argparse.Namespace,
) -> downloader.Options:
    urls: list[str] = list()
    yt_client = YTClient()

    if options.search:
        api_key = os.getenv(yt_client.api_key_name)
        if not api_key:
            raise RuntimeError(
                "yt_api environment variable is not set. please set before continuing"
            )
        results = yt_client.query_youtube(options.search, options.num_results, api_key)
        urls.append(yt_client.show_ytresults_and_get_url(results))
    elif options.url:
        urls.append(options.url)
    elif options.url_file:
        urls.extend(get_urls_from_file(options.url_file))
    elif options.kwfile:
        api_key = os.getenv(yt_client.api_key_name)
        if not api_key:
            raise RuntimeError(
                "yt_api environment variable is not set. please set before continuing"
            )
        urls.extend(get_urls_from_keyword_file(options.kwfile, api_key))
    else:
        if not options.server_mode:
            print("Please provide a url or keywords to query youtube with.")
            print("Use ydl -h for more information")
            exit(-1)

    opts = downloader.Options()
    if options.format:
        opts.format = options.format
    if options.music_dir:
        opts.music_dir = options.music_dir
    if options.video_dir:
        opts.video_dir = options.video_dir

    opts.download_playlist = options.playlist
    opts.list_formats = options.list_formats
    opts.download_video = options.video
    opts.download_audio = options.audio
    opts.download_both = options.both
    opts.verbose = options.verbose
    opts.resolution = options.resolution

    opts.urls = urls
    return opts


def get_urls_from_file(file_path: str) -> list[str]:
    """
    Function gets urls from a batch file
    Returns: A list of the urls
    """

    urls = list()
    with open(file_path, "r") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                # skip empty line
                continue
            urls.append(stripped)

    return urls


def get_urls_from_keyword_file(file_path: str, api_key: str) -> list[str]:
    keywords = list()
    urls = list()
    yt_client = YTClient()

    with open(file_path, "r") as file:
        file
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            keywords.append(stripped)

    print(f"Found keywords for {len(keywords)} videos")
    for keyword in keywords:
        keyword = " ".join(keyword.split())
        results = yt_client.query_youtube(keyword, 1, api_key)["items"]
        if len(results) == 0:
            continue
        url = yt_client.get_full_url_from_video_id(results[0]["id"]["videoId"])
        urls.append(url)

    return urls


def truncate(text, len):
    """
    Function truncate truncates text that is larger than PRINT_MAX_LEN
    """
    return text[:len] + "..."


def get_num_input(
    message1: str, invalidMessage: str, min: int, max: int, allowEmpty: bool
) -> int:
    """
    Function get_num_input is used to get integer input from user
    """

    value = inquirer.number(
        message=message1,
        invalid_message=invalidMessage,
        min_allowed=min,
        max_allowed=max,
        mandatory=True,
        validate=EmptyInputValidator() if not allowEmpty else None,
    ).execute()
    return int(value)


def get_terminal_selection(
    message: str, selections: list[str], default: str | None
) -> str:
    return inquirer.select(
        message=message,
        choices=selections,
        default=default,
        mandatory=True,
        vi_mode=True,
    ).execute()


def get_dir_path(message: str) -> str:
    return inquirer.filepath(
        message=message,
        only_directories=True,
        validate=PathValidator(is_dir=True),
        mandatory=True,
        vi_mode=True,
    ).execute()


def is_video_extension(ext: str) -> bool:
    return ext.lower() in {
        ".mp4",
        ".mkv",
        ".mov",
        ".webm",
        ".m4v",
        ".mpeg",
        ".mpg",
    }


def is_audio_extension(ext: str) -> bool:
    return ext.lower() in {
        ".mp3",
        ".m4a",
        ".wav",
    }


def join_host_port(host: str, port: int) -> str:
    try:
        addr = ipaddress.ip_address(host)
        if addr.version == 6:
            return f"[{host}]:{port}"
    except ValueError:
        pass

    return f"{host}:{port}"
