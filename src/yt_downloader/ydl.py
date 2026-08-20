from yt_downloader.helpers import *
from yt_downloader.downloader import Downloader
from yt_downloader.server import Server
from yt_downloader.client import Client


def start():
    args = parse_args()

    if args.server_mode:
        server = Server()
        return server.run()

    opts = get_opts_from_arguments(args)

    downloader = Downloader()
    if opts.list_formats:
        return downloader.list_ytdlp_formats(opts.urls)

    if args.client_mode:
        client = Client()
        return client.send_download_request(opts)

    downloader.download_content(opts)
