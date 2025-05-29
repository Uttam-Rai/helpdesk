import requests

data = {
    "text": "Hello, I am happy with the support!",
    "sentiment_score": 0.8,
    "emotions": {"happy": 0.9, "sad": 0.0, "angry": 0.0}
}

resp = requests.post("http://localhost:8000/push_segment", json=data)
print(resp.json())
