import logging
import os
from enum import Enum
from deps.dep_base import DepBase
from typing import Optional, Dict, Any, Callable, List
import hdbscan
import numpy as np
import torch
import torchaudio
from speechbrain.inference.speaker import EncoderClassifier

# Configuração de logging
logger = logging.getLogger(__name__)

class Diarizer(DepBase):
    """Diarizer - Identifica diferentes falantes em áudio"""
    name = 'diarizer'
    model = 'speechbrain/spkrec-ecapa-voxceleb'
    embedder = None
    clusterer = None

    def __init__(self, engine: Any):
        """Inicializa o Diarizer"""
        # Converte o nome do modelo para o nome completo
        super().__init__(engine=engine)

    def load(self):
        """Carrega os modelos necessários para diarização"""
        try:
            # Carrega o modelo de embeddings para clustering
            logger.info(f"Carregando modelo de embeddings {self.model}...")
            self.embedder = EncoderClassifier.from_hparams(source=self.model)
            
            # Configura o clusterer HDBSCAN otimizado para detectar mais falantes
            logger.info("Configurando clusterer HDBSCAN para detectar mais falantes...")
            self.clusterer = hdbscan.HDBSCAN(
                min_cluster_size=3,  # Reduzido para detectar clusters menores
                min_samples=2,       # Menos restritivo para mais clusters
                metric="euclidean",  # Euclidean é suportada pelo HDBSCAN
                cluster_selection_epsilon=0.05,  # Mais sensível para detectar mais clusters
                cluster_selection_method='eom', # Usa Excess of Mass para melhor detecção
                allow_single_cluster=False,     # Força múltiplos clusters
                prediction_data=True,           # Permite predições mais precisas
                alpha=1.0,                      # Parâmetro de estabilidade
                algorithm='best'                # Melhor algoritmo disponível
            )
            
            logger.info("Diarizer carregado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao carregar Diarizer: {e}")
            self.embedder = None
            self.clusterer = None

    async def execute(
        self, 
        data: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executa a diarização dos speeches"""
        try:
            # Extrai dados da entrada
            audio_url = data.get("audio_url")
            speechs = data.get("speechs", [])
            
            if not speechs:
                logger.warning("Nenhum speech fornecido para diarização")
                return {"speakers": [], "segments": []}

            # Verifica se os modelos foram carregados corretamente
            if self.embedder is None or self.clusterer is None:
                logger.error("Modelos do diarizer não foram carregados. Tentando recarregar...")
                self.load()

            # 1. Geração de embeddings dos áudios dos speeches
            logger.info(f"Gerando embeddings para {len(speechs)} speeches...")
            print(f"🎤 Processando {len(speechs)} segmentos de fala para diarização...")
            
            # Conta tipos de segmentos
            short_segments = 0
            medium_segments = 0
            long_segments = 0
            
            for speech in speechs:
                duration = speech.get("end", 0) - speech.get("start", 0)
                if duration < 0.5:
                    short_segments += 1
                elif duration < 2.0:
                    medium_segments += 1
                else:
                    long_segments += 1
            
            print(f"   📊 Segmentos: {short_segments} curtos, {medium_segments} médios, {long_segments} longos")
            
            embeddings = []
            
            # Carrega o áudio principal uma vez
            if audio_url and os.path.exists(audio_url):
                try:
                    full_signal, fs = torchaudio.load(audio_url)
                    logger.info(f"Áudio carregado: {fs}Hz, {full_signal.shape}")
                except Exception as e:
                    logger.error(f"Erro ao carregar áudio principal: {e}")
                    return {"speakers": [], "segments": [], "error": f"Erro ao carregar áudio: {e}"}
            else:
                logger.error("URL do áudio não fornecida ou arquivo não encontrado")
                return {"speakers": [], "segments": [], "error": "URL do áudio não fornecida"}
            
            for i, speech in enumerate(speechs):
                try:
                    # Log de progresso a cada 50 segmentos
                    if i % 50 == 0:
                        print(f"   🔄 Processando segmento {i+1}/{len(speechs)}...")
                    
                    # Extrai segmento de áudio baseado nos timestamps
                    start_time = speech.get("start", 0.0)
                    end_time = speech.get("end", start_time + 1.0)
                    
                    # Calcula duração do segmento
                    duration = end_time - start_time
                    
                    # Marca segmentos curtos para processamento especial
                    is_short_segment = duration < 0.5
                    
                    # Adiciona contexto dinâmico baseado na duração do segmento
                    # Para segmentos curtos, usa contexto maior para compensar
                    if is_short_segment:
                        context = 0.3  # 300ms para segmentos curtos (mais contexto)
                    elif duration < 1.0:
                        context = 0.2  # 200ms para segmentos curtos
                    elif duration < 3.0:
                        context = 0.15  # 150ms para segmentos médios
                    else:
                        context = 0.1  # 100ms para segmentos longos
                    
                    extended_start = max(0, start_time - context)
                    extended_end = min(full_signal.shape[-1] / fs, end_time + context)
                    
                    # Converte timestamps para índices de amostra
                    start_sample = int(extended_start * fs)
                    end_sample = int(extended_end * fs)
                    
                    # Garante que temos pelo menos 100ms de áudio
                    min_samples = int(0.1 * fs)  # 100ms mínimo
                    if end_sample - start_sample < min_samples:
                        # Estende o segmento se for muito curto
                        center = (start_sample + end_sample) // 2
                        start_sample = max(0, center - min_samples // 2)
                        end_sample = min(full_signal.shape[-1], center + min_samples // 2)
                    
                    # Extrai segmento do áudio
                    if len(full_signal.shape) > 1:  # Se for estéreo, pega apenas o primeiro canal
                        segment = full_signal[0, start_sample:end_sample]
                    else:
                        segment = full_signal[start_sample:end_sample]
                    
                    # Garante que o segmento não está vazio
                    if len(segment) == 0:
                        logger.warning(f"Segmento vazio para speech {i}, usando embedding zero")
                        embeddings.append(np.zeros(192))
                        continue
                    
                    # Aplica filtro passa-alta para remover ruído de baixa frequência
                    from scipy import signal
                    try:
                        # Filtro passa-alta a 80Hz para remover ruído
                        nyquist = fs / 2
                        high = 80 / nyquist
                        b, a = signal.butter(4, high, btype='high')
                        segment = signal.filtfilt(b, a, segment)
                    except:
                        pass  # Se scipy não estiver disponível, continua sem filtro
                    
                    # Normaliza o áudio para melhor qualidade
                    max_val = np.max(np.abs(segment))
                    if max_val > 0:
                        segment = segment / max_val
                    
                    # Aplica janela de Hamming para reduzir artefatos de borda
                    if len(segment) > 0:
                        window = np.hamming(len(segment))
                        segment = segment * window
                    
                    # Processamento especial baseado no tipo de segmento
                    if is_short_segment:
                        # Para segmentos curtos, usa inferência baseada em contexto
                        # Gera múltiplos embeddings com diferentes janelas
                        segment_length = len(segment)
                        
                        # Log especial para segmentos curtos
                        if i % 100 == 0:  # A cada 100 segmentos curtos
                            print(f"   🔍 Processando segmento curto {i+1} ({duration:.2f}s)...")
                        
                        # Cria janelas sobrepostas para capturar mais informação
                        window_size = max(segment_length // 2, int(0.1 * fs))  # Pelo menos 100ms
                        overlap = window_size // 2
                        
                        window_embeddings = []
                        for start_idx in range(0, segment_length - window_size + 1, overlap):
                            window = segment[start_idx:start_idx + window_size]
                            if len(window) > 0:
                                # Aplica janela de Hamming na sub-janela
                                window = window * np.hamming(len(window))
                                
                                # Gera embedding
                                window_tensor = torch.from_numpy(window).unsqueeze(0)
                                embedding = self.embedder.encode_batch(window_tensor)
                                embedding_np = embedding.squeeze().cpu().numpy()
                                embedding_np = embedding_np / (np.linalg.norm(embedding_np) + 1e-8)
                                window_embeddings.append(embedding_np)
                        
                        # Usa a média ponderada dos embeddings das janelas
                        if window_embeddings:
                            # Peso maior para janelas centrais
                            weights = np.exp(-np.linspace(-1, 1, len(window_embeddings))**2)
                            weights = weights / np.sum(weights)
                            
                            weighted_embedding = np.average(window_embeddings, axis=0, weights=weights)
                            weighted_embedding = weighted_embedding / (np.linalg.norm(weighted_embedding) + 1e-8)
                            embeddings.append(weighted_embedding)
                        else:
                            # Fallback: usa o segmento inteiro
                            segment_tensor = torch.from_numpy(segment).unsqueeze(0)
                            embedding = self.embedder.encode_batch(segment_tensor)
                            embedding_np = embedding.squeeze().cpu().numpy()
                            embedding_np = embedding_np / (np.linalg.norm(embedding_np) + 1e-8)
                            embeddings.append(embedding_np)
                    
                    elif duration > 2.0:
                        # Para segmentos longos, divide em sub-segmentos para melhor diarização
                        segment_length = len(segment)
                        third = segment_length // 3
                        
                        sub_segments = [
                            segment[:third],  # Início
                            segment[third:2*third],  # Meio
                            segment[2*third:]  # Fim
                        ]
                        
                        sub_embeddings = []
                        for sub_seg in sub_segments:
                            if len(sub_seg) > 0:
                                # Gera embedding para cada sub-segmento
                                sub_seg_tensor = torch.from_numpy(sub_seg).unsqueeze(0)
                                embedding = self.embedder.encode_batch(sub_seg_tensor)
                                embedding_np = embedding.squeeze().cpu().numpy()
                                embedding_np = embedding_np / (np.linalg.norm(embedding_np) + 1e-8)
                                sub_embeddings.append(embedding_np)
                        
                        # Usa a média dos embeddings dos sub-segmentos
                        if sub_embeddings:
                            avg_embedding = np.mean(sub_embeddings, axis=0)
                            avg_embedding = avg_embedding / (np.linalg.norm(avg_embedding) + 1e-8)
                            embeddings.append(avg_embedding)
                        else:
                            embeddings.append(np.zeros(192))
                    else:
                        # Gera embedding usando o modelo SpeechBrain
                        segment_tensor = torch.from_numpy(segment).unsqueeze(0)
                        embedding = self.embedder.encode_batch(segment_tensor)
                        embedding_np = embedding.squeeze().cpu().numpy()
                        
                        # Normaliza o embedding para melhor clustering
                        embedding_np = embedding_np / (np.linalg.norm(embedding_np) + 1e-8)
                        
                        embeddings.append(embedding_np)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar speech {i}: {e}")
                    # Usa embedding zero em caso de erro
                    embeddings.append(np.zeros(192))  # ECAPA-TDNN produz embeddings de 192 dimensões
            
            embeddings = np.array(embeddings)
            
            # Validação dos embeddings
            print(f"🔍 Validando embeddings: {embeddings.shape}")
            print(f"   Valores NaN: {np.isnan(embeddings).sum()}")
            print(f"   Valores infinitos: {np.isinf(embeddings).sum()}")
            print(f"   Média: {np.mean(embeddings):.6f}")
            print(f"   Desvio padrão: {np.std(embeddings):.6f}")
            
            # Remove apenas embeddings realmente inválidos (NaN ou Inf)
            valid_embeddings = []
            valid_indices = []
            for i, emb in enumerate(embeddings):
                if not (np.isnan(emb).any() or np.isinf(emb).any()):
                    # Inclui embeddings zero (podem ser de segmentos muito curtos)
                    valid_embeddings.append(emb)
                    valid_indices.append(i)
            
            if len(valid_embeddings) == 0:
                logger.error("Nenhum embedding válido encontrado!")
                return {"speakers": [], "segments": [], "error": "Nenhum embedding válido"}
            
            valid_embeddings = np.array(valid_embeddings)
            print(f"✅ {len(valid_embeddings)} embeddings válidos de {len(embeddings)} total")

            # 2. Normaliza embeddings para melhor clustering euclidiano
            logger.info("Normalizando embeddings para clustering...")
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            normalized_embeddings = scaler.fit_transform(valid_embeddings)
            
            # 3. Clustering para identificar falantes
            logger.info("Executando clustering...")
            labels = self.clusterer.fit_predict(normalized_embeddings)
            
            # Análise de qualidade do clustering
            unique_labels = np.unique(labels)
            n_clusters = len(unique_labels[unique_labels != -1])  # Exclui ruído (-1)
            n_noise = np.sum(labels == -1)
            
            logger.info(f"Clustering result: {n_clusters} clusters, {n_noise} pontos de ruído")
            
            # Se muito poucos clusters ou muitos ruídos, usa fallback
            if n_clusters < 3 or n_noise > len(valid_embeddings) * 0.7:
                logger.info(f"Clustering HDBSCAN falhou: {n_clusters} clusters, {n_noise} ruídos")
                print(f"⚠️ HDBSCAN falhou ({n_clusters} clusters, {n_noise} ruídos), usando estratégia melhorada...")
                
                # Estratégia melhorada: KMeans com mais falantes
                from sklearn.cluster import KMeans
                best_labels = None
                best_n_clusters = 0
                best_silhouette = -1
                
                # Tenta números mais realistas de clusters (4-12 falantes)
                for n_speakers in [4, 5, 6, 7, 8, 9, 10, 11, 12]:
                    if n_speakers > len(valid_embeddings):
                        continue
                        
                    try:
                        print(f"🎯 Tentando {n_speakers} falantes com KMeans...")
                        kmeans = KMeans(n_clusters=n_speakers, random_state=42, n_init=20)
                        test_labels = kmeans.fit_predict(normalized_embeddings)
                        test_unique = np.unique(test_labels)
                        test_n_clusters = len(test_unique)
                        
                        # Avalia qualidade do clustering usando silhouette score
                        from sklearn.metrics import silhouette_score
                        if test_n_clusters > 1:
                            silhouette = silhouette_score(normalized_embeddings, test_labels)
                            print(f"   📊 {test_n_clusters} clusters, silhouette: {silhouette:.3f}")
                            
                            # Prefere mais clusters com boa qualidade
                            if silhouette > best_silhouette or (silhouette > 0.1 and test_n_clusters > best_n_clusters):
                                best_labels = test_labels
                                best_n_clusters = test_n_clusters
                                best_silhouette = silhouette
                                print(f"   ✅ Melhor resultado até agora!")
                        else:
                            print(f"   ⚠️ {test_n_clusters} clusters (muito poucos)")
                            
                    except Exception as e:
                        print(f"   ❌ Falhou com {n_speakers} clusters: {e}")
                        continue
                
                if best_labels is not None:
                    labels = best_labels
                    unique_labels = np.unique(labels)
                    n_clusters = len(unique_labels)
                    n_noise = 0  # KMeans não produz ruído
                    logger.info(f"Melhor KMeans result: {n_clusters} clusters")
                    print(f"✅ Melhor resultado: {n_clusters} falantes identificados")
                else:
                    logger.error("Todos os métodos de clustering falharam")
                    print("❌ Todos os métodos de clustering falharam")
                    # Fallback final: atribui todos ao mesmo falante
                    labels = np.zeros(len(valid_embeddings), dtype=int)
                    unique_labels = [0]
                    n_clusters = 1
                    n_noise = 0
                    print("🔄 Atribuindo todos os segmentos ao mesmo falante")

            # 4. Merge de clusters similares por similaridade coseno (mais conservador)
            logger.info("Aplicando merge de clusters similares...")
            labels, embeddings = self._merge_similar_clusters(labels, valid_embeddings, similarity_threshold=0.9)
            unique_labels = np.unique(labels)
            n_clusters = len(unique_labels[unique_labels != -1])
            n_noise = np.sum(labels == -1)
            
            print(f"   🔗 Após merge: {n_clusters} clusters, {n_noise} ruído")

            # 5. Organização dos resultados
            logger.info("Organizando resultados...")
            speakers_set = set()
            diarized_segments = []
            
            # Limita número máximo de speakers para evitar muitos falantes
            max_speakers = min(15, len(unique_labels))  # Aumentado para 15 speakers
            if len(unique_labels) > max_speakers:
                print(f"⚠️ Muitos speakers detectados ({len(unique_labels)}), limitando para {max_speakers}")
                # Reagrupa usando KMeans com número limitado
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=max_speakers, random_state=42, n_init=20)
                labels = kmeans.fit_predict(normalized_embeddings)
                unique_labels = np.unique(labels)
                n_clusters = len(unique_labels)
                print(f"✅ Reagrupado para {n_clusters} speakers")
            
            # Mapeia labels para nomes de falantes mais descritivos
            label_to_speaker = {}
            speaker_counter = 1
            
            for label in unique_labels:
                if label != -1:  # Não é ruído
                    if label not in label_to_speaker:
                        label_to_speaker[label] = f"Speaker_{speaker_counter}"
                        speaker_counter += 1

            # Mapeia labels de volta para todos os speeches
            for i, speech in enumerate(speechs):
                if i in valid_indices:
                    # Speech tem embedding válido
                    valid_idx = valid_indices.index(i)
                    label = labels[valid_idx]
                    if label == -1:  # Ruído
                        speaker_id = "Unknown"
                    else:
                        speaker_id = label_to_speaker.get(label, f"Speaker_{label}")
                else:
                    # Speech não tem embedding válido
                    speaker_id = "Unknown"
                
                speakers_set.add(speaker_id)
                diarized_segments.append(speaker_id)

            # 4. Resultado final
            result = {
                "speakers": sorted(list(speakers_set)),
                "segments": diarized_segments,
                "total_segments": len(speechs),
                "total_speakers": len([s for s in speakers_set if s != "Unknown"]),
                "clustering_quality": {
                    "n_clusters": n_clusters,
                    "n_noise_points": int(n_noise),
                    "noise_percentage": float(n_noise / len(speechs) * 100)
                }
            }

            print(f"✅ Diarização concluída: {result['total_speakers']} falantes identificados")
            print(f"📊 Qualidade: {n_clusters} clusters, {n_noise} ruído ({n_noise/len(speechs)*100:.1f}%)")
            print(f"🎭 Falantes encontrados: {', '.join(result['speakers'])}")
            
            logger.info(f"Diarização concluída: {result['total_speakers']} falantes identificados")
            logger.info(f"Qualidade: {n_clusters} clusters, {n_noise} ruído ({n_noise/len(speechs)*100:.1f}%)")
            return result

        except Exception as e:
            logger.error(f"Erro durante diarização: {e}")
            return {"speakers": [], "segments": [], "error": str(e)}
    
    def _merge_similar_clusters(self, labels: np.ndarray, embeddings: np.ndarray, similarity_threshold: float = 0.8) -> tuple:
        """Merge clusters similares baseado em similaridade coseno entre centroides"""
        try:
            unique_labels = np.unique(labels)
            valid_labels = unique_labels[unique_labels != -1]  # Remove ruído
            
            if len(valid_labels) <= 1:
                return labels, embeddings
            
            # Calcula centroides de cada cluster
            centroids = {}
            for label in valid_labels:
                cluster_embeddings = embeddings[labels == label]
                if len(cluster_embeddings) > 0:
                    centroids[label] = np.mean(cluster_embeddings, axis=0)
            
            # Calcula matriz de similaridade coseno entre centroides
            centroid_labels = list(centroids.keys())
            n_centroids = len(centroid_labels)
            
            if n_centroids <= 1:
                return labels, embeddings
            
            similarity_matrix = np.zeros((n_centroids, n_centroids))
            
            for i, label1 in enumerate(centroid_labels):
                for j, label2 in enumerate(centroid_labels):
                    if i != j:
                        # Similaridade coseno
                        cos_sim = np.dot(centroids[label1], centroids[label2]) / (
                            np.linalg.norm(centroids[label1]) * np.linalg.norm(centroids[label2]) + 1e-8
                        )
                        similarity_matrix[i, j] = cos_sim
            
            # Identifica pares de clusters similares
            merge_pairs = []
            for i in range(n_centroids):
                for j in range(i + 1, n_centroids):
                    if similarity_matrix[i, j] > similarity_threshold:
                        label1, label2 = centroid_labels[i], centroid_labels[j]
                        merge_pairs.append((label1, label2, similarity_matrix[i, j]))
            
            if not merge_pairs:
                print(f"   ✅ Nenhum cluster similar encontrado (threshold: {similarity_threshold})")
                return labels, embeddings
            
            # Ordena pares por similaridade (maior primeiro)
            merge_pairs.sort(key=lambda x: x[2], reverse=True)
            
            # Aplica merges (evita conflitos)
            merged_labels = labels.copy()
            used_labels = set()
            
            for label1, label2, similarity in merge_pairs:
                if label1 not in used_labels and label2 not in used_labels:
                    # Merge: atribui todos os pontos do label2 para label1
                    merged_labels[merged_labels == label2] = label1
                    used_labels.add(label2)
                    
                    print(f"   🔗 Merge: {label1} + {label2} (similaridade: {similarity:.3f})")
            
            # Recalcula estatísticas após merge
            final_labels = np.unique(merged_labels)
            final_valid_labels = final_labels[final_labels != -1]
            n_merged_clusters = len(final_valid_labels)
            
            print(f"   📊 Merge concluído: {len(valid_labels)} → {n_merged_clusters} clusters")
            
            return merged_labels, embeddings
            
        except Exception as e:
            logger.warning(f"Erro no merge de clusters: {e}")
            return labels, embeddings
