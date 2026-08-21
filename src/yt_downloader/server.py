import threading
from yt_downloader.downloader import Downloader
from yt_downloader.downloader import Options as DLOptions
from queue import Queue
from fastapi import FastAPI, HTTPException
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum
import uvicorn


@dataclass
class Job:
    id: UUID
    status: Status
    download_options: DLOptions


class Status(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class Server:
    def __init__(
        self,
        address: str = "0.0.0.0",
        port: int = 2210,
        music_dir: str = "",
        video_dir: str = "",
    ):
        if not address:
            address = "0.0.0.0"

        self.address: str = address
        self.port = port
        self.queue: Queue[Job] = Queue()
        self.downloader = Downloader(temp_dir="ydl_server_tmp")
        self.app = FastAPI()
        self.jobs: dict[UUID, Job] = dict()
        self.music_dir = music_dir
        self.video_dir = video_dir

        self.app.post("/download")(self.download)
        self.app.get("/jobs/{id}")(self.get_job_status)

    def run(self):
        threading.Thread(target=self.start_worker, daemon=True).start()
        uvicorn.run(
            self.app,
            host=self.address,
            port=self.port,
        )

    def start_worker(self):
        while True:
            try:
                job = self.queue.get()
                self.jobs[job.id].status = Status.DOWNLOADING

                self.downloader.download_content(job.download_options)
                self.jobs[job.id].status = Status.COMPLETED
            except Exception as e:
                self.jobs[job.id].status = Status.FAILED
                print(f"Error: {e}")
            finally:
                self.queue.task_done()

    def download(self, req: DLOptions):
        req.server_mode = True
        if self.video_dir:
            req.video_dir = self.video_dir
        if self.music_dir:
            req.music_dir = self.music_dir

        job = Job(
            id=uuid4(),
            status=Status.QUEUED,
            download_options=req,
        )
        self.jobs[job.id] = job
        self.queue.put(job)

        return {
            "job_id": job.id,
            "status": "queued",
        }

    def get_job_status(self, id: UUID):
        if id in self.jobs:
            job = self.jobs[id]
            return {
                "job_id": job.id,
                "status": job.status,
            }

        raise HTTPException(status_code=404, detail=f"job with id {id} not found")
