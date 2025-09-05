#!/usr/bin/env python3
"""
Exemplo de uso do Worker Kafka com novo formato
"""

from engines.worker import Worker
import time
import json


# Middleware para logging
def logging_middleware(event):
    """Middleware para logging de eventos"""
    print(f"🔍 Middleware: Processando evento {event.event_type} (ID: {event.metadata.event_id})")
    return event


# Middleware para validação
def validation_middleware(event):
    """Middleware para validação básica"""
    if not event.payload:
        print(f"❌ Middleware: Payload vazio para evento {event.event_type}")
        return None
    return event


def main():
    """Função principal de exemplo"""
    
    # Configura o worker
    worker = Worker(
        bootstrap_servers=['localhost:9092'],  # Ajuste para seus servidores Kafka
        group_id='dublar-worker-example'
    )
    
    try:
        # Configura o consumidor para os tópicos de interesse
        worker.setup_consumer(['users', 'orders', 'payments'])
        
        # Configura o produtor (opcional, para enviar eventos de resposta)
        worker.setup_producer()
        
        # Adiciona middleware
        worker.add_middleware(logging_middleware)
        worker.add_middleware(validation_middleware)
        
        # Registra os handlers usando decorators
        @worker.route('user.created')
        def handle_user_created(event):
            """Handler para eventos de usuário criado"""
            print(f"🆕 Usuário criado: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            print(f"   Timestamp: {event.metadata.timestamp}")
            # Aqui você pode implementar a lógica de negócio
            return True
        
        @worker.route('order.processed')
        def handle_order_processed(event):
            """Handler para eventos de pedido processado"""
            print(f"📦 Pedido processado: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            # Aqui você pode implementar a lógica de negócio
            return True
        
        @worker.route('payment.received')
        def handle_payment_received(event):
            """Handler para eventos de pagamento recebido"""
            print(f"💰 Pagamento recebido: {event.payload}")
            print(f"   Event ID: {event.metadata.event_id}")
            # Aqui você pode implementar a lógica de negócio
            return True
        
        # Handler específico para um tópico + evento
        @worker.route('user.updated', 'users')
        def handle_user_updated_specific(event):
            """Handler específico para atualizações de usuário no tópico 'users'"""
            print(f"🔄 Usuário atualizado (específico): {event.payload}")
            return True
        
        # Executa o worker de forma assíncrona
        print("🚀 Iniciando worker...")
        worker_thread = worker.run_async()
        
        # Simula o envio de alguns eventos para teste
        print("📤 Enviando eventos de teste...")
        time.sleep(2)  # Aguarda o worker inicializar
        
        # Envia eventos de teste com o novo formato
        test_events = [
            ('users', 'user.created', {
                'user_id': '12345',
                'email': 'usuario@exemplo.com',
                'name': 'João Silva'
            }),
            ('orders', 'order.processed', {
                'order_id': 'ORD-001',
                'user_id': '12345',
                'total': 99.99,
                'items': ['Produto A', 'Produto B']
            }),
            ('payments', 'payment.received', {
                'payment_id': 'PAY-001',
                'order_id': 'ORD-001',
                'amount': 99.99,
                'method': 'credit_card'
            }),
            ('users', 'user.updated', {
                'user_id': '12345',
                'email': 'joao.silva@exemplo.com',
                'name': 'João Silva Santos'
            })
        ]
        
        event_ids = []
        for topic, event_type, payload in test_events:
            event_id = worker.send_event(
                topic=topic, 
                event_type=event_type, 
                payload=payload,
                correlation_id='test-session-001'
            )
            event_ids.append(event_id)
            time.sleep(1)
        
        # Aguarda um pouco para processar os eventos
        print("⏳ Aguardando processamento dos eventos...")
        time.sleep(5)
        
        # Mostra estatísticas
        stats = worker.get_stats()
        print(f"📊 Estatísticas: {stats}")
        
        # Para o worker
        print("🛑 Parando worker...")
        worker.stop()
        
        # Aguarda a thread terminar
        worker_thread.join(timeout=5)
        
        print("✅ Worker parado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        worker.stop()


if __name__ == "__main__":
    main()
