import handlers

routes = [
  ('audio.separate', handlers.handle_audio_separation),
  ('audio.subtitle', handlers.handle_audio_transcribe)
]