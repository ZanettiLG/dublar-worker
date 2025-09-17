import logging
import os
import subprocess
import tempfile
from deps.dep_base import DepBase
from typing import Optional, Dict, Any, Callable

# Configuração de logging
logger = logging.getLogger(__name__)

class AudioNormalizer(DepBase):
    """Normalizador de áudio - Aplica normalização e filtros para melhor qualidade"""
    name = 'audio_normalizer'

    def __init__(self, engine: Any):
        """Inicializa o AudioNormalizer"""
        super().__init__(engine=engine)

    def load(self):
        """Carrega o normalizador (não requer modelo)"""
        try:
            # Verifica se ffmpeg está disponível
            ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if ffmpeg_check.returncode != 0:
                logger.error("ffmpeg não está disponível no sistema")
                raise Exception("ffmpeg não está disponível")
            
            logger.info("AudioNormalizer carregado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao carregar AudioNormalizer: {e}")
            raise

    async def execute(
        self, 
        audio_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executa normalização de áudio"""
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")
            
            # Se não especificado, cria arquivo temporário
            if output_path is None:
                temp_dir = os.path.dirname(audio_path)
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                output_path = os.path.join(temp_dir, f"{base_name}_normalized.wav")
            
            logger.info(f"Normalizando áudio: {audio_path} → {output_path}")
            print(f"🔊 Normalizando áudio: {os.path.basename(audio_path)}")
            
            # Aplica normalização com ffmpeg
            success = self._normalize_audio(audio_path, output_path)
            
            if success:
                file_size = os.path.getsize(output_path)
                logger.info(f"Normalização concluída: {file_size} bytes")
                print(f"✅ Normalização concluída: {file_size / (1024*1024):.2f} MB")
                
                return {
                    "success": True,
                    "input_path": audio_path,
                    "output_path": output_path,
                    "file_size": file_size,
                    "normalization_applied": True
                }
            else:
                raise Exception("Falha na normalização do áudio")
                
        except Exception as e:
            logger.error(f"Erro durante normalização: {e}")
            return {
                "success": False,
                "error": str(e),
                "input_path": audio_path,
                "output_path": output_path
            }
    
    def _normalize_audio(self, input_path: str, output_path: str) -> bool:
        """Aplica normalização de áudio usando ffmpeg"""
        try:
            # Cria arquivo temporário para normalização
            temp_path = output_path + ".temp"
            
            # Comando ffmpeg com filtros de normalização otimizados
            cmd = [
                'ffmpeg', '-i', input_path,
                '-af', 'highpass=f=80,lowpass=f=8000,compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-30/-20:6:0:-90:0.2,loudnorm=I=-16:TP=-1.5:LRA=11,volume=1.2',
                '-ar', '48000',
                '-ac', '1',
                '-c:a', 'pcm_s16le',
                '-y',
                temp_path
            ]
            
            print(f"   🔧 Executando normalização com ffmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                # Substitui o arquivo original pelo normalizado
                os.replace(temp_path, output_path)
                print(f"   ✅ Normalização aplicada com sucesso")
                return True
            else:
                # Remove arquivo temporário se houver erro
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"   ❌ Erro na normalização: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exceção na normalização: {e}")
            return False
    
    def _analyze_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """Analisa qualidade do áudio e retorna métricas"""
        try:
            # Analisa o áudio com ffmpeg
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-af', 'volumedetect',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Extrai informações de volume do stderr
                stderr = result.stderr
                volume_info = {}
                
                if 'mean_volume:' in stderr:
                    lines = stderr.split('\n')
                    for line in lines:
                        if 'mean_volume:' in line:
                            volume_info['mean_volume'] = line.strip()
                        elif 'max_volume:' in line:
                            volume_info['max_volume'] = line.strip()
                        elif 'n_samples:' in line:
                            volume_info['n_samples'] = line.strip()
                
                return volume_info
            else:
                return {"error": "Falha na análise do áudio"}
                
        except Exception as e:
            return {"error": str(e)}
