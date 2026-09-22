import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Initialize Gemini AI
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def fetch_real_reddit_posts():
    """Povlači prave objave sa subreddita r/CryptoCurrency i r/travel."""
    subreddits = ["CryptoCurrency", "travel"]
    headers = {"User-Agent": "EvolysiumBot/0.2 (by /u/EvolysiumApp)"}
    extracted_posts = []

    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=5"
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for post in data.get("data", {}).get("children", []):
                    pdata = post.get("data", {})
                    # Zanemarujemo automatske PIN-ovane objave
                    if not pdata.get("stickied"):
                        extracted_posts.append({
                            "source": f"Reddit (r/{sub})",
                            "title": pdata.get("title"),
                            "text": pdata.get("selftext", "")[:300],  # Uzimamo prvih 300 karaktera
                            "url": f"https://reddit.com{pdata.get('permalink')}"
                        })
        except Exception as e:
            print(f"Error fetching r/{sub}: {e}")

    return extracted_posts

@app.route("/")
def home():
    return jsonify({"status": "Evolysium AI Backend Online", "version": "0.3-LiveFeeds"})

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY environment variable is not set."}), 500

    # Povlačenje pravih podataka
    raw_feed = fetch_real_reddit_posts()

    if not raw_feed:
        return jsonify({"error": "Failed to fetch live social data."}), 500
    
    prompt = f"""
    You are the core AI Engine for **Evolysium** — a personal AI gatekeeper platform.
    Your goal is to process REAL incoming social posts and provide a clean, high-value, ad-free feed in ENGLISH.
    
    Instructions:
    1. Inspect all incoming posts from Reddit.
    2. Completely ELIMINATE any posts that are promotional, spam, scams, low-effort meme noise, or clickbait.
    3. For the remaining high-value posts, generate a concise, beautifully formatted executive summary in Markdown.
    4. Group insights by topic (e.g., ### 💰 Cryptocurrency, ### ✈️ Travel Insights).
    5. Mention key highlights, market sentiment, or useful user tips.
    6. Include a brief status note at the end summarizing how many posts were analyzed.

    Live Raw Feed:
    {raw_feed}
    """

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content(prompt)
        return jsonify({
            "success": True,
            "language": "en",
            "topics": ["Crypto", "Travel"],
            "sources": ["Reddit Live API"],
            "clean_feed": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
