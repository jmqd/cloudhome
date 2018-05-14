import os
import config as _config

class Local:
    def __init__(self, config: _config.Config) -> None:
        self.config = config

    @property
    def manifest(self):
        with open(LOCAL_MANIFEST_LOCATION, 'r') as f:
            return json.load(f)

    def list_all(self):
        for synced_dir in self.config.synced_dirs:
            return self.__recursive_list(synced_dir)

    def __recursive_list(self, _root):
        for root, dirs, filenames in os.walk(_root):
            for filename in filenames:
                yield filename

            for d in dirs:
                self.__recursive_list(d)
