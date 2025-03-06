from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# ✅ Homepage route to prevent 404 errors
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Stablecoin Yields API is running!",
        "endpoints": ["/yields", "/stablecoin-prices", "/tvl", "/risk-analysis"]
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

# ✅ Fetch live stablecoin prices from CoinGecko
@app.route("/stablecoin-prices", methods=["GET"])
def get_stablecoin_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "usd-coin,dai,tether", "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Fetch market data from CoinLore
@app.route("/market-data", methods=["GET"])
def get_market_data():
    url = "https://api.coinlore.net/api/tickers/"
    try:
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Fetch DeFi protocol data from DefiLlama
@app.route("/defi-protocols", methods=["GET"])
def get_defi_protocols():
    url = "https://api.llama.fi/protocols"
    try:
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Fetch DIA price feed data
@app.route("/dia-price-feed", methods=["GET"])
def get_dia_price_feed():
    url = "https://api.diadata.org/v1/asset/USD"
    try:
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Risk Analysis Endpoint
@app.route("/risk-analysis", methods=["GET"])
def get_risk_scores():
    risk_data = [
        {"platform": "Aave", "risk_score": 10},
        {"platform": "Compound", "risk_score": 5},
        {"platform": "Curve", "risk_score": 8}
    ]
    return jsonify(risk_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
