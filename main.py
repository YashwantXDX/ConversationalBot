from datetime import datetime
import os
import logging
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from schemas import AgentChatResponse, LLMRequest, STTRequest, TTSRequest
from services.stt_service import STTService
from services.tts_service import TTSService
from services.llm_service import LLMService
from utils.helpers import FALLBACK_TEXT, DEFAULT_VOICE_ID, update_chat_history

# NEW: AssemblyAI streaming imports
import assemblyai as aai
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    StreamingParameters,
    BeginEvent,
    TurnEvent,
    TerminationEvent,
    StreamingError,
)

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
load_dotenv()

# Initialize services
stt_service = STTService(api_key=os.getenv("ASSEMBLY_API_KEY"))
tts_service = TTSService(api_key=os.getenv("MURF_API_KEY"))
llm_service = LLMService(api_key=os.getenv("GEMINI_API_KEY"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()

        # STT (file-based)
        try:
            user_text = stt_service.transcribe(STTRequest(audio_bytes=audio_bytes))
        except Exception as stt_error:
            logger.error(f"STT failed: {stt_error}")
            return AgentChatResponse(
                audio_urls=[],
                gemini_response=FALLBACK_TEXT,
                chat_history=[],
                error="Speech to Text failed",
            )

        # Update chat history
        history = update_chat_history(session_id, "user", user_text)

        # LLM
        try:
            ai_response = llm_service.generate_response(LLMRequest(history=history))
        except Exception as llm_error:
            logger.error(f"LLM failed: {llm_error}")
            ai_response = FALLBACK_TEXT

        update_chat_history(session_id, "model", ai_response)

        # TTS
        try:
            audio_urls = tts_service.generate_audio(TTSRequest(text=ai_response))
        except Exception as tts_error:
            logger.error(f"TTS failed: {tts_error}")
            audio_urls = tts_service.fallback_audio(FALLBACK_TEXT, DEFAULT_VOICE_ID)

        return AgentChatResponse(
            audio_urls=audio_urls,
            transcription=user_text,
            gemini_response=ai_response,
            chat_history=history,
        )

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return AgentChatResponse(
            audio_urls=[],
            gemini_response=FALLBACK_TEXT,
            chat_history=[],
            error="Unexpected server error",
        )


# -----------------------------------------------------------------------------
# WebSocket for real-time audio -> AssemblyAI streaming
# Expects: raw PCM, 16 kHz, 16-bit, mono frames from the browser.
# -----------------------------------------------------------------------------
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await stt_service.stream_transcribe(websocket)