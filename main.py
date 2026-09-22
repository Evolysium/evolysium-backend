import os
from flask import Flask, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize Gemini AI
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def simulate_raw_social_feed():
    return [
        {"source": "Reddit (r/CryptoCurrency)", "type": "post", "content": "Bitcoin breaks key resistance levels again as analysts debate the impact of new macroeconomic indicators on market momentum."},
        {"source": "X (Twitter)", "type": "ad", "content": "SPONSORED: Buy 100x MEME COIN now and become a millionaire in 24 hours! Don't miss out!"},
        {"source": "Reddit (r/travel)", "type": "post", "content": "Pro tips for traveling to Japan on a budget: How to get the JR Pass, find affordable off-season stays, and save on dining."},
        {"source": "X (Twitter)", "type": "post", "content": "European airlines announce major summer flight sales. Round-trip flights available under €150 to top destinations."},
        {"source": "X (Twitter)", "type": "ad", "content": "SPONSORED: Best travel insurance plan with 50% discount if you sign up within the next 2 hours!"}
    ]

@app.route("/")
def home():
    return jsonify({"status": "Evolysium AI Backend Online", "version": "0.2-Global"})

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY environment variable is not set."}), 500

    raw_feed = simulate_raw_social_feed()
    
    prompt = f"""
    You are the core AI Engine for **Evolysium** — a personal AI gatekeeper platform.
    Your goal is to provide a clean, high-value, ad-free feed in ENGLISH for topics: **Crypto** and **Travel**.
    
    Instructions:
    1. Carefully inspect all incoming social posts.
    2. Completely ELIMINATE all advertisements, sponsored posts, scams, clickbait, and noise.
    3. For the valid, remaining posts, generate a concise, beautifully structured executive summary in English using Markdown syntax.
    4. Group insights by topic (e.g., ### 💰 Cryptocurrency, ### ✈️ Travel & Flights).
    5. Add a brief status note at the end summarizing how many ads/scams were blocked (e.g., "🛡️ Status: Blocked 2 sponsored ads and low-quality offers").

    Raw input feed:
    {raw_feed}
    """

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content(prompt)
        return jsonify({
            "success": True,
            "language": "en",
            "topics": ["Crypto", "Travel"],
            "sources": ["Reddit", "X"],
            "clean_feed": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
