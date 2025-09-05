#!/usr/bin/env python3
"""
Teste simples do Worker sem conexão Kafka
"""

from engines.worker import Worker, KafkaEvent, EventMetadata, EventStatus
import json


def test_worker_creation():
    """Testa a criação do worker"""
    print("🧪 Testando criação do worker...")
    
    try:
        worker = Worker(
            bootstrap_servers=['localhost:9092'],
            group_id='test-worker'
        )
        print("✅ Worker criado com sucesso!")
        return worker
    except Exception as e:
        print(f"❌ Erro ao criar worker: {e}")
        return None


def test_event_creation():
    """Testa a criação de eventos"""
    print("\n🧪 Testando criação de eventos...")
    
    try:
        # Cria um evento
        event = KafkaEvent(
            topic='test-topic',
            event_type='test.event',
            payload={'test': 'data'},
            metadata=EventMetadata(
                correlation_id='test-123',
                source='test-script'
            )
        )
        
        print(f"✅ Evento criado: {event.event_type}")
        print(f"   ID: {event.metadata.event_id}")
        print(f"   Timestamp: {event.metadata.timestamp}")
        print(f"   Status: {event.status}")
        
        # Testa conversão para dicionário
        event_dict = event.to_dict()
        print(f"   Evento como dict: {json.dumps(event_dict, indent=2)}")
        
        return event
    except Exception as e:
        print(f"❌ Erro ao criar evento: {e}")
        return None


def test_event_parsing():
    """Testa o parsing de eventos"""
    print("\n🧪 Testando parsing de eventos...")
    
    try:
        # Dados de teste
        test_data = {
            'event_type': 'user.created',
            'payload': {
                'user_id': '12345',
                'name': 'João Silva'
            },
            'metadata': {
                'event_id': 'test-uuid-123',
                'timestamp': '2024-01-15T10:30:00Z',
                'version': '1.0',
                'source': 'test-script'
            }
        }
        
        # Cria evento a partir do dict
        event = KafkaEvent.from_dict(test_data, 'users')
        
        print(f"✅ Evento parseado: {event.event_type}")
        print(f"   Tópico: {event.topic}")
        print(f"   Payload: {event.payload}")
        
        return event
    except Exception as e:
        print(f"❌ Erro ao fazer parse: {e}")
        return None


def test_legacy_format():
    """Testa formato legado"""
    print("\n🧪 Testando formato legado...")
    
    try:
        # Formato antigo
        legacy_data = {
            'event': 'order.processed',
            'payload': {
                'order_id': 'ORD-001'
            }
        }
        
        # Simula o parsing que o worker faria
        worker = Worker(['localhost:9092'], 'test')
        
        # Simula uma mensagem Kafka
        class MockMessage:
            def __init__(self, topic, value):
                self.topic = topic
                self.value = value
        
        mock_msg = MockMessage('orders', legacy_data)
        event = worker.parse_kafka_message(mock_msg)
        
        if event:
            print(f"✅ Formato legado convertido: {event.event_type}")
            print(f"   Tópico: {event.topic}")
            print(f"   Payload: {event.payload}")
        else:
            print("❌ Falha ao converter formato legado")
        
        return event
    except Exception as e:
        print(f"❌ Erro ao testar formato legado: {e}")
        return None


def main():
    """Função principal de teste"""
    print("🚀 Iniciando testes do Worker...\n")
    
    # Testa criação
    worker = test_worker_creation()
    if not worker:
        return
    
    # Testa criação de eventos
    event = test_event_creation()
    if not event:
        return
    
    # Testa parsing
    parsed_event = test_event_parsing()
    if not parsed_event:
        return
    
    # Testa formato legado
    legacy_event = test_legacy_format()
    
    print("\n🎉 Todos os testes básicos concluídos!")
    print("\n📋 Resumo:")
    print(f"   - Worker criado: {'✅' if worker else '❌'}")
    print(f"   - Evento criado: {'✅' if event else '❌'}")
    print(f"   - Evento parseado: {'✅' if parsed_event else '❌'}")
    print(f"   - Formato legado: {'✅' if legacy_event else '❌'}")
    
    print("\n💡 Para testar com Kafka real:")
    print("   1. Configure um servidor Kafka local")
    print("   2. Execute: python example_usage.py")


if __name__ == "__main__":
    main()
