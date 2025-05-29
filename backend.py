import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sounddevice as sd
import queue
import threading
import json
from textblob import TextBlob
import vosk

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store of transcript, sentiments, emotions
transcripts = []
sentiments = []
emotions = []

# Expanded emotions dictionary WITHOUT colors (only words)
EMOTIONS = {
    "Happy": {
        "words": {
            "happy", "glad", "great", "awesome", "joyful", "cheerful", "delighted", "content", 
            "ecstatic", "elated", "thrilled", "pleased", "overjoyed", "jubilant", "radiant", 
            "blissful", "joyous", "smiling", "grinning", "laughing", "sunny", "bright", "sparkling",
            "hopeful", "upbeat", "lighthearted", "satisfied", "enthusiastic", "lively", "buoyant",
            "bubbly", "optimistic", "fortunate", "fortunate"
        }
    },
    "Sad": {
        "words": {
            "sad", "upset", "unhappy", "disappointed", "melancholy", "depressed", "gloomy", 
            "heartbroken", "mournful", "tearful", "downcast", "despair", "grief", "blue", "sorrowful", 
            "forlorn", "somber", "woeful", "dismal", "miserable", "dejected", "lonely", "hurt", 
            "anguished", "tragic", "pained", "downhearted", "disheartened", "distressed", "crushed"
        }
    },
    "Angry": {
        "words": {
            "angry", "mad", "furious", "annoyed", "irate", "resentful", "rage", "outraged", 
            "wrathful", "incensed", "exasperated", "fuming", "seething", "enraged", "cross", 
            "bitter", "vexed", "heated", "provoked", "frustrated", "hostile", "aggravated", 
            "infuriated", "offended", "livid", "resentful", "snappy", "testy", "touchy"
        }
    },
    "Abusive": {
        "words": {
            "stupid", "idiot", "crap", "nonsense", "moron", "fool", "jerk", "dumb", "trash", 
            "garbage", "loser", "scumbag", "imbecile", "dick", "bastard", "asshole", "bitch", 
            "damn", "hell", "shit", "suck", "screw", "bloody", "twat", "prick", "slut", "douche", 
            "retard", "cock", "jerkoff", "wanker", "clown"
        }
    },
    "Excitement": {
        "words": {
            "excited", "thrilled", "yay", "awesome", "eager", "enthusiastic", "ecstatic", "pumped", 
            "energetic", "elated", "joyful", "overjoyed", "exhilarated", "buzzing", "cheered", 
            "animated", "jubilant", "high", "amazed", "stoked", "delighted", "pumped", "overwhelmed"
        }
    },
    "Fear": {
        "words": {
            "afraid", "scared", "worried", "nervous", "anxious", "panicked", "terrified", "frightened", 
            "alarmed", "apprehensive", "uneasy", "fearful", "dread", "jumpy", "timid", "shaky", 
            "spooked", "uneasy", "hesitant", "suspicious", "worried", "paranoid", "restless"
        }
    },
    "Surprise": {
        "words": {
            "wow", "amazing", "unbelievable", "whoa", "astonished", "shocked", "startled", 
            "dumbfounded", "flabbergasted", "stunned", "speechless", "dazed", "bewildered", 
            "astonished", "incredulous", "amazed", "astounded", "gobsmacked", "baffled", 
            "staggered", "dropped", "shaken"
        }
    },
    "Confused": {
        "words": {
            "confused", "unsure", "lost", "unclear", "puzzled", "baffled", "perplexed", "dazed", 
            "bewildered", "stumped", "flummoxed", "disoriented", "muddled", "uncertain", "confounded", 
            "stressed", "mixed", "foggy", "uncertain", "conflicted"
        }
    },
    "Calm": {
        "words": {
            "calm", "relaxed", "peaceful", "fine", "serene", "tranquil", "composed", "collected", 
            "easygoing", "gentle", "cool", "placid", "still", "quiet", "soothing", "mellow", "restful", 
            "stable", "balanced", "content"
        }
    },
    "Thankful": {
        "words": {
            "thank", "thanks", "appreciate", "grateful", "gratitude", "thankful", "obliged", 
            "acknowledge", "recognize", "blessed", "indebted", "appreciative", "cheers", "much obliged"
        }
    },
    # Additional emotions
    "Love": {
        "words": {
            "love", "affection", "fondness", "adoration", "devotion", "caring", "passion", 
            "romantic", "heartfelt", "cherish", "tenderness", "sweetheart", "beloved", "darling", 
            "amour", "infatuated", "intimacy", "attached", "smitten"
        }
    },
    "Boredom": {
        "words": {
            "bored", "uninterested", "dull", "tedious", "monotonous", "weary", "apathetic", "listless", 
            "indifferent", "bland", "tedium", "idle", "lackadaisical", "restless", "unmotivated", 
            "fatigued", "lethargic"
        }
    },
    "Hopeful": {
        "words": {
            "hopeful", "optimistic", "positive", "encouraged", "confident", "expectant", "bright", 
            "bullish", "promising", "upbeat", "reassured", "enthusiastic", "hope", "faith", "trusting"
        }
    },
    "Jealousy": {
        "words": {
            "jealous", "envious", "resentful", "covetous", "possessive", "green-eyed", "grudging", 
            "bitter", "suspicious", "resentment", "hostile"
        }
    },
    "Guilt": {
        "words": {
            "guilty", "remorseful", "sorry", "regretful", "ashamed", "contrite", "repentant", 
            "apologetic", "penitent", "culpable", "conscience-stricken"
        }
    },
    "Pride": {
        "words": {
            "proud", "accomplished", "confident", "satisfied", "pleased", "fulfilled", "triumphant", 
            "successful", "dignified", "honored", "prideful", "boastful", "egotistical", "vain"
        }
    },
    "Loneliness": {
        "words": {
            "lonely", "isolated", "alone", "abandoned", "forsaken", "solitary", "withdrawn", "desolate", 
            "alienated", "homesick", "excluded", "forsaken", "apart", "secluded"
        }
    },
    "Frustration": {
        "words": {
            "frustrated", "annoyed", "irritated", "discontent", "displeased", "vexed", "exasperated", 
            "disgruntled", "impatient", "aggravated", "resentful", "uptight"
        }
    },
    "Relief": {
        "words": {
            "relieved", "comforted", "reassured", "soothed", "alleviated", "calmed", "eased", "content", 
            "unburdened", "unworried", "peaceful"
        }
    },
    "Shame": {
        "words": {
            "ashamed", "embarrassed", "humiliated", "mortified", "shameful", "self-conscious", 
            "regretful", "abashed", "disgraced", "dishonored"
        }
    },
    "Curiosity": {
        "words": {
            "curious", "inquisitive", "interested", "intrigued", "inquiring", "questioning", 
            "nosy", "probing", "searching", "inquiring", "inquiring"
        }
    },
    "Disgust": {
        "words": {
            "disgusted", "revolted", "nauseated", "repulsed", "sickened", "distasteful", 
            "offended", "abhorrent", "loathsome", "detestable", "repugnant"
        }
    },
}

def analyze_sentiment(text: str) -> float:
    return TextBlob(text).sentiment.polarity

def detect_emotions(text: str):
    found = []
    words = set(text.lower().split())
    for emo, data in EMOTIONS.items():
        if words.intersection(data["words"]):
            found.append(emo)
    return found

# Vosk setup
model = vosk.Model("model")  # Make sure 'model' folder is in current directory

q = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

listening = True

def speech_recognition_loop():
    rec = vosk.KaldiRecognizer(model, 16000)
    while listening:
        try:
            data = q.get(timeout=0.5)
        except queue.Empty:
            continue
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            text = res.get("text", "").strip()
            if text:
                transcripts.append(text)
                sentiments.append(analyze_sentiment(text))
                emotions.append(detect_emotions(text))
                if len(transcripts) > 100:
                    transcripts.pop(0)
                    sentiments.pop(0)
                    emotions.pop(0)

def start_streaming_recognition():
    global listening
    listening = True
    loop_thread = threading.Thread(target=speech_recognition_loop, daemon=True)
    loop_thread.start()
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback) as stream:
        print("Listening...")
        while listening:
            sd.sleep(1000)
        stream.stop()
    print("Audio streaming stopped")

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=start_streaming_recognition, daemon=True).start()

class TranscriptResponse(BaseModel):
    transcripts: List[str]
    sentiments: List[float]
    emotions: List[List[str]]

@app.post("/stop_listening")
async def stop_listening():
    global listening
    listening = False
    return {"message": "Listening stopped"}

@app.get("/latest_transcripts", response_model=TranscriptResponse)
async def get_latest():
    return {
        "transcripts": transcripts,
        "sentiments": sentiments,
        "emotions": emotions,
    }
