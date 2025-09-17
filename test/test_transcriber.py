"""
Teste de execução do Transcriber usando test/audios/vocals.wav
Testa a transcrição de áudio em inglês (EN)
"""
import os
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

# Importa as dependências
from deps.transcriber import Transcriber, WhisperModels


class TestTranscriber:
    """Teste específico para execução do Transcriber"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.audio_file = "/home/zan-notebook/github/dublar-worker/test/audios/vocals.wav"
    
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
        """Callback para mostrar progresso da transcrição"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"🔄 Progresso: {current}/{total} ({progress:.1f}%)")
    
    async def test_transcriber_execution(self):
        """Testa execução real do Transcriber com vocals.wav em inglês"""
        print("🎤 Testando execução do Transcriber com vocals.wav (EN)...")
        print("=" * 60)
        
        # Verifica se o arquivo de áudio existe
        if not os.path.exists(self.audio_file):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {self.audio_file}")
        
        print(f"📁 Arquivo de entrada: {self.audio_file}")
        print(f"📊 Tamanho do arquivo: {os.path.getsize(self.audio_file) / (1024*1024):.2f} MB")
        
        # Inicializa o Transcriber com modelo SMALL para inglês
        transcriber = Transcriber(engine=self.mock_worker, model=WhisperModels.SMALL.name)
        print("🔄 Carregando modelo Whisper (SMALL)...")
        transcriber.load()
        print("✅ Modelo carregado com sucesso!")
        
        # Cria diretório temporário para saída
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "gto_ep1_transcription.txt")
            print(f"📁 Arquivo de saída: {output_file}")
            
            # Executa transcrição
            print("🚀 Iniciando transcrição de áudio (EN)...")
            start_time = time.time()
            
            try:
                result = await transcriber.execute(
                    audio_path=self.audio_file,
                    output_path=output_file,
                    progress_callback=self._progress_callback
                )
                duration = time.time() - start_time
                
                print(f"✅ Transcrição concluída em {duration:.2f} segundos!")
                
                # Valida resultado
                self._validate_result(result, output_file)
                
                print("\n🎯 TESTE DO TRANSCRIBER EXECUTADO COM SUCESSO!")
                return result
                
            except Exception as e:
                print(f"❌ Erro durante transcrição: {e}")
                raise
    
    def _validate_result(self, result, output_file):
        """Valida o resultado da transcrição"""
        print("\n🔍 Validando resultado...")
        
        # Verifica se o resultado não está vazio
        assert result is not None, "Resultado da transcrição não pode ser None"
        assert len(result) > 0, "Resultado da transcrição não pode estar vazio"
        
        # Verifica estrutura do resultado (frases)
        if isinstance(result, list):
            print(f"✅ Transcrição gerou {len(result)} frases completas")
            
            # Validação específica de timestamps precisos
            self._validate_timestamps(result)
            
            # Mostra algumas frases como exemplo
            for i, sentence in enumerate(result[:3]):  # Mostra apenas as 3 primeiras
                if 'text' in sentence:
                    text = sentence['text'].strip()
                    if text:
                        print(f"   📝 Frase {i+1}: {text[:100]}{'...' if len(text) > 100 else ''}")
                
                if 'timestamp' in sentence:
                    timestamp = sentence['timestamp']
                    print(f"   ⏱️  Timestamp: {timestamp}")
        
        # Verifica se o arquivo de saída foi criado (se aplicável)
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Arquivo de saída criado: {output_file} ({file_size} bytes)")
            
            # Lê e mostra parte do conteúdo
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print(f"📄 Conteúdo (primeiros 200 chars): {content[:200]}{'...' if len(content) > 200 else ''}")
                else:
                    print("⚠️ Arquivo de saída está vazio")
        else:
            print("ℹ️ Arquivo de saída não foi criado (resultado retornado diretamente)")
        
        print("✅ Validação concluída com sucesso!")
    
    def _validate_timestamps(self, sentences):
        """Valida a precisão dos timestamps"""
        print("\n🎯 Validando precisão dos timestamps...")
        
        timestamp_precision_improved = False
        word_timestamps_available = False
        
        for i, sentence in enumerate(sentences[:5]):  # Verifica as primeiras 5 frases
            if 'timestamp' in sentence:
                timestamp = sentence['timestamp']
                if isinstance(timestamp, list) and len(timestamp) == 2:
                    start_time, end_time = timestamp
                    
                    # Verifica se os timestamps têm precisão decimal (não são inteiros)
                    if isinstance(start_time, float) and isinstance(end_time, float):
                        # Verifica se há casas decimais significativas (mais precisão que segundos inteiros)
                        start_decimal = start_time - int(start_time)
                        end_decimal = end_time - int(end_time)
                        
                        if start_decimal > 0.01 or end_decimal > 0.01:  # Pelo menos centésimos de segundo
                            timestamp_precision_improved = True
                            print(f"   ✅ Frase {i+1}: Timestamp preciso {start_time:.3f}s - {end_time:.3f}s")
                        else:
                            print(f"   ⚠️ Frase {i+1}: Timestamp ainda em segundos inteiros {start_time:.1f}s - {end_time:.1f}s")
                    
                    # Verifica se há word_timestamps disponível
                    if 'word_timestamps' in sentence and sentence['word_timestamps']:
                        word_timestamps_available = True
                        word_count = len(sentence['word_timestamps'])
                        print(f"   🎯 Frase {i+1}: {word_count} palavras com timestamps individuais")
        
        # Relatório final de precisão
        print(f"\n📊 Relatório de Precisão dos Timestamps:")
        if timestamp_precision_improved:
            print("   ✅ Timestamps com precisão melhorada (sub-segundo)")
        else:
            print("   ⚠️ Timestamps ainda em precisão de segundos inteiros")
        
        if word_timestamps_available:
            print("   ✅ Timestamps de palavras individuais disponíveis")
        else:
            print("   ⚠️ Timestamps de palavras individuais não disponíveis")
        
        # Verifica se os novos campos estão presentes
        sample_sentence = sentences[0] if sentences else {}
        new_fields = ['start_time', 'end_time', 'confidence', 'word_timestamps']
        available_fields = [field for field in new_fields if field in sample_sentence]
        
        if available_fields:
            print(f"   ✅ Novos campos disponíveis: {', '.join(available_fields)}")
        else:
            print("   ⚠️ Novos campos não encontrados")
    

async def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do Transcriber...")
    print("=" * 60)
    
    try:
        test = TestTranscriber()
        
        # Teste principal
        result = await test.test_transcriber_execution()

        # Salva o resultado como json
        import json

        output_json_path = "test/jsons/gto_ep1_transcription.json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Resultado salvo em {output_json_path}")


        print("\n" + "=" * 60)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resultado: {len(result) if isinstance(result, list) else 'N/A'} chunks gerados")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTE FALHOU!")
        print("=" * 60)
        print(f"Erro: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
 