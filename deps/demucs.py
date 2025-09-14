import os
import torch
from typing import Dict
from pathlib import Path
from .dep_base import DepBase
from demucs.separate import main as demucs_main
import tempfile
import shutil

SEGMENT = '5'
OUTPUT_FORMAT = 'mp3'
OUTPUT_PATH = 'output/demucs'

class Demucs(DepBase):

    name = 'demucs'

    def load(self):
        """Inicializa o Demucs"""
        # Configura o device (CPU ou GPU se disponível)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🔧 Usando device: {self.device}")
        
        # Define o modelo (htdemucs é o padrão e mais eficiente)
        self.model_name = 'htdemucs'
        print(f"🔧 Modelo Demucs: {self.model_name}")

    
    def execute(
        self, 
        audio_path: str,
        output_dir: str = OUTPUT_PATH
    ) -> Dict[str, str]:
        """
        Separa o áudio em vocals e accompaniment usando Demucs
        
        Args:
            audio_path: Caminho para o arquivo de áudio de entrada
            output_dir: Diretório onde os arquivos separados serão salvos
            
        Returns:
            Dict com os caminhos dos arquivos separados: {'vocals': path, 'accompaniment': path}
        """
        # Cria o diretório de saída se não existir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Extrai o nome do arquivo sem extensão
        audio_name = Path(audio_path).stem
        
        print(f"✅ Audio Input name: {audio_name}")
        print(f"🔄 Processando com Demucs...")

        try:
            # Cria um diretório temporário para o Demucs
            #with tempfile.TemporaryDirectory() as temp_dir:
            # Configura os argumentos para o Demucs
            args = [
                '--mp3',
                '--segment', SEGMENT,
                '-n', self.model_name,
                '--two-stems', 'vocals', # Separa apenas vocals e accompaniment
                '--device', self.device,
                audio_path
            ]
            
            # Executa o Demucs
            demucs_main(args)

            model_output_dir = Path("separated") / self.model_name / audio_name

            # Define os caminhos de saída
            vocals_path = f"{output_dir}/vocals.mp3"
            accompaniment_path = f"{output_dir}/accompaniment.mp3"
            
            vocals_source = model_output_dir / "vocals.mp3"
            accompaniment_source = model_output_dir / "no_vocals.mp3"
            
            # DEBUG: Verifica se os arquivos existem antes de copiar
            print(f"🔍 Vocals source existe: {vocals_source.exists()}")
            print(f"🔍 Accompaniment source existe: {accompaniment_source.exists()}")
            
            if vocals_source.exists():
                shutil.copy2(vocals_source, vocals_path)
            else:
                raise Exception(f"Arquivo de vocals não encontrado: {vocals_source}")
            
            if accompaniment_source.exists():
                shutil.copy2(accompaniment_source, accompaniment_path)
            else:
                raise Exception(f"Arquivo de accompaniment não encontrado: {accompaniment_source}")
            
            # Verifica se os arquivos foram criados
            if not os.path.exists(vocals_path):
                raise Exception(f"Arquivo de vocals não foi criado: {vocals_path}")
            
            if not os.path.exists(accompaniment_path):
                raise Exception(f"Arquivo de accompaniment não foi criado: {accompaniment_path}")
            
            print(f"✅ Audio Output vocals: {vocals_path}")
            print(f"✅ Audio Output accompaniment: {accompaniment_path}")

            return {
                'audio_name': audio_name,
                'separated_audios': {
                    'vocals': vocals_path,
                    'accompaniment': accompaniment_path,
                }
            }
            
        except Exception as e:
            print(f"❌ Erro durante separação com Demucs: {e}")
            raise e
