#!/usr/bin/env python3
"""
Test Producer - Envia eventos de teste para o Kafka
Use este script para testar o worker que está rodando
"""

import time
import json
import asyncio
from engines.worker import Worker


async def send_single_event_async(producer, event_data, event_index, total_events):
    """Envia um evento de forma assíncrona"""
    try:
        # Envia o evento
        event_id = producer.send_event(
            topic=event_data['topic'],
            event_type=event_data['event_type'],
            payload=event_data['payload'],
            correlation_id=f'test-session-{int(time.time())}',
            source='test-producer'
        )
        
        print(f"✅ Evento {event_index}/{total_events} enviado:")
        print(f"   Tópico: {event_data['topic']}")
        print(f"   Tipo: {event_data['event_type']}")
        print(f"   ID: {event_id}")
        print(f"   Payload: {json.dumps(event_data['payload'], indent=2)}")
        print()
        
        return event_id
        
    except Exception as e:
        print(f"❌ Erro ao enviar evento {event_index}: {e}")
        return None


async def send_test_events_async():
    """Envia eventos de teste para o Kafka de forma assíncrona"""
    
    # Cria um worker apenas para enviar eventos
    producer = Worker(
        bootstrap_servers=['localhost:9092'],
        group_id='test-producer'
    )
    
    try:
        # Configura apenas o produtor
        print("📤 Configurando produtor Kafka...")
        producer.setup_producer()
        
        # Lista de eventos de teste
        test_events = [
            {
                'topic': 'worker_process',
                'event_type': 'audio.separate',
                'response_topic': 'worker_result',
                'payload': {
                    'process_id': '12345',
                    'process_type': 'separate',
                    'audio_url': './assets/gto_ep1.mp4',
                }
            },
        ]
        
        print(f"🚀 Enviando {len(test_events)} eventos de teste de forma assíncrona...\n")
        
        # Cria tarefas assíncronas para todos os eventos
        tasks = []
        for i, event_data in enumerate(test_events, 1):
            task = send_single_event_async(producer, event_data, i, len(test_events))
            tasks.append(task)
        
        # Executa todas as tarefas em paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Conta sucessos e falhas
        successful = sum(1 for result in results if result is not None and not isinstance(result, Exception))
        failed = len(results) - successful
        
        print(f"\n🎉 Processamento assíncrono concluído!")
        print(f"   ✅ Sucessos: {successful}")
        print(f"   ❌ Falhas: {failed}")
        print(f"   📊 Total: {len(test_events)}")
        print("\n💡 Verifique o worker para ver se os eventos foram processados")
        
    except Exception as e:
        print(f"❌ Erro ao configurar produtor: {e}")
    finally:
        producer.stop()


def send_test_events():
    """Função síncrona que chama a versão assíncrona"""
    asyncio.run(send_test_events_async())

if __name__ == "__main__":
    print("🎯 Test Producer - Enviando eventos de teste para o Kafka (Assíncrono)")
    print("=" * 60)
    
    # Envia eventos de teste de forma assíncrona
    asyncio.run(send_test_events_async())
    
    print("\n" + "=" * 60)
    print("💡 Para enviar um evento específico, use:")
    print("   send_single_event('topic', 'event.type', {'data': 'value'})")
    print("   ou a versão assíncrona:")
    print("   asyncio.run(send_single_event_async('topic', 'event.type', {'data': 'value'}))")
