import os
from flask import Flask, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Inicijalizacija Gemini AI
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def simulate_raw_social_feed():
    return [
        {"source": "Reddit (r/CryptoCurrency)", "type": "post", "content": "Bitcoin ponovno probija ključne razine otpora. Analitičari raspravljaju o utjecaju novih makroekonomskih pokazatelja."},
        {"source": "X (Twitter)", "type": "ad", "content": "SPONSORED: Kupi 100x MEME COIN odmah i postani milijunaš za 24h! Ne propusti priliku!"},
        {"source": "Reddit (r/travel)", "type": "post", "content": "Savjeti za trostruko jeftinije putovanje u Japan: Kako kupiti JR Pass i pronaći povoljan smještaj van sezone."},
        {"source": "X (Twitter)", "type": "post", "content": "Airlines imaju ljetne rasprodaje letova za Europu. Pronašli smo povratne karte za 150 EUR."},
        {"source": "X (Twitter)", "type": "ad", "content": "SPONSORED: Najbolje osiguranje za putovanja! Popust 50% ako se registrirate u sljedeća 2 sata!"}
    ]

@app.route("/")
def home():
    return jsonify({"status": "Evolysium AI Backend is Online", "version": "0.1-PoC"})

@app.route("/api/feed", methods=["GET"])
def get_clean_feed():
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY nije postavljen na Renderu."}), 500

    raw_feed = simulate_raw_social_feed()
    
    prompt = f"""
    Djeluješ kao osobni AI gatekeeper za aplikaciju Evolysium.
    Korisnik želi vidjeti Isključivo korisne informacije vezane uz teme: KRIPTOVALUTE i PUTOVANJA.
    
    Tvoj zadatak:
    1. Pažljivo pregledaj ulazne objave s društvenih mreža.
    2. Potpuno ELIMINIRAJ sve oglase, sponzorirane objave, prevare i bezvrijedan šum.
    3. Za preostale objave napravi kratak, strukturan i elegantan sažetak po temama na hrvatskom jeziku.
    
    Ulazni podaci s mreža:
    {raw_feed}
    """

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content(prompt)
        return jsonify({
            "success": True,
            "topics": ["Kriptovalute", "Putovanja"],
            "sources": ["Reddit", "X"],
            "clean_feed": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
