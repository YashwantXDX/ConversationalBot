import os
from murf import Murf
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import assemblyai as aai
from google import genai
from typing import Dict,List
from google.genai import types

# Configuration & Constants
load_dotenv()

# Constants
FALLBACK_TEXT = "I'm having trouble connecting right now."
FALLBACK_AUDIO_URLS = []
DEFAULT_VOICE_ID = "en-US-terrell"
CHUNK_SIZE = 3000
MODEL_NAME = "gemini-2.5-flash"

# Initialize Services
murf_client = Murf(api_key=os.getenv("MURF_API_KEY"))
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Assembly AI COnfiguration
transcriber = aai.Transcriber(
    config = aai.TranscriptionConfig(
        speech_model=aai.SpeechModel.best,
        punctuate=True,
        format_text=True,
        language_code="en"
    )
)

# Chat History Store {session_id: [{"role": "user" | "model", "context": "text"}]}
chat_history_store : Dict[str, List[Dict[str, str]]] = {}

# Helper Functions
def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio using AssemblyAI"""
    transcript = transcriber.transcribe(audio_bytes)
    return transcript.text.strip()

def build_gemini_input(history: List[Dict[str, str]]) -> List[types.Content]:
    """Format Chat History For Gemini API"""
    return [
        types.Content(
            role=msg["role"],
            parts=[
                types.Part(
                    text=msg["content"]
                )
            ]
        )

        for msg in history
    ]

def generate_gemini_response(history: List[Dict[str, str]]) -> str:
    """Generate Response using Gemini API"""
    response = gemini_client.models.generate_content(
        model=MODEL_NAME,
        contents=build_gemini_input(history)
    )

    return response.text.strip()

def generate_tts_audio(text: str) -> List[str]:
    """Convert text to speech using MURF AI"""
    chunks = [text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    audio_urls = []

    for chunk in chunks:
        result = murf_client.text_to_speech.generate(
            text=chunk,
            voice_id=DEFAULT_VOICE_ID
        )

        audio_urls.append(result.audio_file)

    return audio_urls

def handle_tts_fallback() -> List[str]:
    """Handle TTS Fallback Scenerio"""
    try:
        result = murf_client.text_to_speech.generate(
            text=FALLBACK_TEXT,
            voice_id=DEFAULT_VOICE_ID
        )

        return [result.audio_file]

    except Exception:
        return []
    
# Fast API Setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request
    })

@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    try:
        # Process Audio Input
        audio_bytes = await audio.read()

        try:
            user_text = transcribe_audio(audio_bytes)
        
        except Exception as stt_error:
            print(f"[Error] STT failed: {stt_error}")
            return {
                "audio_urls": FALLBACK_AUDIO_URLS,
                "transcription": None,
                "gemini_response": FALLBACK_TEXT,
                "chat_history": [],
                "error": "Speech To Text Failed"
            }
        
        # Manage Chat History
        history = chat_history_store.get(session_id, [])
        history.append({
            "role": "user",
            "content": user_text
        })

        # Generate AI Response
        try:
            full_text = generate_gemini_response(history)

        except Exception as llm_error:
            print(f"[Error] LLM failed: {llm_error}")
            full_text = FALLBACK_TEXT

        history.append({
            "role" : "model",
            "content": full_text
        })

        chat_history_store[session_id] = history

        # Convert Response to Speech
        try:
            audio_urls = generate_tts_audio(full_text)
        
        except Exception as tts_error:
            print(f"[Error] TTS failed: {tts_error}")
            audio_urls = handle_tts_fallback()

        return {
            "audio_urls": audio_urls,
            "transcription": user_text,
            "gemini_response": full_text,
            "chat_history": history
        }

    except Exception as e:
        print(f"[Fatal Error] {e}")
        return {
            "audio_urls": FALLBACK_AUDIO_URLS,
            "transcription": None,
            "gemini_response": FALLBACK_TEXT,
            "chat_history": [],
            "error": "Unexpected Server Error"
        }