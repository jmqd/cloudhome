import boto3
import typing
from typing import TextIO

class Storage:
    def __init__(self, s3, bucket_name) -> None:
        self.s3 = s3
        self.bucket_name = bucket_name

    def save(self, data: TextIO) -> None:
        pass

    def load_after(self, date: str) -> None:
        pass
