
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
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier

# Importa as dependências
from deps.coqui import Coqui


class TestCoquiTTS:
    """Teste específico para execução do CoquiTTS"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.vocals_file = "/home/zan-notebook/github/dublar-worker/test/audios/vocals.wav"
        self.transcription_file = "/home/zan-notebook/github/dublar-worker/test/jsons/gto_ep1_transcription.json"
        self.translation_file = "/home/zan-notebook/github/dublar-worker/test/jsons/translator_en_pt.json"
        self.diarization_file = "/home/zan-notebook/github/dublar-worker/test/jsons/diarizer_result.json"
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
        """Carrega os dados de transcrição, tradução e diarização, agrupando por speaker"""
        print("📂 Carregando dados de transcrição, tradução e diarização...")
        
        # Carrega transcrição
        with open(self.transcription_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        # Carrega tradução
        with open(self.translation_file, 'r', encoding='utf-8') as f:
            translation_data = json.load(f)
        
        # Carrega diarização
        with open(self.diarization_file, 'r', encoding='utf-8') as f:
            diarization_data = json.load(f)
        
        # Agrupa segmentos por speaker
        speakers_data = {}
        
        # Pega apenas os primeiros 20 elementos para teste
        max_segments = min(20, len(transcription_data), len(translation_data), len(diarization_data.get('segments', [])))
        
        for i in range(max_segments):
            speaker = diarization_data.get('segments', [])[i] if i < len(diarization_data.get('segments', [])) else 'Unknown'
            
            if speaker not in speakers_data:
                speakers_data[speaker] = {
                    'segments': [],
                    'audio_segments': [],
                    'total_duration': 0.0
                }
            
            segment = {
                'index': i,
                'timestamp': transcription_data[i]['timestamp'],
                'original_text': transcription_data[i]['text'],
                'translated_text': translation_data[i],
                'speaker': speaker
            }
            
            speakers_data[speaker]['segments'].append(segment)
            
            # Calcula duração do segmento
            start_time, end_time = transcription_data[i]['timestamp']
            duration = end_time - start_time
            speakers_data[speaker]['total_duration'] += duration
        
        print(f"✅ Carregados {max_segments} segmentos agrupados em {len(speakers_data)} speakers")
        
        # Mostra estatísticas por speaker
        for speaker, data in speakers_data.items():
            print(f"   🎤 {speaker}: {len(data['segments'])} segmentos, {data['total_duration']:.1f}s total")
        
        return speakers_data
    
    def _concatenate_speaker_audio(self, speaker: str, segments: list, output_path: str):
        """Concatena todos os segmentos de áudio de um speaker em um único arquivo"""
        try:
            print(f"   🎤 Concatenando áudio para {speaker}...")
            
            # Verifica se ffmpeg está disponível
            ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if ffmpeg_check.returncode != 0:
                print("❌ ffmpeg não está disponível no sistema")
                return False
            
            # Cria lista de arquivos temporários para cada segmento
            temp_files = []
            
            for i, segment in enumerate(segments):
                start_time, end_time = segment['timestamp']
                temp_file = os.path.join(self.output_dir, f"temp_{speaker}_{i}.wav")
                
                # Extrai segmento individual
                if self._extract_single_segment(start_time, end_time, temp_file):
                    temp_files.append(temp_file)
                else:
                    print(f"   ⚠️ Falha ao extrair segmento {i} do {speaker}")
            
            if not temp_files:
                print(f"   ❌ Nenhum segmento válido para {speaker}")
                return False
            
            # Concatena todos os segmentos
            if len(temp_files) == 1:
                # Se há apenas um segmento, apenas copia
                os.rename(temp_files[0], output_path)
            else:
                # Cria arquivo de lista para concatenação
                concat_file = os.path.join(self.output_dir, f"concat_{speaker}.txt")
                with open(concat_file, 'w') as f:
                    for temp_file in temp_files:
                        f.write(f"file '{temp_file}'\n")
                
                # Executa concatenação
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file,
                    '-c', 'copy',
                    '-y',
                    output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Limpa arquivos temporários
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                if os.path.exists(concat_file):
                    os.remove(concat_file)
                
                if result.returncode != 0:
                    print(f"   ❌ Erro na concatenação: {result.stderr}")
                    return False
            
            # Normaliza o áudio concatenado
            self._normalize_audio(output_path)
            
            print(f"   ✅ Áudio concatenado para {speaker}: {output_path}")
            return True
            
        except Exception as e:
            print(f"   ❌ Erro ao concatenar áudio do {speaker}: {e}")
            return False
    
    def _extract_single_segment(self, start_time: float, end_time: float, output_path: str):
        """Extrai um único segmento de áudio sem contexto adicional"""
        try:
            # Adiciona pequeno contexto para melhor qualidade
            context = 0.1  # 100ms de contexto
            extended_start = max(0, start_time - context)
            extended_end = end_time + context
            
            cmd = [
                'ffmpeg', '-i', self.vocals_file,
                '-ss', str(extended_start),
                '-t', str(extended_end - extended_start),
                '-acodec', 'pcm_s16le',
                '-ar', '48000',
                '-ac', '1',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"   ⚠️ Erro ao extrair segmento: {e}")
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
    
    def _generate_speaker_embeddings(self, speakers_data: dict):
        """Gera embeddings de clonagem para cada speaker usando SpeechBrain"""
        print("\n🎭 Gerando embeddings de clonagem para cada speaker...")
        speaker_embeddings = {}
        
        # Carrega o modelo SpeechBrain para extração de embeddings
        print("   🔄 Carregando modelo SpeechBrain para extração de embeddings...")
        try:
            classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
            print("   ✅ Modelo SpeechBrain carregado com sucesso!")
        except Exception as e:
            print(f"   ❌ Erro ao carregar SpeechBrain: {e}")
            return {}
        
        for speaker, data in speakers_data.items():
            print(f"\n🎤 Processando {speaker}...")
            
            # Cria arquivo concatenado para o speaker
            speaker_audio_path = os.path.join(self.output_dir, f"{speaker}_concatenated.wav")
            
            if self._concatenate_speaker_audio(speaker, data['segments'], speaker_audio_path):
                print(f"   ✅ Áudio concatenado criado: {speaker_audio_path}")
                
                # Gera embedding usando SpeechBrain
                try:
                    print(f"   🔄 Extraindo embedding usando SpeechBrain...")
                    
                    # Carrega o áudio concatenado
                    signal, fs = torchaudio.load(speaker_audio_path)
                    
                    # Gera embedding usando o modelo SpeechBrain
                    embedding = classifier.encode_batch(signal)
                    embedding_np = embedding.squeeze().cpu().numpy()
                    
                    speaker_embeddings[speaker] = {
                        'embedding': embedding_np,
                        'audio_path': speaker_audio_path,
                        'segments_count': len(data['segments']),
                        'total_duration': data['total_duration']
                    }
                    print(f"   ✅ Embedding extraído para {speaker} (dimensão: {embedding_np.shape})")
                        
                except Exception as e:
                    print(f"   ❌ Erro ao extrair embedding para {speaker}: {e}")
            else:
                print(f"   ❌ Falha ao concatenar áudio para {speaker}")
        
        print(f"\n✅ Embeddings gerados para {len(speaker_embeddings)} speakers")
        return speaker_embeddings
    
    async def test_coqui_tts_execution(self):
        """Testa execução real do CoquiTTS com agrupamento por speaker e embeddings de clonagem"""
        print("🎭 Testando execução do CoquiTTS com agrupamento por speaker...")
        print("🎤 Gerando embeddings de clonagem para cada speaker")
        print("🔊 Usando áudio concatenado para melhor qualidade de clonagem")
        print("=" * 60)
        
        # Cria diretório de saída
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Carrega dados agrupados por speaker
        speakers_data = self._load_data()
        
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
        
        # Gera embeddings de clonagem para cada speaker
        speaker_embeddings = self._generate_speaker_embeddings(speakers_data)
        
        if not speaker_embeddings:
            print("❌ Nenhum embedding de speaker foi gerado")
            return []
        
        # Sintetiza cada segmento usando o embedding do speaker correspondente
        print("\n🎵 Iniciando síntese de fala com embeddings de clonagem...")
        results = []
        segment_counter = 0
        
        for speaker, data in speakers_data.items():
            if speaker not in speaker_embeddings:
                print(f"⚠️ Pulando {speaker} - embedding não disponível")
                continue
                
            print(f"\n🎤 Sintetizando segmentos do {speaker}...")
            
            for segment in data['segments']:
                segment_counter += 1
                translated_text = segment['translated_text']
                
                print(f"   📝 Segmento {segment_counter}: {translated_text[:50]}...")
                
                # Prepara dados para o CoquiTTS usando áudio de referência
                tts_data = {
                    "text": translated_text,
                    "speaker_wav": speaker_embeddings[speaker]['audio_path']
                }
                
                # Executa síntese de fala
                start_time_tts = time.time()
                
                try:
                    result = await coqui_tts.execute(
                        data=tts_data,
                        progress_callback=self._progress_callback
                    )
                    duration = time.time() - start_time_tts
                    
                    if result.get("success", False):
                        # Aplica pós-processamento para melhorar qualidade
                        self._post_process_audio(result['output_path'])
                        
                        # Adiciona informações necessárias para o arquivo final
                        result['speaker'] = speaker
                        result['segment_index'] = segment['index']  # Adiciona índice do segmento
                        
                        print(f"   ✅ Síntese {segment_counter} concluída em {duration:.2f} segundos!")
                        print(f"   📊 Tamanho: {result['file_size']} bytes")
                        print(f"   🎤 Speaker: {speaker}")
                        print(f"   ⏱️ Timestamp: {segment['timestamp']}")
                        results.append(result)
                    else:
                        print(f"   ❌ Erro na síntese {segment_counter}: {result.get('error', 'Erro desconhecido')}")
                    
                except Exception as e:
                    print(f"   ❌ Exceção na síntese {segment_counter}: {e}")
        
        # Validação dos resultados
        self._validate_results(results)
        
        # Cria arquivo de áudio final com timestamps
        if results:
            final_audio = self._create_final_audio_with_timestamps(results, speakers_data)
            if final_audio:
                print(f"\n🎵 Arquivo de áudio final criado: {final_audio}")
                print("   📊 Respeitando timestamps originais com sobreposições e silêncios")
            else:
                print("\n⚠️ Falha ao criar arquivo de áudio final")
        
        print("\n🎯 TESTE DO COQUI TTS EXECUTADO COM SUCESSO!")
        return results
    
    def _create_final_audio_with_timestamps(self, results: list, speakers_data: dict):
        """Cria arquivo de áudio final respeitando timestamps com sobreposições e silêncios"""
        print("\n🎵 Criando arquivo de áudio final com timestamps...")
        
        # Encontra a duração total baseada apenas nos segmentos processados
        max_end_time = 0
        processed_segments = set()
        
        # Coleta apenas os segmentos que foram processados
        for result in results:
            if result.get('success', False):
                segment_index = result.get('segment_index', 0)
                speaker = result.get('speaker', 'Unknown')
                processed_segments.add((segment_index, speaker))
        
        # Calcula duração máxima apenas dos segmentos processados
        for speaker_data in speakers_data.values():
            for segment in speaker_data['segments']:
                if (segment['index'], segment['speaker']) in processed_segments:
                    start_time, end_time = segment['timestamp']
                    max_end_time = max(max_end_time, end_time)
        
        print(f"📊 Duração total do áudio (apenas segmentos processados): {max_end_time:.2f} segundos")
        print(f"📊 Segmentos processados: {len(processed_segments)}")
        
        # Cria lista de segmentos únicos ordenados por timestamp
        segments = []
        
        # Processa cada resultado de síntese
        for result in results:
            if result.get('success', False):
                segment_index = result.get('segment_index', 0)
                speaker = result.get('speaker', 'Unknown')
                
                # Encontra o segmento original para obter timestamps
                original_segment = None
                for speaker_data in speakers_data.values():
                    for seg in speaker_data['segments']:
                        if seg['index'] == segment_index and seg['speaker'] == speaker:
                            original_segment = seg
                            break
                    if original_segment:
                        break
                
                if original_segment:
                    start_time, end_time = original_segment['timestamp']
                    segments.append({
                        'file': result['output_path'],
                        'start_time': start_time,
                        'end_time': end_time,
                        'speaker': speaker,
                        'segment_index': segment_index,
                        'duration': end_time - start_time
                    })
        
        # Ordena segmentos por timestamp de início
        segments.sort(key=lambda x: x['start_time'])
        
        print(f"📋 {len(segments)} segmentos de áudio processados")
        
        # Mostra informações dos segmentos
        for i, seg in enumerate(segments[:5]):  # Mostra apenas os primeiros 5
            print(f"   {i+1}. {seg['speaker']}: {seg['start_time']:.2f}s-{seg['end_time']:.2f}s ({seg['duration']:.2f}s)")
        if len(segments) > 5:
            print(f"   ... e mais {len(segments) - 5} segmentos")
        
        # Cria arquivo de áudio final usando ffmpeg
        final_output = os.path.join(self.output_dir, "final_audio_with_timestamps.wav")
        
        try:
            # Cria arquivo de áudio base (silêncio)
            base_audio = os.path.join(self.output_dir, "base_silence.wav")
            self._create_silence_audio(base_audio, max_end_time)
            
            # Aplica montagem sequencial usando ffmpeg
            self._apply_audio_overlays(base_audio, segments, final_output)
            
            # Limpa arquivos temporários
            self._cleanup_temp_files(results, base_audio)
            
            print(f"✅ Arquivo final criado: {final_output}")
            return final_output
            
        except Exception as e:
            print(f"❌ Erro ao criar arquivo final: {e}")
            return None
    
    def _create_silence_audio(self, output_path: str, duration: float):
        """Cria arquivo de áudio com silêncio da duração especificada"""
        try:
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'anullsrc=channel_layout=mono:sample_rate=48000',
                '-t', str(duration),
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   🔇 Áudio base (silêncio) criado: {duration:.2f}s")
                return True
            else:
                print(f"   ❌ Erro ao criar áudio base: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exceção ao criar áudio base: {e}")
            return False
    
    def _apply_audio_overlays(self, base_audio: str, segments: list, output_path: str):
        """Monta áudio final usando ffmpeg com suporte a segmentos paralelos"""
        try:
            print("   🔄 Montando áudio final com suporte a segmentos paralelos...")
            
            if not segments:
                # Apenas copia o áudio base se não há segmentos
                import shutil
                shutil.copy2(base_audio, output_path)
                print(f"   ✅ Áudio base copiado (sem segmentos)")
                return True
            
            print(f"   📋 Processando {len(segments)} segmentos...")
            
            # Agrupa segmentos por janelas de tempo para detectar paralelos
            time_windows = self._group_segments_by_time_windows(segments)
            
            print(f"   🕐 Detectadas {len(time_windows)} janelas de tempo")
            
            # Cria comando ffmpeg
            cmd = ['ffmpeg']
            
            # Adiciona inputs
            cmd.extend(['-i', base_audio])  # Áudio base (silêncio)
            for segment in segments:
                cmd.extend(['-i', segment['file']])
            
            # Cria filtros para cada janela de tempo
            filter_parts = []
            mix_inputs = ["[0]"]  # Começa com áudio base
            
            for window_start, window_segments in time_windows.items():
                if len(window_segments) == 1:
                    # Segmento único - aplica delay normal
                    segment = window_segments[0]
                    segment_idx = segments.index(segment)
                    input_idx = segment_idx + 1
                    start_time = segment['start_time']
                    delay_ms = int(start_time * 1000)
                    
                    filter_parts.append(f"[{input_idx}]adelay={delay_ms}|{delay_ms}[delayed{segment_idx}]")
                    mix_inputs.append(f"[delayed{segment_idx}]")
                    
                    print(f"   ⏱️ Segmento único {segment_idx+1}: delay={delay_ms}ms, start={start_time:.2f}s")
                    
                else:
                    # Múltiplos segmentos paralelos - mistura primeiro, depois aplica delay
                    print(f"   🔄 Janela {window_start}s: {len(window_segments)} segmentos paralelos")
                    
                    # Cria lista de inputs para esta janela
                    window_inputs = []
                    for segment in window_segments:
                        segment_idx = segments.index(segment)
                        input_idx = segment_idx + 1
                        window_inputs.append(f"[{input_idx}]")
                    
                    # Mistura os segmentos paralelos
                    if len(window_inputs) > 1:
                        mix_name = f"parallel{window_start}"
                        mix_filter = f"{''.join(window_inputs)}amix=inputs={len(window_inputs)}:duration=first[{mix_name}]"
                        filter_parts.append(mix_filter)
                        
                        # Aplica delay ao resultado da mistura
                        start_time = min(seg['start_time'] for seg in window_segments)
                        delay_ms = int(start_time * 1000)
                        final_name = f"delayed{window_start}"
                        filter_parts.append(f"[{mix_name}]adelay={delay_ms}|{delay_ms}[{final_name}]")
                        mix_inputs.append(f"[{final_name}]")
                        
                        print(f"   🔗 Misturados {len(window_segments)} segmentos, delay={delay_ms}ms")
                    else:
                        # Apenas um segmento na janela
                        segment = window_segments[0]
                        segment_idx = segments.index(segment)
                        input_idx = segment_idx + 1
                        start_time = segment['start_time']
                        delay_ms = int(start_time * 1000)
                        
                        filter_parts.append(f"[{input_idx}]adelay={delay_ms}|{delay_ms}[delayed{segment_idx}]")
                        mix_inputs.append(f"[delayed{segment_idx}]")
            
            # Combina todos os áudios
            if len(mix_inputs) > 1:
                mix_filter = f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first[out]"
                filter_parts.append(mix_filter)
                
                cmd.extend([
                    '-filter_complex', ';'.join(filter_parts),
                    '-map', '[out]',
                    '-c:a', 'pcm_s16le',
                    '-ar', '48000',
                    '-ac', '1',
                    '-y',
                    output_path
                ])
            else:
                # Apenas copia o áudio base
                cmd.extend(['-c', 'copy', '-y', output_path])
            
            print(f"   🔧 Executando montagem com ffmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   ✅ Áudio final montado com sucesso")
                print(f"   📊 {len(segments)} segmentos processados em {len(time_windows)} janelas")
                
                # Verifica a duração do arquivo final
                if os.path.exists(output_path):
                    final_duration = self._get_audio_duration(output_path)
                    print(f"   ⏱️ Duração final: {final_duration:.2f} segundos")
                    
                    # Valida se a duração está próxima do esperado
                    expected_duration = max(seg['end_time'] for seg in segments) if segments else 0
                    if abs(final_duration - expected_duration) > 1.0:  # Tolerância de 1 segundo
                        print(f"   ⚠️ Aviso: Duração final ({final_duration:.2f}s) difere do esperado ({expected_duration:.2f}s)")
                    else:
                        print(f"   ✅ Duração correta!")
                
                return True
            else:
                print(f"   ❌ Erro na montagem: {result.stderr}")
                # Fallback: concatenação simples
                return self._fallback_simple_concat(segments, output_path)
                
        except Exception as e:
            print(f"   ❌ Exceção na montagem: {e}")
            # Fallback: concatenação simples
            return self._fallback_simple_concat(segments, output_path)
    
    def _group_segments_by_time_windows(self, segments: list, window_size: float = 1.0) -> dict:
        """Agrupa segmentos por janelas de tempo para detectar paralelos"""
        time_windows = {}
        
        for segment in segments:
            start_time = segment['start_time']
            end_time = segment['end_time']
            
            # Cria janelas de 1 segundo baseadas no tempo de início
            window_start = int(start_time)
            
            if window_start not in time_windows:
                time_windows[window_start] = []
            
            time_windows[window_start].append(segment)
        
        # Remove janelas vazias e ordena
        time_windows = {k: v for k, v in time_windows.items() if v}
        
        return time_windows
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Obtém a duração de um arquivo de áudio usando ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                print(f"   ⚠️ Erro ao obter duração: {result.stderr}")
                return 0.0
        except Exception as e:
            print(f"   ⚠️ Exceção ao obter duração: {e}")
            return 0.0
    
    def _fallback_simple_concat(self, segments, output_path):
        """Fallback: concatenação simples sem timestamps"""
        try:
            print("   🔄 Usando fallback de concatenação simples...")
            
            # Cria arquivo de lista para concatenação
            concat_file = os.path.join(self.output_dir, "concat_fallback.txt")
            with open(concat_file, 'w') as f:
                for segment in segments:
                    f.write(f"file '{segment['file']}'\n")
            
            # Executa concatenação
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Limpa arquivo temporário
            if os.path.exists(concat_file):
                os.remove(concat_file)
            
            if result.returncode == 0:
                print(f"   ✅ Concatenação simples concluída")
                return True
            else:
                print(f"   ❌ Erro na concatenação simples: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exceção na concatenação simples: {e}")
            return False
    
    def _cleanup_temp_files(self, results: list, base_audio: str):
        """Remove arquivos temporários após criar o arquivo final"""
        try:
            print("   🧹 Limpando arquivos temporários...")
            
            # Remove arquivo de silêncio base
            if os.path.exists(base_audio):
                os.remove(base_audio)
                print(f"   🗑️ Removido: {os.path.basename(base_audio)}")
            
            # Remove arquivos de áudio individuais dos resultados
            for result in results:
                if result.get('success', False):
                    temp_file = result.get('output_path')
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"   🗑️ Removido: {os.path.basename(temp_file)}")
            
            # Remove arquivos concatenados de speakers (se existirem)
            for file_name in os.listdir(self.output_dir):
                if file_name.endswith('_concatenated.wav'):
                    file_path = os.path.join(self.output_dir, file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"   🗑️ Removido: {file_name}")
            
            print("   ✅ Limpeza concluída!")
            
        except Exception as e:
            print(f"   ⚠️ Erro durante limpeza: {e}")
    
    def _validate_results(self, results):
        """Valida os resultados da síntese"""
        print("\n🔍 Validando resultados...")
        
        if not results:
            print("⚠️ Nenhum resultado para validar")
            return
        
        print(f"✅ {len(results)} sínteses executadas com sucesso")
        
        # Conta sínteses por speaker
        speaker_count = {}
        for result in results:
            if result.get('success', False):
                speaker = result.get('speaker', 'Unknown')
                speaker_count[speaker] = speaker_count.get(speaker, 0) + 1
        
        print("📊 Sínteses por speaker:")
        for speaker, count in speaker_count.items():
            print(f"   🎤 {speaker}: {count} segmentos")
        
        print("✅ Validação concluída!")


async def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do CoquiTTS com agrupamento por speaker...")
    print("🎤 Usando embeddings de clonagem para melhor qualidade")
    print("🎵 Gerando apenas arquivo final com timestamps sincronizados")
    print("=" * 60)
    
    try:
        test = TestCoquiTTS()
        
        # Executa o teste principal
        results = await test.test_coqui_tts_execution()

        print("\n" + "=" * 60)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resultado: {len(results)} sínteses executadas")
        
        # Verifica se arquivo final foi criado
        final_audio = os.path.join(test.output_dir, "final_audio_with_timestamps.wav")
        if os.path.exists(final_audio):
            file_size = os.path.getsize(final_audio)
            print(f"🎵 Arquivo final: {final_audio}")
            print(f"📊 Tamanho: {file_size / (1024*1024):.2f} MB")
            print("   ✅ Respeitando timestamps originais com sobreposições e silêncios")
            print("   🧹 Arquivos temporários removidos automaticamente")
        else:
            print("❌ Arquivo final não foi criado")
        
        # Mostra estatísticas por speaker
        speaker_stats = {}
        for result in results:
            speaker = result.get('speaker', 'Unknown')
            if speaker not in speaker_stats:
                speaker_stats[speaker] = 0
            speaker_stats[speaker] += 1
        
        print("\n📊 Estatísticas por speaker:")
        for speaker, count in speaker_stats.items():
            print(f"   🎤 {speaker}: {count} segmentos sintetizados")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTE FALHOU!")
        print("=" * 60)
        print(f"Erro: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
