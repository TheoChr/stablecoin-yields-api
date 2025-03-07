from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# ✅ Initialize Firebase
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Homepage route
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Stablecoin Yields API is running!",
        "endpoints": ["/yields", "/stablecoin-prices", "/tvl", "/risk-analysis", "/yield-trends"]
    })

# ✅ Fetch TVL Data from DeFiLlama
@app.route("/tvl", methods=["GET"])
def get_tvl():
    url = "https://api.llama.fi/tvl"
    try:
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Fetch stablecoin prices from CoinGecko
@app.route("/stablecoin-prices", methods=["GET"])
def get_stablecoin_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "usd-coin,dai,tether", "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Fetch Yield Data from DeFiLlama & Store in Firebase
@app.route("/yields", methods=["GET"])
def get_yields():
    """Fetch real-time stablecoin yields and store in Firestore for historical trend analysis."""
    url = "https://yields.llama.fi/pools"
    
    try:
        response = requests.get(url)
        data = response.json()

        stablecoin_pools = [
            pool for pool in data["data"]
            if pool["chain"] == "Ethereum" and pool["symbol"] in ["USDC", "DAI", "USDT"]
        ]

        enhanced_pools = []
        for pool in stablecoin_pools:
            platform = pool["project"]
            symbol = pool["symbol"]
            current_apy = pool["apy"]
            tvl = pool["tvlUsd"]
            timestamp = datetime.utcnow().isoformat()

            # ✅ Save to Firestore (Only latest APY for each platform-symbol pair)
            doc_ref = db.collection("stablecoin_yields").document(f"{platform}-{symbol}")
            doc_ref.set({
                "platform": platform,
                "symbol": symbol,
                "apy": current_apy,
                "tvl": tvl,
                "timestamp": timestamp
            })

            enhanced_pools.append({
                "platform": platform,
                "symbol": symbol,
                "apy": current_apy,
                "tvl": tvl,
                "tvl_status": "✅ Healthy Liquidity" if tvl > 300_000_000 else "⚠️ TVL Dropping - Possible liquidity risk"
            })

        return jsonify(enhanced_pools)

    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Yield Trend Analysis Endpoint
@app.route("/yield-trends", methods=["GET"])
def get_yield_trends():
    """Analyze yield trends by comparing current and past APY data."""
    trends = []
    stablecoin_yields_ref = db.collection("stablecoin_yields")
    docs = stablecoin_yields_ref.stream()

    for doc in docs:
        data = doc.to_dict()
        platform = data["platform"]
        symbol = data["symbol"]
        current_apy = data["apy"]
        tvl = data["tvl"]

        # Fetch past APY from Firestore history
        past_doc = db.collection("yield_history").document(f"{platform}-{symbol}").get()
        if past_doc.exists:
            past_data = past_doc.to_dict()
            past_apy = past_data.get("apy", current_apy)
        else:
            past_apy = current_apy

        # Determine Trend
        trend = "🟢 Increasing" if current_apy > past_apy else "🔴 Decreasing"
        trend_comment = f"(Previously {past_apy}%, Now {current_apy}%)"

        trends.append({
            "platform": platform,
            "symbol": symbol,
            "apy_trend": trend + " " + trend_comment,
            "tvl_status": "✅ Healthy Liquidity" if tvl > 300_000_000 else "⚠️ TVL Dropping - Possible liquidity risk"
        })

        # ✅ Update Firestore history
        db.collection("yield_history").document(f"{platform}-{symbol}").set({
            "apy": current_apy,
            "timestamp": datetime.utcnow().isoformat()
        })

    return jsonify(trends)

# ✅ Risk Analysis Endpoint
@app.route("/risk-analysis", methods=["GET"])
def get_risk_scores():
    """Returns risk scores based on liquidity, audits, yield stability & decentralization."""
    risk_data = [
        {"platform": "Aave", "risk_score": 10, "comment": "Highly audited, low risk"},
        {"platform": "Compound", "risk_score": 8, "comment": "Well-established, moderate risk"},
        {"platform": "Curve", "risk_score": 7, "comment": "Liquidity fluctuations observed"},
    ]
    return jsonify(risk_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
