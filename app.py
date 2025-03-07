from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from cachetools import TTLCache, cached
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Cache configuration: TTLCache with a max size of 100 items and TTLs for different endpoints
yield_cache = TTLCache(maxsize=100, ttl=600)  # 10 minutes for yields
price_cache = TTLCache(maxsize=50, ttl=300)   # 5 minutes for prices
tvl_cache = TTLCache(maxsize=30, ttl=1800)    # 30 minutes for TVL data
risk_cache = TTLCache(maxsize=20, ttl=3600)   # 1 hour for risk data

# API Base URLs
DEFILLAMA_YIELDS_URL = "https://yields.llama.fi/pools"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Helper function to fetch API data
def fetch_data(url, params=None, retries=2):
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                app.logger.error(f"Error fetching data from {url}: {e}")
                return None
            app.logger.warning(f"Retry {attempt+1}/{retries} for {url}")

# Homepage route
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Stablecoin Yields API",
        "version": "2.0",
        "endpoints": ["/yields", "/stablecoin-prices", "/tvl", "/risk-analysis"]
    })

# Fetch Yield Data
@app.route("/yields", methods=["GET"])
def get_yields():
    platform = request.args.get("platform", "").lower()
    chain = request.args.get("chain", "").lower()
    stablecoin = request.args.get("stablecoin", "").upper()
    
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))
        min_apy = float(request.args.get("min_apy", 0))
        min_tvl = float(request.args.get("min_tvl", 0))
    except ValueError:
        limit = 20
        min_apy = 0
        min_tvl = 0

    @cached(yield_cache)
    def cached_yields():
        data = fetch_data(DEFILLAMA_YIELDS_URL)
        
        if not data or not isinstance(data, list):  # Ensure it's a list before looping
            return {"error": "Failed to fetch yield data"}

        stablecoin_identifiers = ["USDC", "USDT", "DAI"]
        filtered_pools = []

        for pool in data:
            pool_symbol = pool.get("symbol", "").upper()
            if any(stable in pool_symbol for stable in stablecoin_identifiers):
                project = pool.get("project", "").lower()
                pool_chain = pool.get("chain", "").lower()
                apy = pool.get("apy", 0)
                tvl = pool.get("tvlUsd", 0)

                if ((not platform or platform in project) and
                    (not chain or chain in pool_chain) and
                    (not stablecoin or stablecoin in pool_symbol) and
                    apy >= min_apy and tvl >= min_tvl):
                    
                    filtered_pools.append({
                        "platform": pool.get("project", "Unknown"),
                        "symbol": pool_symbol,
                        "chain": pool.get("chain", "Unknown"),
                        "apy": apy,
                        "tvl_usd": tvl,
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

        return sorted(filtered_pools, key=lambda x: x["apy"], reverse=True)[:limit]

    return jsonify(cached_yields())

# Fetch stablecoin prices
@app.route("/stablecoin-prices", methods=["GET"])
def get_stablecoin_prices():
    stablecoin = request.args.get("stablecoin", "")
    
    @cached(price_cache)
    def cached_prices():
        params = {
            "ids": "usd-coin,tether,dai",
            "vs_currencies": "usd"
        }
        data = fetch_data(f"{COINGECKO_BASE_URL}/simple/price", params=params)
        return data if data else {"error": "Failed to fetch stablecoin prices"}

    return jsonify(cached_prices())

# Fetch TVL Data
@app.route("/tvl", methods=["GET"])
def get_tvl():
    protocol = request.args.get("protocol")

    @cached(tvl_cache)
    def cached_tvl():
        url = f"https://api.llama.fi/protocols"
        data = fetch_data(url)
        if not data or not isinstance(data, list):
            return {"error": "Failed to fetch TVL data"}
        
        if protocol:
            return next((p for p in data if p["name"].lower() == protocol.lower()), {"error": "Protocol not found"})

        return data

    return jsonify(cached_tvl())

# Fetch risk analysis
@app.route("/risk-analysis", methods=["GET"])
def get_risk_analysis():
    platform = request.args.get("platform", "").lower()

    @cached(risk_cache)
    def cached_risk():
        risk_data = {
            "aave": {"risk_score": 10, "audit_status": "Multiple audits by OpenZeppelin"},
            "compound": {"risk_score": 8, "audit_status": "Audited by Trail of Bits"},
            "curve": {"risk_score": 7, "audit_status": "Audited by CertiK"}
        }
        return risk_data.get(platform, risk_data) if platform else risk_data

    return jsonify(cached_risk())

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
