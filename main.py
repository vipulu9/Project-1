import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from features.music.domain.musicLibrary import music

load_dotenv()

app = FastAPI(title="Project-1 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Project-1 backend is running."}

@app.get("/dashboard")
def get_dashboard():
    return {
        "status": "online",
        "features": {
            "assistant": {
                "name": "Jarvis",
                "status": "ready",
                "description": "Voice assistant and AI commands are available."
            },
            "music": {
                "count": len(music),
                "tracks": list(music.keys())
            },
            "news": {
                "status": "configured",
                "provider": "NewsAPI",
                "api_key_configured": bool(os.getenv("NEWS_API_KEY"))
            }
        }
    }

@app.get("/assistant")
def get_assistant():
    return {
        "name": "Jarvis",
        "mode": "voice",
        "capabilities": ["open websites", "play music", "fetch news", "answer commands"],
        "status": "ready"
    }

@app.get("/music")
def get_music():
    return {
        "count": len(music),
        "tracks": [
            {
                "name": track_name,
                "url": track_url
            }
            for track_name, track_url in music.items()
        ]
    }

@app.get("/news")
def get_news():
    return {
        "status": "configured",
        "provider": "NewsAPI",
        "api_key_configured": bool(os.getenv("NEWS_API_KEY")),
        "articles": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
