import yt_dlp
import tempfile
import requests
import argparse
import prettytable
import os
import pathlib


API_EP = "https://youtube.googleapis.com/youtube/v3/search"
YT_BASEURL = "https://www.youtube.com/watch?v="

PRINT_MAX_LEN = 70

VIDEO_PATH : pathlib.Path
MUSIC_PATH : pathlib.Path

def main():
    try:
        start()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Quiting.............")
    except Exception as e:
        print(e)

def start():
    options = get_args()

    home = os.getenv("HOME")
    if not home:
        raise RuntimeError("HOME environment variable is not set") 
    
    HOME = pathlib.Path(home)
    global VIDEO_PATH
    global MUSIC_PATH

    VIDEO_PATH = HOME / "Videos"
    MUSIC_PATH = HOME / "Music"

    if options.search:
        api_key = os.getenv("yt_api")
        if not api_key:
            raise RuntimeError("yt_api environment variable is not set. please set before continuing") 
            exit(-1)
        results = get_yt_results(options.search,options.num_results,  api_key)
        urls = show_and_get_url(results["items"])
    elif options.link:
        urls = options.link
    elif options.batch_file:
        urls = get_urls(options.batch_file)
    elif options.kwfile:
        api_key = os.getenv("yt_api")
        if not api_key:
            raise RuntimeError("yt_api environment variable is not set. please set before continuing") 
            exit(-1)
        urls = search_urls(options.kwfile, api_key)
    else:
        print("Invalid Usage")
        print("Use the -h option to get help")
        exit(-1)
    download_content(urls, options.playlist)


def get_args():
    """
    Use: Function gets arguments from command line

    Returns the result as dictionary

    Currently supported command line arguments
    1. -s which will return the keyword to search for
    2. -l the link to video
    3. -k batch file containing keywords
    4. -b batch file containing urls
    5. -p Download playlist also
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
        help="Path to a file with keywords for the video, each line describing a single video (Should be detailed because the top result is downloaded. Try to include artist/video owner)",
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
            help="The number of results to retrieve for each video if keywords are used to search.",
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

    options = argparser.parse_args()

    return options


def get_urls(file_path: str) -> list:
    """
    Use: Function gets urls from a batch file

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


def get_yt_results(search_str: str, num_results: int, api_key: str) -> dict:
    """
    Use: Function is used to query youtube for search results of given keywords.

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


def search_urls(file_path: str, api_key: str) -> list:
    """
    Use: Function searches for urls of videos based on keywords in batch file

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
                    continue
                    # skipping empty line
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
            keyword = " ".join(keyword.split())  # ---Removeing unnecessary spaces
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


def show_and_get_url(results: dict) -> str:
    """
    Use: Function prints out information using prettytable about the returned youtube resulted
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

    mess1 = "Enter Index of Video to download"
    mess2 = "Enter Correct Index"
    max_input = len(results)

    num = get_num_input(mess1, mess2, 1, max_input, False)

    return YT_BASEURL + get_video_id(results, num)


def download_content(urls: list[str] | str, dl_playlist: bool):
    """
    Use: Function downloads the youtube video pointed to by the urls given using yt_dlp module

    Parameters:
    urls: A list of one or more urls to youtube videos for downloading
    dl_playlist: Indicate whether to download playlist if link supports it True if yes no otherwise.
    """
    TEMP_PATH  = tempfile.gettempdir()

    print("\nContent Types:\n1.Audio\n2.Video\n3.Both Audio and Video")
    mess1 = "Enter the Content Type to download"
    mess2 = "Enter 1 for Audio or 2 for Video"

    content_type = get_num_input(mess1, mess2, 1, 3, False)
    global MUSIC_PATH
    global VIDEO_PATH
    path: str = ""
    format: str = ""

    if content_type == 1:
        m_path = input("Enter music path(Leave blank for default): ")
        if m_path:
            path = m_path
        else:
            path = str(MUSIC_PATH)
        format = "bestaudio"
    else:
        if content_type == 3:
            m_path = input("Enter music path(Leave blank for default): ")
            if m_path:
                MUSIC_PATH = pathlib.Path(m_path)
                format = "bestaudio"
        v_path = input("Enter video path(Leave blank for default): ")
        if v_path:
            VIDEO_PATH = pathlib.Path(v_path)
        formats = ["1440", "1080", "720", "480", "2160", "4320"]
        print(
            "\nVideo Formats:\n1.1440p\n2.1080p\n3.720p\n4.480p.\n\nOthers(May be very large or not available at all):\n5.2160p\n6.4320p"
        )

        mess1 = "Enter a Video format (1-6) to download(Press Enter for Default[720p])"
        mess2 = "Enter number between 1-6 according to the given formats"

        format_index = get_num_input(mess1, mess2, 1, 6, True)

        if not format_index:
            format = (
                "bestaudio+bestvideo[ext=mp4][height<=720]/best[ext=mp4][height<=720]"
            )
        else:
            vid_format = formats[format_index - 1]
            format = f"bestaudio+bestvideo[ext=mp4][height<={vid_format}]/best[ext=m4a][height<={vid_format}]"

        path = str(VIDEO_PATH)
        print(f"Format to download: {format}")

    # -----------------------Options for yt-dlp------------------------------#
    format_sorts = ["ext"]

    output_paths = {"home": path, "temp": str(TEMP_PATH)}

    output_format = {"default": "%(title)s.%(ext)s"}

    ydl_opts: dict = {
        "quiet": False,
        "format": format,
        "format_sort": format_sorts,
        "concurrent_fragment_downloads": 5,
        "outtmpl": output_format,
        "paths": output_paths,
        "noplaylist": not dl_playlist,
    }
    # ------------------------------------------------------------------------#

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
            print(f"\nDownload(s) Successfull.\nSaved at: {path}\n")

        if content_type == 3:  # if audio is also required
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


def get_num_input(message1: str, message2: str, min: int, max: int, allowDefault: bool):
    """
    Use: Function is used to get integer input from user

    Parameters:
    1.message1:     The Message shown to the user the very first time to ask for input
    2.message2:     The Message shown to the user subsequent times if the input is invalid
    3.min:          The lowest integer expected
    4.max:          The highest integer expected
    5.allowDefault: Indicates whether to try to force user to give valid Integer

    Returns:
    An integer between min and max inclusive if allowDefault is false
    If allowDefault is true, returns False if at first attempt the user enters Invalid Input or Nothing at all.
    Else returns an integer between min and max
    """

    try:
        num = int(input(f"\n{message1}: "))
    except ValueError:
        num = None
        if allowDefault:
            return False

    while num is None or num > max or num < min:
        if num is None:
            print("NOT A NUMBER")
        else:
            print("INVALID")

        try:
            num = int(input((f"{message2}: ")))
        except ValueError:
            num = None

    return num


def get_video_id(results: dict, index: int) -> str:
    """
    Use: Function returns the video id of the youtube video selected for downloading

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
    Use: Function truncates text that is larger than PRINT_MAX_LEN

    Parameters:
    1.text: The text to truncate

    Returns:
    The shortened string
    """
    return text[:PRINT_MAX_LEN] + "..."
