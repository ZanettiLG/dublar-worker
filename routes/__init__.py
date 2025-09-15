import handlers

routes = [
  ('audio.separate', handlers.handle_audio_separation),
  ('audio.subtitle', handlers.handle_audio_transcribe),
  ('text.translation', handlers.handle_audio_translation),
  ('synthesize.dialog', handlers.handle_synthesize_dialog),
  ('speaker.diarization', handlers.handle_speaker_diarization),
]