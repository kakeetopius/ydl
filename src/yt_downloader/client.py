import json
import requests
import pika
from dataclasses import dataclass
from yt_downloader.downloader import Options as DLOptions
from yt_downloader.helpers import join_host_port


class Client:
    def __init__(
        self,
        server_address: str = "localhost",
        server_port: int = 2210,
        noqueue: bool = False,
        rbmq_address: str = "localhost",
        rbmq_port: int = 5672,
        rbmq_vhost: str = "",
        rbmq_username: str = "",
        rbmq_password: str = "",
    ):
        if not server_address:
            server_address = "localhost"
        if not server_port:
            server_port = 2210

        self.download_ep = "/download"
        self.address: str = server_address
        self.port = server_port
        self.noqueue = noqueue

        self.rbmq_address = rbmq_address
        self.rbmq_port = rbmq_port
        self.rbmq_vhost = rbmq_vhost
        self.rbmq_username = rbmq_username
        self.rbmq_password = rbmq_password
        self.rbmq_queue_name = "ydl_download_queue"

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

    def send_download_request_to_rbmqueue(self, opts: DLOptions):
        try:
            con = self.get_rabbitmq_connection()
            channel = con.channel()
            channel.queue_declare(
                queue=self.rbmq_queue_name,
                durable=True,
                arguments={"x-queue-type": "quorum"},
            )

            channel.confirm_delivery()
            channel.basic_publish(
                exchange="",
                routing_key=self.rbmq_queue_name,
                body=opts.model_dump_json().encode(),
            )
            con.close()
            print("Successfully sent download request to rabbitmq queue.")
        except Exception as e:
            print(repr(e))

    def send_download_request(self, opts: DLOptions):
        if not self.noqueue:
            return self.send_download_request_to_rbmqueue(opts)

        resp = requests.post(
            self.full_url(self.download_ep),
            json=opts.model_dump(),
        )
        print(resp.json())

    def full_url(self, endpoint: str):
        return f"http://{join_host_port(self.address, self.port)}{endpoint}"
