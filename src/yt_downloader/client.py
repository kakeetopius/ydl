import json
from dataclasses import dataclass
from yt_downloader.downloader import Options as DLOptions
import requests
from yt_downloader.helpers import join_host_port


@dataclass
class Options:
    address: str = "localhost"
    port: int = 2210


class Client:
    opts: Options
    queue: list[str]

    def __init__(self, opts: Options = Options()):
        self.download_ep = "/download"
        self.opts = opts

    def send_download_request(self, opts: DLOptions):
        requests.post(
            self.full_url(self.download_ep),
            json=opts.model_dump(),
        )

    def full_url(self, endpoint: str):
        return f"http://{join_host_port(self.opts.address, self.opts.port)}{endpoint}"
