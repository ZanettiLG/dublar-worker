import logging
from enum import Enum
from deps.transformers import Transformers
from typing import Optional, Dict, Any, Callable

# Configuração de logging
logger = logging.getLogger(__name__)

class WhisperModels (Enum):
    """Modelos do Whisper"""
    TINY = 'openai/whisper-tiny'
    SMALL = 'openai/whisper-small'
    TURBO = 'openai/whisper-large-v3-turbo'
    LARGE = 'openai/whisper-large-v3'
    MEDIUM = 'openai/whisper-medium'

class Transcriber(Transformers):
    """Transcriber"""
    name = 'transcriber'
    model = None
    task = None

    def __init__(self, engine: Any, model: str = WhisperModels.SMALL.name):
        """Inicializa o Transcriber"""
        # Converte o nome do modelo para o nome completo do Hugging Face
        full_model_name = WhisperModels[model].value
        logger.info(f"Transcriber: modelo '{model}' convertido para '{full_model_name}'")
        super().__init__(engine=engine, task='automatic-speech-recognition', model=full_model_name)

    def load(self):
        """Carrega o Transcriber"""
        try:
            super().load()
        except Exception as e:
            logger.error(f"Erro ao carregar Transcriber: {e}")
            # Atualiza o modelo na classe pai para o fallback
            self.model = WhisperModels.TINY.value   # Atualiza o modelo na classe pai
            super().load()
    
    async def execute(
        self, 
        audio_path: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executa a transcrição"""
        try:
            # Verifica se o client foi carregado corretamente
            if self.client is None:
                logger.error("Client do transcriber não foi carregado. Tentando recarregar...")
                self.load()
                if self.client is None:
                    logger.error("Falha ao carregar client do transcriber após tentativa de recarregamento")
                    return {"text": "", "chunks": []}
            
            result = self.client(audio_path, return_timestamps=True)
            return result['chunks']
        except Exception as e:
            logger.error(f"Erro durante transcrição: {e}")
            return {"text": "", "chunks": []}