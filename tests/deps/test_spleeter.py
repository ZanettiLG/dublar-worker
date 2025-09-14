"""
Testes unitários para a classe Spleeter
"""
from unittest.mock import Mock, patch, MagicMock
import pytest
from deps.spleeter import Spleeter


class TestSpleeter:
    """Testes para a classe Spleeter"""

    def test_spleeter_initialization(self, mock_worker, mock_separator, mock_tensorflow):
        """Testa a inicialização da classe Spleeter"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            # Act
            spleeter = Spleeter(engine=mock_worker)
            
            # Assert
            assert spleeter.name == 'spleeter'
            assert spleeter.engine == mock_worker
            assert spleeter.client == mock_separator

    def test_spleeter_load_method(self, mock_worker, mock_separator, mock_tensorflow):
        """Testa o método load do Spleeter"""
        with patch('deps.spleeter.Separator', return_value=mock_separator) as mock_separator_class:
            # Act
            spleeter = Spleeter(engine=mock_worker)
            
            # Assert
            mock_separator_class.assert_called_once_with('spleeter:2stems')
            assert spleeter.client == mock_separator

    def test_spleeter_execute_success(self, mock_worker, mock_separator, mock_tensorflow, 
                                     sample_audio_file, temp_dir, mock_path, mock_os):
        """Testa execução bem-sucedida do Spleeter"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            # Arrange
            spleeter = Spleeter(engine=mock_worker)
            output_dir = f"{temp_dir}/output"
            
            # Act
            result = spleeter.execute(sample_audio_file, output_dir)
            
            # Assert
            assert result['audio_name'] == 'sample'
            assert 'separated_audios' in result
            assert 'vocals' in result['separated_audios']
            assert 'accompaniment' in result['separated_audios']
            mock_separator.separate_to_file.assert_called_once()

    def test_spleeter_execute_default_output_dir(self, mock_worker, mock_separator, 
                                               mock_tensorflow, sample_audio_file, mock_path, mock_os):
        """Testa execução com diretório de saída padrão"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            # Arrange
            spleeter = Spleeter(engine=mock_worker)
            
            # Act
            result = spleeter.execute(sample_audio_file)
            
            # Assert
            assert result['audio_name'] == 'sample'
            mock_separator.separate_to_file.assert_called_once_with(
                sample_audio_file, "output/spleeter"
            )

    def test_spleeter_execute_vocals_file_not_created(self, mock_worker, mock_separator, 
                                                     mock_tensorflow, sample_audio_file, 
                                                     temp_dir, mock_path, mock_os):
        """Testa erro quando arquivo de vocals não é criado"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            with patch('deps.spleeter.os.path.exists', side_effect=lambda x: 'vocals' not in x):
                # Arrange
                spleeter = Spleeter(engine=mock_worker)
                
                # Act & Assert
                with pytest.raises(Exception, match="Arquivo de vocals não foi criado"):
                    spleeter.execute(sample_audio_file, temp_dir)

    def test_spleeter_execute_accompaniment_file_not_created(self, mock_worker, mock_separator, 
                                                           mock_tensorflow, sample_audio_file, 
                                                           temp_dir, mock_path, mock_os):
        """Testa erro quando arquivo de accompaniment não é criado"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            with patch('deps.spleeter.os.path.exists', side_effect=lambda x: 'accompaniment' not in x):
                # Arrange
                spleeter = Spleeter(engine=mock_worker)
                
                # Act & Assert
                with pytest.raises(Exception, match="Arquivo de accompaniment não foi criado"):
                    spleeter.execute(sample_audio_file, temp_dir)

    def test_spleeter_execute_path_creation(self, mock_worker, mock_separator, mock_tensorflow, 
                                           sample_audio_file, temp_dir, mock_path, mock_os):
        """Testa que o diretório de saída é criado"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            # Arrange
            spleeter = Spleeter(engine=mock_worker)
            
            # Act
            spleeter.execute(sample_audio_file, temp_dir)
            
            # Assert
            mock_path.assert_called_with(temp_dir)
            mock_path.return_value.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_spleeter_execute_audio_name_extraction(self, mock_worker, mock_separator, 
                                                   mock_tensorflow, sample_audio_file, 
                                                   temp_dir, mock_path, mock_os):
        """Testa extração do nome do arquivo de áudio"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            # Arrange
            spleeter = Spleeter(engine=mock_worker)
            
            # Act
            result = spleeter.execute(sample_audio_file, temp_dir)
            
            # Assert
            assert result['audio_name'] == 'sample'

    def test_spleeter_execute_output_paths(self, mock_worker, mock_separator, mock_tensorflow, 
                                         sample_audio_file, temp_dir, mock_path, mock_os):
        """Testa construção dos caminhos de saída"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            # Arrange
            spleeter = Spleeter(engine=mock_worker)
            
            # Act
            result = spleeter.execute(sample_audio_file, temp_dir)
            
            # Assert
            expected_vocals = f"{temp_dir}/sample/vocals.wav"
            expected_accompaniment = f"{temp_dir}/sample/accompaniment.wav"
            
            assert result['separated_audios']['vocals'] == expected_vocals
            assert result['separated_audios']['accompaniment'] == expected_accompaniment

    def test_spleeter_tensorflow_configuration(self, mock_worker, mock_tensorflow):
        """Testa configuração do TensorFlow"""
        with patch('deps.spleeter.Separator'):
            # Act
            Spleeter(engine=mock_worker)
            
            # Assert
            # Verifica se as configurações do TensorFlow foram chamadas
            mock_tensorflow.config.threading.set_inter_op_parallelism_threads.assert_called_with(1)
            mock_tensorflow.config.threading.set_intra_op_parallelism_threads.assert_called_with(1)

    def test_spleeter_gpu_memory_growth_config(self, mock_worker, mock_tensorflow):
        """Testa configuração de crescimento de memória GPU quando GPU está disponível"""
        # Arrange
        mock_tensorflow.config.list_physical_devices.return_value = [Mock()]
        
        with patch('deps.spleeter.Separator'):
            # Act
            Spleeter(engine=mock_worker)
            
            # Assert
            mock_tensorflow.config.experimental.set_memory_growth.assert_called_once()

    def test_spleeter_no_gpu_available(self, mock_worker, mock_tensorflow):
        """Testa comportamento quando GPU não está disponível"""
        # Arrange
        mock_tensorflow.config.list_physical_devices.return_value = []
        
        with patch('deps.spleeter.Separator'):
            # Act
            Spleeter(engine=mock_worker)
            
            # Assert
            # Não deve chamar set_memory_growth quando não há GPU
            mock_tensorflow.config.experimental.set_memory_growth.assert_not_called()

    @pytest.mark.unit
    def test_spleeter_unit_marker(self, mock_worker, mock_separator, mock_tensorflow):
        """Testa que o marcador unit funciona"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            spleeter = Spleeter(engine=mock_worker)
            assert spleeter.name == 'spleeter'

    @pytest.mark.slow
    def test_spleeter_slow_marker(self, mock_worker, mock_separator, mock_tensorflow):
        """Testa que o marcador slow funciona"""
        with patch('deps.spleeter.Separator', return_value=mock_separator):
            spleeter = Spleeter(engine=mock_worker)
            assert spleeter.client == mock_separator
