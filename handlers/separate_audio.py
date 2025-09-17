import asyncio
from errors.badrequest_error import BadRequestError

async def handle_audio_separation(worker, event):
  """Handler para eventos de separação de áudio com normalização integrada"""
  print(f"   Payload: {event.payload}")
  print(f"   Event ID: {event.id}")
  print(f"   Timestamp: {event.metadata.timestamp}")
  print(f"   Tentativa: {event.retry.current + 1}/{event.retry.max}")

  audio_path = event.payload.get('audio_url', None);

  if not audio_path:
    raise BadRequestError(event, "not_found", "audio_url", audio_path, 400, f"❌ Audio URL não encontrado")
  
  #audio_path = worker.deps.["media"].download_media(audio_path)
  print(f"✅ Audio path: {audio_path}")
  
  # 1. Normaliza o áudio antes da separação
  print("🔊 Normalizando áudio...")
  normalization_result = await worker.deps["audio_normalizer"].execute(audio_path)
  
  if not normalization_result.get("success", False):
    print("⚠️ Falha na normalização, continuando com áudio original")
    normalized_audio = audio_path
  else:
    normalized_audio = normalization_result["output_path"]
    print(f"✅ Áudio normalizado: {normalization_result['file_size'] / (1024*1024):.2f} MB")
  
  # 2. Separa o áudio normalizado
  print("🎵 Separando áudio...")
  output_paths = worker.deps["spleeter"].execute(normalized_audio)
  
  # 3. Normaliza os áudios separados
  print("🔊 Normalizando áudios separados...")
  normalized_outputs = {}
  
  for key, path in output_paths.items():
    if path and path != normalized_audio:  # Não normaliza o arquivo original se for o mesmo
      norm_result = await worker.deps["audio_normalizer"].execute(path)
      if norm_result.get("success", False):
        normalized_outputs[key] = norm_result["output_path"]
        print(f"   ✅ {key}: normalizado")
      else:
        normalized_outputs[key] = path
        print(f"   ⚠️ {key}: usando original")
    else:
      normalized_outputs[key] = path

  print(f"✅ Pipeline completo: separação + normalização concluída")
  return normalized_outputs