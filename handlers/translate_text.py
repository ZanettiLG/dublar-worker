from errors.badrequest_error import BadRequestError

async def handle_audio_translation(worker, event):
  """Handler para eventos de usuário criado"""
  print(f"   Payload: {event.payload}")
  print(f"   Event ID: {event.id}")
  print(f"   Timestamp: {event.metadata.timestamp}")
  print(f"   Tentativa: {event.retry.current + 1}/{event.retry.max}")

  text = event.payload.get('text', None);
  input_language = event.payload.get('input_language', None);
  target_language = event.payload.get('target_language', None);

  if not text:
    raise BadRequestError(event, "not_found", "text", text, 400, f"❌ Text não encontrado")
  
  #audio_path = worker.deps.["media"].download_media(audio_path)
  print(f"✅ Text: {text}")
  result = await worker.deps["translator"].execute(text, target_language)

  print(f"✅ Text traduzido com sucesso: {result}")
  return result
  