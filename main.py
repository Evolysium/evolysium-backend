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
        "version": "0.8-Rate-Limiting-Active"
    })

# B2B Endpoint - Provjerava API ključ i limit potrošnje
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

    # Provjera kvote/limita potrošnje
    current_usage = client_info.get("current_usage", 0) or 0
    request_limit = client_info.get("request_limit", 1000) or 1000

    if current_usage >= request_limit:
        return jsonify({
            "error": "Rate Limit Exceeded",
            "message": f"Monthly limit of {request_limit} requests reached. Please upgrade your plan.",
            "usage": current_usage,
            "limit": request_limit
        }), 429

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

        # Uvećaj brojač potrošnje u bazi za +1
        new_usage = current_usage + 1
        supabase.table("b2b_clients").update({"current_usage": new_usage}).eq("id", client_info["id"]).execute()

        return jsonify({
            "success": True,
            "b2b_client": client_info["client_name"],
            "plan": client_info["plan"],
            "usage": {
                "used": new_usage,
                "limit": request_limit,
                "remaining": request_limit - new_usage
            },
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

    # Ako Reddit ne vrati podatke, koristimo dinamičke rezervne kartice za izabrane teme
    if not raw_feed:
        fallback_data = {
            "crypto": {
                "title": "Bitcoin Signals Strong Momentum Above Support",
                "text": "Institutional trading volume continues to show healthy inflows across major global cryptocurrency liquidity pools.",
                "source": "r/CryptoCurrency",
                "url": "https://reddit.com/r/CryptoCurrency",
                "image": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop"
            },
            "travel": {
                "title": "Top Off-Grid Travel Destinations for 2026",
                "text": "New flight routes and sustainable eco-resorts open across South East Asia and Northern Europe.",
                "source": "r/travel",
                "url": "https://reddit.com/r/travel",
                "image": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop"
            },
            "tech": {
                "title": "Next-Gen Autonomous AI Models Released",
                "text": "Developers deploy highly efficient on-device neural networks operating with sub-millisecond response times.",
                "source": "r/technology",
                "url": "https://reddit.com/r/technology",
                "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop"
            },
            "gaming": {
                "title": "Unreal Engine 5.5 Visual Benchmarks Surpass Expectations",
                "text": "Next-gen gaming titles achieve full ray-tracing hardware acceleration on modern GPU architectures.",
                "source": "r/gaming",
                "url": "https://reddit.com/r/gaming",
                "image": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&auto=format&fit=crop"
            }
        }

        cards = []
        for topic in selected_topics:
            if topic in fallback_data:
                cards.append(fallback_data[topic])

        if not cards:
            cards.append(fallback_data["crypto"])

        return jsonify({
            "success": True,
            "language": "en",
            "active_topics": selected_topics,
            "items": cards
        })

    # Slika ovisno o primarnoj temi
    topic_images = {
        "crypto": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop",
        "travel": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop",
        "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop",
        "gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&auto=format&fit=crop"
    }

    cards = []
    for item in raw_feed:
        img_url = topic_images.get("tech")
        for t in selected_topics:
            if t in topic_images:
                img_url = topic_images[t]
                break

        cards.append({
            "title": item.get("title"),
            "summary": item.get("text", "")[:180] + "...",
            "source": item.get("source", "Global Stream"),
            "url": item.get("url", "#"),
            "image": img_url
        })

    return jsonify({
        "success": True,
        "language": "en",
        "active_topics": selected_topics,
        "items": cards
    })
