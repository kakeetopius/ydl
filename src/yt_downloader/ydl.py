from yt_downloader.helpers import *
from yt_downloader.downloader import Downloader


def start():
    urls, opts = parse_args()

    downloader = Downloader()

    if opts.list_formats:
        return downloader.list_ytdlp_formats(urls)

    downloader.download_content(urls, opts)
