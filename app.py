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

# ✅ Fetch Yield Data from DeFiLlama with **Historical Analysis**
@app.route("/yields", methods=["GET"])
def get_yields():
    """Fetch real-time stablecoin yields and compare with historical data."""
    url = "https://yields.llama.fi/pools"
    
    try:
        response = requests.get(url)
        data = response.json()

        # Sample historical yield data (You need to store real past APYs for comparison)
        historical_yields = {
            "Aave-USDC": {"7d": 4.8, "30d": 5.1},
            "Compound-USDC": {"7d": 4.2, "30d": 4.5},
            "Curve-DAI": {"7d": 6.0, "30d": 6.8},
        }

        # Filter only stablecoin pools
        stablecoin_pools = [
            pool for pool in data["data"]
            if pool["chain"] == "Ethereum" and pool["symbol"] in ["USDC", "DAI", "USDT"]
        ]

        # Analyze trends and risks
        enhanced_pools = []
        for pool in stablecoin_pools:
            platform_symbol = f"{pool['project']}-{pool['symbol']}"
            current_apy = pool["apy"]
            past_7d_apy = historical_yields.get(platform_symbol, {}).get("7d", current_apy)
            past_30d_apy = historical_yields.get(platform_symbol, {}).get("30d", current_apy)

            # APY Trend Analysis
            trend = "🟢 Increasing" if current_apy > past_7d_apy else "🔴 Decreasing"
            trend_comment = f" (Previously {past_7d_apy}% last 7 days, {past_30d_apy}% last 30 days)"

            # Risk Warnings
            risk_warning = "✅ Stable yield"  
            if current_apy > 10:
                risk_warning = "⚠️ High APY! This could be a temporary liquidity incentive."
            elif current_apy < 1:
                risk_warning = "⚠️ Extremely low APY. Consider alternative options."

            # TVL Monitoring
            tvl_status = "✅ Healthy Liquidity" if pool["tvlUsd"] > 300_000_000 else "⚠️ TVL Dropping - Possible liquidity risk"

            enhanced_pools.append({
                "platform": pool["project"],
                "symbol": pool["symbol"],
                "chain": pool["chain"],
                "apy": current_apy,
                "apy_trend": trend + trend_comment,
                "risk_warning": risk_warning,
                "tvl": pool["tvlUsd"],
                "tvl_status": tvl_status,
            })

        return jsonify(enhanced_pools)

    except Exception as e:
        return jsonify({"error": str(e)})

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
