from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

def fetch_defillama_yields(platform=None, chain=None, stablecoin=None):
    url = "https://yields.llama.fi/pools"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    data = response.json()

    # Apply filters if specified
    filtered_pools = []
    for pool in data.get('data', []):
        if pool.get('stablecoin', False):  # Only stablecoin pools
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
                "apy": round(pool.get('apy', 0), 2),
                "tvl": round(pool.get('tvlUsd', 0), 2)
            })

    return sorted(filtered_pools, key=lambda x: x["apy"], reverse=True)

@app.route('/yields', methods=['GET'])
def get_yields():
    platform = request.args.get('platform')
    chain = request.args.get('chain')
    stablecoin = request.args.get('stablecoin')

    yields = fetch_defillama_yields(platform, chain, stablecoin)
    return jsonify(yields)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
