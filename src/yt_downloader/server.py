import threading
import uvicorn
import asyncio
import pika
import sys
from contextlib import asynccontextmanager
from yt_downloader.downloader import Downloader
from yt_downloader.downloader import Options as DLOptions
from queue import Queue
from fastapi import FastAPI, HTTPException
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


@dataclass
class Job:
    id: UUID
    status: Status
    download_options: DLOptions
    created_at: datetime
    finished_at: datetime | None = None
    retries: int = 0


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
        cleanup_timeout: int = 300,
        retry_timeout: int = 300,
        max_retries: int = 5,
        noqueue: bool = False,
        rbmq_address: str = "localhost",
        rbmq_port: int = 5672,
        rbmq_vhost: str = "",
        rbmq_username: str = "",
        rbmq_password: str = "",
    ):
        if not address:
            address = "0.0.0.0"

        self.address: str = address
        self.port = port
        self.queue: Queue[Job] = Queue()
        self.downloader = Downloader(temp_dir="ydl_server_tmp")
        self.jobs: dict[UUID, Job] = dict()
        self.music_dir = music_dir
        self.video_dir = video_dir
        self.cleanup_timeout = cleanup_timeout
        self.retry_timeout = retry_timeout
        self.max_retries = max_retries

        self.noqueue = noqueue
        self.rbmq_address = rbmq_address
        self.rbmq_port = rbmq_port
        self.rbmq_vhost = rbmq_vhost
        self.rbmq_username = rbmq_username
        self.rbmq_password = rbmq_password
        self.rbmq_queue_name = "ydl_download_queue"

        self.app = FastAPI(lifespan=self.lifespan)
        self.app.post("/download")(self.download)
        self.app.get("/jobs")(self.get_jobs)
        self.app.get("/job/{id}")(self.get_job_status)

        if noqueue:
            return
        try:
            con = self.get_rabbitmq_connection()
            channel = con.channel()
            self.rbmq_channel = channel
        except Exception as e:
            print(repr(e))
            sys.exit(1)

    def run(self):
        threading.Thread(target=self.start_worker, daemon=True).start()
        if not self.noqueue:
            threading.Thread(target=self.get_jobs_from_rabbit_mq, daemon=True).start()
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
                self.jobs[job.id].finished_at = datetime.now()
            except Exception as e:
                self.jobs[job.id].status = Status.FAILED
                print(f"Error: {e}")
            finally:
                self.queue.task_done()

    def download(self, req: DLOptions):
        req.server_mode = True
        req.verbose = True
        if not req.video_dir and self.video_dir:
            req.video_dir = self.video_dir
        if not req.music_dir and self.music_dir:
            req.music_dir = self.music_dir

        job = Job(
            id=uuid4(),
            status=Status.QUEUED,
            download_options=req,
            created_at=datetime.now(),
        )
        self.jobs[job.id] = job
        self.queue.put(job)

        return {"job_id": job.id, "status": Status.QUEUED}

    def get_job_status(self, id: UUID):
        if id in self.jobs:
            job = self.jobs[id]
            return {
                "job_id": job.id,
                "status": job.status,
            }

        raise HTTPException(status_code=404, detail=f"job with id {id} not found")

    def get_jobs_from_rabbit_mq(self):
        try:
            self.rbmq_channel.queue_declare(
                queue=self.rbmq_queue_name,
                durable=True,
                arguments={"x-queue-type": "quorum"},
            )

            self.rbmq_channel.basic_consume(
                queue=self.rbmq_queue_name,
                on_message_callback=self.pika_callback,
                auto_ack=True,
            )

            self.rbmq_channel.start_consuming()
        except Exception as e:
            print(repr(e))
            self.rbmq_channel.close()
            sys.exit(1)

    def pika_callback(self, ch, method, properties, body: bytes):
        job = DLOptions.model_validate_json(body.decode())
        self.download(job)

    def get_jobs(self, status: Status | None = None):
        if status:
            return self.get_jobs_of_status(status)
        return list(self.jobs.values())

    def get_jobs_of_status(self, status: Status) -> list[Job]:
        return [job for job in self.jobs.values() if job.status == status]

    @asynccontextmanager
    async def lifespan(self, _: FastAPI):
        cleanup_task = asyncio.create_task(self.clean_jobs())
        retry_task = asyncio.create_task(self.retry_jobs())

        yield

        cleanup_task.cancel()
        retry_task.cancel()

        asyncio.gather(cleanup_task, retry_task, return_exceptions=True)

    async def clean_jobs(self):
        while True:
            cutoff = datetime.now() - timedelta(hours=1)
            toclean: list[UUID] = list()

            for job in self.jobs.values():
                if (
                    job.status == Status.COMPLETED
                    and job.finished_at
                    and job.finished_at < cutoff
                ):
                    toclean.append(job.id)

            for id in toclean:
                del self.jobs[id]

            await asyncio.sleep(self.cleanup_timeout)

    async def retry_jobs(self):
        while True:
            for job in self.jobs.values():
                if job.status == Status.FAILED and job.retries <= self.max_retries:
                    job.status = Status.QUEUED
                    job.retries += 1
                    self.queue.put(job)

            await asyncio.sleep(self.retry_timeout)

    def get_rabbitmq_connection(self) -> pika.BlockingConnection:
        return pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rbmq_address,
                port=self.rbmq_port,
                virtual_host=self.rbmq_vhost,
                credentials=pika.PlainCredentials(
                    username=self.rbmq_username,
                    password=self.rbmq_password,
                ),
            )
        )
