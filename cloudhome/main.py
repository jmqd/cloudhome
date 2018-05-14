import watchdog
import os
import boto3
import config as _config
from local import Local
from cloud import Storage
from sync import SyncTask

class CloudHome:
    def __init__(
            self,
            config: _config.Config,
            storage: Storage,
            local: Local) -> None:
        self.config = config
        self.storage = storage
        self.local = local

    def start(self) -> None:
        task = SyncTask(self.local, self.storage)
        task.run()


def initialize() -> None:
    s3 = boto3.client('s3')
    config = _config.load()
    storage = Storage(config, s3)
    local = Local(config)
    cloudhome = CloudHome(config, storage, local)
    cloudhome.start()

if __name__ == '__main__':
    initialize()
