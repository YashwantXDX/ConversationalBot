from pydantic import BaseModel
from typing import Dict, List, Optional

class AgentChatResponse(BaseModel):
    audio_urls: List[str]
    transcription: Optional[str] = None
    gemini_response: str
    chat_history: List[Dict[str, str]]
    error: Optional[str] = None

class STTRequest(BaseModel):
    audio_bytes: bytes

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-terrell"
    chunk_size: int = 3000

class LLMRequest(BaseModel):
    history: List[Dict[str, str]]
    model: str = "gemini-2.5-flash"