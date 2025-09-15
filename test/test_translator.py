"""
Teste de execução do Translator usando test/jsons/gto_ep1_transcription.json
Testa a tradução de inglês (EN) para português (PT)
"""
import os
import json
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

# Importa as dependências
from deps.translator import Translator


class TestTranslator:
    """Teste específico para execução do Translator"""
    
    def __init__(self):
        self.mock_worker = self._create_mock_worker()
        self.transcription_file = "/home/zan-notebook/github/dublar-worker/test/jsons/gto_ep1_transcription.json"
        self.input_language = "EN"
        self.target_language = "PT"
    
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
        """Callback para mostrar progresso da tradução"""
        progress = (current / total) * 100 if total > 0 else 0
        print(f"🔄 Progresso: {current}/{total} ({progress:.1f}%)")
    
    def _load_transcription_data(self):
        """Carrega os dados de transcrição do arquivo JSON"""
        print("📁 Carregando arquivo de transcrição...")
        
        if not os.path.exists(self.transcription_file):
            raise FileNotFoundError(f"Arquivo de transcrição não encontrado: {self.transcription_file}")
        
        with open(self.transcription_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        print(f"✅ Arquivo carregado: {len(transcription_data)} chunks de transcrição")
        print(f"📊 Tamanho do arquivo: {os.path.getsize(self.transcription_file) / 1024:.2f} KB")
        
        return transcription_data
    
    def _extract_texts_from_chunks(self, transcription_data):
        """Extrai os textos dos chunks de transcrição"""
        texts = []
        for chunk in transcription_data:
            if 'text' in chunk and chunk['text'].strip():
                texts.append(chunk['text'].strip())
        
        print(f"📝 Textos extraídos: {len(texts)} frases")
        return texts
    
    async def test_translator_execution(self):
        """Testa execução real do Translator com transcrição EN→PT"""
        print("🌐 Testando execução do Translator (EN→PT)...")
        print("=" * 60)
        
        # Carrega dados de transcrição
        transcription_data = self._load_transcription_data()
        texts = self._extract_texts_from_chunks(transcription_data)
        
        if not texts:
            raise ValueError("Nenhum texto encontrado na transcrição")
        
        # Mostra alguns exemplos de texto para traduzir
        print(f"\n📄 Exemplos de texto para traduzir:")
        for i, text in enumerate(texts[:3]):
            print(f"   {i+1}. {text}")
        if len(texts) > 3:
            print(f"   ... e mais {len(texts) - 3} frases")
        
        # Inicializa o Translator
        translator = Translator(engine=self.mock_worker)
        print(f"\n🔄 Carregando modelo de tradução (m2m100-1.2b)...")
        translator.load()
        print("✅ Modelo carregado com sucesso!")
        
        # Cria diretório temporário para saída
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "gto_ep1_translation.json")
            print(f"📁 Arquivo de saída: {output_file}")
            
            # Executa tradução
            print(f"\n🚀 Iniciando tradução de {len(texts)} frases (EN→PT)...")
            start_time = time.time()
            
            try:
                translated_chunks = []
                
                for i, text in enumerate(texts):
                    if i % 10 == 0:  # Mostra progresso a cada 10 frases
                        self._progress_callback(i, len(texts))
                    
                    # Traduz cada texto
                    translated_text = await translator.execute(
                        text=text,
                        target_language=self.target_language,
                        progress_callback=self._progress_callback
                    )
                    
                    # Mantém a estrutura original com timestamp
                    original_chunk = transcription_data[i]
                    translated_chunk = {
                        'timestamp': original_chunk.get('timestamp', []),
                        'text_en': text,
                        'text_pt': translated_text,
                        'original_text': original_chunk.get('text', '')
                    }
                    translated_chunks.append(translated_chunk)
                
                duration = time.time() - start_time
                print(f"\n✅ Tradução concluída em {duration:.2f} segundos!")
                
                # Salva resultado
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(translated_chunks, f, ensure_ascii=False, indent=2)
                
                # Valida resultado
                self._validate_result(translated_chunks, output_file)
                
                print("\n🎯 TESTE DO TRANSLATOR EXECUTADO COM SUCESSO!")
                return translated_chunks
                
            except Exception as e:
                print(f"❌ Erro durante tradução: {e}")
                raise
    
    def _validate_result(self, translated_chunks, output_file):
        """Valida o resultado da tradução"""
        print("\n🔍 Validando resultado...")
        
        # Verifica se o resultado não está vazio
        assert translated_chunks is not None, "Resultado da tradução não pode ser None"
        assert len(translated_chunks) > 0, "Resultado da tradução não pode estar vazio"
        
        print(f"✅ Tradução gerou {len(translated_chunks)} chunks traduzidos")
        
        # Mostra alguns exemplos de tradução
        print(f"\n📝 Exemplos de tradução:")
        for i, chunk in enumerate(translated_chunks[:3]):
            print(f"   {i+1}. EN: {chunk.get('text_en', '')[:50]}...")
            print(f"      PT: {chunk.get('text_pt', '')[:50]}...")
            if 'timestamp' in chunk:
                print(f"      ⏱️  Timestamp: {chunk['timestamp']}")
            print()
        
        # Verifica se o arquivo de saída foi criado
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024
            print(f"✅ Arquivo de saída criado: {output_file} ({file_size:.2f} KB)")
        else:
            print("⚠️ Arquivo de saída não foi criado")
        
        # Verifica estrutura dos chunks
        for chunk in translated_chunks[:5]:  # Verifica apenas os primeiros 5
            assert 'text_en' in chunk, "Chunk deve conter 'text_en'"
            assert 'text_pt' in chunk, "Chunk deve conter 'text_pt'"
            assert chunk['text_pt'].strip(), "Texto traduzido não pode estar vazio"
        
        print("✅ Validação concluída com sucesso!")
    
    async def test_batch_translation(self):
        """Testa tradução em lotes para melhor performance"""
        print("\n🔄 Testando tradução em lotes...")
        print("=" * 60)
        
        # Carrega dados
        transcription_data = self._load_transcription_data()
        texts = self._extract_texts_from_chunks(transcription_data)
        
        test_texts = texts
        print(f"📝 Testando com {len(test_texts)} frases")
        
        translator = Translator(engine=self.mock_worker)
        translator.load()
        
        start_time = time.time()
        
        # Traduz em lotes
        batch_size = 5
        translated_batch = []
        
        for i in range(0, len(test_texts), batch_size):
            batch = test_texts[i:i + batch_size]
            print(f"🔄 Processando lote {i//batch_size + 1}/{(len(test_texts) + batch_size - 1)//batch_size}")
            
            for text in batch:
                translated = await translator.execute(text, self.target_language)
                translated_batch.append(translated)
        
        duration = time.time() - start_time
        print(f"✅ Tradução em lotes concluída em {duration:.2f}s")
        print(f"📊 Performance: {len(test_texts)/duration:.2f} frases/segundo")

        return translated_batch

async def main():
    """Função principal para executar o teste"""
    print("🚀 Iniciando teste do Translator...")
    print("=" * 60)
    
    try:
        test = TestTranslator()
        
        # Teste de performance
        result = await test.test_batch_translation()

        # Salva a tradução em um arquivo
        output_path = "test/jsons/translator_en_pt.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 Tradução salva em: {output_path}")
        
        print("\n" + "=" * 60)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resultado: {len(result)} chunks traduzidos (EN→PT)")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTE FALHOU!")
        print("=" * 60)
        print(f"Erro: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
