import os
import json

CONFIGURATION_LOCATION = os.path.expanduser("~/.cloudhome")

class Config:
    def __init__(self, data: dict) -> None:
        self.synced_dirs = [os.path.expanduser(f) for f in data.get('synced_dirs', [])]

def load() -> Config:
    config_data = read_local_config()
    return Config(config_data)

def read_local_config() -> dict:
    try:
        with open(CONFIGURATION_LOCATION, 'r') as f:
            return json.load(f)
    except IOError:
        return {}
