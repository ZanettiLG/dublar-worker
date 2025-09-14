"""
Testes unitários para a classe Transformers
"""
from unittest.mock import Mock, patch, MagicMock
import pytest
from deps.transformers import Transformers


class TestTransformers:
    """Testes para a classe Transformers"""

    def test_transformers_initialization(self, mock_worker):
        """Testa a inicialização da classe Transformers"""
        # Arrange
        model = "test-model"
        task = "test-task"
        
        # Act
        transformers = Transformers(engine=mock_worker, model=model, task=task)
        
        # Assert
        assert transformers.name == 'transformers'
        assert transformers.model == model
        assert transformers.task == task
        assert transformers.engine == mock_worker

    def test_transformers_load_method(self, mock_worker):
        """Testa o método load do Transformers"""
        with patch('deps.transformers.pipeline') as mock_pipeline:
            # Arrange
            model = "test-model"
            task = "test-task"
            transformers = Transformers(engine=mock_worker, model=model, task=task)
            
            # Act
            transformers.load()
            
            # Assert
            mock_pipeline.assert_called_once_with(task, model=model, device_map="auto")
            assert transformers.client == mock_pipeline.return_value

    def test_transformers_execute_method(self, mock_worker):
        """Testa o método execute do Transformers"""
        with patch('deps.transformers.pipeline') as mock_pipeline:
            # Arrange
            model = "test-model"
            task = "test-task"
            transformers = Transformers(engine=mock_worker, model=model, task=task)
            transformers.load()
            
            url = "test-url"
            output_path = "test-output"
            progress_callback = Mock()
            headers = {"Authorization": "Bearer token"}
            
            # Act
            result = transformers.execute(url, output_path, progress_callback, headers)
            
            # Assert
            # O método execute está vazio, então deve retornar None implicitamente
            assert result is None

    def test_transformers_inheritance_from_dep_base(self, mock_worker):
        """Testa que Transformers herda corretamente de DepBase"""
        # Arrange
        model = "test-model"
        task = "test-task"
        
        # Act
        transformers = Transformers(engine=mock_worker, model=model, task=task)
        
        # Assert
        assert hasattr(transformers, 'name')
        assert hasattr(transformers, 'engine')
        assert hasattr(transformers, 'load')
        assert hasattr(transformers, 'execute')

    def test_transformers_model_and_task_attributes(self, mock_worker):
        """Testa que os atributos model e task são definidos corretamente"""
        # Arrange
        model = "whisper-large-v3"
        task = "automatic-speech-recognition"
        
        # Act
        transformers = Transformers(engine=mock_worker, model=model, task=task)
        
        # Assert
        assert transformers.model == model
        assert transformers.task == task

    def test_transformers_name_attribute(self, mock_worker):
        """Testa que o atributo name está definido corretamente"""
        # Arrange
        model = "test-model"
        task = "test-task"
        
        # Act
        transformers = Transformers(engine=mock_worker, model=model, task=task)
        
        # Assert
        assert transformers.name == 'transformers'

    def test_transformers_pipeline_initialization(self, mock_worker):
        """Testa inicialização do pipeline com parâmetros corretos"""
        with patch('deps.transformers.pipeline') as mock_pipeline:
            # Arrange
            model = "openai/whisper-large-v3"
            task = "automatic-speech-recognition"
            transformers = Transformers(engine=mock_worker, model=model, task=task)
            
            # Act
            transformers.load()
            
            # Assert
            mock_pipeline.assert_called_once_with(
                task, 
                model=model, 
                device_map="auto"
            )

    def test_transformers_device_map_auto(self, mock_worker):
        """Testa que device_map é definido como 'auto'"""
        with patch('deps.transformers.pipeline') as mock_pipeline:
            # Arrange
            model = "test-model"
            task = "test-task"
            transformers = Transformers(engine=mock_worker, model=model, task=task)
            
            # Act
            transformers.load()
            
            # Assert
            call_args = mock_pipeline.call_args
            assert call_args[1]['device_map'] == 'auto'

    @pytest.mark.unit
    def test_transformers_unit_marker(self, mock_worker):
        """Testa que o marcador unit funciona"""
        model = "test-model"
        task = "test-task"
        transformers = Transformers(engine=mock_worker, model=model, task=task)
        assert transformers.name == 'transformers'

    def test_transformers_different_models_and_tasks(self, mock_worker):
        """Testa inicialização com diferentes modelos e tarefas"""
        test_cases = [
            ("whisper-large-v3", "automatic-speech-recognition"),
            ("bert-base-uncased", "text-classification"),
            ("gpt2", "text-generation"),
        ]
        
        for model, task in test_cases:
            with patch('deps.transformers.pipeline'):
                # Act
                transformers = Transformers(engine=mock_worker, model=model, task=task)
                
                # Assert
                assert transformers.model == model
                assert transformers.task == task
