"""
Teste de execução do Spleeter usando assets/gto_ep1.mp4
Testa a separação de áudio em vocals e accompaniment
"""
import os
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

# Importa as dependências
from deps.spleeter import Spleeter


class TestSpleeter:
    """Teste específico para execução do Spleeter"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.audio_file = "/home/zan-notebook/github/dublar-worker/assets/gto_ep1.mp4"
    
    def _create_mock_worker(self):
        """Cria mock do worker para testes"""
        worker = Mock()
        worker.name = 'test_worker'
        worker.logger = Mock()
        worker.logger.info = print
        worker.logger.error = print
        worker.logger.warning = print
        return worker
    
    def test_spleeter_execution(self):
        """Testa execução real do Spleeter com gto_ep1.mp4"""
        print("🎵 Testando execução do Spleeter com gto_ep1.mp4...")
        print("=" * 60)
        
        # Verifica se o arquivo de áudio existe
        if not os.path.exists(self.audio_file):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {self.audio_file}")
        
        print(f"📁 Arquivo de entrada: {self.audio_file}")
        print(f"📊 Tamanho do arquivo: {os.path.getsize(self.audio_file) / (1024*1024):.2f} MB")
        
        # Inicializa o Spleeter
        spleeter = Spleeter(engine=self.mock_worker)
        print("🔄 Carregando modelo Spleeter...")
        spleeter.load()
        print("✅ Modelo carregado com sucesso!")
        
        # Cria diretório temporário para saída
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "spleeter_output")
            print(f"📁 Diretório de saída: {output_dir}")
            
            # Executa separação
            print("🚀 Iniciando separação de áudio...")
            start_time = time.time()
            
            try:
                result = spleeter.execute(self.audio_file, output_dir)
                duration = time.time() - start_time
                
                print(f"✅ Separação concluída em {duration:.2f} segundos!")
                
                # Valida resultado
                self._validate_result(result, output_dir)
                
                print("\n🎯 TESTE DO SPLEETER EXECUTADO COM SUCESSO!")
                return result
                
            except Exception as e:
                print(f"❌ Erro durante separação: {e}")
                raise
    
    def _validate_result(self, result, output_dir):
        """Valida o resultado da separação"""
        print("\n🔍 Validando resultado...")
        
        # Verifica estrutura do resultado
        assert 'audio_name' in result, "Resultado deve conter 'audio_name'"
        assert 'separated_audios' in result, "Resultado deve conter 'separated_audios'"
        
        separated_audios = result['separated_audios']
        assert 'vocals' in separated_audios, "Deve conter 'vocals'"
        assert 'accompaniment' in separated_audios, "Deve conter 'accompaniment'"
        
        vocals_path = separated_audios['vocals']
        accompaniment_path = separated_audios['accompaniment']
        
        # Verifica se os arquivos foram criados
        assert os.path.exists(vocals_path), f"Arquivo vocals não encontrado: {vocals_path}"
        assert os.path.exists(accompaniment_path), f"Arquivo accompaniment não encontrado: {accompaniment_path}"
        
        # Verifica tamanhos dos arquivos
        vocals_size = os.path.getsize(vocals_path) / (1024*1024)
        accompaniment_size = os.path.getsize(accompaniment_path) / (1024*1024)
        
        print(f"✅ Arquivos gerados:")
        print(f"   🎤 Vocals: {vocals_path} ({vocals_size:.2f} MB)")
        print(f"   🎵 Accompaniment: {accompaniment_path} ({accompaniment_size:.2f} MB)")
        
        # Verifica se os arquivos não estão vazios
        assert vocals_size > 0, "Arquivo vocals está vazio"
        assert accompaniment_size > 0, "Arquivo accompaniment está vazio"
        
        print("✅ Validação concluída com sucesso!")


def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do Spleeter...")
    print("=" * 60)
    
    try:
        test = TestSpleeter()
        result = test.test_spleeter_execution()
        
        print("\n" + "=" * 60)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resultado: {result}")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTE FALHOU!")
        print("=" * 60)
        print(f"Erro: {e}")
        raise


if __name__ == "__main__":
    main()
