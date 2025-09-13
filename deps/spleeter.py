import os
import tensorflow as tf
from typing import Dict
from pathlib import Path
from .dep_base import DepBase
from spleeter.separator import Separator

# Configurações para reduzir uso de memória do TensorFlow
tf.config.experimental.set_memory_growth(tf.config.list_physical_devices('GPU')[0], True) if tf.config.list_physical_devices('GPU') else None
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.threading.set_intra_op_parallelism_threads(1)


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
        output_template = f"{output_dir}"
        
        # Executa a separação
        self.client.separate_to_file(audio_path, output_template)
        
        # Constrói os caminhos dos arquivos gerados
        # O Spleeter 2stems gera: vocals.wav e accompaniment.wav
        vocals_path = f"{output_dir}/{audio_name}/vocals.wav"
        accompaniment_path = f"{output_dir}/{audio_name}/accompaniment.wav"
        
        # Verifica se os arquivos foram criados
        if not os.path.exists(vocals_path):
            raise Exception(f"Arquivo de vocals não foi criado: {vocals_path}")
        
        if not os.path.exists(accompaniment_path):
            raise Exception(f"Arquivo de accompaniment não foi criado: {accompaniment_path}")
        
        print(f"✅ Audio Output name: {vocals_path}")

        return {
            'audio_name': audio_name,
            'separated_audios': {
                'vocals': vocals_path,
                'accompaniment': accompaniment_path,
            }
        } 