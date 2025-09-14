import json
import time
import uuid
import asyncio
import logging
import threading
from enum import Enum
from datetime import datetime
from kafka.errors import KafkaError
from dataclasses import dataclass, field
from kafka import KafkaConsumer, KafkaProducer
from errors import BadRequestError, InternalError
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Tuple, Optional, Union, Callable

DEFAULT_MAX_DELAY = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5
DEFAULT_SOURCE = "dublar-worker"
DEFAULT_VERSION = "1.0"

class EventStatus(Enum):
    """Status dos eventos"""
    FAILED = "failed"
    PENDING = "pending"
    RETRYING = "retrying"
    COMPLETED = "completed"
    PROCESSING = "processing"


@dataclass
class EventTrigger:
    """Trigger do evento"""
    topic: str
    event: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte o trigger para dicionário"""
        return {
            "topic": self.topic,
            "event": self.event
        }


@dataclass
class EventRetry:
    """Tentativa de retry"""
    current: int = 0
    max: int = DEFAULT_MAX_RETRIES

    def to_dict(self) -> Dict[str, Any]:
        """Converte o retry para dicionário"""
        return {
            "current": self.current,
            "max": self.max
        }


@dataclass
class EventMetadata:
    """Metadados do evento"""
    version: str = DEFAULT_VERSION
    source: str = DEFAULT_SOURCE
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte os metadados para dicionário"""
        return {
            "version": self.version,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id
        }



@dataclass
class WorkerEvent:
    """Representa um evento Kafka com estrutura melhorada"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    event: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    retry: EventRetry = field(default_factory=EventRetry)
    triggers: List[EventTrigger] = field(default_factory=list)
    metadata: EventMetadata = field(default_factory=EventMetadata)
    status: EventStatus = EventStatus.PENDING
    response: Optional['WorkerEvent'] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte o evento para dicionário"""
        return {
            "id": self.id,
            "topic": self.topic,
            "event": self.event,
            "payload": self.payload,
            "retry": self.retry.to_dict(),
            "triggers": [trigger.to_dict() for trigger in self.triggers],
            "metadata": self.metadata.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], topic: str) -> 'WorkerEvent':
        """Cria um evento a partir de um dicionário"""
        metadata_data = data.get('metadata', {})
        
        # Trata timestamp com diferentes formatos
        timestamp_str = metadata_data.get('timestamp', datetime.utcnow().isoformat())
        try:
            # Tenta parse com Z no final (formato ISO com timezone)
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Fallback para timestamp atual se não conseguir fazer parse
            timestamp = datetime.utcnow()
        
        metadata = EventMetadata(
            version=metadata_data.get('version', DEFAULT_VERSION),
            source=metadata_data.get('source', DEFAULT_SOURCE),
            timestamp=timestamp,
            parent_id=metadata_data.get('parent_id'),
        )

        # Processa triggers
        triggers_data = data.get('triggers', [])
        triggers = []
        for trigger_data in triggers_data:
            if isinstance(trigger_data, dict):
                triggers.append(EventTrigger(
                    topic=trigger_data.get('topic', ''),
                    event=trigger_data.get('event', '')
                ))

        return cls(
            id=data.get('id', str(uuid.uuid4())),
            topic=data.get('topic', topic),
            event=data.get('event', 'unknown'),
            payload=data.get('payload', {}),
            retry=EventRetry(
                current=data.get('retry', {}).get('current', 0), 
                max=data.get('retry', {}).get('max', DEFAULT_MAX_RETRIES)
            ),
            triggers=triggers,
            metadata=metadata,
            status=EventStatus(data.get('status', 'pending')),
        )


class EventRouter:
    """Roteador inteligente de eventos"""

    def __init__(self):
        self.routes = {}
        self.middleware = []

    def add_route(self, event: str, handler: Callable, topic: Optional[str] = None):
        key = f"{event}:{topic}" if topic else event
        self.routes[key] = handler
        return handler

    def route(self, event: str, topic: Optional[str] = None):
        """Decorator para rotear eventos"""
        def decorator(handler):
            key = f"{event}:{topic}" if topic else event
            self.routes[key] = handler
            return handler
        return decorator

    def add_middleware(self, middleware_func):
        """Adiciona middleware para processamento"""
        self.middleware.append(middleware_func)
        return middleware_func

    def get_handler(self, event: str, topic: str):
        """Obtém o handler apropriado para o evento"""
        # Tenta encontrar handler específico para topic + event
        specific_key = f"{event}:{topic}"
        if specific_key in self.routes:
            return self.routes[specific_key]

        # Fallback para handler genérico do event
        if event in self.routes:
            return self.routes[event]

        return None


class Worker:
    def __init__(self, bootstrap_servers: List[str], deps: Dict[str, Any] = None, group_id: str = "dublar-worker-group"):
        """
        Inicializa o worker Kafka

        Args:
            bootstrap_servers: Lista de servidores Kafka (ex: ['localhost:9092'])
            group_id: ID do grupo de consumidores
        """
        self.id = str(uuid.uuid4())
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = None
        self.producer = None
        self.running = False
        self.event_router = EventRouter()
        self.logger = self._setup_logging()
        self.stats = {
            'events_processed': 0,
            'events_failed': 0,
            'events_retried': 0
        }
        self.consumer_routes = []
        # Controle de execução sequencial
        self._processing_lock = threading.Lock()
        self._current_event = None
        self._retry_queue = []
        self._max_retries = DEFAULT_MAX_RETRIES
        self._retry_delay = DEFAULT_RETRY_DELAY  # segundos

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

    def setup_consumer(self, topics: List[str]):
        """
        Configura o consumidor Kafka

        Args:
            topics: Lista de tópicos para consumir
        """
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                key_deserializer=lambda x: x.decode('utf-8') if x else None
            )
            self.logger.info(f"Consumidor configurado para os tópicos: {topics}")
        except Exception as e:
            self.logger.error(f"Erro ao configurar consumidor: {e}")
            raise

    def setup_producer(self):
        """Configura o produtor Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None
            )
            self.logger.info("Produtor configurado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao configurar produtor: {e}")
            raise

    def add_route(self, event: str, handler: Callable, topic: Optional[str] = None, ):
        self.consumer_routes.append(event)
        return self.event_router.add_route(event, handler, topic)

    def route(self, event: str, topic: Optional[str] = None):
        """Decorator para rotear eventos (alias para event_router.route)"""
        return self.event_router.route(event, topic)

    def add_middleware(self, middleware_func):
        """Adiciona middleware para processamento"""
        return self.event_router.add_middleware(middleware_func)

    def _should_retry(self, event: WorkerEvent) -> bool:
        """Verifica se o evento deve ser reprocessado"""
        return event.retry.current < event.retry.max

    def _calculate_retry_delay(self, retry_count: int) -> int:
        """Calcula o delay para retry com backoff exponencial"""
        return min(self._retry_delay * (2 ** retry_count), DEFAULT_MAX_DELAY)  # máximo 5 minutos

    def _add_to_retry_queue(self, event: WorkerEvent):
        """Adiciona evento à fila de retry"""
        if self._should_retry(event):
            event.retry.current += 1
            delay = self._calculate_retry_delay(event.retry.current)
            event.status = EventStatus.RETRYING

            self.logger.warning(
                f"Evento {event.event} (ID: {event.id}) "
                f"adicionado à fila de retry. Tentativa {event.retry.current}/{event.retry.max}. "
                f"Próximo retry em {delay}s"
            )

            # Agenda o retry
            threading.Timer(delay, self._retry_event, args=[event]).start()
            self.stats['events_retried'] += 1
        else:
            self.logger.error(
                f"Evento {event.event} (ID: {event.id}) "
                f"excedeu o número máximo de tentativas ({event.retry.max}). "
                f"Enviando para tópico de erro."
            )
            self._send_to_error_topic(event)

    async def _retry_event(self, event: WorkerEvent):
        """Reprocessa um evento da fila de retry"""
        self.logger.info(f"Reprocessando evento {event.event} (ID: {event.id})")
        await self._process_event_safely(event)

    def _send_to_error_topic(self, event: WorkerEvent):
        """Envia evento com erro para tópico de erro"""
        try:
            if self.producer:
                error_topic = f"{event.topic}.error"
                error_event = event.to_dict()
                error_event['error_info'] = {
                    'failed_at': datetime.utcnow().isoformat(),
                    'current': event.retry.current,
                    'max_retries': event.retry.max
                }

                future = self.producer.send(error_topic, value=error_event)
                future.get(timeout=10)

                self.logger.info(f"Evento enviado para tópico de erro: {error_topic}")
        except Exception as e:
            self.logger.error(f"Erro ao enviar evento para tópico de erro: {e}")

    def _rollback_to_kafka(self, event: WorkerEvent):
        """Faz rollback do evento para a fila original do Kafka"""
        try:
            if self.producer:
                # Reenvia o evento para o tópico original
                message_data = event.to_dict()
                future = self.producer.send(event.topic, value=message_data)
                future.get(timeout=10)

                self.logger.info(
                    f"Rollback realizado: evento {event.event} (ID: {event.id}) "
                    f"reenviado para tópico {event.topic}"
                )
        except Exception as e:
            self.logger.error(f"Erro ao fazer rollback do evento: {e}")

    async def _process_event_safely(self, event: WorkerEvent) -> dict:
        """Processa um evento de forma segura com controle de concorrência"""
        with self._processing_lock:
            if self._current_event is not None:
                self.logger.warning(
                    f"Evento {event.event} (ID: {event.id}) "
                    f"aguardando processamento. Evento atual: {self._current_event.event}"
                )
                return {
                    'data': None,
                    'error': {
                        'cause': "concurrent_processing",
                        'handler': event.event,
                    }
                }

            self._current_event = event

            try:
                return await self.process_event(event)
            finally:
                self._current_event = None

    async def process_event(self, event: WorkerEvent):
        """
        Processa um evento Kafka com middleware

        Args:
            event: Evento Kafka a ser processado

        Returns:
            dict: Resultado do processamento
        """
        try:
            # Aplica middleware antes do processamento
            for middleware in self.event_router.middleware:
                event = middleware(event)

            # Obtém o handler apropriado
            handler = self.event_router.get_handler(event.event, event.topic)

            if handler:
                event.status = EventStatus.PROCESSING
                self.logger.info(f"Processando evento {event.event} do tópico {event.topic} (ID: {event.id})")

                # Verifica se o handler é assíncrono
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(self, event)
                else:
                    result = handler(self, event)

                event.status = EventStatus.COMPLETED
                self.stats['events_processed'] += 1
                self.logger.info(f"Evento {event.event} (ID: {event.id}) processado com sucesso")

                return {
                    'data': result,
                    'error': None
                }
            else:
                self.logger.warning(f"Nenhum handler encontrado para evento: {event.event}")
                # Para eventos sem handler, faz rollback imediatamente
                self._rollback_to_kafka(event)
                return {
                    'data': None,
                    'error': {
                        'cause': "not_found",
                        'handler': event.event,
                    }
                }

        except BadRequestError as e:
            self.logger.error(f"Erro ao processar evento {event.event} (ID: {event.id}): {e}")
            return {
                'data': None,
                'error': {
                    'cause': e.cause,
                    'handler': event.event,
                }
            }

        except Exception as e:
            event.status = EventStatus.FAILED
            self.stats['events_failed'] += 1
            self.logger.error(f"Erro ao processar evento {event.event} (ID: {event.id}): {e}")

            # Em caso de exceção, tenta retry ou rollback
            if self._should_retry(event):
                self._add_to_retry_queue(event)
            else:
                self._rollback_to_kafka(event)

            return {
                'data': None,
                'error': {
                    'cause': "exception",
                    'handler': event.event,
                }
            }

    def parse_kafka_message(self, message) -> Optional[WorkerEvent]:
        """
        Converte uma mensagem Kafka em um objeto WorkerEvent

        Args:
            message: Mensagem recebida do Kafka

        Returns:
            WorkerEvent ou None se não conseguir fazer o parse
        """
        try:
            if message.value:
                # Formato esperado: {"event": "...", "payload": {...}, "metadata": {...}}
                if isinstance(message.value, dict) and 'event' in message.value:
                    return WorkerEvent.from_dict(message.value, message.topic)

                # Fallback para formato legado
                elif isinstance(message.value, dict) and 'event' in message.value:
                    # Converte formato antigo para novo
                    legacy_data = {
                        'event': message.value['event'],
                        'payload': message.value.get('payload', {}),
                        'metadata': {
                            'id': str(uuid.uuid4()),
                            'timestamp': datetime.utcnow().isoformat(),
                            'version': DEFAULT_VERSION,
                            'source': DEFAULT_SOURCE
                        }
                    }
                    return WorkerEvent.from_dict(legacy_data, message.topic)

                # Fallback: assume que a mensagem é o payload
                else:
                    fallback_data = {
                        'event': message.topic,
                        'payload': message.value if isinstance(message.value, dict) else {'data': message.value},
                        'metadata': {
                            'id': str(uuid.uuid4()),
                            'timestamp': datetime.utcnow().isoformat(),
                            'version': DEFAULT_VERSION,
                            'source': DEFAULT_SOURCE
                        }
                    }
                    return WorkerEvent.from_dict(fallback_data, message.topic)

            return None

        except Exception as e:
            self.logger.error(f"Erro ao fazer parse da mensagem: {e}")
            return None

    async def run(self):
      """Executa o worker principal"""
      if not self.consumer:
        raise RuntimeError("Consumidor não configurado. Chame setup_consumer() primeiro.")

      self.running = True
      self.logger.info("Worker iniciado. Aguardando mensagens...")
      self.logger.info("🔒 Modo de execução sequencial ativado - apenas uma task por vez")

      try:
        for message in self.consumer:
          if not self.running:
            break

          # Converte a mensagem Kafka em um evento
          event = self.parse_kafka_message(message)

          print(f"Evento recebido: {event}")
          if not event:
            self.logger.warning(f"Não foi possível fazer parse da mensagem do tópico {message.topic}")
            continue
            
          if event.event not in self.consumer_routes:
            self._rollback_to_kafka(event)
            continue

          self.logger.debug(f"Mensagem recebida do tópico {message.topic} -> {event.event}")
          # Processa o evento de forma segura (sequencial)
          result = await self._process_event_safely(event)
          if result['error']:
            self.logger.warning(f"Falha ao processar evento: {event.event} - {result['error']['cause']}")
            continue
          elif result['data']:
            if event.response:
              print(event.response)
              self.send_event(event.response.topic or "worker_result", event.response.event or event.event, result['data'])
            else:
              # Se não há response definido, envia para tópico padrão
              self.send_event("worker_result", event.event, result['data'])
          
          self.logger.debug(f"Evento processado com sucesso: {event.event}")

      except KeyboardInterrupt:
        self.logger.info("Interrupção recebida. Parando worker...")
      except Exception as e:
        self.logger.error(f"Erro durante execução do worker: {e}")
      finally:
        self.stop()

    def run_async(self):
        """Executa o worker em uma thread separada"""
        worker_thread = threading.Thread(target=self.run, daemon=True)
        worker_thread.start()
        return worker_thread

    def stop(self):
        """Para o worker"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        self.logger.info("Worker parado")

    def send_event(self, topic: str, event: str, payload: Dict[str, Any],
                   key: Optional[str] = None, correlation_id: Optional[str] = None,
                   triggers: Optional[List[EventTrigger]] = None,
                   source: str = DEFAULT_SOURCE) -> str:
        """
        Envia um evento para um tópico Kafka

        Args:
            topic: Tópico de destino
            event: Tipo do evento
            payload: Dados do evento
            key: Chave da mensagem (opcional)
            correlation_id: ID de correlação (opcional)
            source: Origem do evento

        Returns:
            str: ID do evento enviado
        """
        if not self.producer:
            raise RuntimeError("Produtor não configurado. Chame setup_producer() primeiro.")

        try:
            # Cria o evento com metadados
            worker_event = WorkerEvent(
                topic=topic,
                payload=payload,
                event=event,
                triggers=[EventTrigger(topic=topic, event=event)],
                metadata=EventMetadata(
                    parent_id=correlation_id,
                    source=source,
                )
            )

            message_data = worker_event.to_dict()

            future = self.producer.send(topic, value=message_data, key=key)
            record_metadata = future.get(timeout=10)

            self.logger.info(
                f"Evento enviado: {event} -> {topic} "
                f"(ID: {worker_event.id}, "
                f"partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )

            return worker_event.id

        except Exception as e:
            self.logger.error(f"Erro ao enviar evento {event} para {topic}: {e}")
            raise

    def configure_retry(self, max_retries: int = 3, retry_delay: int = 5):
        """
        Configura parâmetros de retry

        Args:
            max_retries: Número máximo de tentativas
            retry_delay: Delay inicial entre tentativas (em segundos)
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.logger.info(f"Configuração de retry atualizada: max_retries={max_retries}, retry_delay={retry_delay}s")

    def get_current_event(self) -> Optional[WorkerEvent]:
        """Retorna o evento atualmente sendo processado"""
        return self._current_event

    def is_processing(self) -> bool:
        """Verifica se há um evento sendo processado no momento"""
        return self._current_event is not None

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do worker"""
        return {
            **self.stats,
            'running': self.running,
            'group_id': self.group_id,
            'bootstrap_servers': self.bootstrap_servers,
            'is_processing': self.is_processing(),
            'current_event': self._current_event.event if self._current_event else None,
            'retry_config': {
                'max_retries': self._max_retries,
                'retry_delay': self._retry_delay
            }
        }

    async def wait_for_response(self, id: str):
        """Aguarda a resposta de um evento"""
        print(f"Aguardando resposta para evento {id}")
        while True:
            event = self.get_current_event()
            print(f"Evento atual: {event}")
            if event and event.id == id:
                print(f"Evento {id} encontrado: {event.id}")
                return event
            await asyncio.sleep(1)