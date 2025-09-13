from .dep_base import DepBase
from httpx import AsyncClient
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import asyncio

class Media(DepBase):
    name = 'media'

    def load(self):
        self.client = AsyncClient()
    
    async def download_media(
        self, 
        url: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Baixa um vídeo do S3 com progresso
        
        Args:
            url: URL do vídeo no S3
            output_path: Caminho onde salvar o arquivo
            progress_callback: Função para callback de progresso (bytes_baixados, total_bytes)
            headers: Headers HTTP adicionais
            
        Returns:
            bool: True se download foi bem-sucedido
        """
        if not self.client:
            self.load()
        
        try:
            # Primeiro, faz uma requisição HEAD para obter o tamanho do arquivo
            head_response = await self.client.head(url, headers=headers)
            total_size = int(head_response.headers.get('content-length', 0))
            
            self.logger.info(f"Iniciando download: {url} -> {output_path}")
            self.logger.info(f"Tamanho do arquivo: {total_size / (1024*1024):.2f} MB")
            
            # Cria o diretório se não existir
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            downloaded = 0
            async with self.client.stream('GET', url, headers=headers) as response:
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Callback de progresso
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
                        
                        # Log de progresso a cada 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            self.logger.info(f"Progresso: {progress:.1f}% ({downloaded / (1024*1024):.1f} MB)")
            
            self.logger.info(f"Download concluído: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no download de {url}: {e}")
            return False

    async def download_media_sync(
        self, 
        url: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Versão síncrona do download"""
        return await self.download_media(url, output_path, progress_callback, headers)

    def download_media_blocking(
        self, 
        url: str, 
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Versão bloqueante do download"""
        return asyncio.run(self.download_media(url, output_path, progress_callback, headers))

    async def get_media_info(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Obtém informações sobre o arquivo sem baixar
        
        Returns:
            Dict com informações do arquivo
        """
        if not self.client:
            self.load()
        
        try:
            response = await self.client.head(url, headers=headers)
            return {
                'size': int(response.headers.get('content-length', 0)),
                'content_type': response.headers.get('content-type', ''),
                'last_modified': response.headers.get('last-modified', ''),
                'etag': response.headers.get('etag', ''),
                'status_code': response.status_code
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter informações de {url}: {e}")
            return {}
    