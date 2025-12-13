import requests
import pandas as pd
import sqlite3

class AVDataFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def fetch_daily_data(self, symbol="AAPL"):
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": "compact"
        }
        response = requests.get(self.base_url, params=params, timeout=30)
        if response.status_code != 200:
            raise ValueError(f"API request failed with status {response.status_code}")
        
        try:
            data = response.json()
        except ValueError as e:
            raise ValueError(f"Invalid JSON response: {e}")
        
        if "Time Series (Daily)" not in data:
            raise ValueError(f"Error fetching data: {data}")
        
        df = pd.DataFrame(data["Time Series (Daily)"]).T
        df.index = pd.to_datetime(df.index, errors='coerce')
        df = df.dropna()
        df.columns = [col.split('. ')[1] if '. ' in col else col for col in df.columns]
        df = df.astype(float)
        return df.sort_index()
    
    def fetch_forex_data(self, from_symbol="EUR", to_symbol="USD"):
        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "apikey": self.api_key,
            "outputsize": "compact"
        }
        response = requests.get(self.base_url, params=params, timeout=30)
        if response.status_code != 200:
            raise ValueError(f"API request failed with status {response.status_code}")
        
        try:
            data = response.json()
        except ValueError as e:
            raise ValueError(f"Invalid JSON response: {e}")
        
        if "Time Series FX (Daily)" not in data:
            raise ValueError(f"Error fetching forex data: {data}")
        
        df = pd.DataFrame(data["Time Series FX (Daily)"]).T
        df.index = pd.to_datetime(df.index, errors='coerce')
        df = df.dropna()
        # Rename columns to remove numbers and periods
        df.columns = [col.split('. ', 1)[1] if '. ' in col else col for col in df.columns]
        df = df.astype(float)
        df['volume'] = 0  # Forex doesn't have volume
        return df.sort_index()
    
    def fetch_commodity_data(self, function="WTI"):
        # Use stock data for commodities as Alpha Vantage commodity API is unreliable
        commodity_symbols = {
            'GOLD': 'GLD',  # Gold ETF
            'NATURAL_GAS': 'UNG',  # Natural Gas ETF
            'COPPER': 'CPER',  # Copper ETF
            'ALUMINUM': 'JJU'  # Aluminum ETF
        }
        
        symbol = commodity_symbols.get(function, 'USO')
        return self.fetch_daily_data(symbol)
    
    def save_to_csv(self, df, filename="data-storage/stock_data.csv"):
        df.to_csv(filename)
        print(f"Data saved to {filename}")
    
    def save_to_db(self, df, db_name="database/stock_data.db", table_name="daily_prices"):
        conn = sqlite3.connect(db_name)
        df.to_sql(table_name, conn, if_exists="replace", index=True)
        conn.close()
        print(f"Data saved to database {db_name}")
    
    def load_from_db(self, db_name="database/stock_data.db", table_name="daily_prices"):
        try:
            conn = sqlite3.connect(db_name)
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn, index_col=0, parse_dates=True)
            conn.close()
            print(f"Data loaded from database {db_name}")
            return df
        except Exception:
            return None
    


if __name__ == "__main__":
    API_KEY = "74M88OXCGWTNUIV9"
    
    fetcher = AVDataFetcher(API_KEY)
    
    # Fetch data
    df = fetcher.fetch_daily_data("AAPL")
    
    # Save to CSV and database
    fetcher.save_to_csv(df)
    fetcher.save_to_db(df)