import logging
import os
import tempfile
from typing import Optional, Dict, Any, Callable
from deps.transformers import Transformers
from TTS.api import TTS

# Configuração de logging
logger = logging.getLogger(__name__)

class Coqui(Transformers):
    """Coqui - Síntese de fala usando Coqui TTS"""
    name = 'coqui'
    model = None
    task = None
    tts_model = None

    def __init__(self, engine: Any, model: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        """Inicializa o CoquiTTS"""
        logger.info(f"CoquiTTS: inicializando com modelo '{model}'")
        super().__init__(engine=engine, task='text-to-speech', model=model)

    def load(self):
        """Carrega o modelo TTS"""
        try:
            logger.info("Carregando modelo Coqui TTS...")
            self.tts_model = TTS(self.model)
            logger.info("Coqui TTS carregado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao carregar Coqui TTS: {e}")
            # Fallback para modelo menor
            try:
                logger.info("Tentando fallback para modelo tts_models/en/ljspeech/tacotron2-DDC...")
                self.tts_model = TTS("tts_models/en/ljspeech/tacotron2-DDC")
                logger.info("Fallback carregado com sucesso!")
            except Exception as fallback_error:
                logger.error(f"Erro no fallback: {fallback_error}")
                self.tts_model = None

    async def execute(
        self, 
        data: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executa a síntese de fala"""
        try:
            # Extrai dados da entrada
            text = data.get("text", "")
            audio_url = data.get("audio_url", "")
            speaker_wav = data.get("speaker_wav", None)  # Para clonagem de voz
            
            if not text:
                logger.warning("Nenhum texto fornecido para síntese")
                return {"error": "Texto não fornecido"}

            # Verifica se o modelo foi carregado corretamente
            if self.tts_model is None:
                logger.error("Modelo TTS não foi carregado. Tentando recarregar...")
                self.load()
                if self.tts_model is None:
                    logger.error("Falha ao carregar modelo TTS após tentativa de recarregamento")
                    return {"error": "Modelo TTS não disponível"}

            # Cria arquivo temporário para saída
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                output_path = temp_file.name

            logger.info(f"Sintetizando fala para texto: '{text[:50]}...'")
            
            # Executa síntese de fala
            if speaker_wav and os.path.exists(speaker_wav):
                # Clonagem de voz usando arquivo de referência
                logger.info(f"Usando clonagem de voz com arquivo: {speaker_wav}")
                self.tts_model.tts_to_file(
                    text=text,
                    speaker_wav=speaker_wav,
                    language="pt",
                    file_path=output_path
                )
            elif audio_url and os.path.exists(audio_url):
                # Clonagem de voz usando URL do áudio
                logger.info(f"Usando clonagem de voz com áudio: {audio_url}")
                self.tts_model.tts_to_file(
                    text=text,
                    speaker_wav=audio_url,
                    language="pt",
                    file_path=output_path
                )
            else:
                # Síntese normal sem clonagem
                logger.info("Executando síntese de fala normal")
                self.tts_model.tts_to_file(
                    text=text,
                    language="pt",
                    file_path=output_path
                )

            # Verifica se o arquivo foi criado
            if not os.path.exists(output_path):
                logger.error("Arquivo de saída não foi criado")
                return {"error": "Falha na síntese de fala"}

            # Obtém informações do arquivo
            file_size = os.path.getsize(output_path)
            logger.info(f"Síntese concluída: {output_path} ({file_size} bytes)")

            # Resultado final
            result = {
                "output_path": output_path,
                "file_size": file_size,
                "text": text,
                "model_used": self.model,
                "success": True
            }

            logger.info("Síntese de fala concluída com sucesso!")
            return result

        except Exception as e:
            logger.error(f"Erro durante síntese de fala: {e}")
            return {"error": str(e), "success": False}

    def cleanup(self, file_path: str):
        """Remove arquivo temporário"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Arquivo temporário removido: {file_path}")
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo temporário {file_path}: {e}")
