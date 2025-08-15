from typing import List
from murf import Murf
from schemas import TTSRequest
import logging

logger = logging.getLogger(__name__)

class TTSService:
    
    def __init__(self, api_key: str):
        self.client = Murf(api_key=api_key)

    def generate_audio(self, request: TTSRequest) -> List[str]:
        try:
            chunks = [request.text[i:i+request.chunk_size] 
                      for i in range(0, len(request.text), request.chunk_size)]
            audio_urls = []
            
            for chunk in chunks:
                result = self.client.text_to_speech.generate(
                    text=chunk,
                    voice_id=request.voice_id
                )
                audio_urls.append(result.audio_file)
            return audio_urls
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise

    def fallback_audio(self, text: str, voice_id: str) -> List[str]:
        try:
            result = self.client.text_to_speech.generate(
                text=text,
                voice_id=voice_id
            )
            return [result.audio_file]
        except Exception:
            return []