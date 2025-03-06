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
def fetch_tvl_data():
    url = "https://api.llama.fi/tvl"
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@app.route("/tvl", methods=["GET"])
def get_tvl():
    """Fetch Total Value Locked (TVL) data from DeFiLlama."""
    return jsonify(fetch_tvl_data())

# ✅ Fetch live data from DeFi APIs
def fetch_aave_data():
    url = "https://api.thegraph.com/subgraphs/name/aave/protocol-v3"
    query = {
        "query": """
        {
          reserves(where: {symbol_in: ["USDC", "DAI", "USDT"]}) {
            symbol
            liquidityRate
            availableLiquidity
          }
        }
        """
    }
    try:
        response = requests.post(url, json=query)
        data = response.json()

        # 🔹 Check if "data" exists in the response
        if "data" not in data or "reserves" not in data["data"]:
            return [{"error": "Invalid response from Aave API"}]

        markets = []
        for reserve in data["data"]["reserves"]:
            markets.append({
                "platform": "Aave",
                "symbol": reserve["symbol"],
                "chain": "Ethereum",
                "apy": float(reserve["liquidityRate"]) / 1e27 * 100,  # Convert to %
                "tvl": float(reserve["availableLiquidity"]) / 1e18  # Convert to USD
            })
        return markets
    except Exception as e:
        return [{"error": str(e)}]

def fetch_compound_data():
    url = "https://api.compound.finance/api/v2/ctoken"
    try:
        response = requests.get(url)
        data = response.json()

        # 🔹 Ensure valid response
        if "cToken" not in data:
            return [{"error": "Invalid response from Compound API"}]

        markets = []
        for ctoken in data["cToken"]:
            if ctoken["symbol"] in ["cUSDC", "cDAI", "cUSDT"]:
                markets.append({
                    "platform": "Compound",
                    "symbol": ctoken["underlying_symbol"],
                    "chain": "Ethereum",
                    "apy": float(ctoken["supply_rate"]["value"]) * 100,
                    "tvl": float(ctoken["total_supply"]) * float(ctoken["exchange_rate"]["value"]) / 1e18
                })
        return markets
    except Exception as e:
        return [{"error": str(e)}]

def fetch_curve_data():
    url = "https://api.curve.fi/api/getPools/ethereum/main"
    try:
        response = requests.get(url)
        data = response.json()

        # 🔹 Ensure valid response
        if "data" not in data or "poolData" not in data["data"]:
            return [{"error": "Invalid response from Curve API"}]

        markets = []
        for pool in data["data"]["poolData"]:
            if any(token in pool["coins"] for token in ["USDC", "DAI", "USDT"]):
                markets.append({
                    "platform": "Curve",
                    "symbol": pool["coins"][0],  # Example: First stablecoin in the pool
                    "chain": "Ethereum",
                    "apy": float(pool["gaugeApr"] or 0),  # APR from Curve gauge
                    "tvl": float(pool["usdTotal"])
                })
        return markets
    except Exception as e:
        return [{"error": str(e)}]

def fetch_coingecko_data():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "usd-coin,dai,tether", "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ✅ New endpoint to fetch live yields
@app.route("/yields", methods=["GET"])
def get_yields():
    """Fetch real-time stablecoin yields with optional filtering and limit."""

    # Fetch live data from all sources
    aave_data = fetch_aave_data()
    compound_data = fetch_compound_data()
    curve_data = fetch_curve_data()

    # 🔹 Ensure all sources return valid data
    if isinstance(aave_data, list) and "error" in aave_data[0]:
        return jsonify({"error": "Aave API issue", "details": aave_data})
    if isinstance(compound_data, list) and "error" in compound_data[0]:
        return jsonify({"error": "Compound API issue", "details": compound_data})
    if isinstance(curve_data, list) and "error" in curve_data[0]:
        return jsonify({"error": "Curve API issue", "details": curve_data})

    all_yields = aave_data + compound_data + curve_data

    # Apply filtering
    platform = request.args.get("platform")
    chain = request.args.get("chain")
    stablecoin = request.args.get("stablecoin")
    limit = int(request.args.get("limit", 10))

    filtered_yields = [
        y for y in all_yields
        if (not platform or y["platform"].lower() == platform.lower()) and
           (not chain or y["chain"].lower() == chain.lower()) and
           (not stablecoin or y["symbol"].lower() == stablecoin.lower())
    ]

    return jsonify(filtered_yields[:limit])

# ✅ New endpoint to check stablecoin prices (for depeg detection)
@app.route("/stablecoin-prices", methods=["GET"])
def get_stablecoin_prices():
    """Fetch live stablecoin prices from CoinGecko."""
    return jsonify(fetch_coingecko_data())

# ✅ Risk Analysis Endpoint
@app.route("/risk-analysis", methods=["GET"])
def get_risk_scores():
    """Return risk scores for different DeFi platforms."""
    risk_data = [
        {"platform": "Aave", "risk_score": 10},
        {"platform": "Compound", "risk_score": 5},
        {"platform": "Curve", "risk_score": 8}
    ]
    return jsonify(risk_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
