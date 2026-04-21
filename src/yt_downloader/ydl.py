import yt_dlp
import tempfile
import requests
import argparse
import prettytable
import os
import pathlib
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator, PathValidator
from enum import Enum

class ContentType(Enum):
    VIDEO = 1
    AUDIO = 2
    BOTH = 3

API_EP = "https://youtube.googleapis.com/youtube/v3/search"
YT_BASEURL = "https://www.youtube.com/watch?v="

PRINT_MAX_LEN = 70

def start():
    options = get_args()

    urls: list[str]
    if options.search:
        api_key = os.getenv("yt_api")
        if not api_key:
            raise RuntimeError("yt_api environment variable is not set. please set before continuing") 
            exit(-1)
        results = query_youtube(options.search,options.num_results,  api_key)
        urls = [show_ytresults_and_get_url(results["items"])]
    elif options.url:
        urls = [ options.url ]
    elif options.url_file:
        urls = get_urls_from_file(options.url_file)
    elif options.kwfile:
        api_key = os.getenv("yt_api")
        if not api_key:
            raise RuntimeError("yt_api environment variable is not set. please set before continuing") 
            exit(-1)
        urls = get_urls_from_keyword_file(options.kwfile, api_key)
    else:
        print("Invalid Usage")
        print("Use the -h option to get help")
        exit(-1)

    if options.list_formats:
        return list_ytdlp_formats(urls)

    ydl_opts = dict()
    if options.format:
        ydl_opts["format"] = options.format
    if options.music_dir:
        ydl_opts["music_dir"] = options.music_dir
    if options.video_dir:
        ydl_opts["video_dir"] = options.video_dir

    ydl_opts["download_playlist"] = options.playlist
    
    ydl_opts["video"] = options.video
    ydl_opts["audio"] = options.audio
    ydl_opts["both"] = options.both

    download_content(urls, ydl_opts)


def get_args():
    """
    Function get_args gets arguments from command line
    """
    description="A python script to search youtube for any video with keywords and then download audio or video."

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
        "-n",
        "--num-results",
        type = str,
        help="The number of results to retrieve for each video if keywords are used to search. (Default is 5)",
        dest="num_results",
        default=5
    )
    argparser.add_argument(
        "-p",
        "--playlist",
        action="store_true",
        help="Download playlist if link points to one.",
        dest="playlist",
    )
    argparser.add_argument(
        "-F",
        "--list-formats",
        action="store_true",
        help="List yt-dlp formats for the video.",
        dest="list_formats",
    )
    argparser.add_argument(
        "-f",
        "--format",
        type = str,
        help="The yt-dlp format to use instead of the defaults",
        dest="format",
    )
    argparser.add_argument(
        "-M",
        "--music-dir",
        type = str,
        help="The directory to save downloaded audio files",
        default="",
        dest="music_dir",
    )
    argparser.add_argument(
        "-V",
        "--video-dir",
        type = str,
        help="The directory to save downloaded video files",
        default="",
        dest="video_dir",
    )

    content_type = argparser.add_mutually_exclusive_group(required=False)
    content_type.add_argument(
        "-a",
        "--audio",
        action="store_true",
        help="Download audio only",
        dest="audio"
    )
    content_type.add_argument(
        "-v",
        "--video",
        action="store_true",
        help="Download video only",
        dest="video"
    )
    content_type.add_argument(
        "-b",
        "--both",
        action="store_true",
        help="Download both video and audio",
        dest="both"
    )

    options = argparser.parse_args()
    return options


def get_urls_from_file(file_path: str) -> list[str]:
    """
    Function gets urls from a batch file
    Returns: A list of the urls
    """

    urls = list()
    try:
        with open(file_path, "r") as file:
            for line in file:
                stripped = line.strip()
                if not stripped:
                    continue
                    # skip empty line
                urls.append(stripped)
    except Exception as e:
        print(f"Error: {e}")
        exit(-1)

    return urls


def query_youtube(search_str: str, num_results: int, api_key: str) -> dict:
    """
    Function is used to query youtube for search results of given keywords.
    """
    # --Removing unnecessary spaces---
    search_str = " ".join(search_str.split())

    headers = {"Accept": "application/json"}

    query_params = {
        "part": "snippet",
        "maxResults": num_results,
        "type": "video",
        "q": search_str,
        "key": api_key,
    }

    try:
        print("Retrieving video url(s) for: ", search_str)
        response = requests.get(
            url=API_EP, headers=headers, params=query_params, timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("Connection Error. Check your connection")
        exit(-1)
    except requests.exceptions.Timeout:
        print("Connection timed out")
        exit(-1)
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occured: \n{err}")
        print("If persistent errors try using direct direct links instead")
        exit(-1)
    except requests.exceptions.RequestException as err:
        print(f"Unexpected error: \n{err}")
        print("If persistent errors try using direct direct links instead")
        exit(-1)
    except Exception as err:
        print(f"Error fetching video info: {err}")
        print("If persistent errors try using direct direct links instead")
        exit(-1)


def get_urls_from_keyword_file(file_path: str, api_key: str) -> list[str]:
    keywords = list()  # Array for keywords got from file
    urls = list()

    try:
        with open(file_path, "r") as file:
            for line in file:
                stripped = line.strip()
                if not stripped:
                    # skipping empty line
                    continue
                keywords.append(stripped)
    except Exception as e:
        print(f"Error: {e}")
        exit(-1)

    print(f"Found keywords for {len(keywords)} videos")
    try:
        for keyword in keywords:
            keyword = " ".join(keyword.split())  # ---Removing unnecessary spaces
            results = query_youtube(keyword, 1, api_key)["items"]
            url = YT_BASEURL + results[0]["id"]["videoId"]
            urls.append(url)

        return urls
    except Exception as err:
        print(f"Error fetching video info: {err}")
        print(
            "If persistent errors and not connection issues. Try using direct direct links instead"
        )
        exit(-1)


def show_ytresults_and_get_url(results: list) -> str:
    """
    Function prints out information using prettytable about the returned youtube resulted
        and then queries the user which video to download
    Returns:
    The url for the youtube video to download
    """
    i = 1
    table = prettytable.PrettyTable()
    table.field_names = ["Index", "Title", "Channel"]

    for result in results:
        title = (result["snippet"]["title"],)
        title = title[0]
        channel = (result["snippet"]["channelTitle"],)
        channel = channel[0]

        if len(title) > PRINT_MAX_LEN:
            title = truncate(title)
        if len(channel) > PRINT_MAX_LEN:
            channel = truncate(channel)

        table.add_row([i, title, channel])
        i += 1

    print(table)

    mess1 = "Enter Index of Video to download:"
    mess2 = "Enter Correct Index"
    max_input = len(results)

    num = get_num_input(mess1, mess2, 1, max_input, False)
    if not num:
        return ""
    
    return YT_BASEURL + get_video_id(results, num)


def download_content(urls: list[str] | str, opts: dict):
    """
    Function download_content downloads the youtube video pointed to by the urls given using yt_dlp module

    Parameters:
    urls: A list of one or more urls to youtube videos for downloading
    """
    TEMP_PATH  = tempfile.gettempdir()
    HOME = pathlib.Path.home()
    DEFAULT_VIDEO_PATH = HOME / "Videos"
    DEFAULT_MUSIC_PATH = HOME / "Music"

    content_type: ContentType
    if opts["video"]:
        content_type = ContentType.VIDEO
    elif opts["audio"]:
        content_type = ContentType.AUDIO
    elif opts["both"]:
        content_type = ContentType.BOTH
    else:
        result = get_terminal_selection (
            message = "Select Content Type to download:",
            selections= ["Audio", "Video", "Both"],
            default = None
        )
        if result == "Video":
            content_type = ContentType.VIDEO
        elif result == "Audio":
            content_type = ContentType.AUDIO
        elif result == "Both":
            content_type = ContentType.BOTH

    ytdlp_path = ""
    music_path = ""
    video_path = ""

    ytdlp_format= ""
    music_format = ""
    video_format = ""
    format_given = False
    
    if "format" in opts:
        # if ytdlp format was provided by user
        format_given = True
        ytdlp_format = opts["format"]

    if content_type == ContentType.AUDIO or content_type == ContentType.BOTH:
        if "music_dir" in opts:
            music_path = opts["music_dir"]
        else:
            #if music directory was not provided by user prompt the user for one or use default.
            m_path = get_dir_path("Enter music path(Leave blank for default): ")
            if m_path:
                music_path = m_path
            else:
                music_path = str(DEFAULT_MUSIC_PATH)
        music_format = "bestaudio"
    if content_type == ContentType.VIDEO or content_type == ContentType.BOTH:
        if "video_dir" in opts:
            video_path = opts["video_dir"]
        else:
            #if video directory was not provided by user prompt the user for one or use default.
            v_path = get_dir_path("Enter video path(Leave blank for default): ")
            if v_path:
                video_path = v_path
            else:
                video_path = str(DEFAULT_VIDEO_PATH)
        if not format_given: 
            formats = [ "2160", "4320", "1440", "1080", "720", "480"]
            format = get_terminal_selection( "Choose format to download", formats, "720")
            video_format = f"bestaudio+bestvideo[ext=mp4][height<={format}]/best[ext=m4a][height<={format}]"


    if content_type == ContentType.VIDEO or content_type == ContentType.BOTH:
        #We start by working on video only by setting the ytdlp format to the video format and ytdlp path to video path in case BOTH content type is provided.
        if not format_given:
            ytdlp_format = video_format
        ytdlp_path = video_path
    elif content_type == ContentType.AUDIO: 
        if not format_given:
            ytdlp_format = music_format
        ytdlp_path = music_path

    print(f"Format to download: {ytdlp_format}")

    # -----------------------Options for yt-dlp------------------------------#
    format_sorts = ["ext"]

    output_paths = {"home": ytdlp_path, "temp": str(TEMP_PATH)}

    output_format = {"default": "%(title)s.%(ext)s"}

    ydl_opts: dict = {
        "quiet": False,
        "format": ytdlp_format,
        "format_sort": format_sorts,
        "concurrent_fragment_downloads": 5,
        "outtmpl": output_format,
        "paths": output_paths,
        "noplaylist": not opts["download_playlist"],
    }
    # ------------------------------------------------------------------------#

    print("\n")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
            print(f"\nDownload(s) Successfull.\nSaved at: {ytdlp_path}\n")

        if content_type == ContentType.BOTH:  
            #if both audio and video is required we set the ytdlp options now to the audio options for both format and path and download again.
            #if user gave a format with BOTH content type option that format is assumed to be for video so we override the yt_dlp format to the default music format.
            ydl_opts["format"] = music_format
            ydl_opts["paths"]["home"] = music_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
                print(f"\nDownload(s) Successfull.\nSaved at: {music_path}\n")

    except yt_dlp.DownloadError as err:
        print(f"\nDownload failed:\n {err}")
    except Exception as e:
        print(f"Error: {e}")

def list_ytdlp_formats(urls: list[str]):
    yt_dlp_opts = {
        "listformats" : True
    }

    with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
        ydl.download(urls)

def get_video_id(results: list, index: int) -> str:
    """
    Function get_video_id returns the video id of the youtube video selected for downloading
    """
    i = 1

    for result in results:
        if index == i:
            return result["id"]["videoId"]

        i += 1

    return ""


def truncate(text):
    """
    Function truncate truncates text that is larger than PRINT_MAX_LEN
    """
    return text[:PRINT_MAX_LEN] + "..."

def get_num_input(message1: str, invalidMessage: str, min: int, max: int, allowEmpty: bool) -> int | None:
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

def get_terminal_selection(message: str, selections: list[str], default) -> str:
    return inquirer.select(
        message = message,
        choices = selections,
        default = default,
        mandatory = True,
        vi_mode=True,
    ).execute()

def get_dir_path(message: str):
    return inquirer.filepath(
        message = message,
        only_directories= True,
        validate = PathValidator(is_dir=True),
        mandatory = True,
        vi_mode=True,
    ).execute()
