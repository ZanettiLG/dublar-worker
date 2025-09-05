# 🚀 Instruções para Testar o Dublar Worker

## 📋 Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.11+ com ambiente virtual ativo
- Dependências instaladas (`uv pip install -r requirements.txt`)

## 🐳 Passo 1: Iniciar os Serviços

```bash
# Inicia todos os serviços (Kafka, PostgreSQL, MinIO, Redis)
docker-compose up -d

# Verifica se todos os serviços estão rodando
docker-compose ps
```

**Portas utilizadas:**
- **Kafka**: `localhost:9092`
- **Kafka UI**: `http://localhost:8080`
- **PostgreSQL**: `localhost:5432`
- **MinIO**: `localhost:9000` (API), `localhost:9001` (Console)
- **Redis**: `localhost:6379`

## 🔧 Passo 2: Iniciar o Worker

Em um terminal, execute o worker principal:

```bash
# Ativa o ambiente virtual (se necessário)
.venv\Scripts\activate

# Executa o worker (fica aguardando mensagens)
python __main__.py
```

Você deve ver:
```
🚀 Iniciando Dublar Worker...
📡 Configurando consumidor Kafka...
📤 Configurando produtor Kafka...
🔧 Registrando handlers de eventos...
✅ Worker configurado com sucesso!
📋 Tópicos configurados: users, orders, payments, audio_processing
🔧 Handlers registrados: user.created, order.processed, payment.received, audio.uploaded
🔄 Iniciando processamento de eventos...
💡 Pressione Ctrl+C para parar o worker
```

## 📤 Passo 3: Enviar Eventos de Teste

Em outro terminal, execute o produtor de teste:

```bash
# Ativa o ambiente virtual
.venv\Scripts\activate

# Envia eventos de teste
python test_producer.py
```

## 📊 Passo 4: Monitorar o Sistema

### Kafka UI
Acesse `http://localhost:8080` para visualizar:
- Tópicos criados
- Mensagens enviadas
- Consumidores ativos

### Logs do Worker
No terminal do worker, você verá:
```
🔍 Processando evento user.created (ID: uuid-123)
🆕 Usuário criado: {'user_id': '12345', 'email': 'usuario@exemplo.com', ...}
   Event ID: uuid-123
   Timestamp: 2024-01-15T10:30:00Z
```

## 🧪 Testando Funcionalidades

### 1. **Envio de Evento Único**
```python
from test_producer import send_single_event

# Envia um evento específico
send_single_event(
    topic='users',
    event_type='user.created',
    payload={'user_id': '999', 'name': 'Test User'}
)
```

### 2. **Verificar Estatísticas**
No worker, você pode acessar estatísticas:
```python
stats = worker.get_stats()
print(f"Eventos processados: {stats['events_processed']}")
print(f"Eventos falharam: {stats['events_failed']}")
```

### 3. **Adicionar Novos Handlers**
Edite `__main__.py` para adicionar novos tipos de eventos:
```python
@worker.route('custom.event')
def handle_custom_event(event):
    print(f"Evento customizado: {event.payload}")
    return True
```

## 🛑 Parando o Sistema

### Parar o Worker
```bash
# No terminal do worker, pressione Ctrl+C
```

### Parar os Serviços
```bash
# Para todos os serviços
docker-compose down

# Para remover volumes (dados)
docker-compose down -v
```

## 🔍 Troubleshooting

### Problema: Worker não conecta ao Kafka
```bash
# Verifica se Kafka está rodando
docker-compose ps kafka

# Verifica logs do Kafka
docker-compose logs kafka
```

### Problema: Eventos não são processados
1. Verifique se o worker está rodando
2. Verifique se os tópicos existem no Kafka UI
3. Verifique se os handlers estão registrados corretamente

### Problema: Erro de conexão
```bash
# Reinicia os serviços
docker-compose restart

# Verifica se as portas estão disponíveis
netstat -an | findstr :9092
```

## 📁 Estrutura de Arquivos

```
dublar-worker/
├── __main__.py              # Worker principal (serviço)
├── test_producer.py         # Produtor de eventos de teste
├── engines/
│   └── worker.py           # Classe Worker
├── docker-compose.yml       # Serviços Docker
├── requirements.txt         # Dependências Python
└── INSTRUCTIONS.md         # Este arquivo
```

## 🎯 Próximos Passos

1. **Implementar Lógica de Negócio**: Adicione sua lógica específica nos handlers
2. **Configurar Banco de Dados**: Conecte ao PostgreSQL para persistir dados
3. **Configurar MinIO**: Use para armazenar arquivos de áudio
4. **Adicionar Monitoramento**: Métricas, alertas e dashboards
5. **Implementar Retry Logic**: Para eventos que falham
6. **Adicionar Testes**: Testes unitários e de integração

## 💡 Dicas

- **Mantenha o worker rodando** em um terminal separado
- **Use o Kafka UI** para debugar mensagens
- **Monitore os logs** para identificar problemas
- **Teste com poucos eventos** antes de enviar muitos
- **Use correlation IDs** para rastrear fluxos de eventos
