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

# Mapiranje slika po kategorijama
CATEGORY_IMAGES = {
    "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop",
    "gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&auto=format&fit=crop",
    "lifestyle": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=600&auto=format&fit=crop",
    "funny": "https://images.unsplash.com/photo-1513360371669-4adf3dd7dff8?w=600&auto=format&fit=crop",
    "luxury": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&auto=format&fit=crop",
    "architecture": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&auto=format&fit=crop",
    "crypto": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop",
    "travel": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop",
    "18plus": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=600&auto=format&fit=crop"
}

}

# Subreddit mapiranje za Reddit izvore
REDDIT_MAP = {
    "tech": "technology",
    "gaming": "gaming",
    "lifestyle": "lifestyle",
    "funny": "funny",
    "luxury": "Luxury",
    "architecture": "ArchitecturePorn",
    "crypto": "CryptoCurrency",
    "travel": "travel",
    "18plus": "nsfw"
}
"
}

def fetch_reddit_data(categories):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    posts = []
    
    for cat in categories:
        sub = REDDIT_MAP.get(cat, "all")
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=3"
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                for p in data.get("data", {}).get("children", []):
                    pdata = p.get("data", {})
                    if not pdata.get("stickied"):
                        posts.append({
                            "platform": "reddit",
                            "category": cat,
                            "source": f"Reddit (r/{sub})",
                            "title": pdata.get("title"),
                            "summary": (pdata.get("selftext") or pdata.get("title"))[:180] + "...",
                            "url": f"https://reddit.com{pdata.get('permalink')}",
                            "image": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["tech"]),
                            "score": 95,
                            "sentiment": "Community Insight",
                            "keywords": [cat, "reddit", sub]
                        })
        except Exception as e:
            print(f"Reddit error on {cat}: {e}")
            
    return posts

def generate_mock_platform_data(platform, categories):
    results = []
    
    # Različite AI oznake i score po kategorijama
    sentiment_map = {
        "tech": "High Value",
        "gaming": "Trending",
        "crypto": "Market Shift",
        "lifestyle": "Educational"
    }

    score_map = {
        "tech": 94,
        "gaming": 88,
        "crypto": 91,
        "lifestyle": 85
    }

    for cat in categories:
        img_url = CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["tech"])
        score = score_map.get(cat, 82)
        sentiment = sentiment_map.get(cat, "Trending Signal")
        
        if platform == "tiktok":
            results.append({
                "platform": "tiktok",
                "category": cat,
                "source": "TikTok (@creator_signal)",
                "title": f"Top Trending {cat.capitalize()} Video Signal",
                "summary": f"Viral short-form breakdown covering key updates and unfiltered insights in {cat}.",
                "url": "https://www.tiktok.com",
                "image": img_url,
                "score": score,
                "sentiment": sentiment,
                "keywords": [cat, "tiktok", "viral", "video"]
            })
        elif platform == "x":
            results.append({
                "platform": "x",
                "category": cat,
                "source": "X / Twitter",
                "title": f"Verified Stream: {cat.capitalize()} Insights",
                "summary": f"Ad-free summary of high-engagement discussions and updates from top voices in {cat}.",
                "url": "https://x.com",
                "image": img_url,
                "score": score + 2,
                "sentiment": sentiment,
                "keywords": [cat, "x", "twitter", "insights"]
            })
        elif platform == "linkedin":
            results.append({
                "platform": "linkedin",
                "category": cat,
                "source": "LinkedIn Industry",
                "title": f"Executive Overview: {cat.capitalize()} Industry Trends",
                "summary": f"Professional analysis and market breakdown focused on modern developments in {cat}.",
                "url": "https://www.linkedin.com",
                "image": img_url,
                "score": score + 4,
                "sentiment": "High Value",
                "keywords": [cat, "linkedin", "business", "pro"]
            })
            
    return results

@app.route("/")
def home():
    return jsonify({
        "platform": "Evolysium Multi-Platform AI Engine",
        "status": "Online",
        "version": "1.1-AI-Scoring-Keywords",
        "gemini_active": bool(api_key)
    })

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    platforms_param = request.args.get("platforms", "tiktok,reddit,x,linkedin")
    selected_platforms = [p.strip().lower() for p in platforms_param.split(",") if p.strip()]

    categories_param = request.args.get("categories", "tech,gaming,luxury,lifestyle")
    selected_categories = [c.strip().lower() for c in categories_param.split(",") if c.strip()]

    search_query = request.args.get("search", "").strip().lower()

    all_cards = []

    # Dohvati Reddit podatke
    if "reddit" in selected_platforms:
        reddit_items = fetch_reddit_data(selected_categories)
        all_cards.extend(reddit_items)

    # Generiši signal kartice za ostale platforme
    for platform in selected_platforms:
        if platform in ["tiktok", "x", "linkedin"]:
            platform_items = generate_mock_platform_data(platform, selected_categories)
            all_cards.extend(platform_items)

    # Filtriranje po ključnoj reči (search parametru) ako postoji
    if search_query:
        filtered_cards = []
        for card in all_cards:
            in_title = search_query in card.get("title", "").lower()
            in_summary = search_query in card.get("summary", "").lower()
            in_keywords = any(search_query in k.lower() for k in card.get("keywords", []))
            if in_title or in_summary or in_keywords:
                filtered_cards.append(card)
        all_cards = filtered_cards

    # Sortiranje svih kartica po AI Quality Score-u (najveći rezultat prvi)
    all_cards.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Rezervne kartice ako nema povratnih podataka
    if not all_cards:
        all_cards.append({
            "platform": "system",
            "category": "tech",
            "source": "Evolysium AI",
            "title": "No Matching Signals Found",
            "summary": "Try adjusting your search keywords or choosing additional content categories.",
            "url": "#",
            "image": CATEGORY_IMAGES["tech"],
            "score": 100,
            "sentiment": "System Info",
            "keywords": ["system"]
        })

    return jsonify({
        "success": True,
        "count": len(all_cards),
        "active_platforms": selected_platforms,
        "active_categories": selected_categories,
        "items": all_cards
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
