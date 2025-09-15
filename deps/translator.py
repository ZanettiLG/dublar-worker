from deps.transformers import Transformers
from transformers import pipeline
from typing import Optional, Dict, Any, Callable
import torch
from enum import Enum

device = "cuda" if torch.cuda.is_available() else "cpu"

class TranslatorModels (Enum):
    """Modelos do Translator"""
    M2M100_1_2B = 'facebook/m2m100_1.2B'

class Translator(Transformers):
    name = 'translator'
    model = None
    task = None

    def __init__(self, engine: Any, model: str = TranslatorModels.M2M100_1_2B.name):
        full_model_name = TranslatorModels[model].value
        super().__init__(engine=engine, task='translation', model=full_model_name)

    def load(self):
        super().load()
    
    async def execute(
        self, 
        text: str,
        target_language: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        # Mapeia códigos de idioma para o formato do M2M100
        lang_map = {
            'PT': 'pt',
            'EN': 'en',
            'ES': 'es',
            'FR': 'fr',
            'DE': 'de'
        }
        
        src_lang = 'en'  # Sempre inglês como origem
        tgt_lang = lang_map.get(target_language.upper(), 'pt')
        
        result = self.client(text, src_lang=src_lang, tgt_lang=tgt_lang)
        
        # Retorna apenas o texto traduzido
        if isinstance(result, list) and len(result) > 0:
            return result[0]['translation_text']
        elif isinstance(result, dict) and 'translation_text' in result:
            return result['translation_text']
        else:
            return str(result)