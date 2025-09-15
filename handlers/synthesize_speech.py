from errors.badrequest_error import BadRequestError

def handle_synthesize_dialog(worker, event):
  """Handler para síntese de fala usando Coqui TTS"""
  print(f"   Payload: {event.payload}")
  print(f"   Event ID: {event.id}")
  print(f"   Timestamp: {event.metadata.timestamp}")
  print(f"   Tentativa: {event.retry.current + 1}/{event.retry.max}")

  # Extrai dados do payload
  audio_url = event.payload.get('audio_url', None)
  text = event.payload.get('text', None)

  # Validação dos parâmetros obrigatórios
  if not text:
    raise BadRequestError(event, "not_found", "text", text, 400, f"❌ Texto não encontrado")
  
  if not audio_url:
    raise BadRequestError(event, "not_found", "audio_url", audio_url, 400, f"❌ Audio URL não encontrado")
  
  print(f"✅ Texto para síntese: {text[:50]}...")
  print(f"✅ Audio URL: {audio_url}")
  
  # Executa síntese de fala usando Coqui TTS
  try:
    result = worker.deps["coqui"].execute({
      "text": text,
      "audio_url": audio_url
    })
    
    if result.get("success", False):
      print(f"✅ Síntese de fala concluída: {result['output_path']}")
      return result
    else:
      error_msg = result.get("error", "Erro desconhecido na síntese")
      raise BadRequestError(event, "synthesis_failed", "coqui", result, 500, f"❌ Erro na síntese: {error_msg}")
      
  except Exception as e:
    print(f"❌ Erro na síntese de fala: {e}")
    raise BadRequestError(event, "synthesis_error", "coqui", str(e), 500, f"❌ Erro na síntese: {str(e)}")