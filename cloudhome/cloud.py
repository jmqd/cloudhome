import boto3
import typing
from typing import TextIO

class Storage:
    def __init__(self, config, s3) -> None:
        self.config = config
        self.s3 = s3

    def save(self, data: TextIO) -> None:
        pass

    def load_after(self, date: str) -> None:
        pass
