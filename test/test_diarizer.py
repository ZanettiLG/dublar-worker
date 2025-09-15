"""
Teste de execução do Diarizer usando vocals.wav e gto_ep1_transcription.json
Testa a identificação de diferentes falantes no áudio
"""
import os
import json
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

# Importa as dependências
from deps.diarizer import Diarizer, DiarizerModels


class TestDiarizer:
    """Teste específico para execução do Diarizer"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.audio_file = "/home/zan-notebook/github/dublar-worker/test/audios/vocals.wav"
        self.transcription_file = "/home/zan-notebook/github/dublar-worker/test/jsons/gto_ep1_transcription.json"
    
    def _create_mock_worker(self):
        """Cria mock do worker para testes"""
        worker = Mock()
        worker.name = 'test_worker'
        worker.logger = Mock()
        worker.logger.info = print
        worker.logger.error = print
        worker.logger.warning = print
        return worker
    
    def _progress_callback(self, current: int, total: int):
        """Callback para mostrar progresso da diarização"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"🔄 Progresso: {current}/{total} ({progress:.1f}%)")
    
    def _load_transcription_data(self):
        """Carrega os dados de transcrição do arquivo JSON"""
        print("📁 Carregando arquivo de transcrição...")
        
        if not os.path.exists(self.transcription_file):
            raise FileNotFoundError(f"Arquivo de transcrição não encontrado: {self.transcription_file}")
        
        with open(self.transcription_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        print(f"✅ Arquivo carregado: {len(transcription_data)} chunks de transcrição")
        print(f"📊 Tamanho do arquivo: {os.path.getsize(self.transcription_file) / 1024:.2f} KB")
        
        return transcription_data
    
    def _prepare_speechs_data(self, transcription_data):
        """Prepara os dados de speeches para o diarizer"""
        print("🔄 Preparando dados de speeches...")
        
        speechs = []
        for i, chunk in enumerate(transcription_data):
            if 'text' in chunk and chunk['text'].strip():
                speech_data = {
                    "text": chunk['text'].strip(),
                    "start": chunk.get('timestamp', [0.0, 0.0])[0],
                    "end": chunk.get('timestamp', [0.0, 0.0])[1],
                    "confidence": 0.9,  # Valor padrão de confiança
                    "index": i
                }
                speechs.append(speech_data)
        
        print(f"✅ {len(speechs)} speeches preparados para diarização")
        
        # Mostra alguns exemplos
        print(f"\n📄 Exemplos de speeches:")
        for i, speech in enumerate(speechs[:3]):
            print(f"   {i+1}. [{speech['start']:.1f}s-{speech['end']:.1f}s] {speech['text'][:50]}...")
        if len(speechs) > 3:
            print(f"   ... e mais {len(speechs) - 3} speeches")
        
        return speechs
    
    async def test_diarizer_execution(self):
        """Testa execução real do Diarizer com vocals.wav e speeches"""
        print("🎭 Testando execução do Diarizer...")
        print("=" * 60)
        
        # Verifica se o arquivo de áudio existe
        if not os.path.exists(self.audio_file):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {self.audio_file}")
        
        print(f"📁 Arquivo de áudio: {self.audio_file}")
        print(f"📊 Tamanho do áudio: {os.path.getsize(self.audio_file) / (1024*1024):.2f} MB")
        
        # Carrega dados de transcrição
        transcription_data = self._load_transcription_data()
        speechs = self._prepare_speechs_data(transcription_data)
        
        if not speechs:
            raise ValueError("Nenhum speech encontrado na transcrição")
        
        # Inicializa o Diarizer
        diarizer = Diarizer(engine=self.mock_worker, model=DiarizerModels.MULTILINGUAL_MINI.name)
        print(f"\n🔄 Carregando modelo de diarização (paraphrase-multilingual-MiniLM-L12-v2)...")
        diarizer.load()
        print("✅ Modelo carregado com sucesso!")
        
        # Cria diretório temporário para saída
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "gto_ep1_diarization.json")
            print(f"📁 Arquivo de saída: {output_file}")
            
            # Prepara dados para o diarizer
            diarizer_data = {
                "audio_url": self.audio_file,
                "speechs": speechs
            }
            
            # Executa diarização
            print(f"\n🚀 Iniciando diarização de {len(speechs)} speeches...")
            start_time = time.time()
            
            try:
                result = await diarizer.execute(
                    data=diarizer_data,
                    progress_callback=self._progress_callback
                )
                duration = time.time() - start_time
                
                print(f"\n✅ Diarização concluída em {duration:.2f} segundos!")
                
                # Salva resultado
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # Valida resultado
                self._validate_result(result, output_file)
                
                print("\n🎯 TESTE DO DIARIZER EXECUTADO COM SUCESSO!")
                return result
                
            except Exception as e:
                print(f"❌ Erro durante diarização: {e}")
                raise
    
    def _validate_result(self, result, output_file):
        """Valida o resultado da diarização"""
        print("\n🔍 Validando resultado...")
        
        # Verifica se o resultado não está vazio
        assert result is not None, "Resultado da diarização não pode ser None"
        assert 'speakers' in result, "Resultado deve conter 'speakers'"
        assert 'segments' in result, "Resultado deve conter 'segments'"
        
        speakers = result['speakers']
        segments = result['segments']
        
        print(f"✅ Diarização identificou {len(speakers)} falantes únicos")
        print(f"✅ Processou {len(segments)} segmentos de áudio")
        
        # Conta estatísticas dos falantes
        speaker_counts = {}
        for segment in segments:
            if segment not in speaker_counts:
                speaker_counts[segment] = 0
            speaker_counts[segment] += 1
        
        # Mostra estatísticas dos falantes
        print(f"\n👥 Estatísticas dos falantes:")
        for speaker, count in speaker_counts.items():
            print(f"   {speaker}: {count} segmentos")
        
        # Mostra alguns exemplos de segmentos
        print(f"\n📝 Exemplos de segmentos diarizados:")
        for i, segment in enumerate(segments[:5]):
            print(f"   {i+1}. Speaker: {segment}")
        
        # Verifica se o arquivo de saída foi criado
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024
            print(f"\n✅ Arquivo de saída criado: {output_file} ({file_size:.2f} KB)")
        else:
            print("\n⚠️ Arquivo de saída não foi criado")
        
        # Validações específicas
        assert len(segments) > 0, "Deve haver pelo menos um segmento"
        assert len(speakers) > 0, "Deve haver pelo menos um falante identificado"
        
        # Verifica estrutura dos segmentos (agora são strings)
        for segment in segments[:3]:
            assert isinstance(segment, str), "Segmento deve ser uma string com o nome do speaker"
        
        print("✅ Validação concluída com sucesso!")
    
    async def test_different_models(self):
        """Testa diferentes modelos de diarização"""
        print("\n🧪 Testando diferentes modelos de diarização...")
        print("=" * 60)
        
        # Carrega dados
        transcription_data = self._load_transcription_data()
        speechs = self._prepare_speechs_data(transcription_data)
        
        # Pega apenas os primeiros 20 speeches para teste rápido
        test_speechs = speechs[:20]
        print(f"📝 Testando com {len(test_speechs)} speeches")
        
        models_to_test = [
            (DiarizerModels.MULTILINGUAL_MINI, "Multilingual Mini (mais rápido)"),
            (DiarizerModels.ALL_MINI, "All Mini (inglês)")
        ]
        
        for model_enum, description in models_to_test:
            print(f"\n🔄 Testando {description}...")
            
            try:
                diarizer = Diarizer(engine=self.mock_worker, model=model_enum.name)
                diarizer.load()
                
                diarizer_data = {
                    "audio_url": self.audio_file,
                    "speechs": test_speechs
                }
                
                start_time = time.time()
                result = await diarizer.execute(diarizer_data)
                duration = time.time() - start_time
                
                speakers_count = len(result.get('speakers', []))
                segments_count = len(result.get('segments', []))
                print(f"✅ {description} - {speakers_count} falantes, {segments_count} segmentos em {duration:.2f}s")
                
            except Exception as e:
                print(f"❌ {description} - Erro: {e}")


async def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do Diarizer...")
    print("=" * 60)
    
    try:
        test = TestDiarizer()
        
        # Teste principal
        result = await test.test_diarizer_execution()
        
        # Salva o resultado do diarizer em um arquivo JSON para análise posterior
        diarizer_result_path = os.path.join(
            os.path.dirname(__file__),
            "jsons",
            "diarizer_result.json"
        )
        with open(diarizer_result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 Resultado salvo em {diarizer_result_path}")

        print("\n" + "=" * 60)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resultado: {len(result.get('speakers', []))} falantes identificados")
        print(f"📊 Segmentos: {len(result.get('segments', []))} segmentos processados")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTE FALHOU!")
        print("=" * 60)
        print(f"Erro: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
