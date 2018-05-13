import config as _config

class Local:
    def __init__(config: _config.Config) -> None:
        self.config = config

    @property
    def root(self):
        return config.get('root')

    @property
    def manifest(self):
        with open(LOCAL_MANIFEST_LOCATION, 'r') as f:
            return json.load(f)

    def list(self):
        for root, dirs, filenames in os.walk(self.config.root_dir):
            for filename in filenames:
                print(os.path.join(root, filename))
