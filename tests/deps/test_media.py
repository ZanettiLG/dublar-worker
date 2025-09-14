"""
Testes unitários para a classe Media
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from deps.media import Media
import asyncio


class TestMedia:
    """Testes para a classe Media"""

    def test_media_initialization(self, mock_worker, mock_httpx_client):
        """Testa a inicialização da classe Media"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            # Act
            media = Media(engine=mock_worker)
            
            # Assert
            assert media.name == 'media'
            assert media.engine == mock_worker
            assert media.client == mock_httpx_client

    def test_media_load_method(self, mock_worker, mock_httpx_client):
        """Testa o método load do Media"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client) as mock_client_class:
            # Act
            media = Media(engine=mock_worker)
            
            # Assert
            mock_client_class.assert_called_once()
            assert media.client == mock_httpx_client

    @pytest.mark.asyncio
    async def test_download_media_success(self, mock_worker, mock_httpx_client, 
                                        sample_media_url, temp_dir, mock_logger, 
                                        progress_callback, sample_headers):
        """Testa download bem-sucedido de mídia"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                
                # Mock da resposta de stream
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.aiter_bytes = AsyncMock(return_value=[b"chunk1", b"chunk2"])
                mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
                
                # Act
                result = await media.download_media(
                    sample_media_url, 
                    output_path, 
                    progress_callback, 
                    sample_headers
                )
                
                # Assert
                assert result is True
                mock_httpx_client.head.assert_called_once_with(sample_media_url, headers=sample_headers)
                mock_httpx_client.stream.assert_called_once_with('GET', sample_media_url, headers=sample_headers)

    @pytest.mark.asyncio
    async def test_download_media_without_headers(self, mock_worker, mock_httpx_client, 
                                                 sample_media_url, temp_dir, mock_logger):
        """Testa download sem headers customizados"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                
                # Mock da resposta de stream
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.aiter_bytes = AsyncMock(return_value=[b"chunk1"])
                mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
                
                # Act
                result = await media.download_media(sample_media_url, output_path)
                
                # Assert
                assert result is True
                mock_httpx_client.head.assert_called_once_with(sample_media_url, headers=None)

    @pytest.mark.asyncio
    async def test_download_media_without_progress_callback(self, mock_worker, mock_httpx_client, 
                                                          sample_media_url, temp_dir, mock_logger):
        """Testa download sem callback de progresso"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                
                # Mock da resposta de stream
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.aiter_bytes = AsyncMock(return_value=[b"chunk1"])
                mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
                
                # Act
                result = await media.download_media(sample_media_url, output_path)
                
                # Assert
                assert result is True

    @pytest.mark.asyncio
    async def test_download_media_error_handling(self, mock_worker, mock_httpx_client, 
                                               sample_media_url, temp_dir, mock_logger):
        """Testa tratamento de erro durante download"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                mock_httpx_client.head.side_effect = Exception("Network error")
                
                # Act
                result = await media.download_media(sample_media_url, output_path)
                
                # Assert
                assert result is False
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_download_media_sync(self, mock_worker, mock_httpx_client, 
                                     sample_media_url, temp_dir, mock_logger):
        """Testa método download_media_sync"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                
                # Mock da resposta de stream
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.aiter_bytes = AsyncMock(return_value=[b"chunk1"])
                mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
                
                # Act
                result = await media.download_media_sync(sample_media_url, output_path)
                
                # Assert
                assert result is True

    def test_download_media_blocking(self, mock_worker, mock_httpx_client, 
                                   sample_media_url, temp_dir, mock_logger, mock_asyncio_run):
        """Testa método download_media_blocking"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                
                # Act
                result = media.download_media_blocking(sample_media_url, output_path)
                
                # Assert
                assert result is True

    @pytest.mark.asyncio
    async def test_get_media_info_success(self, mock_worker, mock_httpx_client, 
                                        sample_media_url, sample_headers):
        """Testa obtenção de informações de mídia com sucesso"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            # Arrange
            media = Media(engine=mock_worker)
            
            # Act
            result = await media.get_media_info(sample_media_url, sample_headers)
            
            # Assert
            assert result['size'] == 1024
            assert result['content_type'] == 'audio/wav'
            assert result['status_code'] == 200
            mock_httpx_client.head.assert_called_once_with(sample_media_url, headers=sample_headers)

    @pytest.mark.asyncio
    async def test_get_media_info_without_headers(self, mock_worker, mock_httpx_client, 
                                                sample_media_url):
        """Testa obtenção de informações sem headers"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            # Arrange
            media = Media(engine=mock_worker)
            
            # Act
            result = await media.get_media_info(sample_media_url)
            
            # Assert
            assert result['size'] == 1024
            mock_httpx_client.head.assert_called_once_with(sample_media_url, headers=None)

    @pytest.mark.asyncio
    async def test_get_media_info_error_handling(self, mock_worker, mock_httpx_client, 
                                               sample_media_url, mock_logger):
        """Testa tratamento de erro na obtenção de informações"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                mock_httpx_client.head.side_effect = Exception("Network error")
                
                # Act
                result = await media.get_media_info(sample_media_url)
                
                # Assert
                assert result == {}
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_download_media_client_not_initialized(self, mock_worker, sample_media_url, 
                                                       temp_dir, mock_logger):
        """Testa download quando cliente não está inicializado"""
        with patch('deps.media.AsyncClient') as mock_client_class:
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                media.client = None  # Simula cliente não inicializado
                output_path = f"{temp_dir}/downloaded_file.wav"
                
                # Mock da resposta de stream
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.aiter_bytes = AsyncMock(return_value=[b"chunk1"])
                mock_client_class.return_value.stream.return_value.__aenter__.return_value = mock_response
                
                # Act
                result = await media.download_media(sample_media_url, output_path)
                
                # Assert
                assert result is True
                # Verifica que o cliente foi inicializado
                mock_client_class.assert_called()

    @pytest.mark.asyncio
    async def test_download_media_progress_callback(self, mock_worker, mock_httpx_client, 
                                                  sample_media_url, temp_dir, mock_logger):
        """Testa callback de progresso durante download"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            with patch.object(Media, 'logger', mock_logger):
                # Arrange
                media = Media(engine=mock_worker)
                output_path = f"{temp_dir}/downloaded_file.wav"
                progress_calls = []
                
                def progress_callback(bytes_downloaded, total_bytes):
                    progress_calls.append((bytes_downloaded, total_bytes))
                
                # Mock da resposta de stream
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.aiter_bytes = AsyncMock(return_value=[b"chunk1", b"chunk2"])
                mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
                
                # Act
                result = await media.download_media(sample_media_url, output_path, progress_callback)
                
                # Assert
                assert result is True
                assert len(progress_calls) == 2  # Duas chamadas para dois chunks

    @pytest.mark.unit
    def test_media_unit_marker(self, mock_worker, mock_httpx_client):
        """Testa que o marcador unit funciona"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            media = Media(engine=mock_worker)
            assert media.name == 'media'

    @pytest.mark.integration
    def test_media_integration_marker(self, mock_worker, mock_httpx_client):
        """Testa que o marcador integration funciona"""
        with patch('deps.media.AsyncClient', return_value=mock_httpx_client):
            media = Media(engine=mock_worker)
            assert media.client == mock_httpx_client
