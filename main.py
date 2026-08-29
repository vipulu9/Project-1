import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from features.music.domain.musicLibrary import music

load_dotenv()

app = FastAPI(title="Project-1 API")


def interpret_command(command: str):
    text = (command or '').strip()
    if not text:
        raise HTTPException(status_code=400, detail='No command provided.')

    lowered = text.lower()

    known_sites = {
        'google': 'https://www.google.com',
        'youtube': 'https://www.youtube.com',
        'gmail': 'https://mail.google.com',
        'news': 'https://news.google.com',
        'weather': 'https://weather.com'
    }

    if 'open' in lowered or 'launch' in lowered:
        for site_name, site_url in known_sites.items():
            if site_name in lowered:
                return {
                    'action': 'open_site',
                    'url': site_url,
                    'message': f'Opening {site_name.title()}.'
                }

    if ('play' in lowered or 'open' in lowered) and (
        'music' in lowered or 'track' in lowered or any(track in lowered for track in music)
    ):
        track_name = 'stealth'
        for candidate in music:
            if candidate in lowered:
                track_name = candidate
                break

        return {
            'action': 'play_music',
            'track': track_name,
            'url': music.get(track_name),
            'message': f'Opening {track_name} from your music library.'
        }

    if 'news' in lowered or 'headline' in lowered:
        return {
            'action': 'fetch_news',
            'message': 'Fetching the latest headlines from the news feed now.'
        }

    if 'weather' in lowered:
        return {
            'action': 'check_weather',
            'message': 'Checking the latest weather conditions for your area.'
        }

    if 'stop' in lowered or 'pause' in lowered:
        return {
            'action': 'pause',
            'message': 'Listening paused. I am ready when you want to continue.'
        }

    return {
        'action': 'general',
        'message': f'I heard: "{text}". I am ready for your next command.'
    }

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

@app.post("/assistant/command")
def handle_assistant_command(payload: dict):
    command = (payload or {}).get('command', '')
    return interpret_command(command)

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
