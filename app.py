from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# ✅ Fetch live data from DeFi APIs
def fetch_aave_data():
    url = "https://api.thegraph.com/subgraphs/name/aave/protocol-v3"
    query = {
        "query": """
        {
          reserves(where: {symbol_in: ["USDC", "DAI", "USDT"]}) {
            symbol
            liquidityRate
            variableBorrowRate
            stableBorrowRate
            availableLiquidity
          }
        }
        """
    }
    try:
        response = requests.post(url, json=query)
        data = response.json()
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

    # Get query parameters
    platform = request.args.get("platform")
    chain = request.args.get("chain")
    stablecoin = request.args.get("stablecoin")

    try:
        limit = int(request.args.get("limit", 10))
        if limit < 1 or limit > 100:
            limit = 10
    except ValueError:
        limit = 10

    # Fetch live data from all sources
    all_yields = fetch_aave_data() + fetch_compound_data() + fetch_curve_data()

    # Filter results
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
