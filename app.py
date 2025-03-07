from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from cachetools import TTLCache, cached

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Cache settings
yield_cache = TTLCache(maxsize=100, ttl=600)  # 10 minutes for yields

# API URLs
DEFILLAMA_YIELDS_URL = "https://yields.llama.fi/pools"

# Helper function to fetch API data with error handling
def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        app.logger.error(f"API error: {e}")
        return None

# Homepage route
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Stablecoin Yields API",
        "version": "2.0",
        "endpoints": ["/yields", "/stablecoin-prices", "/tvl", "/risk-analysis"]
    })

# /yields endpoint
@app.route("/yields", methods=["GET"])
def get_yields():
    @cached(yield_cache)
    def cached_yields():
        data = fetch_data(DEFILLAMA_YIELDS_URL)
        if not data or not isinstance(data, list):
            return {"error": "Yield data unavailable"}
        # Return top 10 results (or you can adjust this as needed)
        return data[:10]
    return jsonify(cached_yields())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Ensure this matches Render's port setting
    app.run(host="0.0.0.0", port=port, debug=True)
