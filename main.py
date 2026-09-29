import os
import random
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import google.generativeai as genai
from supabase import create_client, Client
import stripe

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

# Media pool za Evolysium
CATEGORY_MEDIA_POOL = {
    "tech": {
        "images": [
            "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop"
        ],
        "videos": [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
        ]
    },
    "gaming": {
        "images": [
            "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=600&auto=format&fit=crop"
        ],
        "videos": [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
        ]
    },
    "crypto": {
        "images": [
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop"
        ],
        "videos": [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoy.mp4"
        ]
    },
    "lifestyle": {
        "images": [
            "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop"
        ],
        "videos": [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4"
        ]
    },
    "luxury": {
        "images": [
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600&auto=format&fit=crop"
        ],
        "videos": [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackSeeTheWorld.mp4"
        ]
    },
    "18plus": {
        "images": [
            "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=600&auto=format&fit=crop"
        ],
        "videos": [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4"
        ]
    }
}

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

def fetch_reddit_data(categories):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    posts = []
    for cat in categories:
        sub = REDDIT_MAP.get(cat, "all")
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                for p in data.get("data", {}).get("children", []):
                    pdata = p.get("data", {})
                    if not pdata.get("stickied"):
                        pool = CATEGORY_MEDIA_POOL.get(cat, CATEGORY_MEDIA_POOL["tech"])
                        posts.append({
                            "platform": "evolysium",
                            "category": cat,
                            "source": "Evolysium Stream",
                            "title": f"⚡ {pdata.get('title')}",
                            "summary": (pdata.get("selftext") or pdata.get("title"))[:180] + "...",
                            "url": f"https://reddit.com{pdata.get('permalink')}",
                            "image": random.choice(pool["images"]),
                            "video_url": random.choice(pool["videos"]),
                            "score": random.randint(92, 99),
                            "sentiment": "Evolysium Signal",
                            "keywords": [cat, "evolysium"]
                        })
        except Exception as e:
            print(f"Reddit error on {cat}: {e}")
    return posts

def generate_mock_platform_data(platform, categories):
    results = []
    hype_titles = {
        "tech": [
            "Evolysium Core Update: Decentralized AI Agent Routing Live",
            "Next-Gen Protocol Architecture Released on Evolysium Network"
        ],
        "gaming": [
            "Evolysium Arena: High-Performance Sandbox Node Integration",
            "Optimized Latency Framework for Distributed Gaming Streams"
        ],
        "crypto": [
            "Evolysium Liquidity Stream: Real-Time Node Tracking Active",
            "Cross-Chain Asset Flow and Validator Synchronization"
        ],
        "lifestyle": [
            "Evolysium Flow State: Optimized Workspace Protocol for Creators",
            "Minimalist Infrastructure & High-Output Daily Routine"
        ],
        "luxury": [
            "Evolysium Vault: Exclusive Asset Tracking and Verified Drops",
            "High-End Architecture & Private Network Highlights"
        ],
        "18plus": [
            "Evolysium Private Stream: Encrypted Creator Network Access",
            "Secured Monetization Channels for Independent Publishers"
        ]
    }
    hype_summaries = [
        "Evolysium verified data stream. Direct signal processing with zero latency.",
        "Active validator node consensus reached across the Evolysium ecosystem."
    ]
    for cat in categories:
        pool = CATEGORY_MEDIA_POOL.get(cat, CATEGORY_MEDIA_POOL["tech"])
        img_url = random.choice(pool["images"])
        vid_url = random.choice(pool["videos"])
        t_list = hype_titles.get(cat, ["Evolysium High-Impact Signal Detected"])
        chosen_title = random.choice(t_list)
        chosen_summary = random.choice(hype_summaries)
        score_base = random.randint(90, 99)
        results.append({
            "platform": "evolysium",
            "category": cat,
            "source": "Evolysium Network",
            "title": f"⚡ {chosen_title}",
            "summary": chosen_summary,
            "url": "https://evolysium.github.io/evolysium-frontend/",
            "image": img_url,
            "video_url": vid_url,
            "score": score_base,
            "sentiment": "Evolysium Signal",
            "keywords": [cat, "evolysium", "alpha"]
        })
    return results

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    platforms_param = request.args.get("platforms", "evolysium")
    selected_platforms = [p.strip().lower() for p in platforms_param.split(",") if p.strip()]

    categories_param = request.args.get("categories", "tech,gaming,luxury,lifestyle,crypto,18plus")
    selected_categories = [c.strip().lower() for c in categories_param.split(",") if c.strip()]

    search_query = request.args.get("search", "").strip().lower()

    all_cards = []

    if supabase:
        try:
            res = supabase.table("vibe_trails").select("*").in_("category", selected_categories).execute()
            if res.data:
                all_cards.extend(res.data)
        except Exception as e:
            print(f"Supabase read error: {e}")

    if not all_cards:
        for platform in selected_platforms:
            all_cards.extend(generate_mock_platform_data(platform, selected_categories))

    if search_query:
        all_cards = [
            card for card in all_cards 
            if search_query in card.get("title", "").lower() 
            or search_query in card.get("summary", "").lower()
            or any(search_query in str(k).lower() for k in card.get("keywords", []))
        ]

    all_cards.sort(key=lambda x: x.get("score", 0), reverse=True)

    if not all_cards:
        all_cards.append({
            "platform": "evolysium",
            "category": "tech",
            "source": "Evolysium Core",
            "title": "⚡ Evolysium Stream Clean",
            "summary": "No active cluster found. System operational.",
            "url": "#",
            "image": CATEGORY_MEDIA_POOL["tech"]["images"][0],
            "video_url": CATEGORY_MEDIA_POOL["tech"]["videos"][0],
            "score": 100,
            "sentiment": "System Edge",
            "keywords": ["evolysium"]
        })

    return jsonify({
        "success": True,
        "count": len(all_cards),
        "active_platforms": selected_platforms,
        "active_categories": selected_categories,
        "items": all_cards
    })

@app.route("/api/posts/create", methods=["POST"])
def create_post():
    data = request.json or {}
    
    platform = "evolysium"
    category = data.get("category", "tech").strip().lower()
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    image = data.get("image", "").strip()
    video_url = data.get("video_url", "").strip()
    is_story = data.get("is_story", False)

    if not title:
        return jsonify({"success": False, "error": "Naslov objave je obavezan."}), 400

    pool = CATEGORY_MEDIA_POOL.get(category, CATEGORY_MEDIA_POOL["tech"])
    
    new_signal = {
        "platform": platform,
        "category": category,
        "source": f"Evolysium // {'Story' if is_story else 'Objava'}",
        "title": title,
        "summary": summary or title,
        "url": data.get("url", "https://evolysium.github.io/evolysium-frontend/"),
        "image": image if image else random.choice(pool["images"]),
        "video_url": video_url if video_url else random.choice(pool["videos"]),
        "score": 99,  
        "sentiment": "Evolysium User Alpha",
        "keywords": [category, "evolysium", "story" if is_story else "post"]
    }

    if supabase:
        try:
            response = supabase.table("vibe_trails").insert(new_signal).execute()
            return jsonify({
                "success": True, 
                "message": "Uspješno objavljeno na Evolysiumu!",
                "data": response.data
            })
        except Exception as e:
            print(f"Supabase insert error: {e}")
            return jsonify({"success": False, "error": f"Greška pri spremanju u bazu: {str(e)}"}), 500
    else:
        return jsonify({"success": False, "error": "Supabase baza nije konfigurirana na poslužitelju."}), 500

@app.route("/api/auth/register", methods=["POST"])
def register_user():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "error": "Email i lozinka su obavezni."}), 400

    if not supabase:
        return jsonify({"success": False, "error": "Supabase nije konfiguriran."}), 500

    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        return jsonify({
            "success": True, 
            "message": "Registracija uspješna!",
            "data": res.user
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    data = request.json or {}
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "error": "Email je obavezan."}), 400

    if not supabase:
        return jsonify({"success": False, "error": "Supabase nije aktivan."}), 500

    try:
        supabase.table("newsletter").insert({"email": email}).execute()
        return jsonify({"success": True, "message": "Uspješno prijavljeni na Evolysium newsletter!"})
    except Exception as e:
        return jsonify({"success": False, "error": "Ovaj email je već prijavljen ili je došlo do greške."}), 400

@app.route("/api/tiers", methods=["GET"])
def get_tiers():
    tiers_data = [
        {
            "id": "explorer",
            "name": "Explorer",
            "price": 0,
            "features": [
                "Access to Evolysium public feed",
                "Basic story viewing",
                "Standard data refresh rate",
                "Community support access"
            ]
        },
        {
            "id": "creator",
            "name": "Pro / Personal",
            "price": 8.99,
            "features": [
                "Ad-free Evolysium stream",
                "Private/Public story controls",
                "Real-time signal filtering",
                "Priority email support"
            ]
        },
        {
            "id": "business",
            "name": "Business / Creator",
            "price": 11.99,
            "features": [
                "Priority public post placement",
                "Advanced story analytics",
                "Custom API data exports",
                "Multi-user workspace access"
            ]
        },
        {
            "id": "elite",
            "name": "VIP / Enterprise",
            "price": 24.99,
            "features": [
                "White-label Evolysium feed",
                "VIP status badge & perks",
                "Dedicated account manager",
                "Custom webhooks & integrations"
            ]
        }
    ]
    return jsonify({"success": True, "tiers": tiers_data})

@app.route("/api/payment/create-checkout-session", methods=["POST"])
def create_checkout_session():
    data = request.json or {}
    tier = data.get("tier", "creator")
    email = data.get("email")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()

    if not stripe_key or len(stripe_key) < 10:
        return jsonify({"success": False, "error": "STRIPE_SECRET_KEY nedostaje."}), 500

    stripe.api_key = stripe_key

    prices = {
        "explorer": 0,
        "creator": 899,
        "business": 1199,
        "elite": 2499
    }

    amount = prices.get(tier, 899)
    
    if amount == 0:
        return jsonify({"success": False, "error": "Free tier."}), 400

    frontend_url = os.environ.get("FRONTEND_URL", "https://evolysium.github.io/evolysium-frontend/")

    try:
        session_params = {
            'line_items': [{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f'Evolysium - {tier.capitalize()} Pass',
                    },
                    'unit_amount': amount,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': f"{frontend_url}?success=true",
            'cancel_url': f"{frontend_url}?canceled=true",
        }
        
        if email:
            session_params['customer_email'] = email

        checkout_session = stripe.checkout.Session.create(**session_params)
        return jsonify({"success": True, "url": checkout_session.url})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
