from unittest import result
from errors.badrequest_error import BadRequestError
import asyncio

async def handle_audio_transcribe(worker, event):
  """Handler para eventos de usuário criado"""
  print(f"   Payload: {event.payload}")
  print(f"   Event ID: {event.id}")
  print(f"   Timestamp: {event.metadata.timestamp}")
  print(f"   Tentativa: {event.retry.current + 1}/{event.retry.max}")

  audio_path = event.payload.get('audio_url', None);

  if not audio_path:
    raise BadRequestError(event, "not_found", "audio_url", audio_path, 400, f"❌ Audio URL não encontrado")
  
  #audio_path = worker.deps.["media"].download_media(audio_path)
  print(f"✅ Audio path: {audio_path}")
  result = await worker.deps["transcriber"].execute(audio_path, "")

  print(f"✅ Audio transcrito com sucesso: {result}")
  return result
  