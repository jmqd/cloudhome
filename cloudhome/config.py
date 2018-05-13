class Config:
    def __init__(self, data: dict) -> None:
        self.root_dir = data.get('root_dir')
        self.ignore = data.get('ignore')
