CONFIGURATION_LOCATION = os.path.expanduser("~/.cloudhome")

class Config:
    def __init__(self, data: dict) -> None:
        self.root_dir = data.get('root_dir')
        self.include = data.get('include')

def load() -> Config:
    config_data = read_local_config()
    config = Config(config_data)

def read_local_config() -> dict:
    try:
        with open(CONFIGURATION_LOCATION, 'r') as f:
            return json.load(f)
    except IOError:
        return {}
