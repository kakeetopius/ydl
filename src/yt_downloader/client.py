import json
from dataclasses import dataclass
from yt_downloader.downloader import Options as DLOptions
import requests
from yt_downloader.helpers import join_host_port


class Client:
    def __init__(self, address: str = "localhost", port: int = 2210):
        if not address:
            address = "localhost"

        self.download_ep = "/download"
        self.address: str = address
        self.port = port

    def send_download_request(self, opts: DLOptions):
        resp = requests.post(
            self.full_url(self.download_ep),
            json=opts.model_dump(),
        )
        print(resp.json())

    def full_url(self, endpoint: str):
        return f"http://{join_host_port(self.address, self.port)}{endpoint}"
