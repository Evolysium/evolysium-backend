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
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=2"
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for post in data.get("data", {}).get("children", []):
                    pdata = post.get("data", {})
                    if not pdata.get("stickied"):
                        extracted_posts.append({
                            "type": "reddit",
                            "source": f"Reddit (r/{sub})",
                            "title": pdata.get("title"),
                            "text": pdata.get("selftext", "")[:180] + "...",
                            "url": f"https://reddit.com{pdata.get('permalink')}"
                        })
        except Exception as e:
            print(f"Error fetching r/{sub}: {e}")

    return extracted_posts

def fetch_tiktok_content(selected_topics):
    """
    Generates structured, clean TikTok trending signals for selected topics.
    In production, this plugs into a TikTok RapidAPI/RSS scraper bridge.
    """
    tiktok_database = {
        "crypto": [
            {
                "type": "tiktok",
                "source": "TikTok (@cryptobrief)",
                "author": "@cryptobrief",
                "title": "Top 3 Crypto Signals Watchlist for 2026 📈",
                "summary": "Breakdown of liquidity movement and top performing layer-2 tokens this week. Clean actionable insight without the noise.",
                "url": "https://www.tiktok.com",
                "image": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop"
            }
        ],
        "travel": [
            {
                "type": "tiktok",
                "source": "TikTok (@nomad_guides)",
                "author": "@nomad_guides",
                "title": "Hidden Travel Gems in South East Asia ✈️",
                "summary": "Affordable solo-travel destinations with high-speed internet and great infrastructure for digital nomads.",
                "url": "https://www.tiktok.com",
                "image": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop"
            }
        ],
        "tech": [
            {
                "type": "tiktok",
                "source": "TikTok (@future_tech_ai)",
                "author": "@future_tech_ai",
                "title": "New On-Device AI Benchmarks Explained 🤖",
                "summary": "How localized neural networks are processing complex queries directly on mobile hardware in under 10ms.",
                "url": "https://www.tiktok.com",
                "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop"
            }
        ],
        "gaming": [
            {
                "type": "tiktok",
                "source": "TikTok (@gamer_vault)",
                "author": "@gamer_vault",
                "title": "Unreal Engine 5.5 Next-Gen Graphics Test 🎮",
                "summary": "Real-time ray tracing acceleration on modern mobile GPUs evaluated side-by-side.",
                "url": "https://www.tiktok.com",
                "image": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&auto=format&fit=crop"
            }
        ]
    }

    tiktok_cards = []
    for topic in selected_topics:
        if topic in tiktok_database:
            tiktok_cards.extend(tiktok_database[topic])

    return tiktok_cards

@app.route("/")
def home():
    return jsonify({
        "platform": "Evolysium B2B & B2C Engine",
        "database": "Connected" if supabase else "Disconnected",
        "tiktok_engine": "Active",
        "status": "Online",
        "version": "0.9-TikTok-Integrated"
    })

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    topics_param = request.args.get("topics", "crypto,travel")
    selected_topics = [t.strip().lower() for t in topics_param.split(",")]

    # Fetch both Reddit posts and TikTok trending content
    reddit_posts = fetch_real_reddit_posts(selected_topics)
    tiktok_posts = fetch_tiktok_content(selected_topics)

    cards = []

    # Format TikTok content
    for item in tiktok_posts:
        cards.append({
            "type": "tiktok",
            "title": item["title"],
            "summary": item["summary"],
            "source": item["source"],
            "author": item.get("author", "@tiktok"),
            "url": item["url"],
            "image": item["image"]
        })

    # Format Reddit content
    topic_images = {
        "crypto": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop",
        "travel": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop",
        "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop",
        "gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&auto=format&fit=crop"
    }

    for item in reddit_posts:
        img_url = topic_images.get("tech")
        for t in selected_topics:
            if t in topic_images:
                img_url = topic_images[t]
                break

        cards.append({
            "type": "reddit",
            "title": item.get("title"),
            "summary": item.get("text", "")[:180] + "...",
            "source": item.get("source", "Reddit Stream"),
            "author": "Reddit Feed",
            "url": item.get("url", "#"),
            "image": img_url
        })

    return jsonify({
        "success": True,
        "language": "en",
        "active_topics": selected_topics,
        "items": cards
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
