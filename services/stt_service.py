import asyncio
import logging
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
from fastapi import WebSocket, WebSocketDisconnect
from schemas import STTRequest

logger = logging.getLogger(__name__)

class STTService:
    """
    Handles both:
      1. File/binary transcription (non-streaming)
      2. Streaming transcription over WebSocket
    """

    def __init__(self, api_key: str):
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber(
            config=aai.TranscriptionConfig(
                punctuate=True,
                format_text=True,
            )
        )
        self.api_key = api_key

    # --- File-based transcription (legacy) ---
    def transcribe(self, request: STTRequest) -> str:
        try:
            transcript = self.transcriber.transcribe(request.audio_bytes)
            return (transcript.text or "").strip()
        except Exception as e:
            logger.error(f"STT Failed: {e}")
            raise

    # --- Streaming transcription ---
    async def stream_transcribe(self, websocket: WebSocket):
        await websocket.accept()
        logger.info("Client connected to /ws/audio (streaming)")

        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        # Prepare AssemblyAI streaming client
        client = StreamingClient(StreamingClientOptions(api_key=self.api_key))

        # Event handlers
        def on_begin(self, event: BeginEvent):
            logger.info(f"[AssemblyAI] Session started: {event.id}")

        def on_turn(self, event: TurnEvent):
            text = event.transcript or ""
            if text:
                logger.info(f"[Transcript] {text}")
                # Push transcript to browser UI
                asyncio.run_coroutine_threadsafe(websocket.send_text(text), loop)

        def on_terminated(self, event: TerminationEvent):
            logger.info(
                f"[AssemblyAI] Session terminated; audio seconds processed={event.audio_duration_seconds}"
            )

        def on_error(self, error: StreamingError):
            logger.error(f"[AssemblyAI] Error: {error}")

        client.on(StreamingEvents.Begin, on_begin)
        client.on(StreamingEvents.Turn, on_turn)
        client.on(StreamingEvents.Termination, on_terminated)
        client.on(StreamingEvents.Error, on_error)

        # Start streaming session
        client.connect(
            StreamingParameters(
                sample_rate=16_000,
                formatted_finals=True,
            )
        )

        # Sync generator for SDK
        def audio_generator():
            while True:
                chunk = asyncio.run(audio_queue.get())
                if chunk is None:
                    break
                yield chunk

        stream_task = asyncio.to_thread(client.stream, audio_generator())

        try:
            while True:
                msg = await websocket.receive()
                if "bytes" in msg and msg["bytes"] is not None:
                    await audio_queue.put(msg["bytes"])
                elif msg.get("type") == "websocket.disconnect":
                    raise WebSocketDisconnect()
                else:
                    continue

        except WebSocketDisconnect:
            logger.info("Browser websocket disconnected")
        except Exception as e:
            logger.error(f"Audio WebSocket error: {e}")
        finally:
            await audio_queue.put(None)
            try:
                await stream_task
            except Exception:
                pass
            try:
                client.disconnect()
            except Exception:
                pass
            try:
                await websocket.close()
            except Exception:
                pass
            logger.info("Cleaned up streaming session")
