openapi: 3.1.0
info:
  title: Stablecoin Yields API
  description: >
    GPT **must** use this API for all stablecoin yield, price, TVL, and risk score queries. 
    It **must not** generate yield data, price data, or risk scores on its own. 
    If the API is unavailable, GPT should indicate the API is unreachable rather than attempting to estimate data.
  version: 2.0.0

servers:
  - url: https://stablecoin-yields-api.onrender.com
    description: Live API Server

paths:
  /yields:
    get:
      operationId: getYields
      summary: Get stablecoin yield opportunities with filtering.
      description: Fetches the latest stablecoin yields with optional filters.
      parameters:
        - name: platform
          in: query
          description: Filter by platform (e.g., Aave, Compound, Curve, Yearn)
          schema:
            type: string
        - name: chain
          in: query
          description: Filter by blockchain (e.g., Ethereum, BSC, Arbitrum, Polygon)
          schema:
            type: string
        - name: stablecoin
          in: query
          description: Filter by stablecoin (e.g., USDC, DAI, USDT)
          schema:
            type: string
        - name: limit
          in: query
          description: Maximum number of results (default is 20, max is 100)
          schema:
            type: integer
            default: 20
        - name: min_apy
          in: query
          description: Minimum APY filter (e.g., 3.5 for 3.5%)
          schema:
            type: number
        - name: min_tvl
          in: query
          description: Minimum TVL filter in USD
          schema:
            type: number
      responses:
        "200":
          description: A list of stablecoin yield opportunities.
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    pool_id:
                      type: string
                      description: Unique identifier for the pool
                    platform:
                      type: string
                      description: Name of the lending platform
                    chain:
                      type: string
                      description: Blockchain network (e.g., Ethereum, BSC)
                    stablecoin:
                      type: string
                      description: Stablecoin symbol (e.g., USDC, DAI, USDT)
                    apy:
                      type: number
                      format: float
                      description: Annual Percentage Yield
                    tvl_usd:
                      type: number
                      format: float
                      description: Total Value Locked (TVL) in USD
                    risk_level:
                      type: string
                      description: Risk assessment (Low, Medium, High)
                    last_updated:
                      type: string
                      format: date-time
                      description: Timestamp of last data update
        "400":
          description: Invalid request parameters
        "500":
          description: Internal server error

  /historical-yields:
    get:
      operationId: getHistoricalYields
      summary: Fetch historical yield data for a specific pool.
      parameters:
        - name: pool_id
          in: query
          required: true
          description: ID of the yield pool to analyze
          schema:
            type: string
        - name: days
          in: query
          description: Number of days of history to return (default 30)
          schema:
            type: integer
            default: 30
      responses:
        "200":
          description: Historical yield data.
          content:
            application/json:
              schema:
                type: object
                properties:
                  pool_id:
                    type: string
                  data_points:
                    type: array
                    items:
                      type: object
                      properties:
                        date:
                          type: string
                          format: date
                        apy:
                          type: number
                          format: float
                        tvl:
                          type: number
        "400":
          description: Missing required pool_id parameter
        "500":
          description: Internal server error

  /cross-chain:
    get:
      operationId: getCrossChainComparison
      summary: Compare yields across different blockchains.
      parameters:
        - name: stablecoin
          in: query
          description: Stablecoin symbol to compare (default USDC)
          schema:
            type: string
            default: USDC
      responses:
        "200":
          description: Cross-chain comparison data.
          content:
            application/json:
              schema:
                type: object
                properties:
                  stablecoin:
                    type: string
                  chains:
                    type: object
                    additionalProperties:
                      type: object
                      properties:
                        best_yield:
                          type: object
                          properties:
                            platform:
                              type: string
                            apy:
                              type: number
                            tvl:
                              type: number
        "500":
          description: Internal server error

  /portfolio-optimization:
    get:
      operationId: getPortfolioOptimization
      summary: Get optimized portfolio allocations based on risk preference.
      parameters:
        - name: risk
          in: query
          description: Risk preference (low, medium, high)
          schema:
            type: string
            default: medium
            enum: [low, medium, high]
        - name: amount
          in: query
          description: Investment amount in USD
          schema:
            type: number
            default: 10000
      responses:
        "200":
          description: Optimized portfolio recommendations.
          content:
            application/json:
              schema:
                type: object
                properties:
                  risk_profile:
                    type: string
                  investment_amount:
                    type: number
                  portfolio:
                    type: array
                    items:
                      type: object
                      properties:
                        platform:
                          type: string
                        stablecoin:
                          type: string
                        chain:
                          type: string
                        allocation_pct:
                          type: number
                        allocation_amount:
                          type: number
                        expected_apy:
                          type: number
        "500":
          description: Internal server error

  /risk-analysis:
    get:
      operationId: getRiskAnalysis
      summary: Fetch detailed risk analysis for DeFi platforms.
      parameters:
        - name: platform
          in: query
          description: Platform name to analyze
          schema:
            type: string
      responses:
        "200":
          description: Risk analysis data.
          content:
            application/json:
              schema:
                type: object
                properties:
                  platform:
                    type: string
                  smart_contract_risk:
                    type: string
                  security_score:
                    type: number
                  audit_status:
                    type: string
                  last_audit_date:
                    type: string
                  previous_incidents:
                    type: string
                  governance_risk:
                    type: string
                  liquidity_risk:
                    type: string
                  regulatory_risk:
                    type: string
                  insurance_options:
                    type: string
        "500":
          description: Internal server error

  /tvl:
    get:
      operationId: getTVL
      summary: Fetch Total Value Locked (TVL) data.
      parameters:
        - name: protocol
          in: query
          description: Specific protocol to analyze
          schema:
            type: string
      responses:
        "200":
          description: TVL data.
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  tvl:
                    type: number
                  chains:
                    type: array
                    items:
                      type: string
        "500":
          description: Internal server error
