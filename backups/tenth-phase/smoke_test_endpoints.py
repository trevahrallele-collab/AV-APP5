import requests
import sqlite3
import pandas as pd
import os

BASE_URL = "http://localhost:8081"

def test_endpoints():
    print("=== ENDPOINT SMOKE TESTS ===\n")
    
    # Test main page
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Main page: {response.status_code}")
    except Exception as e:
        print(f"❌ Main page: {e}")
    
    # Test dashboard
    try:
        response = requests.get(f"{BASE_URL}/dashboard", timeout=5)
        print(f"✅ Dashboard: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard: {e}")
    
    # Test data endpoints
    test_cases = [
        ("stocks", "AAPL"),
        ("forex", "EUR/USD"),
        ("commodities", "WTI"),
        ("commodities", "GOLD")
    ]
    
    for data_type, symbol in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/api/data?type={data_type}&symbol={symbol}&range=1M", timeout=30)
            result = response.json()
            if response.status_code == 200:
                print(f"✅ {data_type.upper()} {symbol}: {len(result.get('dates', []))} records")
            else:
                print(f"❌ {data_type.upper()} {symbol}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ {data_type.upper()} {symbol}: {e}")

def check_databases():
    print("\n=== DATABASE CONTENTS ===\n")
    
    databases = [
        ("database/stock_data.db", "Stock"),
        ("database/forex_data.db", "Forex"),
        ("database/commodity_data.db", "Commodity")
    ]
    
    for db_path, db_type in databases:
        print(f"{db_type} Database ({db_path}):")
        
        if not os.path.exists(db_path):
            print("  ❌ Database file not found")
            continue
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                print("  ❌ No tables found")
            else:
                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 1")
                        sample = cursor.fetchone()
                        cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                        columns = [col[1] for col in cursor.fetchall()]
                        print(f"  ✅ {table_name}: {count} records, columns: {columns}")
                    else:
                        print(f"  ⚠️  {table_name}: 0 records")
            
            conn.close()
            
        except Exception as e:
            print(f"  ❌ Error reading database: {e}")
        
        print()

if __name__ == "__main__":
    print("Starting smoke tests...\n")
    test_endpoints()
    check_databases()
    print("Smoke tests completed!")