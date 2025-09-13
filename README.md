# Dublar Worker - Sistema de Processamento de Eventos Kafka

Um worker robusto e flexível para processar eventos Kafka com suporte a roteamento inteligente, middleware e metadados avançados.

## 🚀 Características

- **Formato de Eventos Padronizado**: Estrutura consistente com metadados ricos
- **Roteamento Inteligente**: Suporte a handlers específicos por tópico + evento
- **Sistema de Middleware**: Processamento em pipeline antes dos handlers
- **Metadados Avançados**: IDs únicos, timestamps, correlação, retry logic
- **Compatibilidade**: Suporte a formatos legados com fallback automático
- **Estatísticas**: Monitoramento de eventos processados, falhas e retries
- **Logging Robusto**: Sistema de logs estruturado e configurável

## 📦 Instalação

```bash
pip install -r requirements.txt
```

## 🔧 Uso Básico

### 1. Configuração do Worker

```python
from engines.worker import Worker

# Cria o worker
worker = Worker(
    bootstrap_servers=['localhost:9092'],
    group_id='meu-worker-group'
)

# Configura consumidor e produtor
worker.setup_consumer(['users', 'orders'])
worker.setup_producer()
```

### 2. Registrando Handlers com Decorators

```python
# Handler genérico para todos os tópicos
@worker.route('user.created')
def handle_user_created(event):
    print(f"Usuário criado: {event.payload}")
    return True

# Handler específico para um tópico
@worker.route('user.updated', 'users')
def handle_user_updated_specific(event):
    print(f"Usuário atualizado no tópico users: {event.payload}")
    return True
```

### 3. Adicionando Middleware

```python
# Middleware para logging
@worker.add_middleware
def logging_middleware(event):
    print(f"Processando: {event.event}")
    return event

# Middleware para validação
@worker.add_middleware
def validation_middleware(event):
    if not event.payload:
        return None  # Rejeita o evento
    return event
```

### 4. Executando o Worker

```python
# Execução assíncrona
worker_thread = worker.run_async()

# Ou execução síncrona
worker.run()
```

## 📋 Formato dos Eventos

### Formato Novo (Recomendado)

```json
{
  "event": "user.created",
  "payload": {
    "user_id": "12345",
    "email": "user@example.com",
    "name": "João Silva"
  },
  "metadata": {
    "event_id": "uuid-gerado-automaticamente",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0",
    "source": "dublar-worker",
    "correlation_id": "session-123",
    "retry_count": 0,
    "max_retries": 3
  },
  "status": "pending"
}
```

### Formato Legado (Suportado)

```json
{
  "event": "user.created",
  "payload": {
    "user_id": "12345",
    "email": "user@example.com"
  }
}
```

## 🔄 Enviando Eventos

```python
# Envio básico
event_id = worker.send_event(
    topic='users',
    event='user.created',
    payload={'user_id': '12345'}
)

# Envio com metadados avançados
event_id = worker.send_event(
    topic='users',
    event='user.updated',
    payload={'user_id': '12345', 'name': 'João'},
    correlation_id='session-456',
    source='user-service'
)
```

## 📊 Monitoramento

```python
# Obtém estatísticas do worker
stats = worker.get_stats()
print(f"Eventos processados: {stats['events_processed']}")
print(f"Eventos falharam: {stats['events_failed']}")
print(f"Worker rodando: {stats['running']}")
```

## 🏗️ Estrutura do Projeto

```
dublar-worker/
├── engines/
│   └── worker.py          # Classe principal do Worker
├── example_usage.py       # Exemplo de uso
├── requirements.txt       # Dependências
└── README.md             # Este arquivo
```

## 🔍 Exemplo Completo

Veja o arquivo `example_usage.py` para um exemplo completo de implementação.

## 🚨 Tratamento de Erros

O worker inclui tratamento robusto de erros:

- **Retry Logic**: Configurável via metadados
- **Fallback de Formatos**: Suporte a formatos legados
- **Logging Estruturado**: Rastreamento completo de eventos
- **Graceful Shutdown**: Parada segura do worker

## 🔧 Configuração Avançada

### Configurações do Kafka

```python
worker = Worker(
    bootstrap_servers=['kafka1:9092', 'kafka2:9092'],
    group_id='worker-prod-001'
)
```

### Middleware Customizado

```python
@worker.add_middleware
def custom_middleware(event):
    # Lógica customizada
    if event.metadata.retry_count > event.metadata.max_retries:
        event.status = EventStatus.FAILED
        return None
    return event
```

## 📝 Logs

O worker gera logs estruturados para:

- Configuração de conexões
- Processamento de eventos
- Erros e falhas
- Estatísticas de performance

## 🤝 Contribuição

Para contribuir com o projeto:

1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente as mudanças
4. Adicione testes
5. Submeta um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.