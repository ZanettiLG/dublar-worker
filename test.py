#!/usr/bin/env python3
"""
Test Producer - Envia eventos de teste para o Kafka
Use este script para testar o worker que está rodando
"""

import time
import json
import asyncio
from engines.worker import Worker


async def send_single_event_async(producer, event_data):
    """Envia um evento de forma assíncrona"""
    try:
        # Envia o evento
        event_id = producer.send_event(
            topic=event_data['topic'],
            event_type=event_data['event'],
            payload=event_data['payload'],
            correlation_id=f'test-session-{int(time.time())}',
            source='test-producer'
        )
        
        print(f"   Tópico: {event_data['topic']}")
        print(f"   Tipo: {event_data['event']}")
        print(f"   ID: {event_id}")
        print(f"   Payload: {json.dumps(event_data['payload'], indent=2)}")
        print()
        
        return event_id
        
    except Exception as e:
        print(f"❌ Erro ao enviar evento {event_data['event']}: {e}")
        return None

async def send_test_events_async(worker):
    """Envia eventos de teste para o Kafka de forma assíncrona"""
    # Lista de eventos de teste
    test_events = [
        
    ]
    
    print(f"🚀 Enviando {len(test_events)} eventos de teste de forma assíncrona...\n")
    
    # Cria tarefas assíncronas para todos os eventos
    tasks = []
    for i, event_data in enumerate(test_events, 1):
        task = send_single_event_async(worker, event_data, i, len(test_events))
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

async def separate_audio(worker, audio_url):
    separate_audio_event = {
        'topic': 'worker_process',
        'event': 'audio.separate',
        'payload': {
            'process_id': '12345',
            'audio_url': audio_url,
            'process_type': 'separate',
        }
    }
    event_id = await send_single_event_async(worker, separate_audio_event)
    print(f"✅ Sent event id: {event_id}")
    
    response = await worker.wait_for_response(event_id)
    print(f"✅ Response: {response}")
    return response

async def transcribe_audio(worker, audio_url):
    transcribe_audio_event = {
        'topic': 'worker_process',
        'event': 'audio.transcribe',
        'payload': {
            'process_id': '12345',
            'audio_url': audio_url,
            'process_type': 'transcribe',
        }
    }
    event_id = await send_single_event_async(worker, transcribe_audio_event)
    print(f"✅ Sent event id: {event_id}")
    response = await worker.wait_for_response(event_id)
    print(f"✅ Response: {response}")
    return response

async def run_process(worker):
    audio_url = './assets/gto_ep1.mp4'
    separated_audio = await separate_audio(worker, audio_url)
    #vocals_url = 'output/spleeter/gto_ep1/vocals.wav'
    #await transcribe_audio(worker, vocals_url)


def send_test_events():
    """Função síncrona que chama a versão assíncrona"""
    asyncio.run(send_test_events_async())

if __name__ == "__main__":
    print("🎯 Test Producer - Enviando eventos de teste para o Kafka (Assíncrono)")
    print("=" * 60)
    try:
        worker = Worker(
            bootstrap_servers=['localhost:9092'],
            group_id='test-producer'
        )

        print("📤 Configurando produtor Kafka...")
        worker.setup_producer()
        worker.setup_consumer(['worker_result'])
        worker.consumer_routes.append('audio.separate')
        worker.consumer_routes.append('audio.transcribe')

        # Envia eventos de teste de forma assíncrona
        asyncio.run(run_process(worker))
        
        print("\n" + "=" * 60)
    finally:
        worker.stop()
