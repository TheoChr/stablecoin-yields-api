from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS to allow API access from different domains

# Sample data (Replace with actual database/API integration)
stablecoin_yields = [
    {"platform": "Aave", "symbol": "USDC", "chain": "Ethereum", "apy": 4.2, "tvl": 500000000},
    {"platform": "Compound", "symbol": "DAI", "chain": "Ethereum", "apy": 3.8, "tvl": 300000000},
    {"platform": "Aave", "symbol": "DAI", "chain": "Ethereum", "apy": 4.5, "tvl": 250000000},
    {"platform": "Compound", "symbol": "USDT", "chain": "Ethereum", "apy": 3.9, "tvl": 200000000},
    {"platform": "Aave", "symbol": "USDT", "chain": "Ethereum", "apy": 4.1, "tvl": 220000000},
    {"platform": "Yearn", "symbol": "USDC", "chain": "Ethereum", "apy": 5.0, "tvl": 150000000},
    {"platform": "Yearn", "symbol": "DAI", "chain": "Ethereum", "apy": 4.8, "tvl": 120000000},
    {"platform": "Yearn", "symbol": "USDT", "chain": "Ethereum", "apy": 4.7, "tvl": 100000000},
    {"platform": "Curve", "symbol": "USDC", "chain": "Ethereum", "apy": 3.5, "tvl": 700000000},
    {"platform": "Curve", "symbol": "DAI", "chain": "Ethereum", "apy": 3.6, "tvl": 650000000},
    {"platform": "Curve", "symbol": "USDT", "chain": "Ethereum", "apy": 3.4, "tvl": 600000000},
]  # Example data, replace this with an actual API or database query


@app.route("/yields", methods=["GET"])
def get_yields():
    """Fetch stablecoin yields with optional filtering and limit."""
    
    # Get query parameters
    platform = request.args.get("platform")  # Filter by platform (Aave, Compound, etc.)
    chain = request.args.get("chain")  # Filter by blockchain (Ethereum, BSC, etc.)
    stablecoin = request.args.get("stablecoin")  # Filter by stablecoin symbol (USDC, DAI, etc.)
    
    # Default limit is 10, but can be adjusted via query parameter
    try:
        limit = int(request.args.get("limit", 10))  # Convert to integer
        if limit < 1 or limit > 100:  # Restrict limits to reasonable range
            limit = 10
    except ValueError:
        limit = 10  # Fallback to default if invalid value

    # Apply filters if provided
    filtered_yields = [
        y for y in stablecoin_yields
        if (not platform or y["platform"].lower() == platform.lower()) and
           (not chain or y["chain"].lower() == chain.lower()) and
           (not stablecoin or y["symbol"].lower() == stablecoin.lower())
    ]

    # Limit results
    return jsonify(filtered_yields[:limit])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
