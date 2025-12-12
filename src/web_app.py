from flask import Flask, render_template, jsonify, request
from av_data_fetcher import AVDataFetcher
import pandas as pd

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    API_KEY = "74M88OXCGWTNUIV9"
    
    try:
        fetcher = AVDataFetcher(API_KEY)
        
        # Try to load from database first
        df = fetcher.load_from_db()
        
        if df is None or df.empty:
            # Fetch new data if no stored data
            df = fetcher.fetch_daily_data("AAPL")
            fetcher.save_to_csv(df)
            fetcher.save_to_db(df)
        

        

        
        return render_template('index.html')
    except Exception as e:
        error_msg = str(e).lower()
        if "api call frequency" in error_msg or "premium" in error_msg or "invalid api key" in error_msg:
            return "401 Unauthorized: API Key limit exceeded or invalid", 401
        return f"Service temporarily unavailable: {str(e)}", 503



@app.route('/dashboard')
def dashboard():
    return render_template('interactive_dashboard.html')

@app.route('/api/data')
def api_data():
    data_type = request.args.get('type', 'stocks')
    symbol = request.args.get('symbol', 'AAPL')
    time_range = request.args.get('range', '1Y')
    
    API_KEY = "74M88OXCGWTNUIV9"
    
    try:
        fetcher = AVDataFetcher(API_KEY)
        
        # Determine database path
        if data_type == 'stocks':
            db_path = "../database/stock_data.db"
        elif data_type == 'forex':
            db_path = "../database/forex_data.db"
        else:  # commodities
            db_path = "../database/commodity_data.db"
        
        # Try to load from database first
        df = fetcher.load_from_db(db_path, symbol.replace('/', '_'))
        
        if df is None or df.empty:
            # Fetch new data
            if data_type == 'stocks':
                df = fetcher.fetch_daily_data(symbol)
            elif data_type == 'forex':
                from_symbol, to_symbol = symbol.split('/')
                df = fetcher.fetch_forex_data(from_symbol, to_symbol)
            else:  # commodities
                df = fetcher.fetch_commodity_data(symbol)
            
            # Save to database
            fetcher.save_to_db(df, db_path, symbol.replace('/', '_'))
        
        # Filter data based on time range
        if time_range == '1M':
            df = df.tail(30)
        elif time_range == '3M':
            df = df.tail(90)
        elif time_range == '6M':
            df = df.tail(180)
        elif time_range == '1Y':
            df = df.tail(365)
        elif time_range == '2Y':
            df = df.tail(730)
        
        return jsonify({
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'prices': {
                'open': df['open'].tolist(),
                'high': df['high'].tolist(),
                'low': df['low'].tolist(),
                'close': df['close'].tolist(),
                'volume': df['volume'].tolist()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)