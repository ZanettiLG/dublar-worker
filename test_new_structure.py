#!/usr/bin/env python3
"""
Teste da nova estrutura do WorkerEvent
"""

from engines.worker import WorkerEvent, EventTrigger, EventRetry, EventMetadata
import json

def test_new_structure():
    """Testa a nova estrutura do evento"""
    print("🧪 Testando nova estrutura do WorkerEvent...")
    
    # Cria um evento de teste
    event = WorkerEvent(
        id="test-123",
        topic="audio.processing",
        event="audio.separate",
        payload={"audio_url": "test.mp3", "output_format": "wav"},
        retry=EventRetry(current=0, max=3),
        triggers=[
            EventTrigger(topic="audio.processing", event="audio.separate"),
            EventTrigger(topic="worker.result", event="audio.separated")
        ],
        metadata=EventMetadata(
            version="1.0",
            source="test-script",
            parent_id="parent-123"
        )
    )
    
    print(f"✅ Evento criado:")
    print(f"   ID: {event.id}")
    print(f"   Topic: {event.topic}")
    print(f"   Event: {event.event}")
    print(f"   Payload: {event.payload}")
    print(f"   Retry: {event.retry.to_dict()}")
    print(f"   Triggers: {[t.to_dict() for t in event.triggers]}")
    print(f"   Metadata: {event.metadata.to_dict()}")
    
    # Testa conversão para dicionário
    event_dict = event.to_dict()
    print(f"\n📋 Evento como dicionário:")
    print(json.dumps(event_dict, indent=2, default=str))
    
    # Testa conversão de volta
    event_from_dict = WorkerEvent.from_dict(event_dict, "audio.processing")
    print(f"\n🔄 Evento reconstruído:")
    print(f"   ID: {event_from_dict.id}")
    print(f"   Topic: {event_from_dict.topic}")
    print(f"   Event: {event_from_dict.event}")
    print(f"   Triggers count: {len(event_from_dict.triggers)}")
    
    # Verifica se a estrutura está correta
    expected_keys = ["id", "topic", "event", "payload", "retry", "triggers", "metadata"]
    actual_keys = list(event_dict.keys())
    
    print(f"\n✅ Verificação da estrutura:")
    for key in expected_keys:
        if key in actual_keys:
            print(f"   ✓ {key}: presente")
        else:
            print(f"   ✗ {key}: FALTANDO")
    
    # Verifica estrutura do retry
    retry_keys = ["current", "max"]
    retry_actual = list(event_dict["retry"].keys())
    print(f"\n✅ Verificação do retry:")
    for key in retry_keys:
        if key in retry_actual:
            print(f"   ✓ retry.{key}: presente")
        else:
            print(f"   ✗ retry.{key}: FALTANDO")
    
    # Verifica estrutura dos triggers
    if event_dict["triggers"] and len(event_dict["triggers"]) > 0:
        trigger_keys = ["topic", "event"]
        trigger_actual = list(event_dict["triggers"][0].keys())
        print(f"\n✅ Verificação dos triggers:")
        for key in trigger_keys:
            if key in trigger_actual:
                print(f"   ✓ triggers[0].{key}: presente")
            else:
                print(f"   ✗ triggers[0].{key}: FALTANDO")
    
    # Verifica estrutura dos metadata
    metadata_keys = ["version", "source", "timestamp", "parent_id"]
    metadata_actual = list(event_dict["metadata"].keys())
    print(f"\n✅ Verificação dos metadata:")
    for key in metadata_keys:
        if key in metadata_actual:
            print(f"   ✓ metadata.{key}: presente")
        else:
            print(f"   ✗ metadata.{key}: FALTANDO")
    
    print(f"\n🎉 Teste concluído!")

if __name__ == "__main__":
    test_new_structure()
