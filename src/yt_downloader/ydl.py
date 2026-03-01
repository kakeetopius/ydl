import yt_dlp
import tempfile
import requests
import argparse
import prettytable
import os
import pathlib
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator, PathValidator

API_EP = "https://youtube.googleapis.com/youtube/v3/search"
YT_BASEURL = "https://www.youtube.com/watch?v="

PRINT_MAX_LEN = 70

VIDEO_PATH : pathlib.Path
MUSIC_PATH : pathlib.Path

def start():
    options = get_args()

    HOME = pathlib.Path.home()
    global VIDEO_PATH
    global MUSIC_PATH

    VIDEO_PATH = HOME / "Videos"
    MUSIC_PATH = HOME / "Music"

    urls: list[str]
    if options.search:
        api_key = os.getenv("yt_api")
        if not api_key:
            raise RuntimeError("yt_api environment variable is not set. please set before continuing") 
            exit(-1)
        results = query_youtube(options.search,options.num_results,  api_key)
        urls = [show_ytresults_and_get_url(results["items"])]
    elif options.link:
        urls = [ options.link ]
    elif options.batch_file:
        urls = get_urls_from_file(options.batch_file)
    elif options.kwfile:
        api_key = os.getenv("yt_api")
        if not api_key:
            raise RuntimeError("yt_api environment variable is not set. please set before continuing") 
            exit(-1)
        urls = query_youtube_from_file(options.kwfile, api_key)
    else:
        print("Invalid Usage")
        print("Use the -h option to get help")
        exit(-1)

    if options.list_formats:
        return list_ytdlp_formats(urls)

    ydl_opts = dict()
    if options.format:
        ydl_opts["format"] = options.format
    ydl_opts["download_playlist"] = options.playlist

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
        "-l", "--link", type=str, help="A direct url for the youtube video", dest="link"
    )
    argparser.add_argument(
        "-k",
        "--keywords",
        type=str,
        help="Path to a file with keywords for the video, each line describing a single video (Should be detailed because the top result is downloaded)",
        dest="kwfile",
    )
    argparser.add_argument(
        "-b",
        "--batch",
        type=str,
        help="Path to a file with youtube urls. One per line",
        dest="batch_file",
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
    options = argparser.parse_args()

    return options


def get_urls_from_file(file_path: str) -> list[str]:
    """
    Function gets urls from a batch file

    Paramaters:
        file_path: The path to the batch file

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

    Parameters:
    1.str: a string with key words
    2.api_key: the youtube api key
    Returns:
    A dictionary of the results returned by youtube.
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
        print("Retrieving corresponding video urls................")
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


def query_youtube_from_file(file_path: str, api_key: str) -> list[str]:
    """
    Function searches for urls of videos based on keywords in batch file

    Paramaters:
    1.file_path: Path to the batch file
    2.api_key: The youtube api key

    Returns: A list of urls for the top result of the search
    """

    # --Removing unnecessary spaces---

    keywords = list()  # Array for keywords got from file
    urls = list()  # Array for urls for returned videos

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

    headers = {"Accept": "application/json"}

    query_params = {
        "part": "snippet",
        "maxResults": 1,
        "type": "video",
        "q": "",
        "key": api_key,
    }

    print(f"Found keywords for {len(keywords)} videos")
    print("Retrieving corresponding video urls................")
    try:
        for keyword in keywords:
            keyword = " ".join(keyword.split())  # ---Removing unnecessary spaces
            query_params["q"] = keyword

            response = requests.get(
                url=API_EP, headers=headers, params=query_params, timeout=5
            )
            response.raise_for_status()
            resp_dict = response.json()

            video_details = resp_dict["items"]

            if len(video_details) < 1:
                print("Error fetching Youtube Info")
                print("If persistent errors try using direct direct links instead")
                exit(-1)

            urls.append(YT_BASEURL + video_details[0]["id"]["videoId"])

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

    Paramaters:
    1.results: the dictionary containing information returned by youtube.

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
    dl_playlist: Indicate whether to download playlist if link supports it True if yes no otherwise.
    """
    TEMP_PATH  = tempfile.gettempdir()

    content_type = get_terminal_selection (
        message = "Select Content Type to download:",
        selections= ["Audio", "Video", "Both"],
        default = None
    )
    global MUSIC_PATH
    global VIDEO_PATH
    path: str = ""
    ytdlp_format: str = ""
    format_given: bool = False
    
    if "format" in opts:
        format_given = True
        ytdlp_format = opts["format"]

    if content_type == "Audio":
        m_path = get_dir_path("Enter music path(Leave blank for default): ")
        if m_path:
            path = m_path
        else:
            path = str(MUSIC_PATH)
        if not format_given:
            ytdlp_format = "bestaudio"
    else:
        if content_type == "Both":
            m_path = get_dir_path("Enter music path(Leave blank for default): ")
            if m_path:
                MUSIC_PATH = pathlib.Path(m_path)
                ytdlp_format = "bestaudio"
        v_path = get_dir_path("Enter video path(Leave blank for default): ")
        if v_path:
            VIDEO_PATH = pathlib.Path(v_path)
        if not format_given: 
            formats = [ "2160", "4320", "1440", "1080", "720", "480"]

            format = get_terminal_selection( "Choose format to download", formats, "720")

            ytdlp_format = f"bestaudio+bestvideo[ext=mp4][height<={format}]/best[ext=m4a][height<={format}]"

        path = str(VIDEO_PATH)
        print(f"Format to download: {ytdlp_format}")

    # -----------------------Options for yt-dlp------------------------------#
    format_sorts = ["ext"]

    output_paths = {"home": path, "temp": str(TEMP_PATH)}

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
            print(f"\nDownload(s) Successfull.\nSaved at: {path}\n")

        if content_type == "Both":  # if audio is also required
            ydl_opts["format"] = "bestaudio"
            ydl_opts["paths"]["home"] = str(MUSIC_PATH)
            path = str(MUSIC_PATH)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
                print(f"\nDownload(s) Successfull.\nSaved at: {path}\n")

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

    Parameters:
    1.results: Is the result dict containing the info returend by youtube.
    2.index: The index in the dict to get the video id

    Returns:
    The video id for the youtube video to download
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

    Parameters:
    1.text: The text to truncate

    Returns:
    The shortened string
    """
    return text[:PRINT_MAX_LEN] + "..."

def get_num_input(message1: str, message2: str, min: int, max: int, allowEmpty: bool) -> int | None:
    """
    Function get_num_input is used to get integer input from user

    Parameters:
    1.message1:     The Message shown to the user the very first time to ask for input
    2.message2:     The Message shown to the user subsequent times if the input is invalid
    3.min:          The lowest integer expected
    4.max:          The highest integer expected
    5.allowEmpty:   Indicates whether to try to force user to give an input.

    Returns:
    An integer between min and max inclusive if allowEmpty is false
    """
    
    value = inquirer.number(
        message=message1,
        invalid_message=message2,
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
