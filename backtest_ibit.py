#!/usr/bin/env python3

import pandas as pd
import json
import os
from src.av_data_fetcher import AVDataFetcher

def simple_backtest(df, symbol, initial_capital=10000):
    """Simple buy-and-hold backtest"""
    if df.empty:
        return {"error": "No data available"}
    
    start_price = df['close'].iloc[0]
    end_price = df['close'].iloc[-1]
    total_return = (end_price - start_price) / start_price * 100
    
    return {
        "symbol": symbol,
        "strategy": "buy_hold",
        "summary": {
            "num_trades": 1,
            "avg_outcome_R": total_return / 100,
            "win_rate_pos_R": 1.0 if total_return > 0 else 0.0,
            "bullish_trades": 1,
            "bearish_trades": 0
        },
        "trades": [{
            "entry_date": df.index[0].isoformat(),
            "exit_date": df.index[-1].isoformat(),
            "entry_price": start_price,
            "exit_price": end_price,
            "outcome_R": total_return / 100,
            "type": "Bullish"
        }],
        "equity_curve": [0, total_return / 100]
    }

def save_to_cache(df, result, symbol):
    """Save data and results to cache"""
    os.makedirs('cache', exist_ok=True)
    
    market_data = {
        'dates': df.index.strftime('%Y-%m-%d').tolist(),
        'prices': {
            'open': df['open'].tolist(),
            'high': df['high'].tolist(),
            'low': df['low'].tolist(),
            'close': df['close'].tolist(),
            'volume': df['volume'].tolist()
        }
    }
    
    # Update market data cache
    cache_file = 'cache/market_data.json'
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
    else:
        cache = {}
    
    if 'etfs' not in cache:
        cache['etfs'] = {}
    cache['etfs'][symbol] = market_data
    
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)
    
    # Update backtest results cache
    results_file = 'cache/backtest_results.json'
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            results = json.load(f)
    else:
        results = {}
    
    if 'etfs' not in results:
        results['etfs'] = {}
    results['etfs'][symbol] = result
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

def main():
    API_KEY = "74M88OXCGWTNUIV9"
    fetcher = AVDataFetcher(API_KEY)
    symbol = "IBIT"
    
    print(f"Fetching {symbol} ETF data...")
    try:
        df = fetcher.fetch_etf_data(symbol)
        result = simple_backtest(df, symbol)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            save_to_cache(df, result, symbol)
            summary = result['summary']
            print(f"\n=== {symbol} ETF BACKTEST RESULTS ===")
            print(f"Period: {result['trades'][0]['entry_date'][:10]} to {result['trades'][0]['exit_date'][:10]}")
            print(f"Total Return: {summary['avg_outcome_R']*100:.2f}%")
            print(f"✅ Results saved to web app cache")
            
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    main()