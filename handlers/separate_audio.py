def handle_audio_separation(worker, event):
  """Handler para eventos de usuário criado"""
  print(f"   Payload: {event.payload}")
  print(f"   Event ID: {event.metadata.event_id}")
  print(f"   Timestamp: {event.metadata.timestamp}")
  print(f"   Tentativa: {event.metadata.retry_count + 1}/{event.metadata.max_retries}")

  audio_path = event.payload.get('audio_url', None);

  if not audio_path:
    raise BadRequestError(event, "not_found", "audio_url", audio_path, 400, f"❌ Audio URL não encontrado")
  
  #audio_path = worker.deps.["media"].download_media(audio_path)
  print(f"✅ Audio path: {audio_path}")
  output_paths = worker.deps["spleeter"].execute(audio_path)

  print(f"✅ Audio separado com sucesso: {output_paths}")
  return output_paths