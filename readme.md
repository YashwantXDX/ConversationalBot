# Conversation Bot – AI-Powered Communication Assistant

Conversation Bot is an **AI-driven communication bot** that listens to your voice, understands your query, and responds with an AI-generated voice reply.  
It integrates **Speech-to-Text**, **Large Language Models**, and **Text-to-Speech** for a complete voice conversation experience.

---

## Tech Stack

**Frontend:**
- HTML
- CSS
- JavaScript

**Backend:**
- Python
- [FastAPI](https://fastapi.tiangolo.com/) – Web framework for APIs

**AI & APIs:**
- [Gemini LLM](https://ai.google.dev/) – For generating intelligent responses
- [AssemblyAI](https://www.assemblyai.com/) – For speech-to-text transcription
- [Murf AI](https://murf.ai/) – For converting text back to natural speech

---

## Architecture

```
[ User Voice Input ]
         │
         ▼
 AssemblyAI (Speech-to-Text)
         │
         ▼
 Gemini LLM (AI Response Generation)
         │
         ▼
 Murf AI (Text-to-Speech)
         │
         ▼
[ User Hears AI Voice Reply ]
```

**Session Management:**  
The bot maintains a chat history for each `session_id` to provide contextual conversations.

---

## Features

- **Voice-to-Text:** Transcribe speech into text using AssemblyAI  
- **AI Responses:** Context-aware replies from Gemini LLM  
- **Text-to-Voice:** Convert AI replies into natural-sounding speech with Murf AI  
- **Chat History:** Keeps track of conversations per session  
- **Fast API Server:** Lightweight & high-performance backend  

---

## Folder Structure

```
conversation-bot/
│
├── static/                   # Frontend static assets
│   ├── script.js
│   ├── session_management.js
│   └── style.css
│
├── templates/                # HTML templates
│   └── index.html
│
├── main.py                    # FastAPI backend application
├── README.md                  # Project documentation
└── .env                       # Environment variables (not committed to Git)
```
---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/YashwantXDX/ConversationalBot.git
cd ConversationalBot
```

### 2. Install Dependencies
```bash
pip install fastapi uvicorn python-dotenv murf assemblyai google-genai
```

### 3. Create a `.env` File
In the root directory, add your API keys:
```env
MURF_API_KEY=your_murf_api_key
ASSEMBLY_API_KEY=your_assemblyai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Run the Application
```bash
uvicorn main:app --reload
```
Server will be available at **http://localhost:8000**

---

## Screenshots
![Pic 1](https://github.com/user-attachments/assets/ce449aae-9474-4e97-af66-062f1ab2c0a1)
![Pic 2](https://github.com/user-attachments/assets/3599ca1d-0032-4821-89e0-a31d224436a9)
![Pic 3](https://github.com/user-attachments/assets/3321fd56-5b0a-4180-a14d-8d6c9d3d5296)
![Pic 4](https://github.com/user-attachments/assets/fb7c49ea-47ef-4c90-bb1b-9ad5475d4a72)

## Future Improvements
- WebSocket support for real-time streaming
- Multi-language support
- Enhanced UI

---
