#!/usr/bin/env python3
"""
Dublar Worker - Serviço principal
Executa o worker Kafka e fica aguardando mensagens continuamente
"""

import signal
import sys
import time
from engines.worker import Worker


def signal_handler(signum, frame):
    """Handler para sinais de interrupção (Ctrl+C)"""
    print(f"\n🛑 Recebido sinal {signum}. Parando worker...")
    if hasattr(signal_handler, 'worker'):
        signal_handler.worker.stop()
    sys.exit(0)


def main():
    """Função principal que executa o worker como serviço"""
    print("🚀 Iniciando Dublar Worker...")
    
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
        worker.setup_consumer(['users', 'orders', 'payments', 'audio_processing'])
        
        # Configura o produtor (opcional, para enviar eventos de resposta)
        print("📤 Configurando produtor Kafka...")
        worker.setup_producer()
        
        # Registra handlers para diferentes tipos de eventos
        print("🔧 Registrando handlers de eventos...")
        
        @worker.route('user.created')
        def handle_user_created(event):
            """Handler para eventos de usuário criado"""
            print(f"🆕 Usuário criado: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            print(f"   Timestamp: {event.metadata.timestamp}")
            print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")
            
            # Simula processamento
            time.sleep(2)
            
            # Simula falha ocasional para testar retry
            import random
            if random.random() < 0.3:  # 30% de chance de falha
                print(f"❌ Simulando falha no processamento do usuário {event.payload.get('user_id', 'unknown')}")
                raise Exception(f"Simulando falha no processamento do usuário {event.payload.get('user_id', 'unknown')}")
            
            print(f"✅ Usuário processado com sucesso: {event.payload.get('user_id', 'unknown')}")
            return True
        
        @worker.route('order.processed')
        def handle_order_processed(event):
            """Handler para eventos de pedido processado"""
            print(f"📦 Pedido processado: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")
            
            # Simula processamento
            time.sleep(1)
            print(f"✅ Pedido processado com sucesso: {event.payload.get('order_id', 'unknown')}")
            return True
        
        @worker.route('payment.received')
        def handle_payment_received(event):
            """Handler para eventos de pagamento recebido"""
            print(f"💰 Pagamento recebido: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")
            
            # Simula processamento
            time.sleep(1.5)
            print(f"✅ Pagamento processado com sucesso: {event.payload.get('payment_id', 'unknown')}")
            return True
        
        @worker.route('audio.uploaded')
        def handle_audio_uploaded(event):
            """Handler para eventos de áudio enviado"""
            print(f"🎵 Áudio enviado: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")
            
            # Simula processamento de áudio
            time.sleep(3)
            print(f"✅ Áudio processado com sucesso: {event.payload.get('audio_id', 'unknown')}")
            return True
        
        @worker.route('user.updated')
        def handle_user_updated(event):
            """Handler para eventos de usuário atualizado"""
            print(f"🔄 Usuário atualizado: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            print(f"   Timestamp: {event.metadata.timestamp}")
            print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")
            
            # Simula processamento
            time.sleep(1)
            print(f"✅ Usuário atualizado com sucesso: {event.payload.get('user_id', 'unknown')}")
            return True
        
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
            if not event.payload:
                print(f"❌ Payload vazio para evento {event.event_type}")
                return None
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
        print("📋 Tópicos configurados: users, orders, payments, audio_processing")
        print("🔧 Handlers registrados: user.created, order.processed, payment.received, audio.uploaded, user.updated")
        print("🔒 Modo de execução: SEQUENCIAL (apenas uma task por vez)")
        print("🔄 Sistema de retry: Ativado (máximo 3 tentativas com backoff exponencial)")
        print("📤 Sistema de rollback: Ativado (eventos com erro retornam para a fila)")
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