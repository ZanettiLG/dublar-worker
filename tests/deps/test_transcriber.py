"""
Testes unitários para a classe Transcriber
"""
from unittest.mock import Mock, patch, MagicMock
import pytest
import logging
from deps.transcriber import WhisperModels

class TestTranscriber:
    """Testes para a classe Transcriber"""

    def test_transcriber_initialization(self, mock_worker):
        """Testa a inicialização da classe Transcriber"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = WhisperModels.LARGE
            
            # Act
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            
            # Assert
            assert transcriber.name == 'transcriber'
            assert transcriber.model == model
            assert transcriber.task == 'automatic-speech-recognition'
            assert transcriber.engine == mock_worker

    def test_transcriber_models_dictionary(self, mock_worker):
        """Testa que o dicionário de modelos está definido corretamente"""
        with patch('deps.transcriber.Transformers'):
            # Arrange
            model = "whisper-large"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            
            # Assert
            expected_models = {
                'whisper-turbo': 'openai/whisper-large-v3-turbo',
                'whisper-large': 'openai/whisper-large-v3',
                'whisper-medium': 'openai/whisper-medium',
                'whisper-small': 'openai/whisper-small',
                'whisper-tiny': 'openai/whisper-tiny',
            }
            assert transcriber.models == expected_models

    def test_transcriber_inheritance_from_transformers(self, mock_worker):
        """Testa que Transcriber herda corretamente de Transformers"""
        with patch('deps.transcriber.Transformers'):
            # Arrange
            model = "whisper-large"
            from deps.transcriber import Transcriber
            
            # Act
            transcriber = Transcriber(engine=mock_worker, model=model)
            
            # Assert
            assert hasattr(transcriber, 'name')
            assert hasattr(transcriber, 'model')
            assert hasattr(transcriber, 'task')
            assert hasattr(transcriber, 'engine')
            assert hasattr(transcriber, 'load')
            assert hasattr(transcriber, 'execute')
            assert hasattr(transcriber, 'models')

    def test_transcriber_task_automatic_speech_recognition(self, mock_worker):
        """Testa que a task é definida como automatic-speech-recognition"""
        with patch('deps.transcriber.Transformers'):
            # Arrange
            model = "whisper-medium"
            from deps.transcriber import Transcriber
            
            # Act
            transcriber = Transcriber(engine=mock_worker, model=model)
            
            # Assert
            assert transcriber.task == 'automatic-speech-recognition'

    def test_transcriber_load_calls_super(self, mock_worker):
        """Testa que o método load chama o método da classe pai"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = "whisper-small"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            
            # Act
            transcriber.load()
            
            # Assert
            mock_transformers.return_value.load.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcriber_execute_method_success(self, mock_worker):
        """Testa o método execute do Transcriber com sucesso"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = "whisper-large"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            transcriber.client = Mock()
            transcriber.client.return_value = {"text": "Hello world", "chunks": []}
            
            audio_path = "test_audio.wav"
            output_path = "test_output.txt"
            progress_callback = Mock()
            headers = {"Authorization": "Bearer token"}
            
            # Act
            result = await transcriber.execute(audio_path, output_path, progress_callback, headers)
            
            # Assert
            transcriber.client.assert_called_once_with(audio_path, return_timestamps=True)
            assert result == {"text": "Hello world", "chunks": []}

    @pytest.mark.asyncio
    async def test_transcriber_execute_method_error(self, mock_worker):
        """Testa o método execute do Transcriber com erro"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = "whisper-large"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            transcriber.client = Mock()
            transcriber.client.side_effect = Exception("Transcription error")
            
            audio_path = "test_audio.wav"
            output_path = "test_output.txt"
            
            # Act
            result = await transcriber.execute(audio_path, output_path)
            
            # Assert
            assert result == {"text": "", "chunks": []}

    @pytest.mark.asyncio
    async def test_transcriber_execute_without_callback_and_headers(self, mock_worker):
        """Testa o método execute sem callback e headers"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = "whisper-tiny"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            transcriber.client = Mock()
            transcriber.client.return_value = {"text": "Test transcription"}
            
            audio_path = "test_audio.wav"
            output_path = "test_output.txt"
            
            # Act
            result = await transcriber.execute(audio_path, output_path)
            
            # Assert
            transcriber.client.assert_called_once_with(audio_path, return_timestamps=True)
            assert result == {"text": "Test transcription"}

    @pytest.mark.asyncio
    async def test_transcriber_execute_return_timestamps_true(self, mock_worker):
        """Testa que return_timestamps é sempre True no execute"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = "whisper-medium"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            transcriber.client = Mock()
            transcriber.client.return_value = {"text": "Test", "chunks": []}
            
            audio_path = "test_audio.wav"
            output_path = "test_output.txt"
            
            # Act
            await transcriber.execute(audio_path, output_path)
            
            # Assert
            call_args = transcriber.client.call_args
            assert call_args[1]['return_timestamps'] is True

    def test_transcriber_different_models(self, mock_worker):
        """Testa inicialização com diferentes modelos"""
        test_models = [
            "whisper-turbo",
            "whisper-large", 
            "whisper-medium",
            "whisper-small",
            "whisper-tiny"
        ]
        
        for model in test_models:
            with patch('deps.transcriber.Transformers'):
                # Act
                from deps.transcriber import Transcriber
                transcriber = Transcriber(engine=mock_worker, model=model)
                
                # Assert
                assert transcriber.model == model
                assert transcriber.task == 'automatic-speech-recognition'

    def test_transcriber_models_attribute_access(self, mock_worker):
        """Testa acesso aos modelos disponíveis"""
        with patch('deps.transcriber.Transformers'):
            # Arrange
            model = "whisper-large"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            
            # Assert
            assert 'whisper-turbo' in transcriber.models
            assert 'whisper-large' in transcriber.models
            assert 'whisper-medium' in transcriber.models
            assert 'whisper-small' in transcriber.models
            assert 'whisper-tiny' in transcriber.models
            
            # Verifica valores específicos
            assert transcriber.models['whisper-turbo'] == 'openai/whisper-large-v3-turbo'
            assert transcriber.models['whisper-large'] == 'openai/whisper-large-v3'
            assert transcriber.models['whisper-medium'] == 'openai/whisper-medium'

    @pytest.mark.asyncio
    async def test_transcriber_execute_with_timestamps(self, mock_worker):
        """Testa que o execute retorna timestamps quando disponível"""
        with patch('deps.transcriber.Transformers') as mock_transformers:
            # Arrange
            model = "whisper-large"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            transcriber.client = Mock()
            expected_result = {
                "text": "Hello world",
                "chunks": [
                    {"text": "Hello", "timestamp": (0.0, 1.0)},
                    {"text": "world", "timestamp": (1.0, 2.0)}
                ]
            }
            transcriber.client.return_value = expected_result
            
            audio_path = "test_audio.wav"
            output_path = "test_output.txt"
            
            # Act
            result = await transcriber.execute(audio_path, output_path)
            
            # Assert
            assert result == expected_result
            assert 'chunks' in result
            assert len(result['chunks']) == 2

    @pytest.mark.unit
    def test_transcriber_unit_marker(self, mock_worker):
        """Testa que o marcador unit funciona"""
        with patch('deps.transcriber.Transformers'):
            model = "whisper-small"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            assert transcriber.name == 'transcriber'

    @pytest.mark.slow
    def test_transcriber_slow_marker(self, mock_worker):
        """Testa que o marcador slow funciona"""
        with patch('deps.transcriber.Transformers'):
            model = "whisper-large"
            from deps.transcriber import Transcriber
            transcriber = Transcriber(engine=mock_worker, model=model)
            assert transcriber.task == 'automatic-speech-recognition'