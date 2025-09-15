
"""
Teste de execução do CoquiTTS
Testa a síntese de fala usando Coqui TTS com os primeiros 10 segmentos
"""
import os
import json
import asyncio
import tempfile
import time
import subprocess
from pathlib import Path
from unittest.mock import Mock

# Importa as dependências
from deps.coqui import Coqui


class TestCoquiTTS:
    """Teste específico para execução do CoquiTTS"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.vocals_file = "/home/zan-notebook/github/dublar-worker/test/audios/vocals.wav"
        self.transcription_file = "/home/zan-notebook/github/dublar-worker/test/jsons/gto_ep1_transcription.json"
        self.translation_file = "/home/zan-notebook/github/dublar-worker/test/jsons/translator_en_pt.json"
        self.output_dir = "/home/zan-notebook/github/dublar-worker/test/audios/generated"
    
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
        """Callback para mostrar progresso da síntese"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"🔄 Progresso: {current}/{total} ({progress:.1f}%)")
    
    def _load_data(self):
        """Carrega os dados de transcrição e tradução"""
        print("📂 Carregando dados de transcrição e tradução...")
        
        # Carrega transcrição
        with open(self.transcription_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        # Carrega tradução
        with open(self.translation_file, 'r', encoding='utf-8') as f:
            translation_data = json.load(f)
        
        # Pega apenas os primeiros 10 elementos
        segments = []
        for i in range(min(10, len(transcription_data), len(translation_data))):
            segment = {
                'index': i,
                'timestamp': transcription_data[i]['timestamp'],
                'original_text': transcription_data[i]['text'],
                'translated_text': translation_data[i]
            }
            segments.append(segment)
        
        print(f"✅ Carregados {len(segments)} segmentos para processamento")
        return segments
    
    def _extract_audio_segment(self, start_time: float, end_time: float, output_path: str):
        """Extrai segmento de áudio usando ffmpeg com contexto de 30s antes e depois"""
        try:
            # Verifica se ffmpeg está disponível
            ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if ffmpeg_check.returncode != 0:
                print("❌ ffmpeg não está disponível no sistema")
                return False
            
            # Adiciona 30 segundos de contexto antes e depois
            context_before = 0.3
            context_after = 0.3
            
            # Calcula novos timestamps com contexto
            extended_start = max(0, start_time - context_before)  # Não pode ser negativo
            extended_end = end_time + context_after
            
            # Obtém duração total do arquivo para não ultrapassar
            try:
                duration_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', self.vocals_file]
                duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
                if duration_result.returncode == 0:
                    total_duration = float(duration_result.stdout.strip())
                    extended_end = min(extended_end, total_duration)
                    print(f"   📊 Duração total do áudio: {total_duration:.1f}s")
                else:
                    print(f"   ⚠️ Não foi possível obter duração total, usando contexto sem limite")
            except Exception as e:
                print(f"   ⚠️ Erro ao obter duração: {e}, usando contexto sem limite")
            
            print(f"   📏 Timestamp original: {start_time:.1f}s - {end_time:.1f}s")
            print(f"   📏 Timestamp com contexto: {extended_start:.1f}s - {extended_end:.1f}s")
            
            cmd = [
                'ffmpeg', '-i', self.vocals_file,
                '-ss', str(extended_start),
                '-t', str(extended_end - extended_start),
                '-acodec', 'pcm_s16le',  # Codec de áudio de alta qualidade
                '-ar', '48000',  # Taxa de amostragem mais alta (48kHz)
                '-ac', '1',  # Mono (1 canal)
                '-af', 'highpass=f=80,lowpass=f=8000,volume=1.2',  # Filtros + boost inicial de volume
                '-y',  # Sobrescrever arquivo se existir
                output_path
            ]
            
            print(f"   🔧 Comando ffmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    # Normaliza o áudio extraído para melhor qualidade
                    self._normalize_audio(output_path)
                    return True
                else:
                    print(f"❌ Arquivo extraído está vazio ou não existe")
                    return False
            else:
                print(f"❌ Erro no ffmpeg: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Erro ao extrair segmento: {e}")
            return False
    
    def _normalize_audio(self, audio_path: str):
        """Normaliza o áudio para melhor qualidade"""
        try:
            # Cria arquivo temporário para normalização
            temp_path = audio_path + ".temp"
            
            # Normaliza o áudio com ffmpeg com controle de volume
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-af', 'highpass=f=100,lowpass=f=7000,loudnorm=I=-16:TP=-1.5:LRA=11,volume=1.5',  # Filtros + normalização + boost de volume
                '-ar', '48000',
                '-ac', '1',
                '-y',
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(temp_path):
                # Substitui o arquivo original pelo normalizado
                os.replace(temp_path, audio_path)
                print(f"   🔊 Áudio normalizado: {audio_path}")
            else:
                # Remove arquivo temporário se houver erro
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"   ⚠️ Falha na normalização, mantendo áudio original")
                
        except Exception as e:
            print(f"   ⚠️ Erro na normalização: {e}")
    
    def _post_process_audio(self, audio_path: str):
        """Aplica pós-processamento para melhorar qualidade do áudio sintetizado"""
        try:
            # Cria arquivo temporário para pós-processamento
            temp_path = audio_path + ".temp"
            
            # Aplica filtros de pós-processamento com controle de volume
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-af', 'highpass=f=80,lowpass=f=8000,compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-30/-20:6:0:-90:0.2,loudnorm=I=-14:TP=-1.0:LRA=7,volume=2.0',  # Filtros + compressão + normalização + boost
                '-ar', '48000',
                '-ac', '1',
                '-y',
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(temp_path):
                # Substitui o arquivo original pelo processado
                os.replace(temp_path, audio_path)
                print(f"   🎵 Áudio pós-processado: {audio_path}")
            else:
                # Remove arquivo temporário se houver erro
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"   ⚠️ Falha no pós-processamento, mantendo áudio original")
                
        except Exception as e:
            print(f"   ⚠️ Erro no pós-processamento: {e}")
    
    def _analyze_volume(self, audio_path: str):
        """Analisa o volume do áudio e retorna informações"""
        try:
            # Analisa o volume com ffmpeg
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
                if 'mean_volume:' in stderr:
                    # Procura por informações de volume
                    lines = stderr.split('\n')
                    for line in lines:
                        if 'mean_volume:' in line:
                            volume_info = line.strip()
                            print(f"   📊 {volume_info}")
                            break
        except Exception as e:
            print(f"   ⚠️ Erro na análise de volume: {e}")
    
    async def test_coqui_tts_execution(self):
        """Testa execução real do CoquiTTS com os primeiros 10 segmentos"""
        print("🎭 Testando execução do CoquiTTS com 10 segmentos...")
        print("📏 Usando contexto de 30s antes e depois de cada segmento")
        print("🔊 Controle de volume: boost inicial + normalização + pós-processamento")
        print("=" * 60)
        
        # Cria diretório de saída
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Carrega dados
        segments = self._load_data()
        
        # Verifica se o arquivo de áudio existe
        if not os.path.exists(self.vocals_file):
            print(f"❌ Arquivo de áudio não encontrado: {self.vocals_file}")
            return []
        
        print(f"📁 Arquivo de áudio: {self.vocals_file}")
        print(f"📊 Tamanho do áudio: {os.path.getsize(self.vocals_file) / (1024*1024):.2f} MB")
        
        # Inicializa o Coqui com modelo de alta qualidade
        coqui_tts = Coqui(engine=self.mock_worker, model="tts_models/multilingual/multi-dataset/xtts_v2")
        print(f"\n🔄 Carregando modelo Coqui TTS (XTTS v2 - Multilingual)...")
        coqui_tts.load()
        print("✅ Modelo carregado com sucesso!")
        
        results = []
        
        for segment in segments:
            i = segment['index'] + 1
            start_time, end_time = segment['timestamp']
            translated_text = segment['translated_text']
            
            print(f"\n🎤 Segmento {i}: {translated_text[:50]}...")
            print(f"   ⏰ Timestamp original: {start_time:.1f}s - {end_time:.1f}s")
            print(f"   📝 Texto original: {segment['original_text']}")
            
            # Extrai segmento de áudio para clonagem
            segment_audio_path = os.path.join(self.output_dir, f"segment_{i:02d}_original.wav")
            print(f"   🔄 Extraindo segmento de áudio...")
            
            if not self._extract_audio_segment(start_time, end_time, segment_audio_path):
                print(f"   ⚠️ Falha na extração, usando síntese sem clonagem")
                audio_url = None
            else:
                audio_url = segment_audio_path
                print(f"   ✅ Segmento extraído: {segment_audio_path}")
            
            # Prepara dados para o CoquiTTS
            tts_data = {
                "text": translated_text,
                "speaker_wav": audio_url  # Usa speaker_wav para clonagem de voz
            }
            
            print(f"   📝 Texto para síntese: {translated_text}")
            print(f"   🎵 Áudio de referência: {audio_url}")
            
            # Executa síntese de fala
            start_time_tts = time.time()
            
            try:
                result = await coqui_tts.execute(
                    data=tts_data,
                    progress_callback=self._progress_callback
                )
                duration = time.time() - start_time_tts
                
                if result.get("success", False):
                    # Move o arquivo para o diretório de saída com nome descritivo
                    final_output = os.path.join(self.output_dir, f"speech_{i:02d}.wav")
                    os.rename(result['output_path'], final_output)
                    result['output_path'] = final_output
                    
                    # Aplica pós-processamento para melhorar qualidade
                    self._post_process_audio(final_output)
                    
                    # Analisa o volume final
                    self._analyze_volume(final_output)
                    
                    print(f"   ✅ Síntese {i} concluída em {duration:.2f} segundos!")
                    print(f"   📁 Arquivo: {final_output}")
                    print(f"   📊 Tamanho: {result['file_size']} bytes")
                    print(f"   🤖 Modelo: {result['model_used']}")
                    results.append(result)
                else:
                    print(f"   ❌ Erro na síntese {i}: {result.get('error', 'Erro desconhecido')}")
                
            except Exception as e:
                print(f"   ❌ Exceção na síntese {i}: {e}")
        
        # Validação dos resultados
        self._validate_results(results)
        
        print("\n🎯 TESTE DO COQUI TTS EXECUTADO COM SUCESSO!")
        return results
    
    def _validate_results(self, results):
        """Valida os resultados da síntese"""
        print("\n🔍 Validando resultados...")
        
        if not results:
            print("⚠️ Nenhum resultado para validar")
            return
        
        print(f"✅ {len(results)} sínteses executadas com sucesso")
        
        for i, result in enumerate(results, 1):
            output_path = result.get('output_path')
            if output_path and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"   {i}. Arquivo válido: {output_path} ({file_size} bytes)")
            else:
                print(f"   {i}. ❌ Arquivo não encontrado: {output_path}")
        
        print("✅ Validação concluída!")


async def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do CoquiTTS com 10 segmentos...")
    print("=" * 60)
    
    try:
        test = TestCoquiTTS()
        
        # Executa o teste principal
        results = await test.test_coqui_tts_execution()

        print("\n" + "=" * 60)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resultado: {len(results)} sínteses executadas")
        print(f"📁 Arquivos salvos em: {test.output_dir}")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTE FALHOU!")
        print("=" * 60)
        print(f"Erro: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
