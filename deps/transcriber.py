from deps.transformers import Transformers
from transformers import pipeline, infer_device
from typing import Optional, Dict, Any, Callable

device = infer_device()

class Transcriber(Transformers):

    static models = {
        'whisper-turbo': 'openai/whisper-large-v3-turbo',
        'whisper-large': 'openai/whisper-large-v3',
        'whisper-medium': 'openai/whisper-medium',
        'whisper-small': 'openai/whisper-small',
        'whisper-tiny': 'openai/whisper-tiny',
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
        audio_path: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        return self.client(audio_path, return_timestamps=True)