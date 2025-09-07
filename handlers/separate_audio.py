def handle_audio_separation(worker, event):
  """Handler para eventos de usuário criado"""
  print(f"🆕 Usuário criado: {event.payload}")
  print(f"   Event ID: {event.metadata.event_id}")
  print(f"   Timestamp: {event.metadata.timestamp}")
  print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")

  
  
  print(f"✅ Usuário processado com sucesso: {event.payload.get('url', 'unknown')}")
  return "teste"