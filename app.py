from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from cachetools import TTLCache, cached
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Cache configuration: TTLCache with a max size of 100 items and TTLs for different endpoints
yield_cache = TTLCache(maxsize=100, ttl=600)  # 10 minutes for yields
price_cache = TTLCache(maxsize=50, ttl=300)   # 5 minutes for prices
tvl_cache = TTLCache(maxsize=30, ttl=1800)    # 30 minutes for TVL data
risk_cache = TTLCache(maxsize=20, ttl=3600)   # 1 hour for risk data

# API Base URLs
DEFILLAMA_BASE_URL = "https://api.llama.fi"
DEFILLAMA_YIELDS_URL = "https://yields.llama.fi/pools"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Helper function to handle API requests with error handling and retries
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

# Homepage route to provide API information
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Stablecoin Yields API",
        "version": "2.0",
        "endpoints": [
            {
                "path": "/yields",
                "description": "Get stablecoin yield opportunities with filtering",
                "parameters": ["platform", "chain", "stablecoin", "limit", "min_apy", "min_tvl"]
            },
            {
                "path": "/historical-yields",
                "description": "Get historical yield data for a specific pool",
                "parameters": ["pool_id", "days"]
            },
            {
                "path": "/cross-chain",
                "description": "Compare yields across different blockchains",
                "parameters": ["stablecoin"]
            },
            {
                "path": "/portfolio-optimization",
                "description": "Get optimal portfolio allocation based on risk preference",
                "parameters": ["risk", "amount"]
            },
            {
                "path": "/risk-analysis",
                "description": "Get detailed risk analysis for DeFi platforms",
                "parameters": ["platform"]
            },
            {
                "path": "/stablecoin-prices",
                "description": "Get current stablecoin prices and stability metrics",
                "parameters": ["stablecoin"]
            },
            {
                "path": "/tvl",
                "description": "Get TVL data for protocols",
                "parameters": ["protocol"]
            }
        ]
    })

# Fetch TVL Data from DeFiLlama
@app.route("/tvl", methods=["GET"])
def get_tvl():
    @cached(tvl_cache)
    def cached_tvl(protocol=None):
        if protocol:
            url = f"{DEFILLAMA_BASE_URL}/protocol/{protocol}"
        else:
            url = f"{DEFILLAMA_BASE_URL}/protocols"
        
        data = fetch_data(url)
        return data if data else {"error": "Failed to fetch TVL data"}
    
    protocol = request.args.get("protocol")
    return jsonify(cached_tvl(protocol))

# Fetch live stablecoin prices and metrics from CoinGecko
@app.route("/stablecoin-prices", methods=["GET"])
def get_stablecoin_prices():
    stablecoin = request.args.get("stablecoin", "")
    
    @cached(price_cache)
    def cached_prices(coin_id=None):
        # Map of common stablecoins to their CoinGecko IDs
        stablecoin_map = {
            "USDC": "usd-coin",
            "USDT": "tether",
            "DAI": "dai",
            "BUSD": "binance-usd",
            "TUSD": "true-usd",
            "USDD": "usdd",
            "FRAX": "frax",
            "LUSD": "liquity-usd",
        }
        
        if coin_id and coin_id.upper() in stablecoin_map:
            specific_id = stablecoin_map[coin_id.upper()]
            url = f"{COINGECKO_BASE_URL}/coins/{specific_id}"
            data = fetch_data(url)
            
            if not data:
                return {"error": f"Failed to fetch data for {coin_id}"}
            
            # Calculate peg stability based on price history
            market_data = data.get("market_data", {})
            current_price = market_data.get("current_price", {}).get("usd", 0)
            price_change = market_data.get("price_change_percentage_24h", 0)
            
            # Peg stability assessment
            peg_stability = "High"
            if abs(current_price - 1.0) > 0.02:
                peg_stability = "Low"
            elif abs(current_price - 1.0) > 0.005:
                peg_stability = "Medium"
            
            return {
                "name": data.get("name"),
                "symbol": data.get("symbol", "").upper(),
                "price_usd": current_price,
                "price_change_24h": price_change,
                "market_cap": market_data.get("market_cap", {}).get("usd"),
                "total_supply": market_data.get("total_supply"),
                "peg_deviation": abs(current_price - 1.0),
                "peg_stability": peg_stability
            }
        else:
            # Get data for multiple stablecoins
            url = f"{COINGECKO_BASE_URL}/simple/price"
            stablecoin_ids = ",".join(stablecoin_map.values())
            params = {
                "ids": stablecoin_ids,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_change": "true"
            }
            
            data = fetch_data(url, params=params)
            if not data:
                return {"error": "Failed to fetch stablecoin prices"}
                
            # Process and enhance the data
            processed_data = {}
            for cg_id, values in data.items():
                # Find the corresponding symbol
                symbol = next((k for k, v in stablecoin_map.items() if v == cg_id), cg_id.upper())
                
                # Calculate peg stability
                price = values.get("usd", 0)
                peg_stability = "High"
                if abs(price - 1.0) > 0.02:
                    peg_stability = "Low"
                elif abs(price - 1.0) > 0.005:
                    peg_stability = "Medium"
                
                processed_data[symbol] = {
                    "price_usd": price,
                    "price_change_24h": values.get("usd_24h_change", 0),
                    "market_cap": values.get("usd_market_cap", 0),
                    "peg_deviation": abs(price - 1.0),
                    "peg_stability": peg_stability
                }
            
            return processed_data
    
    return jsonify(cached_prices(stablecoin))

# Fetch Yield Data with Enhanced Filtering and Analytics
@app.route("/yields", methods=["GET"])
def get_yields():
    # Extract and validate query parameters
    platform = request.args.get("platform", "").lower()
    chain = request.args.get("chain", "").lower()
    stablecoin = request.args.get("stablecoin", "").upper()
    
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))  # Between 1 and 100
        min_apy = float(request.args.get("min_apy", 0))
        min_tvl = float(request.args.get("min_tvl", 0))
    except ValueError:
        limit = 20
        min_apy = 0
        min_tvl = 0
    
    @cached(yield_cache)
    def cached_yields(platform_key, chain_key, stablecoin_key, limit_key, min_apy_key, min_tvl_key):
        url = DEFILLAMA_YIELDS_URL
        data = fetch_data(url)
        
        if not data:
            return {"error": "Failed to fetch yield data from DeFi Llama"}
        
        # Define stablecoins to track
        stablecoin_identifiers = ["USDC", "USDT", "DAI", "BUSD", "TUSD", "USDD", "FRAX", "LUSD"]
        
        # Filter for stablecoin pools
        filtered_pools = []
        for pool in data:
            pool_symbol = pool.get("symbol", "").upper()
            
            # Check if this is a stablecoin pool
            is_stablecoin_pool = any(stable in pool_symbol for stable in stablecoin_identifiers)
            
            if is_stablecoin_pool:
                project = pool.get("project", "").lower()
                pool_chain = pool.get("chain", "").lower()
                apy = pool.get("apy", 0)
                tvl = pool.get("tvlUsd", 0)
                
                # Apply filters
                if ((not platform_key or platform_key in project) and
                    (not chain_key or chain_key in pool_chain) and
                    (not stablecoin_key or stablecoin_key in pool_symbol) and
                    apy >= min_apy_key and
                    tvl >= min_tvl_key):
                    
                    # Determine specific stablecoin
                    primary_stablecoin = next((s for s in stablecoin_identifiers if s in pool_symbol), "Unknown")
                    
                    # Analytics and risk assessment
                    risk_level = "Medium"
                    risk_factors = []
                    
                    # APY Risk Assessment
                    if apy > 15:
                        risk_level = "High"
                        risk_factors.append("Unusually high APY")
                    elif apy > 10:
                        risk_level = "Medium-High"
                        risk_factors.append("Higher than average APY")
                    
                    # TVL Risk Assessment
                    if tvl < 1_000_000:
                        risk_level = "High"
                        risk_factors.append("Very low TVL")
                    elif tvl < 10_000_000:
                        risk_factors.append("Moderate TVL")
                    
                    # Platform Reputation (simplified)
                    top_platforms = ["aave", "compound", "curve", "yearn", "maker"]
                    if project in top_platforms:
                        if risk_level == "Medium":
                            risk_level = "Low-Medium"
                        elif risk_level == "Medium-High":
                            risk_level = "Medium"
                    
                    # Enhance with additional data
                    enhanced_pool = {
                        "pool_id": pool.get("pool", ""),
                        "platform": pool.get("project", "Unknown"),
                        "symbol": pool_symbol,
                        "chain": pool.get("chain", "Unknown"),
                        "primary_stablecoin": primary_stablecoin,
                        "apy": apy,
                        "tvl_usd": tvl,
                        "risk_level": risk_level,
                        "risk_factors": risk_factors,
                        "il_risk": "Low" if "stableswap" in pool_symbol.lower() else "Medium",
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    filtered_pools.append(enhanced_pool)
        
        # Sort by APY (highest first)
        sorted_pools = sorted(filtered_pools, key=lambda x: x["apy"], reverse=True)
        
        return sorted_pools[:limit_key]
    
    # Get cached or fresh data
    cache_key = f"{platform}_{chain}_{stablecoin}_{limit}_{min_apy}_{min_tvl}"
    yields_data = cached_yields(platform, chain, stablecoin, limit, min_apy, min_tvl)
    
    return jsonify(yields_data)

# Historical yield data for a specific pool
@app.route("/historical-yields", methods=["GET"])
def get_historical_yields():
    pool_id = request.args.get("pool_id")
    days = int(request.args.get("days", 30))
    
    if not pool_id:
        return jsonify({"error": "Pool ID is required"}), 400
    
    @cached(yield_cache)
    def cached_historical(pool_id_key, days_key):
        url = f"https://yields.llama.fi/chart/{pool_id_key}"
        data = fetch_data(url)
        
        if not data:
            return {"error": f"Failed to fetch historical data for pool {pool_id_key}"}
        
        # Process and limit the data
        processed_data = []
        for item in data[-days_key:]:
            processed_data.append({
                "date": item.get("timestamp", ""),
                "apy": item.get("apy", 0),
                "tvl": item.get("tvlUsd", 0)
            })
        
        # Calculate trend metrics
        if len(processed_data) > 1:
            current_apy = processed_data[-1]["apy"]
            past_apy = processed_data[0]["apy"]
            apy_change = current_apy - past_apy
            apy_change_pct = (apy_change / past_apy * 100) if past_apy > 0 else 0
            
            return {
                "pool_id": pool_id_key,
                "data_points": processed_data,
                "current_apy": current_apy,
                "apy_change": apy_change,
                "apy_change_pct": apy_change_pct,
                "trend": "Increasing" if apy_change > 0 else "Decreasing" if apy_change < 0 else "Stable"
            }
        return {"pool_id": pool_id_key, "data_points": processed_data}
    
    return jsonify(cached_historical(pool_id, days))

# Cross-chain comparison for stablecoins
@app.route("/cross-chain", methods=["GET"])
def get_cross_chain_comparison():
    stablecoin = request.args.get("stablecoin", "USDC").upper()
    
    @cached(yield_cache)
    def cached_cross_chain(stablecoin_key):
        url = DEFILLAMA_YIELDS_URL
        data = fetch_data(url)
        
        if not data:
            return {"error": "Failed to fetch yield data"}
        
        # Group yields by chain
        chain_data = {}
        for pool in data:
            if stablecoin_key in pool.get("symbol", "").upper():
                chain = pool.get("chain", "Unknown")
                apy = pool.get("apy", 0)
                tvl = pool.get("tvlUsd", 0)
                project = pool.get("project", "Unknown")
                
                if chain not in chain_data:
                    chain_data[chain] = []
                
                # Estimate gas costs (simplified)
                gas_cost = 15 if chain.lower() == "ethereum" else 1 if chain.lower() in ["bsc", "polygon"] else 0.5
                
                chain_data[chain].append({
                    "platform": project,
                    "apy": apy,
                    "tvl": tvl,
                    "estimated_gas_usd": gas_cost,
                    "min_deposit_for_gas": int(gas_cost * 100 / apy) if apy > 0 else "N/A"  # Deposit needed to recover gas in 1 year
                })
        
        # For each chain, get the best option
        result = {}
        for chain, pools in chain_data.items():
            if pools:
                # Sort by APY
                best_pools = sorted(pools, key=lambda x: x["apy"], reverse=True)
                result[chain] = {
                    "best_yield": best_pools[0],
                    "avg_apy": sum(p["apy"] for p in pools) / len(pools),
                    "total_options": len(pools),
                    "total_tvl": sum(p["tvl"] for p in pools)
                }
        
        return {
            "stablecoin": stablecoin_key,
            "chains": result,
            "best_chain": max(result.items(), key=lambda x: x[1]["best_yield"]["apy"])[0] if result else None
        }
    
    return jsonify(cached_cross_chain(stablecoin))

# Portfolio optimization based on risk preference
@app.route("/portfolio-optimization", methods=["GET"])
def get_portfolio_optimization():
    risk_preference = request.args.get("risk", "medium").lower()
    amount = float(request.args.get("amount", 10000))
    
    @cached(risk_cache)
    def cached_portfolio(risk_key, amount_key):
        # Get yield data first
        url = DEFILLAMA_YIELDS_URL
        data = fetch_data(url)
        
        if not data:
            return {"error": "Failed to fetch yield data"}
        
        # Filter for stablecoin pools
        stablecoin_pools = []
        stablecoin_identifiers = ["USDC", "USDT", "DAI"]
        
        for pool in data:
            if any(stable in pool.get("symbol", "").upper() for stable in stablecoin_identifiers):
                stablecoin_pools.append(pool)
        
        # Sort pools by a combination of APY and TVL
        def safety_score(pool):
            apy = pool.get("apy", 0)
            tvl = pool.get("tvlUsd", 0)
            project = pool.get("project", "").lower()
            
            # Platform reputation factor
            platform_factor = 1.5 if project in ["aave", "compound", "curve"] else 1.0
            
            # Balance APY with TVL (higher TVL = safer)
            tvl_factor = min(1.0, tvl / 1_000_000_000)  # Cap at 1B TVL
            
            if risk_key == "low":
                return (tvl_factor * platform_factor) - (apy * 0.1)  # Prioritize safety
            elif risk_key == "high":
                return apy  # Prioritize yield
            else:  # medium
                return (apy * 0.5) + (tvl_factor * platform_factor * 0.5)  # Balance
        
        sorted_pools = sorted(stablecoin_pools, key=safety_score, reverse=True)
        
        # Build portfolio based on risk preference
        portfolio = []
        total_allocation = 0
        
        if risk_key == "low":
            # Conservative strategy: 3-4 established platforms
            allocations = [0.35, 0.25, 0.25, 0.15]
            for i, alloc in enumerate(allocations):
                if i < len(sorted_pools):
                    pool = sorted_pools[i]
                    portfolio.append({
                        "platform": pool.get("project", "Unknown"),
                        "stablecoin": next((s for s in stablecoin_identifiers if s in pool.get("symbol", "")), "Stablecoin"),
                        "chain": pool.get("chain", "Unknown"),
                        "allocation_pct": alloc * 100,
                        "allocation_amount": amount_key * alloc,
                        "expected_apy": pool.get("apy", 0),
                        "expected_annual_yield": amount_key * alloc * pool.get("apy", 0) / 100
                    })
                    total_allocation += alloc
        
        elif risk_key == "high":
            # Aggressive strategy: 2-3 highest yield platforms
            allocations = [0.5, 0.3, 0.2]
            for i, alloc in enumerate(allocations):
                if i < len(sorted_pools):
                    pool = sorted_pools[i]
                    portfolio.append({
                        "platform": pool.get("project", "Unknown"),
                        "stablecoin": next((s for s in stablecoin_identifiers if s in pool.get("symbol", "")), "Stablecoin"),
                        "chain": pool.get("chain", "Unknown"),
                        "allocation_pct": alloc * 100,
                        "allocation_amount": amount_key * alloc,
                        "expected_apy": pool.get("apy", 0),
                        "expected_annual_yield": amount_key * alloc * pool.get("apy", 0) / 100
                    })
                    total_allocation += alloc
        
        else:  # medium risk
            # Balanced strategy: 4-5 mixed platforms
            allocations = [0.3, 0.25, 0.2, 0.15, 0.1]
            for i, alloc in enumerate(allocations):
                if i < len(sorted_pools):
                    pool = sorted_pools[i]
                    portfolio.append({
                        "platform": pool.get("project", "Unknown"),
                        "stablecoin": next((s for s in stablecoin_identifiers if s in pool.get("symbol", "")), "Stablecoin"),
                        "chain": pool.get("chain", "Unknown"),
                        "allocation_pct": alloc * 100,
                        "allocation_amount": amount_key * alloc,
                        "expected_apy": pool.get("apy", 0),
                        "expected_annual_yield": amount_key * alloc * pool.get("apy", 0) / 100
                    })
                    total_allocation += alloc
        
        # Calculate portfolio metrics
        total_expected_yield = sum(p["expected_annual_yield"] for p in portfolio)
        weighted_avg_apy = sum(p["expected_apy"] * p["allocation_pct"] for p in portfolio) / 100
        
        return {
            "risk_profile": risk_key.capitalize(),
            "investment_amount": amount_key,
            "portfolio": portfolio,
            "weighted_avg_apy": weighted_avg_apy,
            "expected_annual_yield": total_expected_yield,
            "rebalance_frequency": "Quarterly" if risk_key == "low" else "Monthly" if risk_key == "medium" else "Bi-weekly"
        }
    
    return jsonify(cached_portfolio(risk_preference, amount))

# Risk analysis for DeFi platforms
@app.route("/risk-analysis", methods=["GET"])
def get_risk_analysis():
    platform = request.args.get("platform", "").lower()
    
    @cached(risk_cache)
    def cached_risk_analysis(platform_key=None):
        # This is currently static data
        # In a production app, this would be connected to real audit data sources
        risk_data = {
            "aave": {
                "smart_contract_risk": "Low",
                "security_score": 8.7,
                "audit_status": "Multiple audits by Trail of Bits, OpenZeppelin",
                "last_audit_date": "2024-10",
                "previous_incidents": "None in the last 24 months",
                "governance_risk": "Low",
                "liquidity_risk": "Low",
                "regulatory_risk": "Medium",
                "insurance_options": "Available via Nexus Mutual",
                "risk_factors": ["Complex codebase", "Large attack surface"],
                "risk_mitigations": ["Multiple audits", "Bug bounty program", "Time-tested code"]
            },
            "compound": {
                "smart_contract_risk": "Low",
                "security_score": 8.5,
                "audit_status": "Multiple audits by Trail of Bits, OpenZeppelin",
                "last_audit_date": "2024-09",
                "previous_incidents": "Minor issue in 2023, no funds lost",
                "governance_risk": "Low",
                "liquidity_risk": "Low",
                "regulatory_risk": "Medium",
                "insurance_options": "Available via Nexus Mutual",
                "risk_factors": ["Governance attack vectors", "Oracle dependencies"],
                "risk_mitigations": ["Timelock on governance", "Multiple oracle sources"]
            },
            "curve": {
                "smart_contract_risk": "Low-Medium",
                "security_score": 7.8,
                "audit_status": "Audited by Trail of Bits, ChainSecurity",
                "last_audit_date": "2024-08",
                "previous_incidents": "None in the last 24 months",
                "governance_risk": "Medium",
                "liquidity_risk": "Low",
                "regulatory_risk": "Medium",
                "insurance_options": "Available via Nexus Mutual",
                "risk_factors": ["Complex stableswap algorithm", "Concentrated governance power"],
                "risk_mitigations": ["Battle-tested code", "Emergency shutdown mechanisms"]
            },
            "yearn": {
                "smart_contract_risk": "Medium",
                "security_score": 7.5,
                "audit_status": "Audited by Trail of Bits, CertiK",
                "last_audit_date": "2024-07",
                "previous_incidents": "Minor incidents in 2023, all funds recovered",
                "governance_risk": "Medium",
                "liquidity_risk": "Medium",
                "regulatory_risk": "Medium-High",
                "insurance_options": "Limited coverage via Nexus Mutual",
                "risk_factors": ["Complex vault strategies", "Multiple protocol dependencies"],
                "risk_mitigations": ["Strategy review process", "Security council oversight"]
            }
        }
        
        # Add more platforms as needed
        additional_platforms = {
            "maker": {
                "smart_contract_risk": "Low",
                "security_score": 8.6,
                "audit_status": "Multiple audits by Trail of Bits, Quantstamp",
                "last_audit_date": "2024-08",
                "previous_incidents": "None in the last 36 months",
                "governance_risk": "Low",
                "liquidity_risk": "Low",
                "regulatory_risk": "Medium",
                "insurance_options": "Available via Nexus Mutual",
                "risk_factors": ["Complex liquidation mechanisms", "DAI peg maintenance"],
                "risk_mitigations": ["Conservative risk parameters", "Multiple collateral types"]
            },
            # Add more platforms as needed
        }
        
        risk_data.update(additional_platforms)
        
        if platform_key and platform_key in risk_data:
            return {platform_key: risk_data[platform_key]}
        
        return risk_data
    
    return jsonify(cached_risk_analysis(platform))

# For local testing
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
