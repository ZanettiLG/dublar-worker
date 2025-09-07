#!/usr/bin/env python3
"""
Dublar Worker - Serviço principal
Executa o worker Kafka e fica aguardando mensagens continuamente
"""

import signal
import sys
import time
from engines.worker import Worker
import routes
from errors.badrequest_error import BadRequestError
from errors.internal_error import InternalError

def signal_handler(signum, frame):
    """Handler para sinais de interrupção (Ctrl+C)"""
    print(f"\n🛑 Recebido sinal {signum}. Parando worker...")
    if hasattr(signal_handler, 'worker'):
        signal_handler.worker.stop()
    sys.exit(0)


def main():
    """Função principal que executa o worker como serviço"""
    print("🚀 Iniciando Dublar Worker...")

    consumer_topics = ['worker_process']
    consumer_routes = [route[0] for route in routes.routes]
        
    # Configura o worker
    worker = Worker(
        bootstrap_servers=['localhost:9092'],
        group_id='dublar-worker-prod'
    )
    
    # Configura parâmetros de retry
    worker.configure_retry(max_retries=3, retry_delay=5)
    
    try:
        # Configura o consumidor para os tópicos de interesse
        print("📡 Configurando consumidor Kafka...")
        worker.setup_consumer(consumer_topics)
        
        # Configura o produtor (opcional, para enviar eventos de resposta)
        print("📤 Configurando produtor Kafka...")
        worker.setup_producer()
        
        # Registra handlers para diferentes tipos de eventos
        print("🔧 Registrando handlers de eventos...")
        
        for route in routes.routes:
            print(f"🔧 Registrando handler para {route[1]} no tópico {route[0]}")
            worker.add_route(route[0], route[1])

        # Middleware para logging
        @worker.add_middleware
        def logging_middleware(event):
            """Middleware para logging de eventos"""
            print(f"🔍 Processando evento {event.event_type} (ID: {event.metadata.event_id})")
            return event
        
        # Middleware para validação
        @worker.add_middleware
        def validation_middleware(event):
            """Middleware para validação básica"""
            if event.event_type not in consumer_routes:
                raise InternalError(event, "not_found", "event_type", event.event_type, 400, f"❌ Evento {event.event_type} não registrado")
            if not event.payload:
                raise BadRequestError(event, "is_empty", "payload", event.payload, 400, f"❌ Payload vazio para evento {event.event_type}")
            return event
        
        # Middleware para monitoramento de processamento
        @worker.add_middleware
        def processing_monitor_middleware(event):
            """Middleware para monitorar o processamento"""
            if worker.is_processing():
                current = worker.get_current_event()
                if current:
                    print(f"⚠️  Aguardando conclusão do evento atual: {current.event_type} (ID: {current.metadata.event_id})")
            return event
        
        # Configura handler de sinais para parada graciosa
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        signal_handler.worker = worker
        
        print("✅ Worker configurado com sucesso!")
        print(f"📋 Tópicos configurados: {consumer_topics}")
        print(f"🔧 Handlers registrados: {consumer_routes}")
        print("🔄 Iniciando processamento de eventos...")
        print("💡 Pressione Ctrl+C para parar o worker\n")
        
        # Executa o worker (fica aguardando mensagens continuamente)
        worker.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupção recebida. Parando worker...")
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
    finally:
        print("🔄 Parando worker...")
        worker.stop()
        print("✅ Worker parado com sucesso!")


if __name__ == "__main__":
    main()