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
        
        # Verifica estrutura do resultado (chunks)
        if isinstance(result, list):
            print(f"✅ Transcrição gerou {len(result)} chunks de áudio")
            
            # Mostra alguns chunks como exemplo
            for i, chunk in enumerate(result[:3]):  # Mostra apenas os 3 primeiros
                if 'text' in chunk:
                    text = chunk['text'].strip()
                    if text:
                        print(f"   📝 Chunk {i+1}: {text[:100]}{'...' if len(text) > 100 else ''}")
                
                if 'timestamp' in chunk:
                    timestamp = chunk['timestamp']
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
    

async def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do Transcriber...")
    print("=" * 60)
    
    try:
        test = TestTranscriber()
        
        # Teste principal
        result = await test.test_transcriber_execution()

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
 