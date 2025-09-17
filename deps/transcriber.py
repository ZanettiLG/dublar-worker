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
        """Executa a transcrição com timestamps precisos"""
        try:
            # Usa return_timestamps="word" para obter timestamps no nível da palavra
            result = self.client(audio_path, return_timestamps="word")
            
            # Processa os timestamps de palavras para criar frases completas
            processed_sentences = self._process_word_timestamps(result)
            
            return processed_sentences
            
        except Exception as e:
            logger.error(f"Erro durante transcrição: {e}")
            return {"text": "", "chunks": []}
    
    def _process_word_timestamps(self, result: Dict[str, Any]) -> list:
        """Processa timestamps de palavras para criar frases completas agrupadas"""
        try:
            print("🔍 Analisando estrutura do resultado do Whisper...")
            print(f"   Chaves disponíveis: {list(result.keys())}")
            
            chunks = result.get('chunks', [])
            if not chunks:
                print("⚠️ Nenhum chunk encontrado no resultado")
                return []
            
            print(f"   Encontrados {len(chunks)} chunks")
            
            # Coleta todas as palavras de todos os chunks
            all_words = []
            
            for i, chunk in enumerate(chunks):
                # Verifica se o chunk tem texto válido
                if not chunk.get('text', '').strip():
                    continue
                
                # Obtém timestamps de palavras se disponíveis
                word_timestamps = chunk.get('word_timestamps', [])
                
                if word_timestamps:
                    all_words.extend(word_timestamps)
                else:
                    # Se não há word_timestamps, cria uma palavra artificial do chunk
                    text = chunk.get('text', '').strip()
                    timestamp = chunk.get('timestamp', [0, 0])
                    word_data = {
                        'word': text,
                        'start': timestamp[0],
                        'end': timestamp[1]
                    }
                    all_words.append(word_data)
            
            print(f"   Total de palavras coletadas: {len(all_words)}")
            
            if not all_words:
                print("⚠️ Nenhuma palavra encontrada, usando fallback para chunks")
                return self._fallback_to_chunks(chunks)
            
            # Agrupa palavras em frases baseado em pontuação e pausas
            print("🔄 Agrupando palavras em frases...")
            sentences = self._group_words_into_sentences(all_words)
            
            # Aplica fusão adaptativa para unir segmentos de fala contínua
            print("🔗 Aplicando fusão adaptativa...")
            merged_sentences = self._adaptive_segmentation_merge(sentences)
            
            print(f"✅ Processadas {len(merged_sentences)} frases (fusão: {len(sentences)} → {len(merged_sentences)})")
            logger.info(f"Processadas {len(merged_sentences)} frases após fusão adaptativa")
            return merged_sentences
            
        except Exception as e:
            logger.error(f"Erro ao processar timestamps de palavras: {e}")
            # Fallback para processamento básico
            return [chunk for chunk in result.get('chunks', []) if chunk.get('text', '').strip() != '']
    
    def _group_words_into_sentences(self, words: list) -> list:
        """Agrupa palavras em frases baseado em pontuação e pausas"""
        if not words:
            return []
        
        sentences = []
        current_sentence_words = []
        
        for i, word_data in enumerate(words):
            word = word_data['word']
            current_sentence_words.append(word_data)
            
            # Verifica se é o fim de uma frase
            is_sentence_end = self._is_sentence_end(word, word_data, words, i)
            
            if is_sentence_end or i == len(words) - 1:
                if current_sentence_words:
                    sentence = self._create_sentence_from_words(current_sentence_words)
                    if sentence['text'].strip():
                        sentences.append(sentence)
                    current_sentence_words = []
        
        return sentences
    
    def _is_sentence_end(self, word: str, word_data: dict, all_words: list, index: int) -> bool:
        """Determina se uma palavra marca o fim de uma frase baseado em múltiplos critérios"""
        if index >= len(all_words) - 1:
            return True  # Última palavra sempre é fim de frase
        
        next_word = all_words[index + 1]
        pause_duration = next_word['start'] - word_data['end']
        next_word_text = next_word['word']
        
        # 1. PONTUAÇÃO FORTE - Sempre quebra frase
        if word.endswith(('.', '!', '?')):
            return True
        
        # 2. PAUSA MUITO LONGA - Sempre quebra frase
        if pause_duration > 1.2:
            return True
        
        # 3. ANÁLISE SEMÂNTICA BÁSICA - Verifica mudança de contexto
        if self._is_context_break(word, next_word_text, pause_duration, index, all_words):
            return True
        
        # 4. PAUSA LONGA COM PONTUAÇÃO - Quebra com pausa menor
        has_punctuation = word.endswith((',', ';', ':'))
        if has_punctuation and pause_duration > 0.6:
            return True
        
        # 5. MUDANÇA DE FALANTE INDICADA - Maiúscula + pausa moderada
        if (next_word_text and next_word_text[0].isupper() and 
            pause_duration > 0.4 and index > 2):
            return True
        
        # 6. PAUSA LONGA GERAL - Fallback para pausas longas
        if pause_duration > 0.8:
            return True
        
        return False
    
    def _is_context_break(self, current_word: str, next_word: str, pause_duration: float, index: int, all_words: list) -> bool:
        """Analisa se há quebra de contexto entre palavras"""
        if not next_word or index < 2:
            return False
        
        # Palavras que indicam início de nova frase/contexto
        context_starters = {
            'and', 'but', 'however', 'therefore', 'meanwhile', 'suddenly', 
            'then', 'now', 'so', 'well', 'okay', 'yes', 'no', 'oh',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that',
            'the', 'a', 'an', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        # Palavras que indicam continuação
        continuation_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over', 'under'
        }
        
        # Se a próxima palavra é um iniciador de contexto E há pausa moderada
        if (next_word.lower() in context_starters and pause_duration > 0.3):
            return True
        
        # Se a palavra atual termina com pontuação fraca E próxima é iniciador
        weak_punctuation = current_word.endswith((',', ';', ':'))
        if weak_punctuation and next_word.lower() in context_starters:
            return True
        
        # Análise de padrões de fala
        if self._detect_speech_pattern_break(current_word, next_word, pause_duration, index, all_words):
            return True
        
        return False
    
    def _detect_speech_pattern_break(self, current_word: str, next_word: str, pause_duration: float, index: int, all_words: list) -> bool:
        """Detecta quebras baseadas em padrões de fala"""
        if index < 3 or index >= len(all_words) - 2:
            return False
        
        # Padrão: pergunta + resposta
        if (current_word.endswith('?') and 
            next_word.lower() in ['yes', 'no', 'well', 'okay', 'sure', 'right'] and
            pause_duration > 0.2):
            return True
        
        # Padrão: exclamação + nova frase
        if (current_word.endswith('!') and 
            next_word[0].isupper() and pause_duration > 0.3):
            return True
        
        # Padrão: mudança de pessoa (I -> You, You -> I, etc.)
        person_pronouns = {'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        if (current_word.lower() in person_pronouns and 
            next_word.lower() in person_pronouns and
            current_word.lower() != next_word.lower() and
            pause_duration > 0.4):
            return True
        
        # Padrão: mudança de tempo verbal (was -> is, did -> do, etc.)
        if self._detect_tense_change(current_word, next_word, pause_duration):
            return True
        
        return False
    
    def _detect_tense_change(self, current_word: str, next_word: str, pause_duration: float) -> bool:
        """Detecta mudança de tempo verbal que pode indicar nova frase"""
        if pause_duration < 0.3:
            return False
        
        # Verbos auxiliares que indicam mudança de tempo
        past_aux = {'was', 'were', 'had', 'did', 'could', 'would', 'should'}
        present_aux = {'is', 'are', 'have', 'do', 'can', 'will', 'shall'}
        
        current_lower = current_word.lower()
        next_lower = next_word.lower()
        
        # Mudança de passado para presente
        if (current_lower in past_aux and next_lower in present_aux):
            return True
        
        # Mudança de presente para passado
        if (current_lower in present_aux and next_lower in past_aux):
            return True
        
        return False
    
    def _create_sentence_from_words(self, word_timestamps: list) -> dict:
        """Cria uma frase completa a partir de uma lista de palavras"""
        if not word_timestamps:
            return {'text': '', 'start_time': 0.0, 'end_time': 0.0}
        
        # Reconstrói o texto da frase
        words = [word_data['word'] for word_data in word_timestamps]
        sentence_text = ' '.join(words)
        
        # Usa o primeiro e último timestamp para maior precisão
        start_time = word_timestamps[0]['start']
        end_time = word_timestamps[-1]['end']
        
        return {
            'text': sentence_text.strip(),
            'timestamp': [start_time, end_time],
            'start_time': start_time,
            'end_time': end_time,
            'confidence': 1.0,  # Pode ser calculado baseado nas confianças das palavras
            'word_timestamps': word_timestamps
        }
    
    def _fallback_to_chunks(self, chunks: list) -> list:
        """Fallback para usar chunks originais quando word_timestamps não está disponível"""
        processed_chunks = []
        
        for chunk in chunks:
            if not chunk.get('text', '').strip():
                continue
            
            start_time = chunk.get('timestamp', [0, 0])[0]
            end_time = chunk.get('timestamp', [0, 0])[1]
            
            processed_chunk = {
                'text': chunk['text'].strip(),
                'timestamp': [start_time, end_time],
                'start_time': start_time,
                'end_time': end_time,
                'confidence': chunk.get('confidence', 1.0)
            }
            
            processed_chunks.append(processed_chunk)
        
        return processed_chunks
    
    def _adaptive_segmentation_merge(self, sentences: list, silence_threshold: float = 0.5, max_duration: float = 10.0) -> list:
        """Fusão adaptativa inteligente: une segmentos de fala contínua baseado em contexto e semântica"""
        if not sentences or len(sentences) <= 1:
            return sentences
        
        merged_sentences = []
        current_merge = None
        
        for i, sentence in enumerate(sentences):
            start_time = sentence.get('start_time', 0)
            end_time = sentence.get('end_time', start_time + 1)
            duration = end_time - start_time
            
            # Se não há merge ativo, inicia um novo
            if current_merge is None:
                current_merge = {
                    'text': sentence['text'],
                    'timestamp': [start_time, end_time],
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': sentence.get('confidence', 1.0),
                    'word_timestamps': sentence.get('word_timestamps', [])
                }
                continue
            
            # Calcula pausa entre segmentos
            pause_duration = start_time - current_merge['end_time']
            current_duration = end_time - current_merge['start_time']
            
            # Análise semântica para determinar se deve fazer merge
            should_merge = self._should_merge_sentences(
                current_merge['text'], 
                sentence['text'], 
                pause_duration, 
                current_duration, 
                max_duration,
                i < len(sentences) - 1
            )
            
            if should_merge:
                # Fusão: combina textos e atualiza timestamps
                current_merge['text'] += ' ' + sentence['text']
                current_merge['timestamp'] = [current_merge['start_time'], end_time]
                current_merge['end_time'] = end_time
                current_merge['confidence'] = min(current_merge['confidence'], sentence.get('confidence', 1.0))
                
                # Combina word_timestamps se disponível
                if sentence.get('word_timestamps'):
                    if current_merge.get('word_timestamps'):
                        current_merge['word_timestamps'].extend(sentence['word_timestamps'])
                    else:
                        current_merge['word_timestamps'] = sentence['word_timestamps']
                
                print(f"   🔗 Fusão: {pause_duration:.2f}s pausa, {current_duration:.2f}s total")
            else:
                # Finaliza merge atual e inicia novo
                merged_sentences.append(current_merge)
                current_merge = {
                    'text': sentence['text'],
                    'timestamp': [start_time, end_time],
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': sentence.get('confidence', 1.0),
                    'word_timestamps': sentence.get('word_timestamps', [])
                }
                
                if pause_duration >= silence_threshold:
                    print(f"   ⏸️ Pausa longa: {pause_duration:.2f}s")
                elif current_duration > max_duration:
                    print(f"   ⏱️ Duração máxima: {current_duration:.2f}s")
                else:
                    print(f"   🚫 Quebra semântica detectada")
        
        # Adiciona o último merge se existir
        if current_merge is not None:
            merged_sentences.append(current_merge)
        
        # Estatísticas da fusão
        original_count = len(sentences)
        merged_count = len(merged_sentences)
        fusion_rate = (original_count - merged_count) / original_count * 100 if original_count > 0 else 0
        
        print(f"   📊 Fusão: {original_count} → {merged_count} segmentos ({fusion_rate:.1f}% redução)")
        
        return merged_sentences
    
    def _should_merge_sentences(self, current_text: str, next_text: str, pause_duration: float, 
                               current_duration: float, max_duration: float, not_last: bool) -> bool:
        """Determina se duas frases devem ser unidas baseado em análise semântica"""
        
        # 1. Critérios básicos de duração e pausa
        if not not_last or current_duration > max_duration or pause_duration > 0.8:
            return False
        
        # 2. Análise de pontuação - não une se há pontuação forte no final
        if current_text.rstrip().endswith(('.', '!', '?')):
            return False
        
        # 3. Análise de contexto - verifica se as frases são relacionadas
        if not self._are_sentences_related(current_text, next_text):
            return False
        
        # 4. Análise de padrões de fala
        if self._detect_conversation_break(current_text, next_text):
            return False
        
        # 5. Critério de pausa adaptativo baseado no contexto
        required_pause = self._get_required_pause_for_merge(current_text, next_text)
        if pause_duration > required_pause:
            return False
        
        return True
    
    def _are_sentences_related(self, current_text: str, next_text: str) -> bool:
        """Verifica se duas frases são semanticamente relacionadas"""
        current_lower = current_text.lower().strip()
        next_lower = next_text.lower().strip()
        
        # Palavras que indicam continuação
        continuation_indicators = {
            'and', 'but', 'so', 'then', 'also', 'furthermore', 'moreover',
            'however', 'although', 'while', 'because', 'since', 'as'
        }
        
        # Se a próxima frase começa com indicador de continuação
        next_first_word = next_lower.split()[0] if next_lower.split() else ""
        if next_first_word in continuation_indicators:
            return True
        
        # Palavras que indicam quebra de contexto
        context_breakers = {
            'okay', 'well', 'right', 'sure', 'yes', 'no', 'oh', 'ah',
            'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Se a próxima frase começa com quebrador de contexto
        if next_first_word in context_breakers:
            return False
        
        # Análise de pronomes - mudança de pessoa indica nova frase
        person_pronouns = {'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        current_has_pronoun = any(pronoun in current_lower for pronoun in person_pronouns)
        next_has_pronoun = any(pronoun in next_lower for pronoun in person_pronouns)
        
        if current_has_pronoun and next_has_pronoun:
            # Verifica se são pronomes diferentes
            current_pronouns = [p for p in person_pronouns if p in current_lower]
            next_pronouns = [p for p in person_pronouns if p in next_lower]
            
            if current_pronouns and next_pronouns:
                if not any(p in next_pronouns for p in current_pronouns):
                    return False
        
        return True
    
    def _detect_conversation_break(self, current_text: str, next_text: str) -> bool:
        """Detecta quebras de conversação que indicam falantes diferentes"""
        current_lower = current_text.lower().strip()
        next_lower = next_text.lower().strip()
        
        # Padrões de pergunta e resposta
        if (current_lower.endswith('?') and 
            next_lower in ['yes', 'no', 'sure', 'okay', 'right', 'exactly', 'correct']):
            return True
        
        # Padrões de exclamação seguida de nova declaração
        if (current_lower.endswith('!') and 
            next_lower.split()[0] in ['i', 'you', 'he', 'she', 'it', 'we', 'they']):
            return True
        
        # Padrões de interjeições
        interjections = ['oh', 'ah', 'um', 'uh', 'well', 'okay', 'right']
        if next_lower.split()[0] in interjections:
            return True
        
        return False
    
    def _get_required_pause_for_merge(self, current_text: str, next_text: str) -> float:
        """Calcula a pausa mínima necessária para merge baseado no contexto"""
        current_lower = current_text.lower().strip()
        next_lower = next_text.lower().strip()
        
        # Pausa mínima base
        base_pause = 0.3
        
        # Ajusta baseado na pontuação
        if current_lower.endswith(','):
            return base_pause + 0.1  # Pausa menor para vírgulas
        elif current_lower.endswith((';', ':')):
            return base_pause + 0.2  # Pausa moderada para ponto e vírgula
        elif current_lower.endswith(('.', '!', '?')):
            return base_pause + 0.5  # Pausa maior para pontuação forte
        
        # Ajusta baseado no início da próxima frase
        next_first_word = next_lower.split()[0] if next_lower.split() else ""
        
        # Conectores que permitem pausa menor
        short_pause_connectors = {'and', 'but', 'so', 'then', 'also'}
        if next_first_word in short_pause_connectors:
            return base_pause - 0.1
        
        # Pronomes que requerem pausa maior
        pronoun_starters = {'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        if next_first_word in pronoun_starters:
            return base_pause + 0.2
        
        return base_pause