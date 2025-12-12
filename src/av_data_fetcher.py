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
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        if "Time Series (Daily)" not in data:
            raise ValueError(f"Error fetching data: {data}")
        
        df = pd.DataFrame(data["Time Series (Daily)"]).T
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df.columns = ["open", "high", "low", "close", "volume"]
        return df.sort_index()
    
    def fetch_forex_data(self, from_symbol="EUR", to_symbol="USD"):
        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "apikey": self.api_key,
            "outputsize": "compact"
        }
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        if "Time Series (FX Daily)" not in data:
            raise ValueError(f"Error fetching forex data: {data}")
        
        df = pd.DataFrame(data["Time Series (FX Daily)"]).T
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df.columns = ["open", "high", "low", "close"]
        df['volume'] = 0  # Forex doesn't have volume
        return df.sort_index()
    
    def fetch_commodity_data(self, function="WTI"):
        params = {
            "function": function,
            "interval": "daily",
            "apikey": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        data_key = list(data.keys())[1] if len(data.keys()) > 1 else None
        if not data_key or data_key not in data:
            raise ValueError(f"Error fetching commodity data: {data}")
        
        df = pd.DataFrame(data[data_key]).T
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df.columns = ["value"]
        # Create OHLC from value for consistency
        df['open'] = df['value']
        df['high'] = df['value']
        df['low'] = df['value']
        df['close'] = df['value']
        df['volume'] = 0
        return df.sort_index()
    
    def save_to_csv(self, df, filename="../data-storage/stock_data.csv"):
        df.to_csv(filename)
        print(f"Data saved to {filename}")
    
    def save_to_db(self, df, db_name="../database/stock_data.db", table_name="daily_prices"):
        conn = sqlite3.connect(db_name)
        df.to_sql(table_name, conn, if_exists="replace", index=True)
        conn.close()
        print(f"Data saved to database {db_name}")
    
    def load_from_db(self, db_name="../database/stock_data.db", table_name="daily_prices"):
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