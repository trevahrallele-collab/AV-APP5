import sqlite3
import pandas as pd
import json
import os

def export_databases_to_json():
    print("=== EXPORTING DATABASES TO JSON ===\n")
    
    # Create cache directory
    os.makedirs('cache', exist_ok=True)
    
    databases = [
        ("database/stock_data.db", "stocks"),
        ("database/forex_data.db", "forex"),
        ("database/commodity_data.db", "commodities"),
        ("database/etf_data.db", "etfs")
    ]
    
    all_data = {}
    
    for db_path, data_type in databases:
        if not os.path.exists(db_path):
            print(f"❌ {db_path} not found")
            continue
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            type_data = {}
            
            for (table_name,) in tables:
                df = pd.read_sql_query(f"SELECT * FROM `{table_name}`", conn, parse_dates=['index'])
                df.set_index('index', inplace=True)
                
                if not df.empty:
                    # Convert to JSON format
                    symbol_data = {
                        'dates': df.index.strftime('%Y-%m-%d').tolist(),
                        'prices': {
                            'open': df['open'].tolist(),
                            'high': df['high'].tolist(),
                            'low': df['low'].tolist(),
                            'close': df['close'].tolist(),
                            'volume': df['volume'].tolist()
                        }
                    }
                    type_data[table_name] = symbol_data
                    print(f"✅ {data_type.upper()} {table_name}: {len(df)} records")
            
            all_data[data_type] = type_data
            conn.close()
            
        except Exception as e:
            print(f"❌ Error reading {db_path}: {e}")
    
    # Save to JSON file
    with open('cache/market_data.json', 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n✅ Data exported to cache/market_data.json")
    print(f"Total data types: {len(all_data)}")
    for data_type, symbols in all_data.items():
        print(f"  {data_type.upper()}: {len(symbols)} symbols")

if __name__ == "__main__":
    export_databases_to_json()