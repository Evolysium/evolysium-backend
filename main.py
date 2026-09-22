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

# Mapiranje slika po novim kategorijama sadržaja
CATEGORY_IMAGES = {
    "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop",
    "gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&auto=format&fit=crop",
    "lifestyle": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=600&auto=format&fit=crop",
    "funny": "https://images.unsplash.com/photo-1513360371669-4adf3dd7dff8?w=600&auto=format&fit=crop",
    "luxury": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&auto=format&fit=crop",
    "architecture": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&auto=format&fit=crop",
    "18plus": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=600&auto=format&fit=crop",
    "crypto": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop",
    "travel": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop"
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
    "travel": "travel"
}

def fetch_reddit_data(categories):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    posts = []
    
    for cat in categories:
        sub = REDDIT_MAP.get(cat, "all")
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=2"
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
                            "image": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["tech"])
                        })
        except Exception as e:
            print(f"Reddit error on {cat}: {e}")
            
    return posts

def generate_mock_platform_data(platform, categories):
    results = []
    platform_names = {
        "tiktok": "TikTok Trending",
        "x": "X (Twitter) Feed",
        "linkedin": "LinkedIn Professional"
    }
    
    for cat in categories:
        img_url = CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["tech"])
        
        if platform == "tiktok":
            results.append({
                "platform": "tiktok",
                "category": cat,
                "source": "TikTok (@creator_signal)",
                "title": f"Top Trending {cat.capitalize()} Video Signal",
                "summary": f"Viral short-form breakdown covering key updates and unfiltered insights in {cat}.",
                "url": "https://www.tiktok.com",
                "image": img_url
            })
        elif platform == "x":
            results.append({
                "platform": "x",
                "category": cat,
                "source": "X / Twitter",
                "title": f"Verified Stream: {cat.capitalize()} Insights",
                "summary": f"Ad-free summary of high-engagement discussions and updates from top voices in {cat}.",
                "url": "https://x.com",
                "image": img_url
            })
        elif platform == "linkedin":
            results.append({
                "platform": "linkedin",
                "category": cat,
                "source": "LinkedIn Industry",
                "title": f"Executive Overview: {cat.capitalize()} Industry Trends",
                "summary": f"Professional analysis and market breakdown focused on modern developments in {cat}.",
                "url": "https://www.linkedin.com",
                "image": img_url
            })
            
    return results

@app.route("/")
def home():
    return jsonify({
        "platform": "Evolysium Multi-Platform AI Engine",
        "status": "Online",
        "version": "1.0-Multi-Source-Categories"
    })

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    # Parsovanje izabranih platformi (npr. tiktok,x,reddit,linkedin)
    platforms_param = request.args.get("platforms", "tiktok,reddit,x,linkedin")
    selected_platforms = [p.strip().lower() for p in platforms_param.split(",")]

    # Parsovanje izabranih kategorija (npr. tech,gaming,luxury)
    categories_param = request.args.get("categories", "tech,gaming,luxury,lifestyle")
    selected_categories = [c.strip().lower() for c in categories_param.split(",")]

    all_cards = []

    # Dohvati Reddit podatke ako je Reddit odabran
    if "reddit" in selected_platforms:
        reddit_items = fetch_reddit_data(selected_categories)
        all_cards.extend(reddit_items)

    # Generiši prilagođene signal kartice za ostale odabrane platforme
    for platform in selected_platforms:
        if platform in ["tiktok", "x", "linkedin"]:
            platform_items = generate_mock_platform_data(platform, selected_categories)
            all_cards.extend(platform_items)

    # Rezervne kartice ako nema povratnih podataka
    if not all_cards:
        all_cards.append({
            "platform": "system",
            "category": "tech",
            "source": "Evolysium AI",
            "title": "Welcome to Evolysium AI Gatekeeper",
            "summary": "Select your favorite platforms and content categories above to start streaming filtered signals.",
            "url": "#",
            "image": CATEGORY_IMAGES["tech"]
        })

    return jsonify({
        "success": True,
        "active_platforms": selected_platforms,
        "active_categories": selected_categories,
        "items": all_cards
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
