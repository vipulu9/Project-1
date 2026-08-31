# Standard library imports
import os
import sys
import webbrowser
from pathlib import Path

# Ensure the project root is importable when this file is executed directly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Third-party imports
import requests
import pyttsx3
import speech_recognition as sr
import pygame
import whisper
import numpy as np
from gtts import gTTS
from openai import OpenAI
from dotenv import load_dotenv

# Wake word specific imports
import pyaudio
from openwakeword.model import Model

# Local imports
from features.music.domain import musicLibrary

# Load environment variables from .env file
load_dotenv()

# ==========================================
# INITIALIZATION & SETTINGS
# ==========================================

# Initialize Speech Recognition for COMMANDS ONLY
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 200            
recognizer.pause_threshold = 0.8             

engine = pyttsx3.init()

# OpenRouter Client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Load AI Models
whisper_model = whisper.load_model("base.en")

# Ensure models are downloaded before loading
import openwakeword
openwakeword.utils.download_models()

# Explicitly use ONNX runtime to avoid tflite issues on Windows
oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def speak_offline(text):
    """Fallback offline text-to-speech using pyttsx3."""
    engine.say(text)
    engine.runAndWait()

def speak(text):
    """Online text-to-speech using Google TTS."""
    try:
        tts = gTTS(text)
        tts.save('temp.mp3') 

        pygame.mixer.init()
        pygame.mixer.music.load('temp.mp3')
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        pygame.mixer.music.unload()
        pygame.quit() 
        
        if os.path.exists("temp.mp3"):
            os.remove("temp.mp3") 
            
    except Exception as e:
        print(f"Online TTS failed, falling back to offline: {e}")
        speak_offline(text)

def transcribe_audio(audio_data_obj):
    """Converts speech_recognition audio to 16kHz and runs Whisper locally."""
    try:
        raw_16k_data = audio_data_obj.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw_16k_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        result = whisper_model.transcribe(
            audio_np, 
            fp16=False,
            condition_on_previous_text=False,
            no_speech_threshold=0.6           
        )
        return result["text"].strip()
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""

def aiProcess(command):
    """Processes open-ended commands using OpenRouter."""
    print(f"Sending to OpenRouter: {command}") 
    try:
        completion = client.chat.completions.create(
            model="openrouter/free", 
            messages=[
                {"role": "system", "content": "You are a virtual assistant named Jarvis. Give short, concise responses."},
                {"role": "user", "content": command}
            ]
        )
        response = completion.choices[0].message.content
        print(f"OpenRouter replied: {response}") 
        return response
    except Exception as e:
        print(f"OpenRouter Error: {e}") 
        return "Sorry, I encountered an error connecting to my brain."

def processCommand(c):
    """Routes specific commands to web actions or AI processing."""
    command_lower = c.lower()
    
    if "open google" in command_lower:
        webbrowser.open("https://google.com")
        speak("Opening Google")
        
    elif "open facebook" in command_lower:
        webbrowser.open("https://facebook.com")
        speak("Opening Facebook")
        
    elif "open youtube" in command_lower:
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube")
        
    elif "open linkedin" in command_lower:
        webbrowser.open("https://linkedin.com")
        speak("Opening LinkedIn")
        
    elif command_lower.startswith("play"):
        try:
            song = command_lower.split(" ", 1)[1]
            if song in musicLibrary.music:
                link = musicLibrary.music[song]
                webbrowser.open(link)
                speak(f"Playing {song}")
            else:
                speak("I couldn't find that song in your library.")
        except IndexError:
            speak("What song would you like me to play?")

    elif "news" in command_lower:
        if not NEWS_API_KEY:
            speak("News API key is not configured.")
            return
        try:
            r = requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}")
            if r.status_code == 200:
                data = r.json()
                articles = data.get('articles', [])
                speak("Here are the top headlines.")
                for article in articles[:3]: 
                    speak(article['title'])
            else:
                speak("I couldn't fetch the news right now.")
        except Exception:
            speak("I encountered an error trying to fetch the news.")

    else:
        output = aiProcess(c)
        speak(output) 


# ==========================================
# MAIN LOOP
# ==========================================

if __name__ == "__main__":
    speak("Initializing Jarvis....")
    
    # Setup PyAudio specifically for the Wake Word engine
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280

    audio_interface = pyaudio.PyAudio()
    mic_stream = audio_interface.open(
        format=FORMAT, 
        channels=CHANNELS, 
        rate=RATE, 
        input=True, 
        frames_per_buffer=CHUNK
    )

    print("\nSystem ready. Say 'Hey Jarvis' to wake me up.")
    
    try:
        while True:
            # 1. LOOP UNTIL WAKE WORD IS HEARD
            wake_word_detected = False
            while not wake_word_detected:
                audio_chunk = np.frombuffer(
                    mic_stream.read(CHUNK, exception_on_overflow=False),
                    dtype=np.int16,
                )

                prediction = oww_model.predict(audio_chunk)

                # Lowered threshold to 0.3 (30% confidence) for easier triggering
                if prediction['hey_jarvis'] > 0.3:
                    wake_word_detected = True

            # 2. WAKE WORD DETECTED
            mic_stream.stop_stream()
            speak("Yes sir?")

            # 3. LISTEN FOR COMMAND USING WHISPER
            with sr.Microphone(sample_rate=16000) as source:
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    command_audio = recognizer.listen(source, timeout=4, phrase_time_limit=8)
                    command = transcribe_audio(command_audio)

                    if command.strip():
                        processCommand(command)
                except sr.WaitTimeoutError:
                    pass

            # 4. RESTART WAKE WORD LISTENING
            oww_model.reset()
            mic_stream.start_stream()

    except KeyboardInterrupt:
        pass
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        audio_interface.terminate()