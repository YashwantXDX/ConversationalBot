from google import genai
from google.genai import types
from schemas import LLMRequest
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    def generate_response(self, request: LLMRequest) -> str:
        try:
            formatted_history = [
                types.Content(
                    role=msg["role"],
                    parts=[types.Part(text=msg["content"])]
                )
                for msg in request.history
            ]
            
            response = self.client.models.generate_content(
                model=request.model,
                contents=formatted_history
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"LLM failed: {e}")
            raise