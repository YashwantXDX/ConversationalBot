import assemblyai as aai
from schemas import STTRequest
import logging

logger = logging.getLogger(__name__)

class STTService:
    
    def __init__(self, api_key: str):
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber(
            config=aai.TranscriptionConfig(
                speech_model=aai.SpeechModel.best,
                punctuate=True,
                format_text=True,
                language_code="en"
            )
        )

    def transcribe(self, request: STTRequest) -> str:
        try:
            transcript = self.transcriber.transcribe(request.audio_bytes)
            return transcript.text.strip()
        except Exception as e:
            logger.error(f"STT Failed: {e}")
            raise