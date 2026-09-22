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
    headers = {"User-Agent": "mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) chrome/120.0.0.0 safari/537.36"}
    extracted_posts = []

    target_subreddits = []
    for topic in selected_topics:
        if topic in SUBREDDIT_MAP:
            target_subreddits.extend(SUBREDDIT_MAP[topic])

    if not target_subreddits:
        target_subreddits = ["CryptoCurrency", "travel"]

    for sub in target_subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=4"
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                for post in data.get("data", {}).get("children", []):
                    pdata = post.get("data", {})
                    if not pdata.get("stickied"):
                        extracted_posts.append({
                            "source": f"Reddit (r/{sub})",
                            "title": pdata.get("title"),
                            "text": pdata.get("selftext", "")[:300],
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
        "version": "0.6-Database-Integrated"
    })

# B2B Endpoint - Provjerava API ključ direktno iz Supabase Baze
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
    You are the core AI Engine for **Evolysium B2B API**.
    Provide a clean, ad-free executive feed in English for enterprise client: {client_info['client_name']}.
    Topics requested: {', '.join(selected_topics).upper()}
    
    Instructions:
    1. Eliminate all ads, spam, clickbait, and low-quality posts.
    2. Format clean Markdown output grouped by topic.

    Live Raw Feed:
    {raw_feed}
    """

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
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
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY environment variable is not set."}), 500

    topics_param = request.args.get("topics", "crypto,travel")
    selected_topics = [t.strip().lower() for t in topics_param.split(",")]

    raw_feed = fetch_real_reddit_posts(selected_topics)

    if not raw_feed:
        raw_feed = [
            {"source": "Reddit (r/CryptoCurrency)", "title": "Market dynamics and institutional flow analysis", "text": "Bitcoin holds key moving averages during market consolidation."},
            {"source": "Reddit (r/travel)", "title": "Global travel tips and flight deals", "text": "Off-season flight discounts announced for major routes."}
        ]

    prompt = f"""
    You are the core AI Engine for **Evolysium** — a personal AI gatekeeper platform.
    Your goal is to process REAL incoming social posts and provide a clean, high-value, ad-free feed in ENGLISH.
    Requested topics: {', '.join(selected_topics).upper()}
    
    Instructions:
    1. Inspect all incoming posts from Reddit.
    2. Completely ELIMINATE any posts that are promotional, spam, scams, low-effort meme noise, or clickbait.
    3. For the remaining high-value posts, generate a concise, beautifully formatted executive summary in Markdown.
    4. Group insights clearly by topic (e.g., ### 💰 Cryptocurrency, ### ✈️ Travel, ### 💻 Tech & AI, ### 🎮 Gaming).
    5. Include a brief status note at the end summarizing how many posts were analyzed and filtered.

    Live Raw Feed:
    {raw_feed}
    """

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content(prompt)
        return jsonify({
            "success": True,
            "language": "en",
            "active_topics": selected_topics,
            "clean_feed": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
