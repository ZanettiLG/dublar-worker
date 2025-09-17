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
    
    async def execute_batch(
        self, 
        texts: list[str],
        target_language: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> list[str]:
        """
        Traduz múltiplos textos em uma única chamada ao modelo para melhor performance.
        Usa enumeração para separar os textos na resposta.
        """
        if not texts:
            return []
        
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
        
        # Cria texto enumerado para tradução em lote
        # Formato: "1. Texto 1\n2. Texto 2\n3. Texto 3..."
        enumerated_text = "\n".join([f"{i+1}. {text}" for i, text in enumerate(texts)])
        
        # Traduz o texto enumerado
        result = self.client(enumerated_text, src_lang=src_lang, tgt_lang=tgt_lang)
        
        # Extrai o texto traduzido
        if isinstance(result, list) and len(result) > 0:
            translated_text = result[0]['translation_text']
        elif isinstance(result, dict) and 'translation_text' in result:
            translated_text = result['translation_text']
        else:
            translated_text = str(result)
        
        # Parseia a resposta para extrair cada tradução individual
        return self._parse_batch_translation(translated_text, len(texts))
    
    def _parse_batch_translation(self, translated_text: str, expected_count: int) -> list[str]:
        """
        Parseia o texto traduzido enumerado para extrair as traduções individuais.
        """
        lines = translated_text.strip().split('\n')
        translations = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Procura por padrão "número. tradução" no início da linha
            # Exemplo: "1. Minha mãe disse que eu poderia pegar dois."
            for i in range(1, expected_count + 1):
                if line.startswith(f"{i}."):
                    # Remove o número e ponto do início
                    translation = line[2:].strip()
                    translations.append(translation)
                    break
            else:
                # Se não encontrou o padrão esperado, adiciona a linha como está
                # (fallback para casos onde a numeração pode ter mudado)
                translations.append(line)
        
        # Garante que temos o número correto de traduções
        while len(translations) < expected_count:
            translations.append("")
        
        return translations[:expected_count]