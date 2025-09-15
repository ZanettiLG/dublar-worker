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
            import torch
            
            # Usar device baseado na disponibilidade de CUDA
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Carregando pipeline {self.task} com modelo {self.model} no device {device}")
            
            self.client = pipeline(self.task, model=self.model, device=device)
            logger.info("Pipeline carregado com sucesso!")
            
        except ImportError as e:
            logger.error(f"Transformers não disponível: {e}")
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