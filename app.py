from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Flask App
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configure rate limiting
limiter = Limiter(app, key_func=get_remote_address, default_limits=["50 per minute"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API URLs stored in environment variables
DEFILLAMA_YIELDS_URL = os.getenv("DEFILLAMA_YIELDS_URL", "https://yields.llama.fi/pools")
DEFILLAMA_TVL_URL = os.getenv("DEFILLAMA_TVL_URL", "https://api.llama.fi/protocols")
COINGECKO_URL = os.getenv("COINGECKO_URL", "https://api.coingecko.com/api/v3/simple/price")

# ✅ Homepage Route
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Stablecoin Yields API is running!",
        "endpoints": ["/yields", "/stablecoin-prices", "/tvl", "/risk-analysis"]
    })

# ✅ Fetch TVL Data from DeFiLlama
@app.route("/tvl", methods=["GET"])
@limiter.limit("10 per minute")
def get_tvl():
    try:
        response = requests.get(DEFILLAMA_TVL_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        filtered_data = [
            {"name": p["name"], "tvl": p["tvl"], "chain": p["chain"]}
            for p in data if "tvl" in p and p["tvl"] > 0
        ]
        return jsonify(filtered_data)
    except requests.Timeout:
        logger.error("Timeout error when fetching TVL data")
        return jsonify({"error": "Request timed out"}), 504
    except requests.RequestException as e:
        logger.error(f"Failed to fetch TVL data: {e}")
        return jsonify({"error": "Failed to fetch TVL data"}), 500

# ✅ Fetch Stablecoin Prices from CoinGecko
@app.route("/stablecoin-prices", methods=["GET"])
@limiter.limit("20 per minute")
def get_stablecoin_prices():
    try:
        params = {"ids": "usd-coin,dai,tether", "vs_currencies": "usd"}
        response = requests.get(COINGECKO_URL, params=params, timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.Timeout:
        logger.error("Timeout error when fetching stablecoin prices")
        return jsonify({"error": "Request timed out"}), 504
    except requests.RequestException as e:
        logger.error(f"Failed to fetch stablecoin prices: {e}")
        return jsonify({"error": "Failed to fetch stablecoin prices"}), 500

# ✅ Fetch Yield Data with Pagination
@app.route("/yields", methods=["GET"])
@limiter.limit("10 per minute")
def get_yields():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    try:
        response = requests.get(DEFILLAMA_YIELDS_URL, timeout=10)
        response.raise_for_status()
        pools = response.json()

        stablecoin_symbols = ["USDC", "DAI", "USDT"]
        stablecoin_pools = [
            pool for pool in pools
            if pool.get("chain") == "Ethereum" and any(symbol in pool.get("symbol", "") for symbol in stablecoin_symbols)
        ]

        total_pools = len(stablecoin_pools)
        start = (page - 1) * per_page
        end = start + per_page

        paginated_pools = stablecoin_pools[start:end]

        enhanced_pools = []
        for pool in paginated_pools:
            current_apy = float(pool.get("apy", 0) or 0)
            tvl = float(pool.get("tvlUsd", 0) or 0)
            risk_warning = "✅ Stable yield"

            if current_apy > 10:
                risk_warning = "⚠️ High APY! Might be unsustainable."
            elif current_apy < 1:
                risk_warning = "⚠️ Low APY. Look elsewhere."
            
            tvl_status = "✅ Good Liquidity" if tvl > 300_000_000 else "⚠️ Low TVL - Liquidity risk"

            enhanced_pools.append({
                "platform": pool.get("project", ""),
                "symbol": pool.get("symbol", ""),
                "chain": pool.get("chain", ""),
                "apy": current_apy,
                "risk_warning": risk_warning,
                "tvl": tvl,
                "tvl_status": tvl_status
            })

        return jsonify({
            "total_pools": total_pools,
            "page": page,
            "per_page": per_page,
            "pools": enhanced_pools
        })

    except requests.Timeout:
        logger.error("Timeout error when fetching yields")
        return jsonify({"error": "Request timed out"}), 504
    except requests.RequestException as e:
        logger.error(f"Failed to fetch yields: {e}")
        return jsonify({"error": "Failed to fetch yields"}), 500

# ✅ Static Risk Analysis
@app.route("/risk-analysis", methods=["GET"])
@limiter.limit("5 per minute")
def get_risk_scores():
    risk_data = [
        {"platform": "Aave", "risk_score": 10, "comment": "Highly audited, low risk"},
        {"platform": "Compound", "risk_score": 15, "comment": "Well-established, moderate risk"},
        {"platform": "Curve", "risk_score": 20, "comment": "Liquidity fluctuations observed"}
    ]
    return jsonify(risk_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
