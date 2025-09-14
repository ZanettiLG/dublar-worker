"""
Configurações e fixtures comuns para os testes
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock
import asyncio
from typing import Dict, Any


@pytest.fixture
def temp_dir():
    """Cria um diretório temporário para testes"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def sample_audio_file(temp_dir):
    """Cria um arquivo de áudio de exemplo para testes"""
    audio_path = os.path.join(temp_dir, "sample.wav")
    # Cria um arquivo vazio para simular um arquivo de áudio
    with open(audio_path, 'wb') as f:
        f.write(b"fake audio data")
    return audio_path


@pytest.fixture
def mock_worker():
    """Mock da classe Worker"""
    return Mock()


@pytest.fixture
def mock_separator():
    """Mock do Separator do Spleeter"""
    mock_sep = Mock()
    mock_sep.separate_to_file = Mock()
    return mock_sep


@pytest.fixture
def mock_demucs_main():
    """Mock da função main do Demucs"""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("deps.demucs.demucs_main", Mock())
        yield


@pytest.fixture
def mock_httpx_client():
    """Mock do AsyncClient do httpx"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.headers = {
        'content-length': '1024',
        'content-type': 'audio/wav',
        'last-modified': 'Mon, 01 Jan 2024 00:00:00 GMT',
        'etag': '"test-etag"'
    }
    mock_response.status_code = 200
    mock_client.head = Mock(return_value=mock_response)
    mock_client.stream = Mock()
    return mock_client


@pytest.fixture
def mock_logger():
    """Mock do logger"""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    return logger


@pytest.fixture
def sample_media_url():
    """URL de exemplo para testes de download"""
    return "https://example.com/sample.wav"


@pytest.fixture
def sample_headers():
    """Headers de exemplo para testes"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def progress_callback():
    """Callback de progresso para testes"""
    def callback(bytes_downloaded: int, total_bytes: int):
        pass
    return callback


@pytest.fixture
def mock_torch():
    """Mock do torch para testes do Demucs"""
    with pytest.MonkeyPatch().context() as m:
        mock_torch = Mock()
        mock_torch.cuda = Mock()
        mock_torch.cuda.is_available = Mock(return_value=False)
        m.setattr("deps.demucs.torch", mock_torch)
        yield mock_torch


@pytest.fixture
def mock_tensorflow():
    """Mock do TensorFlow para testes do Spleeter"""
    with pytest.MonkeyPatch().context() as m:
        mock_tf = Mock()
        mock_tf.config = Mock()
        mock_tf.config.experimental = Mock()
        mock_tf.config.threading = Mock()
        mock_tf.config.list_physical_devices = Mock(return_value=[])
        m.setattr("deps.spleeter.tf", mock_tf)
        yield mock_tf


@pytest.fixture
def mock_path():
    """Mock do pathlib.Path"""
    with pytest.MonkeyPatch().context() as m:
        mock_path = Mock()
        mock_path.mkdir = Mock()
        mock_path.exists = Mock(return_value=True)
        mock_path.stem = "sample"
        m.setattr("deps.spleeter.Path", mock_path)
        m.setattr("deps.demucs.Path", mock_path)
        m.setattr("deps.media.Path", mock_path)
        yield mock_path


@pytest.fixture
def mock_os():
    """Mock do módulo os"""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("deps.spleeter.os.path.exists", Mock(return_value=True))
        m.setattr("deps.demucs.os.path.exists", Mock(return_value=True))
        yield


@pytest.fixture
def mock_shutil():
    """Mock do módulo shutil"""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("deps.demucs.shutil.copy2", Mock())
        yield


@pytest.fixture
def event_loop():
    """Event loop para testes assíncronos"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_asyncio_run():
    """Mock do asyncio.run para testes síncronos"""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("deps.media.asyncio.run", Mock(return_value=True))
        yield


@pytest.fixture
def mock_transformers_pipeline():
    """Mock do pipeline do transformers"""
    mock_pipeline = Mock()
    mock_pipeline.return_value = {
        "text": "Hello world",
        "chunks": [
            {"text": "Hello", "timestamp": (0.0, 1.0)},
            {"text": "world", "timestamp": (1.0, 2.0)}
        ]
    }
    return mock_pipeline


@pytest.fixture
def mock_infer_device():
    """Mock da função infer_device"""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("deps.transcriber.infer_device", Mock(return_value='cpu'))
        yield


@pytest.fixture
def sample_audio_path(temp_dir):
    """Caminho de arquivo de áudio de exemplo para testes"""
    audio_path = f"{temp_dir}/sample_audio.wav"
    with open(audio_path, 'wb') as f:
        f.write(b"fake audio data")
    return audio_path


@pytest.fixture
def sample_transcription_result():
    """Resultado de transcrição de exemplo"""
    return {
        "text": "Esta é uma transcrição de exemplo",
        "chunks": [
            {"text": "Esta é uma", "timestamp": (0.0, 2.5)},
            {"text": "transcrição de exemplo", "timestamp": (2.5, 5.0)}
        ]
    }
