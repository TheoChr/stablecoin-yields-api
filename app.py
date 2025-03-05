from flask import Flask, jsonify
import requests

app = Flask(__name__)

def fetch_defillama_yields():
    url = "https://yields.llama.fi/pools"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    data = response.json()
    
    # Filter only stablecoins and relevant fields
    filtered_pools = []
    for pool in data.get('data', []):
        if pool.get('stablecoin', False):  # Check if it's a stablecoin
            filtered_pools.append({
                "platform": pool.get('project', 'Unknown'),  # Lending platform
                "symbol": pool.get('symbol', 'N/A'),  # Stablecoin symbol (USDT, USDC, DAI)
                "chain": pool.get('chain', 'Unknown'),  # Blockchain (Ethereum, BSC, etc.)
                "apy": round(pool.get('apy', 0), 2),  # Annual Percentage Yield (APY)
                "tvl": round(pool.get('tvlUsd', 0), 2)  # Total Value Locked (TVL in USD)
            })
    
    return sorted(filtered_pools, key=lambda x: x["apy"], reverse=True)  # Sort by highest APY

@app.route('/yields', methods=['GET'])
def get_yields():
    yields = fetch_defillama_yields()
    return jsonify(yields)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
