from engines.worker import Worker

class DepBase:

    name = "dep"

    def __init__(self, engine=Worker):
        self.engine = engine
        self.load()
    
    def load(self):
        pass