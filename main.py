import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Initialize Gemini AI
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Mapa podržanih tema i odgovarajućih subreddita
SUBREDDIT_MAP = {
    "crypto": ["CryptoCurrency", "Bitcoin"],
    "travel": ["travel", "solotravel"],
    "tech": ["technology", "artificial"],
    "gaming": ["gaming", "pcgaming"]
}

def fetch_real_reddit_posts(selected_topics):
    """Povlači prave objave s odabranih subreddita."""
    headers = {"User-Agent": "mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) chrome/120.0.0.0 safari/537.36"}
    extracted_posts = []

    # Odredi koje subreddite povlačimo na temelju korisničkog odabira
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
    return jsonify({"status": "Evolysium AI Backend Online", "version": "0.4-MultiTopic"})

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY environment variable is not set."}), 500

    # Dohvaćanje odabranih tema iz query parametra (npr. ?topics=crypto,tech)
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
