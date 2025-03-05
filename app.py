from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

def fetch_defillama_yields(platform=None, chain=None, stablecoin=None, limit=20):
    """
    Fetch stablecoin yield data from DeFiLlama API and apply optional filters.
    
    Parameters:
        platform (str): Filter by lending platform (e.g., Aave, Compound).
        chain (str): Filter by blockchain (e.g., Ethereum, BSC).
        stablecoin (str): Filter by stablecoin symbol (e.g., USDT, USDC, DAI).
        limit (int): Limit the number of results to return.

    Returns:
        list: Sorted list of stablecoin yield opportunities.
    """
    url = "https://yields.llama.fi/pools"
    response = requests.get(url)
    
    if response.status_code != 200:
        return []

    data = response.json()
    
    # Filter only stablecoin yields
    filtered_pools = []
    for pool in data.get('data', []):
        if pool.get('stablecoin', False):  # Only include stablecoin pools
            if platform and platform.lower() not in pool.get('project', '').lower():
                continue
            if chain and chain.lower() not in pool.get('chain', '').lower():
                continue
            if stablecoin and stablecoin.lower() not in pool.get('symbol', '').lower():
                continue

            filtered_pools.append({
                "platform": pool.get('project', 'Unknown'),
                "symbol": pool.get('symbol', 'N/A'),
                "chain": pool.get('chain', 'Unknown'),
                "apy": round(pool.get('apy', 2), 2),
                "tvl": round(pool.get('tvlUsd', 2), 2)
            })

    # Sort by highest APY and apply result limit
    return sorted(filtered_pools, key=lambda x: x["apy"], reverse=True)[:limit]

@app.route('/yields', methods=['GET'])
def get_yields():
    """
    API endpoint to retrieve stablecoin yield data with optional filtering.

    Query Parameters:
        platform (str): Filter results by platform (e.g., Aave, Compound).
        chain (str): Filter results by blockchain (e.g., Ethereum, BSC).
        stablecoin (str): Filter results by stablecoin symbol (e.g., USDT, USDC, DAI).
        limit (int): Limit the number of results (default is 20).

    Returns:
        JSON response with filtered stablecoin yield data.
    """
    platform = request.args.get('platform')
    chain = request.args.get('chain')
    stablecoin = request.args.get('stablecoin')
    limit = int(request.args.get('limit', 20))  # Default limit to 20

    yields = fetch_defillama_yields(platform, chain, stablecoin, limit)
    return jsonify(yields)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
