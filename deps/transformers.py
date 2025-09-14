from .dep_base import DepBase
from typing import Optional, Dict, Any, Callable
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

class Transformers(DepBase):

    name = 'transformers'
    model = None
    task = None

    def __init__(self, engine: Any, task: str, model: str):
        super().__init__(engine=engine)
        self.model = model
        self.task = task

    def load(self):
        try:
            from transformers import pipeline
            # Usar device padrão se infer_device não estiver disponível
            try:
                from transformers import infer_device
                device = infer_device()
            except ImportError:
                device = "cpu"
            self.client = pipeline(self.task, model=self.model, device=device)
        except ImportError as e:
            logger.error(f"Transformers não disponível: {e}")
            # Mock client para testes
            self.client = None
        except Exception as e:
            logger.error(f"Erro ao carregar pipeline: {e}")
            self.client = None
    
    async def execute(
        self, 
        url: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        pass