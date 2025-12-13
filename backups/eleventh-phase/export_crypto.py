import sqlite3
import json
import os

def export_crypto_data():
    """Export crypto data from stock database to separate crypto section in JSON"""
    
    # Load existing market data
    with open('cache/market_data.json', 'r') as f:
        market_data = json.load(f)
    
    # Add crypto section if not exists
    if 'crypto' not in market_data:
        market_data['crypto'] = {}
    
    # Connect to stock database (where crypto data is stored)
    conn = sqlite3.connect('database/stock_data.db')
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    crypto_symbols = ['BTC', 'ETH', 'SOL', 'LTC', 'XRP']
    
    for symbol in crypto_symbols:
        if symbol in tables:
            print(f"Exporting {symbol} to crypto section...")
            
            # Fetch data from database
            cursor.execute(f"SELECT * FROM {symbol} ORDER BY `index`")
            rows = cursor.fetchall()
            
            if rows:
                # Get column names
                cursor.execute(f"PRAGMA table_info({symbol})")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to structured format
                dates = []
                prices = {'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
                
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    dates.append(row_dict['index'])
                    prices['open'].append(float(row_dict['open']))
                    prices['high'].append(float(row_dict['high']))
                    prices['low'].append(float(row_dict['low']))
                    prices['close'].append(float(row_dict['close']))
                    prices['volume'].append(float(row_dict['volume']))
                
                market_data['crypto'][symbol] = {
                    'dates': dates,
                    'prices': prices
                }
                
                # Remove from stocks section if exists
                if symbol in market_data.get('stocks', {}):
                    del market_data['stocks'][symbol]
                    print(f"Moved {symbol} from stocks to crypto")
    
    conn.close()
    
    # Save updated market data
    with open('cache/market_data.json', 'w') as f:
        json.dump(market_data, f, indent=2)
    
    print(f"✅ Crypto data exported to cache/market_data.json")
    return market_data

if __name__ == "__main__":
    export_crypto_data()