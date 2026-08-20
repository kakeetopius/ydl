from dataclasses import dataclass
from yt_downloader.downloader import Downloader
from yt_downloader.downloader import Options as DLOptions
from fastapi import FastAPI
import uvicorn


@dataclass
class Options:
    address: str = "0.0.0.0"
    port: int = 2210


class Server:
    def __init__(self, opts: Options = Options()):
        self.opts = opts
        self.downloader = Downloader()
        self.app = FastAPI()

        self.app.post("/download")(self.download)

    def run(self):
        uvicorn.run(
            self.app,
            host=self.opts.address,
            port=self.opts.port,
        )

    def download(self, req: DLOptions):
        self.downloader.download_content(req)
