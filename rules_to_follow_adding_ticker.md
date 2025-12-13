# Rules for Adding New Tickers to AV-APP

## 1. Data Type Classification
- **Stocks**: Use symbol directly (e.g., "AAPL", "MSFT")
- **Forex**: Use format "FROM_TO" (e.g., "EUR_USD", "GBP_USD") 
- **Commodities**: Use ETF symbols (GLD=Gold, UNG=Natural Gas, CPER=Copper, JJU=Aluminum)
- **ETFs**: Use symbol directly (e.g., "SPY", "QQQ", "TQQQ")

## 2. API Fetch Process
```bash
# Use web endpoint to fetch new data
GET /api/fetch-data?type={stocks|forex|commodities|etfs}&symbol={SYMBOL}
```

## 3. Database Storage
- Data automatically saved to appropriate database:
  - `database/stock_data.db` (stocks)
  - `database/forex_data.db` (forex) 
  - `database/commodity_data.db` (commodities)
  - `database/etf_data.db` (etfs)
- Table name = symbol with "/" replaced by "_"

## 4. JSON Cache Update
```bash
# Run export script to update JSON cache
python backups/phase-two/export_to_json.py
```

## 5. Verification Steps
1. Check database contains new table: `sqlite3 database/{type}_data.db ".tables"`
2. Verify JSON cache updated: Check `cache/market_data.json`
3. Test web endpoint: `GET /api/data?type={type}&symbol={SYMBOL}`

## 6. Supported Alpha Vantage Functions
- **TIME_SERIES_DAILY**: All stocks
- **FX_DAILY**: Forex pairs
- **Commodity ETFs**: Use stock function with ETF symbols

## 7. Error Handling
- Invalid symbols return API error in JSON response
- Missing data creates empty database table
- Export script skips empty tables automatically