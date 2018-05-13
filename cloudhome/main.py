import watchdog
import os

HOME_DIRECTORY = os.path.expanduser("~")

class CloudHome:
    def __init__(self, config: dict) -> None:
        self.config = config

    def start(self) -> None:
        local_hash = self.determine_local_hash()

def initialize() -> None:
    with open(CONFIGURATION_LOCATION, 'r') as f:
        config = json.load(f)

    cloudhome = CloudHome(config)
    cloudhome.start()

if __name__ == '__main__':
    initialize()
