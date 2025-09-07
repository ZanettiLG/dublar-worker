from dep_base import DepBase
from transformers import pipeline, infer_device
from typing import Optional, Dict, Any, Callable

class Transformers(DepBase):

    model = None
    task = None

    def __init__(self, name: str, model: str, task: str):
        super().__init__(name)
        self.model = model
        self.task = task

    def load(self):
        self.client = pipeline(self.task, model=self.model, device_map="auto")
    
    async def execute(
        self, 
        url: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        