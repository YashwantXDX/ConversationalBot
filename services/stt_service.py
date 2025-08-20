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

        loop = asyncio.get_running_loop()
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        ws_open = True  # guard to avoid sends after close

        client = StreamingClient(StreamingClientOptions(api_key=self.api_key))

        # --- Event handlers ---
        def on_begin(_client, event: BeginEvent):
            logger.info(f"[AssemblyAI] Session started: {event.id}")

        def on_turn(_client, event: TurnEvent):
            text = event.transcript or ""
            if not text or not ws_open:
                return
            try:
                # schedule send on the main loop; don't block thread
                asyncio.run_coroutine_threadsafe(websocket.send_text(text), loop)
                logger.info(f"[Transcript] {text}")
            except Exception as e:
                logger.warning(f"Skip send_text after close: {e}")

        def on_terminated(_client, event: TerminationEvent):
            logger.info(
                f"[AssemblyAI] Session terminated; audio seconds processed={event.audio_duration_seconds}"
            )

        def on_error(_client, error: StreamingError):
            logger.error(f"[AssemblyAI] Error: {error}")

        client.on(StreamingEvents.Begin, on_begin)
        client.on(StreamingEvents.Turn, on_turn)
        client.on(StreamingEvents.Termination, on_terminated)
        client.on(StreamingEvents.Error, on_error)

        # Start AssemblyAI streaming session
        client.connect(
            StreamingParameters(
                sample_rate=16_000,
                formatted_finals=True,
            )
        )

        # --- Thread-side generator: pull from asyncio.Queue safely ---
        def audio_generator():
            while True:
                fut = asyncio.run_coroutine_threadsafe(audio_queue.get(), loop)
                chunk = fut.result()  # blocks this thread, not the event loop
                if chunk is None:
                    break
                yield chunk

        # IMPORTANT: schedule the blocking stream on a background thread NOW
        stream_task = asyncio.create_task(
            asyncio.to_thread(client.stream, audio_generator())
        )

        try:
            while True:
                # Only accept binary frames (PCM16)
                msg = await websocket.receive()
                if msg.get("bytes") is not None:
                    await audio_queue.put(msg["bytes"])
                elif msg.get("type") == "websocket.disconnect":
                    raise WebSocketDisconnect()
                # ignore text frames/others
        except WebSocketDisconnect:
            logger.info("Browser websocket disconnected")
        except Exception as e:
            logger.error(f"Audio WebSocket error: {e}")
        finally:
            # stop turn-sends and drain the generator
            ws_open = False
            # unblock generator
            await audio_queue.put(None)

            # wait for the streaming thread to finish; cancel if stubborn
            try:
                await asyncio.wait_for(stream_task, timeout=5)
            except asyncio.TimeoutError:
                stream_task.cancel()
                try:
                    await stream_task
                except Exception:
                    pass
            except Exception:
                pass

            # disconnect client & close socket
            try:
                client.disconnect()
            except Exception:
                pass
            try:
                await websocket.close()
            except Exception:
                pass

            logger.info("Cleaned up streaming session")
