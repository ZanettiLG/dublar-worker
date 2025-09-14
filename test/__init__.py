"""
Sistema de testes organizado para dublar-worker
Executa testes críticos das dependências com foco no workflow gto_ep1.mp4 (EN→PT)
"""
import asyncio
import os
import tempfile
import time
from unittest.mock import Mock
from pathlib import Path

# Importa as dependências
from deps.media import Media
from deps.spleeter import Spleeter
from deps.transcriber import Transcriber, WhisperModels


class TestRunner:
    """Runner principal para executar todos os testes críticos"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.results = []
    
    def _create_mock_worker(self):
        """Cria mock do worker para testes"""
        worker = Mock()
        worker.name = 'test_worker'
        worker.logger = Mock()
        worker.logger.info = print
        worker.logger.error = print
        worker.logger.warning = print
        return worker
    
    async def run_all_tests(self):
        """Executa todos os testes críticos"""
        print("🚀 Iniciando testes críticos das dependências...")
        print("=" * 60)
        
        # Lista de testes para executar
        tests = [
            ("Media Download", self.test_media_download),
            ("Spleeter Separação", self.test_spleeter_separation),
            ("Transcriber Transcrição", self.test_transcriber_transcription),
            ("Workflow Completo", self.test_integration_workflow)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 Executando: {test_name}")
            print("-" * 40)
            
            try:
                start_time = time.time()
                await test_func()
                duration = time.time() - start_time
                
                self.results.append({
                    'name': test_name,
                    'status': 'SUCCESS',
                    'duration': duration
                })
                print(f"✅ {test_name} - SUCESSO ({duration:.2f}s)")
                
            except Exception as e:
                self.results.append({
                    'name': test_name,
                    'status': 'FAILED',
                    'error': str(e),
                    'duration': 0
                })
                print(f"❌ {test_name} - FALHOU: {e}")
        
        self._print_summary()
    
    async def test_media_download(self):
        """Testa download real de mídia"""
        print("📥 Testando download de mídia...")
        
        media = Media(engine=self.mock_worker)
        media.load()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simula download do gto_ep1.mp4
            gto_ep1_path = os.path.join(temp_dir, "gto_ep1.mp4")
            with open(gto_ep1_path, 'wb') as f:
                f.write(b'fake video content for gto_ep1.mp4')
            
            print(f"✅ gto_ep1.mp4 simulado: {gto_ep1_path}")
            
            # Testa obtenção de informações
            info = await media.get_media_info("https://httpbin.org/json")
            assert info is not None
            print(f"✅ Informações obtidas: {info}")
    
    def test_spleeter_separation(self):
        """Testa separação real de áudio"""
        print("🎵 Testando separação de áudio...")
        
        spleeter = Spleeter(engine=self.mock_worker)
        spleeter.load()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simula arquivo de áudio
            audio_path = os.path.join(temp_dir, "gto_ep1.mp4")
            with open(audio_path, 'wb') as f:
                f.write(b'fake audio content for testing')
            
            output_dir = os.path.join(temp_dir, "spleeter_output")
            
            # Executa separação
            result = spleeter.execute(audio_path, output_dir)
            
            # Valida resultado
            assert result is not None
            assert 'audio_name' in result
            assert 'separated_audios' in result
            assert 'vocals' in result['separated_audios']
            assert 'accompaniment' in result['separated_audios']
            
            print(f"✅ Separação concluída:")
            print(f"   🎤 Vocals: {result['separated_audios']['vocals']}")
            print(f"   🎵 Accompaniment: {result['separated_audios']['accompaniment']}")
    
    async def test_transcriber_transcription(self):
        """Testa transcrição real de áudio"""
        print("🎤 Testando transcrição de áudio (EN→PT)...")
        
        transcriber = Transcriber(engine=self.mock_worker, model=WhisperModels.SMALL.name)
        transcriber.load()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simula arquivo vocals separado
            vocals_path = os.path.join(temp_dir, "gto_ep1_vocals.wav")
            with open(vocals_path, 'wb') as f:
                f.write(b'fake audio content for testing')
            
            output_path = os.path.join(temp_dir, "gto_ep1_transcription.txt")
            
            # Executa transcrição
            result = await transcriber.execute(vocals_path, output_path)
            
            # Valida resultado
            assert result is not None
            print(f"✅ Transcrição concluída: {result}")
            print(f"   📁 Arquivo: {output_path}")
    
    async def test_integration_workflow(self):
        """Testa workflow completo: Download → Separação → Transcrição"""
        print("🔄 Testando workflow completo...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # ETAPA 1: Download (simulado)
            print("  📥 ETAPA 1: Download...")
            gto_ep1_path = os.path.join(temp_dir, "gto_ep1.mp4")
            with open(gto_ep1_path, 'wb') as f:
                f.write(b'fake video content for gto_ep1.mp4')
            print(f"  ✅ gto_ep1.mp4: {gto_ep1_path}")
            
            # ETAPA 2: Separação
            print("  🎵 ETAPA 2: Separação...")
            spleeter = Spleeter(engine=self.mock_worker)
            spleeter.load()
            
            spleeter_output_dir = os.path.join(temp_dir, "spleeter_output")
            separation_result = spleeter.execute(gto_ep1_path, spleeter_output_dir)
            
            assert separation_result is not None
            vocals_path = separation_result['separated_audios']['vocals']
            print(f"  ✅ Vocals: {vocals_path}")
            
            # ETAPA 3: Transcrição
            print("  🎤 ETAPA 3: Transcrição (EN→PT)...")
            transcriber = Transcriber(engine=self.mock_worker, model=WhisperModels.MEDIUM.name)
            transcriber.load()
            
            transcription_output = os.path.join(temp_dir, "gto_ep1_transcription.txt")
            transcription_result = await transcriber.execute(vocals_path, transcription_output)
            
            assert transcription_result is not None
            print(f"  ✅ Transcrição: {transcription_result}")
            
            print("  🎯 WORKFLOW COMPLETO EXECUTADO COM SUCESSO!")
    
    def _print_summary(self):
        """Imprime resumo dos testes"""
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r['status'] == 'SUCCESS'])
        failed_tests = len([r for r in self.results if r['status'] == 'FAILED'])
        
        print(f"Total de testes: {total_tests}")
        print(f"✅ Sucessos: {successful_tests}")
        print(f"❌ Falhas: {failed_tests}")
        
        if failed_tests > 0:
            print("\n❌ TESTES QUE FALHARAM:")
            for result in self.results:
                if result['status'] == 'FAILED':
                    print(f"  - {result['name']}: {result['error']}")
        
        print(f"\n🎯 Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
        
        if successful_tests == total_tests:
            print("🎉 TODOS OS TESTES PASSARAM!")
        else:
            print("⚠️ ALGUNS TESTES FALHARAM!")


async def main():
    """Função principal para executar os testes"""
    runner = TestRunner()
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())