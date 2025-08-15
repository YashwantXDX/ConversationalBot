# Global constants
FALLBACK_TEXT = "I'm having trouble connecting right now."
DEFAULT_VOICE_ID = "en-US-terrell"

# Chat history store (consider moving to database later)
chat_history_store: dict = {}

def update_chat_history(session_id: str, role: str, content: str):
    history = chat_history_store.get(session_id, [])
    history.append({"role": role, "content": content})
    chat_history_store[session_id] = history
    return history