import streamlit as st
import pandas as pd
import re
import requests
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Real-time Call Sentiment Dashboard", layout="wide")

API_URL = "http://localhost:8000/latest_transcripts"  # Change if backend hosted elsewhere

# --- Sidebar ---
import requests

with st.sidebar:
    st.title("Help Desk Sentiment Analyzer")
    st.markdown("""
    **About:**  
    Real-time sentiment analysis of ongoing help desk calls.
    """)
    st.markdown("---")
    st.header("Controls")
    call_id = st.text_input("Call ID", value="CALL12345")
    auto_update = st.checkbox("Auto Update Sentiment", value=True)
    update_interval = st.slider("Update Interval (seconds)", 1, 10, 3)
    st.markdown("---")

    st.header("Read Aloud")

    if st.button("🔊 Read Conversation Aloud"):
        convo_text = "<br>".join(st.session_state.transcript) if st.session_state.get("transcript") else "No conversation yet."
        js_code = f"""
        <script>
        const text = `{convo_text.replace("`", "'")}`;
        const utterance = new SpeechSynthesisUtterance(text.replace(/<br>/g, ' '));
        speechSynthesis.cancel();  // Stop any ongoing speech
        speechSynthesis.speak(utterance);
        </script>
        """
        components.html(js_code, height=0, width=0)

    if st.button("⏹️ Stop Reading"):
        js_stop = """
        <script>
        speechSynthesis.cancel();
        </script>
        """
        components.html(js_stop, height=0, width=0)

    # New Stop Listening button: call backend to stop voice listening
    if st.button("🛑 Stop Listening"):
        try:
            response = requests.post("http://localhost:8000/stop_listening")
            if response.status_code == 200:
                st.success("Voice listening stopped on backend.")
            else:
                st.error(f"Failed to stop listening. Status code: {response.status_code}")
        except Exception as e:
            st.error(f"Error stopping listening: {e}")

    # Sentiment summary placeholders
    st.subheader("Sentiment Summary")
    pos_count = st.empty()
    neu_count = st.empty()
    neg_count = st.empty()
    st.markdown("---")
    st.caption("Developed by YourName | 2025")

# --- Auto-refresh every update_interval seconds if auto_update enabled ---
if auto_update:
    st_autorefresh(interval=update_interval * 1000, key="datarefresh")

emotions = {
    "Happy": {
        "words": {
            "happy", "glad", "great", "awesome", "joyful", "cheerful", "delighted",
            "content", "ecstatic", "elated", "thrilled", "joy", "smile", "blessed",
            "jubilant", "merry", "upbeat", "radiant"
        },
        "color": "#d4edda", "text_color": "#155724"
    },
    "Excitement": {  # merged similar words with Happy color
        "words": {
            "excited", "thrilled", "yay", "awesome", "eager", "enthusiastic",
            "elated", "ecstatic", "overjoyed", "pumped"
        },
        "color": "#d4edda", "text_color": "#155724"
    },

    "Sad": {
        "words": {
            "sad", "upset", "unhappy", "disappointed", "melancholy", "depressed",
            "gloomy", "heartbroken", "down", "blue", "mournful", "sorrowful",
            "wistful", "dismal", "grief"
        },
        "color": "#cce5ff", "text_color": "#004085"
    },
    "Loneliness": {  # related to Sad, kept distinct color
        "words": {
            "lonely", "isolated", "alone", "abandoned", "forsaken", "solitary",
            "desolate", "withdrawn"
        },
        "color": "#b0c4de", "text_color": "#334466"
    },

    "Angry": {
        "words": {
            "angry", "mad", "furious", "annoyed", "irate", "resentful", "rage",
            "outraged", "cross", "frustrated", "heated", "vexed", "aggravated"
        },
        "color": "#f8d7da", "text_color": "#721c24"
    },
    "Frustration": {  # merged "annoyed", "irritated" overlap with Angry but distinct color
        "words": {
            "frustrated", "annoyed", "irritated", "discontent", "displeased",
            "exasperated", "disgruntled"
        },
        "color": "#ffb347", "text_color": "#663300"
    },

    "Abusive": {
        "words": {
            "stupid", "idiot", "crap", "nonsense", "moron", "fool", "jerk",
            "dumb", "imbecile", "loser", "scumbag", "bastard", "trash"
        },
        "color": "#ff4c4c", "text_color": "#700000"
    },

    "Fear": {
        "words": {
            "afraid", "scared", "worried", "nervous", "anxious", "panicked",
            "terrified", "fearful", "alarmed", "uneasy", "apprehensive"
        },
        "color": "#e6ccff", "text_color": "#4b0082"
    },

    "Surprise": {
        "words": {
            "wow", "amazing", "unbelievable", "whoa", "astonished", "shocked",
            "stunned", "startled", "speechless", "flabbergasted"
        },
        "color": "#ffe5b4", "text_color": "#cc7a00"
    },

    "Confused": {
        "words": {
            "confused", "unsure", "lost", "unclear", "puzzled", "baffled",
            "perplexed", "bewildered", "muddled", "uncertain"
        },
        "color": "#d6d8db", "text_color": "#383d41"
    },

    "Calm": {
        "words": {
            "calm", "relaxed", "peaceful", "fine", "serene", "tranquil",
            "composed", "collected", "soothing", "gentle"
        },
        "color": "#d1ecf1", "text_color": "#0c5460"
    },

    "Thankful": {
        "words": {
            "thank", "thanks", "appreciate", "grateful", "gratitude",
            "thankful", "obliged", "indebted", "recognition"
        },
        "color": "#fff8dc", "text_color": "#665c00"
    },

    "Love": {
        "words": {
            "love", "affection", "fondness", "adoration", "devotion",
            "caring", "passion", "romantic", "heart", "cherish", "darling",
            "sweetheart", "beloved", "intimate"
        },
        "color": "#ffc0cb", "text_color": "#800000"
    },

    "Boredom": {
        "words": {
            "bored", "uninterested", "dull", "tedious", "monotonous",
            "weary", "apathetic", "listless", "uninspired", "indifferent"
        },
        "color": "#f0e68c", "text_color": "#666600"
    },

    "Hopeful": {
        "words": {
            "hopeful", "optimistic", "positive", "encouraged", "confident",
            "expectant", "upbeat", "bright", "buoyant", "enthused"
        },
        "color": "#d1f2a5", "text_color": "#336600"
    },

    "Jealousy": {
        "words": {
            "jealous", "envious", "resentful", "covetous", "green-eyed",
            "begrudging", "possessive"
        },
        "color": "#dda0dd", "text_color": "#550055"
    },

    "Guilt": {
        "words": {
            "guilty", "remorseful", "sorry", "regretful", "ashamed",
            "contrite", "repentant"
        },
        "color": "#e0cda9", "text_color": "#665500"
    },

    "Pride": {
        "words": {
            "proud", "accomplished", "confident", "satisfied", "pleased",
            "self-esteem", "triumphant", "boastful", "glory"
        },
        "color": "#ffd700", "text_color": "#994d00"
    },

    "Relief": {
        "words": {
            "relieved", "comforted", "reassured", "soothed", "alleviated",
            "unburdened", "released"
        },
        "color": "#98fb98", "text_color": "#2f4f2f"
    },

    "Shame": {
        "words": {
            "ashamed", "embarrassed", "humiliated", "mortified", "shameful",
            "abashed", "chagrined"
        },
        "color": "#f5a9a9", "text_color": "#660000"
    },

    "Curiosity": {
        "words": {
            "curious", "inquisitive", "interested", "intrigued",
            "inquiring", "questioning", "inquiring"
        },
        "color": "#add8e6", "text_color": "#004466"
    },

    "Disgust": {
        "words": {
            "disgusted", "revolted", "nauseated", "repulsed", "grossed out",
            "sickened", "abhorrent"
        },
        "color": "#8fbc8f", "text_color": "#204020"
    }
}

# Initialize session state once
if "transcript" not in st.session_state:
    st.session_state.transcript = []
if "sentiments" not in st.session_state:
    st.session_state.sentiments = []
if "emotions" not in st.session_state:
    st.session_state.emotions = []
if "__reset_trigger__" not in st.session_state:
    st.session_state["__reset_trigger__"] = False  # Dummy state for reset rerun

# --- Helper functions ---

def fetch_live_data():
    try:
        response = requests.get(API_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching live data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Exception fetching live data: {e}")
        return None

def sentiment_label(score):
    if score > 0.5:
        return "Positive 😊", "🟢"
    elif score > 0:
        return "Slightly Positive 🙂", "🟡"
    elif score == 0:
        return "Neutral 😐", "🟡"
    elif score > -0.5:
        return "Slightly Negative 🙁", "🟠"
    else:
        return "Negative 😠", "🔴"

def highlight_text(text):
    tokens = re.findall(r'\w+|\W+', text)
    result = []
    for word in tokens:
        lw = word.lower()
        highlighted = False
        for emo, info in emotions.items():
            if lw.strip() in info["words"]:
                span = f"<span style='background-color:{info['color']}; color:{info['text_color']}; font-weight:bold'>{word}</span>"
                result.append(span)
                highlighted = True
                break
        if not highlighted:
            result.append(word)
    return "".join(result)

# --- Main Page ---
st.title("📞 Live Call Sentiment Analysis")
st.subheader(f"Call ID: {call_id}")

# Placeholders
# Placeholders - create once
transcript_placeholder = st.empty()
sentiment_placeholder = st.empty()
chart_placeholder = st.empty()
full_convo_placeholder = st.empty()
legend_placeholder = st.empty()

def update_ui():
    # Show latest 5 lines with highlights
    latest_transcripts = st.session_state.transcript[-5:]
    highlighted_transcript = "<br>".join([highlight_text(line) for line in latest_transcripts])
    transcript_placeholder.markdown("### Transcript (latest 5 lines)")
    transcript_placeholder.markdown(highlighted_transcript, unsafe_allow_html=True)

    # Current sentiment
    if st.session_state.sentiments:
        last_sentiment = st.session_state.sentiments[-1]
        label, emoji = sentiment_label(last_sentiment)
        sentiment_placeholder.markdown(f"### Current Sentiment: {label} {emoji}")
        sentiment_placeholder.progress((last_sentiment + 1) / 2)
    else:
        sentiment_placeholder.markdown("No sentiment data yet.")

    # Sentiment trend chart
    if st.session_state.sentiments:
        df = pd.DataFrame({
            "Segment": list(range(1, len(st.session_state.sentiments) + 1)),
            "Sentiment": st.session_state.sentiments
        })
        chart_placeholder.line_chart(df.set_index("Segment"))
    else:
        chart_placeholder.empty()

    # Sentiment summary counts and percentages
    pos = sum(1 for s in st.session_state.sentiments if s > 0.5)
    neu = sum(1 for s in st.session_state.sentiments if -0.5 <= s <= 0.5)
    neg = sum(1 for s in st.session_state.sentiments if s < -0.5)
    total = len(st.session_state.sentiments) or 1
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style="background-color:#d4edda; padding:15px; border-radius:10px; text-align:center; color:#155724; font-weight:bold;">
            <h3>Positive</h3>
            <p style="font-size: 24px;">{pos} ({pos/total*100:.1f}%)</p>
            <p style="font-size: 30px;">🟢</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color:#d1ecf1; padding:15px; border-radius:10px; text-align:center; color:#0c5460; font-weight:bold;">
            <h3>Neutral</h3>
            <p style="font-size: 24px;">{neu} ({neu/total*100:.1f}%)</p>
            <p style="font-size: 30px;">🟡</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background-color:#f8d7da; padding:15px; border-radius:10px; text-align:center; color:#721c24; font-weight:bold;">
            <h3>Negative</h3>
            <p style="font-size: 24px;">{neg} ({neg/total*100:.1f}%)</p>
            <p style="font-size: 30px;">🔴</p>
        </div>
        """, unsafe_allow_html=True)
    st.sidebar.markdown(f"**Positive:** {pos} ({pos/total*100:.1f}%)")
    st.sidebar.markdown(f"**Neutral:** {neu} ({neu/total*100:.1f}%)")
    st.sidebar.markdown(f"**Negative:** {neg} ({neg/total*100:.1f}%)")

    # Full conversation with highlights
    full_convo_highlighted = "<br>".join([highlight_text(line) for line in st.session_state.transcript])
    full_convo_placeholder.markdown("### Full Conversation")
    full_convo_placeholder.markdown(full_convo_highlighted, unsafe_allow_html=True)

    # Highlight legend
    legend_html = "**Highlight Legend:**<br>"
    for emo, info in emotions.items():
        legend_html += f"<span style='background-color:{info['color']}; color:{info['text_color']}; font-weight:bold'>&nbsp;&nbsp;{emo}&nbsp;&nbsp;</span>  "
    legend_placeholder.markdown(legend_html, unsafe_allow_html=True)


# Fetch and update session state only if new data exists and length differs
if auto_update:
    data = fetch_live_data()
    if data:
        if len(data.get("transcripts", [])) != len(st.session_state.transcript):
            st.session_state.transcript = data.get("transcripts", [])
            st.session_state.sentiments = data.get("sentiments", [])
            st.session_state.emotions = data.get("emotions", [])

# Now update UI once per run
update_ui()

# Reset button triggers immediate rerun
if st.button("Reset"):
    st.session_state.transcript = []
    st.session_state.sentiments = []
    st.session_state.emotions = []
    st.experimental_rerun()
