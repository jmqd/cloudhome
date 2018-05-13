import watchdog
import os
import config as _config
from cloud import Storage
from sync import SyncTask

class CloudHome:
    def __init__(self, config: _config.Config, storage: Storage) -> None:
        self.config = config

    def start(self) -> None:
        task = SyncTask(self.config)
        task.run()


def initialize() -> None:
    config = _config.load()
    storage = Storage(config)
    cloudhome = CloudHome(config, storage)
    cloudhome.start()

if __name__ == '__main__':
    initialize()
