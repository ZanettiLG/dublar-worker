import logging
from enum import Enum
from deps.transformers import Transformers
from typing import Optional, Dict, Any, Callable, List
from sentence_transformers import SentenceTransformer
import hdbscan
import numpy as np

# Configuração de logging
logger = logging.getLogger(__name__)

class DiarizerModels(Enum):
    """Modelos para diarização"""
    MULTILINGUAL_MINI = 'paraphrase-multilingual-MiniLM-L12-v2'
    MULTILINGUAL_BASE = 'paraphrase-multilingual-mpnet-base-v2'
    ALL_MINI = 'all-MiniLM-L6-v2'

class Diarizer(Transformers):
    """Diarizer - Identifica diferentes falantes em áudio"""
    name = 'diarizer'
    model = None
    task = None
    embedder = None
    clusterer = None

    def __init__(self, engine: Any, model: str = DiarizerModels.MULTILINGUAL_MINI.name):
        """Inicializa o Diarizer"""
        # Converte o nome do modelo para o nome completo
        full_model_name = DiarizerModels[model].value
        logger.info(f"Diarizer: modelo '{model}' convertido para '{full_model_name}'")
        super().__init__(engine=engine, task='feature-extraction', model=full_model_name)

    def load(self):
        """Carrega os modelos necessários para diarização"""
        try:
            # Carrega o modelo de embeddings para clustering
            logger.info("Carregando modelo de embeddings...")
            self.embedder = SentenceTransformer(self.model)
            
            # Configura o clusterer HDBSCAN
            logger.info("Configurando clusterer HDBSCAN...")
            self.clusterer = hdbscan.HDBSCAN(
                min_cluster_size=2, 
                metric="euclidean",
                cluster_selection_epsilon=0.1
            )
            
            logger.info("Diarizer carregado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao carregar Diarizer: {e}")
            # Fallback para modelo menor em caso de erro
            try:
                logger.info("Tentando fallback para modelo multilingual mini...")
                self.embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
                self.clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean")
                logger.info("Fallback carregado com sucesso!")
            except Exception as fallback_error:
                logger.error(f"Erro no fallback: {fallback_error}")
                self.embedder = None
                self.clusterer = None

    async def execute(
        self, 
        data: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executa a diarização dos speeches"""
        try:
            # Extrai dados da entrada
            audio_url = data.get("audio_url")
            speechs = data.get("speechs", [])
            
            if not speechs:
                logger.warning("Nenhum speech fornecido para diarização")
                return {"speakers": [], "segments": []}

            # Verifica se os modelos foram carregados corretamente
            if self.embedder is None or self.clusterer is None:
                logger.error("Modelos do diarizer não foram carregados. Tentando recarregar...")
                self.load()
                if self.embedder is None:
                    logger.error("Falha ao carregar modelos do diarizer após tentativa de recarregamento")
                    return {"speakers": [], "segments": []}

            # 1. Geração de embeddings dos textos dos speeches
            logger.info("Gerando embeddings dos speeches...")
            texts = [speech.get("text", "") for speech in speechs]
            embeddings = self.embedder.encode(texts)

            # 2. Clustering para identificar falantes
            logger.info("Executando clustering...")
            labels = self.clusterer.fit_predict(embeddings)

            # 3. Organização dos resultados
            logger.info("Organizando resultados...")
            speakers_set = set()
            diarized_segments = []

            for i, (speech, label) in enumerate(zip(speechs, labels)):
                speaker_id = f"Speaker_{label}" if label != -1 else "Unknown"
                speakers_set.add(speaker_id)
                diarized_segments.append(speaker_id)

            # 4. Resultado final
            result = {
                "speakers": sorted(list(speakers_set)),
                "segments": diarized_segments,
                "total_segments": len(speechs),
                "total_speakers": len([s for s in speakers_set if s != "Unknown"])
            }

            logger.info(f"Diarização concluída: {result['total_speakers']} falantes identificados")
            return result

        except Exception as e:
            logger.error(f"Erro durante diarização: {e}")
            return {"speakers": [], "segments": [], "error": str(e)}
