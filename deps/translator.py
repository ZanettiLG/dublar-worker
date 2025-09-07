from deps.transformers import Transformers
from transformers import pipeline, infer_device
from typing import Optional, Dict, Any, Callable

device = infer_device()

class Translator(Transformers):

    static models = {
        'm2m100-1.2b': 'facebook/m2m100-1.2b',
        'm2m100-1.2b': 'facebook/m2m100-1.2b',
    }

    model = None
    task = None

    def __init__(self, name: str, model: str):
        super().__init__(name)
        self.model = model
        self.task = 'automatic-speech-recognition'

    def load(self):
        super().load()
    
    async def execute(
        self, 
        text: str,
        target_language: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        return self.client(text, target_language=target_language)