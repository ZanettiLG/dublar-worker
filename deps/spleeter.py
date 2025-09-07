from dep_base import DepBase
from spleeter import Spleeter

class Spleeter(DepBase):

    def __init__(self, name: str):
        super().__init__(name)

    def load(self):
        self.client = Spleeter('spleeter:2stems')
    
    async def execute(
        self, 
        audio_path: str, 
        output_path: str,
    ) -> bool:
        self.client.separate_to_file(audio_path, output_path)
        