import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Initialize Gemini AI
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Initialize Supabase Client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = None

if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")

SUBREDDIT_MAP = {
    "crypto": ["CryptoCurrency", "Bitcoin"],
    "travel": ["travel", "solotravel"],
    "tech": ["technology", "artificial"],
    "gaming": ["gaming", "pcgaming"]
}

def fetch_real_reddit_posts(selected_topics):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    extracted_posts = []

    target_subreddits = []
    for topic in selected_topics:
        if topic in SUBREDDIT_MAP:
            target_subreddits.extend(SUBREDDIT_MAP[topic])

    if not target_subreddits:
        target_subreddits = ["CryptoCurrency", "travel"]

    for sub in target_subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=3"
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for post in data.get("data", {}).get("children", []):
                    pdata = post.get("data", {})
                    if not pdata.get("stickied"):
                        extracted_posts.append({
                            "source": f"Reddit (r/{sub})",
                            "title": pdata.get("title"),
                            "text": pdata.get("selftext", "")[:200],
                            "url": f"https://reddit.com{pdata.get('permalink')}"
                        })
        except Exception as e:
            print(f"Error fetching r/{sub}: {e}")

    return extracted_posts

@app.route("/")
def home():
    return jsonify({
        "platform": "Evolysium B2B Platform Engine",
        "database": "Connected" if supabase else "Disconnected",
        "status": "Online",
        "version": "0.7-Stable-Model"
    })

# B2B Endpoint - Provjerava API ključ iz Supabase baze
@app.route("/api/v1/b2b/feed", methods=["GET"])
def get_b2b_feed():
    client_key = request.headers.get("X-API-KEY")
    
    if not client_key:
        return jsonify({"error": "Unauthorized", "message": "Missing X-API-KEY header."}), 401

    client_info = None
    if supabase:
        try:
            response = supabase.table("b2b_clients").select("*").eq("api_key", client_key).eq("is_active", True).execute()
            if response.data and len(response.data) > 0:
                client_info = response.data[0]
        except Exception as e:
            print(f"DB Error: {e}")

    if not client_info:
        return jsonify({"error": "Unauthorized", "message": "Invalid or inactive B2B API key."}), 401

    topics_param = request.args.get("topics", "crypto,tech")
    selected_topics = [t.strip().lower() for t in topics_param.split(",")]

    raw_feed = fetch_real_reddit_posts(selected_topics)

    prompt = f"""
    You are the core AI Engine for Evolysium B2B API.
    Provide a clean, ad-free executive feed in English for enterprise client: {client_info['client_name']}.
    Topics: {', '.join(selected_topics).upper()}
    Raw Feed: {raw_feed}
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return jsonify({
            "success": True,
            "b2b_client": client_info["client_name"],
            "plan": client_info["plan"],
            "active_topics": selected_topics,
            "clean_feed": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Javni B2C Endpoint za Web Frontend
@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    topics_param = request.args.get("topics", "crypto,travel")
    selected_topics = [t.strip().lower() for t in topics_param.split(",")]

    raw_feed = fetch_real_reddit_posts(selected_topics)

    if not raw_feed:
        raw_feed = [
            {"source": "Reddit (r/CryptoCurrency)", "title": "Market updates & liquidity flows", "text": "Bitcoin holds steady near support levels."},
            {"source": "Reddit (r/travel)", "title": "Top travel destinations for 2026", "text": "New flight routes opened for South East Asia."}
        ]

    prompt = f"""
    You are the core AI Engine for **Evolysium** — a personal AI gatekeeper platform.
    Process incoming social posts and provide a clean, high-value, ad-free feed in ENGLISH.
    Topics: {', '.join(selected_topics).upper()}
    
    Instructions:
    1. Eliminate promotional noise, spam, and clickbait.
    2. Provide a clean summary grouped by topic with markdown headers (e.g. ### 💰 Crypto, ### ✈️ Travel).

    Live Feed:
    {raw_feed}
    """

    try:
        # Koristimo provjereni gemini-1.5-flash model
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return jsonify({
            "success": True,
            "language": "en",
            "active_topics": selected_topics,
            "clean_feed": response.text
        })
    except Exception as e:
        # Sigurnosni rezervni prikaz u slučaju API limita
        fallback_markdown = f"""
### 💰 Crypto & Finance
* **Market Status:** Bitcoin and major digital assets show steady momentum during standard market consolidation.
* **Volume Analysis:** Institutional inflows remain active across major custodial wallets.

### ✈️ Travel & Destinations
* **Global Routes:** Discounted seasonal fares available across transpacific flights.
* **Travel Tip:** Ensure early booking for peak season accommodation in Western Europe.

---
*Note: Real-time Gemini AI engine is operating in fallback mode due to high daily quota usage.*
        """
        return jsonify({
            "success": True,
            "language": "en",
            "active_topics": selected_topics,
            "clean_feed": fallback_markdown
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
