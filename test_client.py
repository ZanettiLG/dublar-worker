#!/usr/bin/env python3
"""
Cliente de Teste Assíncrono para Kafka
Permite enviar eventos e aguardar respostas de forma assíncrona
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import logging


@dataclass
class TestEvent:
    """Representa um evento de teste"""
    topic: str
    event: str
    payload: Dict[str, Any]
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    response_topic: Optional[str] = None
    timeout: int = 30  # segundos
    expected_response_type: Optional[str] = None


@dataclass
class TestResult:
    """Resultado de um teste"""
    event: TestEvent
    success: bool
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EventWaiter:
    """Sistema para aguardar respostas de eventos específicos"""
    
    def __init__(self):
        self.pending_events: Dict[str, asyncio.Future] = {}
        self.responses: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def wait_for_response(self, correlation_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Aguarda uma resposta para um correlation_id específico"""
        async with self._lock:
            if correlation_id in self.responses:
                return self.responses.pop(correlation_id)
            
            if correlation_id not in self.pending_events:
                self.pending_events[correlation_id] = asyncio.Future()
        
        try:
            response = await asyncio.wait_for(
                self.pending_events[correlation_id], 
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            async with self._lock:
                self.pending_events.pop(correlation_id, None)
            return None
    
    async def set_response(self, correlation_id: str, response: Dict[str, Any]):
        """Define uma resposta para um correlation_id"""
        async with self._lock:
            if correlation_id in self.pending_events:
                future = self.pending_events.pop(correlation_id)
                if not future.done():
                    future.set_result(response)
            else:
                self.responses[correlation_id] = response


class AsyncTestClient:
    """Cliente assíncrono para testes Kafka"""
    
    def __init__(self, bootstrap_servers: List[str], group_id: str = "test-client"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.producer = None
        self.consumer = None
        self.event_waiter = EventWaiter()
        self.running = False
        self.logger = self._setup_logging()
        self._consumer_task = None
    
    def _setup_logging(self) -> logging.Logger:
        """Configura o sistema de logging"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def setup(self, response_topics: List[str] = None):
        """Configura o cliente de teste"""
        if response_topics is None:
            response_topics = ['worker_result']
        
        # Configura produtor
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None
        )
        
        # Configura consumidor para respostas
        self.consumer = KafkaConsumer(
            *response_topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{self.group_id}-{int(time.time())}",  # Grupo único
            auto_offset_reset='latest',  # Apenas mensagens novas
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
            key_deserializer=lambda x: x.decode('utf-8') if x else None
        )
        
        self.logger.info(f"Cliente de teste configurado para tópicos de resposta: {response_topics}")
    
    async def start_consumer(self):
        """Inicia o consumidor de respostas em background"""
        if not self.consumer:
            raise RuntimeError("Consumidor não configurado. Chame setup() primeiro.")
        
        self.running = True
        self._consumer_task = asyncio.create_task(self._consume_responses())
        self.logger.info("Consumidor de respostas iniciado")
    
    async def stop_consumer(self):
        """Para o consumidor de respostas"""
        self.running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Consumidor de respostas parado")
    
    async def _consume_responses(self):
        """Consome respostas do Kafka"""
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                if message.value:
                    # Extrai correlation_id da resposta
                    correlation_id = None
                    if isinstance(message.value, dict):
                        metadata = message.value.get('metadata', {})
                        correlation_id = metadata.get('correlation_id')
                    
                    if correlation_id:
                        await self.event_waiter.set_response(correlation_id, message.value)
                        self.logger.debug(f"Resposta recebida para correlation_id: {correlation_id}")
                    else:
                        self.logger.warning("Resposta recebida sem correlation_id")
        
        except Exception as e:
            self.logger.error(f"Erro no consumidor de respostas: {e}")
    
    async def send_event_async(self, event: TestEvent) -> TestResult:
        """Envia um evento e aguarda a resposta"""
        if not self.producer:
            raise RuntimeError("Produtor não configurado. Chame setup() primeiro.")
        
        start_time = time.time()
        
        try:
            # Prepara o evento
            event_data = {
                "event": event.event,
                "response_topic": event.response_topic,
                "payload": event.payload,
                "metadata": {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0",
                    "source": "test-client",
                    "correlation_id": event.correlation_id
                },
                "status": "pending"
            }
            
            # Envia o evento
            future = self.producer.send(event.topic, value=event_data)
            record_metadata = future.get(timeout=10)
            
            self.logger.info(
                f"Evento enviado: {event.event} -> {event.topic} "
                f"(correlation_id: {event.correlation_id})"
            )
            
            # Aguarda a resposta
            response = await self.event_waiter.wait_for_response(
                event.correlation_id, 
                event.timeout
            )
            
            duration = time.time() - start_time
            
            if response:
                self.logger.info(f"Resposta recebida para {event.event} em {duration:.2f}s")
                return TestResult(
                    event=event,
                    success=True,
                    response=response,
                    duration=duration
                )
            else:
                self.logger.warning(f"Timeout aguardando resposta para {event.event}")
                return TestResult(
                    event=event,
                    success=False,
                    error="Timeout aguardando resposta",
                    duration=duration
                )
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Erro ao enviar evento {event.event}: {e}")
            return TestResult(
                event=event,
                success=False,
                error=str(e),
                duration=duration
            )
    
    async def send_multiple_events_async(self, events: List[TestEvent]) -> List[TestResult]:
        """Envia múltiplos eventos em paralelo e aguarda todas as respostas"""
        self.logger.info(f"Enviando {len(events)} eventos em paralelo...")
        
        tasks = [self.send_event_async(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(TestResult(
                    event=events[i],
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        # Estatísticas
        successful = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - successful
        avg_duration = sum(r.duration for r in processed_results) / len(processed_results)
        
        self.logger.info(
            f"Processamento concluído: {successful} sucessos, {failed} falhas, "
            f"tempo médio: {avg_duration:.2f}s"
        )
        
        return processed_results
    
    def create_test_event(self, topic: str, event: str, payload: Dict[str, Any], 
                         response_topic: str = "worker_result", timeout: int = 30) -> TestEvent:
        """Cria um evento de teste"""
        return TestEvent(
            topic=topic,
            event=event,
            payload=payload,
            response_topic=response_topic,
            timeout=timeout
        )
    
    async def close(self):
        """Fecha o cliente de teste"""
        await self.stop_consumer()
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
        self.logger.info("Cliente de teste fechado")


# Funções de conveniência para testes
async def test_single_event(client: AsyncTestClient, topic: str, event: str, 
                           payload: Dict[str, Any], timeout: int = 30) -> TestResult:
    """Testa um único evento"""
    event = client.create_test_event(topic, event, payload, timeout=timeout)
    return await client.send_event_async(event)


async def test_multiple_events(client: AsyncTestClient, events_data: List[Dict[str, Any]]) -> List[TestResult]:
    """Testa múltiplos eventos"""
    events = []
    for event_data in events_data:
        event = client.create_test_event(**event_data)
        events.append(event)
    
    return await client.send_multiple_events_async(events)


# Exemplo de uso
async def example_usage():
    """Exemplo de como usar o cliente de teste"""
    client = AsyncTestClient(['localhost:9092'])
    
    try:
        # Configura o cliente
        await client.setup(['worker_result'])
        await client.start_consumer()
        
        # Teste 1: Evento único
        print("🧪 Testando evento único...")
        result = await test_single_event(
            client=client,
            topic='worker_process',
            event='audio.separate',
            payload={
                'process_id': '12345',
                'process_type': 'separate',
                'audio_url': './assets/gto_ep1.mp4'
            }
        )
        
        if result.success:
            print(f"✅ Sucesso: {result.response}")
        else:
            print(f"❌ Falha: {result.error}")
        
        # Teste 2: Múltiplos eventos
        print("\n🧪 Testando múltiplos eventos...")
        events_data = [
            {
                'topic': 'worker_process',
                'event': 'audio.separate',
                'payload': {
                    'process_id': '12346',
                    'process_type': 'separate',
                    'audio_url': './assets/gto_ep1.mp4'
                }
            },
            {
                'topic': 'worker_process',
                'event': 'audio.separate',
                'payload': {
                    'process_id': '12347',
                    'process_type': 'separate',
                    'audio_url': './assets/gto_ep1.mp4'
                }
            }
        ]
        
        results = await test_multiple_events(client, events_data)
        
        for i, result in enumerate(results):
            if result.success:
                print(f"✅ Evento {i+1} sucesso: {result.duration:.2f}s")
            else:
                print(f"❌ Evento {i+1} falha: {result.error}")
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
