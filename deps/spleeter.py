import os
from pathlib import Path
from typing import Dict
from .dep_base import DepBase
from spleeter.separator import Separator

class Spleeter(DepBase):

    name = 'spleeter'

    def load(self):
        self.client = Separator('spleeter:2stems')
    
    def execute(
        self, 
        audio_path: str,
        output_dir: str = "output/spleeter"
    ) -> Dict[str, str]:
        """
        Separa o áudio em vocals e accompaniment usando Spleeter
        
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

        # Define o template de saída
        output_template = f"{output_dir}/{audio_name}/{{filename}}_{{instrument}}.{{codec}}"
        
        # Executa a separação
        self.client.separate_to_file(audio_path, output_template)
        
        # Constrói os caminhos dos arquivos gerados
        # O Spleeter 2stems gera: vocals.wav e accompaniment.wav
        vocals_path = f"{output_dir}/{audio_name}/{audio_name}_vocals.wav"
        accompaniment_path = f"{output_dir}/{audio_name}/{audio_name}_accompaniment.wav"
        
        # Verifica se os arquivos foram criados
        if not os.path.exists(vocals_path):
            raise FileNotFoundError(f"Arquivo de vocals não foi criado: {vocals_path}")
        
        if not os.path.exists(accompaniment_path):
            raise FileNotFoundError(f"Arquivo de accompaniment não foi criado: {accompaniment_path}")
        
        print(f"✅ Audio Output name: {vocals_path}")

        return {
            'vocals': vocals_path,
            'accompaniment': accompaniment_path
        } 