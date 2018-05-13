from local import Local
from cloud import Storage

class SyncTask:
    def __init__(self, local: Local, storage: Storage) -> None:
        self.local = local
        self.storage = storage

    def run(self):
        self.local.update_local_manifest()
        storage_manifest = self.storage.read_manifest()
        local_manifest = self.local.read_manifest()

    def update_local_manifest(self):
        local_files = self.local.list()

