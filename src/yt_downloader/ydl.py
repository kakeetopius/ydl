from yt_downloader.helpers import *
from yt_downloader.downloader import Downloader
from yt_downloader.server import Server
from yt_downloader.client import Client


def start():
    args, settings = get_args_and_settings()

    opts = get_opts_from_arguments(args)

    if args.server_mode:
        server = Server(
            music_dir=opts.music_dir,
            video_dir=opts.video_dir,
            address=settings.get("server.address", "localhost"),
            port=settings.get("server.port", 2210),
            noqueue=settings.get("server.noqueue", False),
            rbmq_address=settings.get("rabbitmq.address", "localhost"),
            rbmq_port=settings.get("rabbitmq.port", 5672),
            rbmq_vhost=settings.get("rabbitmq.vhost", ""),
            rbmq_username=settings.get("rabbitmq.username", ""),
            rbmq_password=settings.get("rabbitmq.password", ""),
        )
        return server.run()

    downloader = Downloader()
    if opts.list_formats:
        return downloader.list_ytdlp_formats(opts.urls)

    if args.client_mode:
        client = Client(
            server_address=settings.get("server.address", "localhost"),
            server_port=settings.get("server.port", 2210),
            noqueue=settings.get("server.noqueue", False),
            rbmq_address=settings.get("rabbitmq.address", "localhost"),
            rbmq_port=settings.get("rabbitmq.port", 5672),
            rbmq_vhost=settings.get("rabbitmq.vhost", ""),
            rbmq_username=settings.get("rabbitmq.username", ""),
            rbmq_password=settings.get("rabbitmq.password", ""),
        )
        return client.send_download_request(opts)

    downloader.download_content(opts)
