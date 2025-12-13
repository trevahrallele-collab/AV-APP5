from flask import Flask, render_template, jsonify, request
from av_data_fetcher import AVDataFetcher
import pandas as pd
import json

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/dashboard')
def dashboard():
    return render_template('interactive_dashboard.html')

@app.route('/backtests')
def backtests():
    return render_template('backtest_results.html')

@app.route('/backtest/<data_type>/<symbol>')
def backtest_detail(data_type, symbol):
    return render_template('backtest_detail.html', data_type=data_type, symbol=symbol)

@app.route('/api/backtest-detail/<data_type>/<symbol>')
def api_backtest_detail(data_type, symbol):
    try:
        with open('../cache/backtest_results.json', 'r') as f:
            results = json.load(f)
        
        with open('../cache/market_data.json', 'r') as f:
            market_data = json.load(f)
        
        if data_type not in results or symbol not in results[data_type]:
            return jsonify({'error': 'Symbol not found'}), 404
        
        backtest_result = results[data_type][symbol]
        price_data = market_data[data_type][symbol]
        
        # Get admin settings from query parameters
        risk_per_trade = float(request.args.get('risk', 100))
        starting_capital = float(request.args.get('capital', 10000))
        
        trades = backtest_result['trades']
        equity_curve = [starting_capital]
        total_invested = 0
        total_return = 0
        returns = []
        
        for trade in trades:
            pnl = trade['outcome_R'] * risk_per_trade
            total_return += pnl
            equity_curve.append(equity_curve[-1] + pnl)
            total_invested += risk_per_trade
            returns.append(pnl / equity_curve[-2] if equity_curve[-2] > 0 else 0)
        
        final_capital = equity_curve[-1] if equity_curve else starting_capital
        roi_percent = ((final_capital - starting_capital) / starting_capital) * 100
        
        # Calculate drawdown
        drawdown = []
        peak = equity_curve[0]
        max_drawdown = 0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (value - peak) / peak
            drawdown.append(dd)
            if dd < max_drawdown:
                max_drawdown = dd
        
        # Calculate ratios
        import math
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            return_std = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1))
            
            # Sharpe Ratio (assuming 0% risk-free rate)
            sharpe_ratio = avg_return / return_std if return_std > 0 else 0
            
            # Sortino Ratio (downside deviation)
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                downside_std = math.sqrt(sum(r ** 2 for r in negative_returns) / len(negative_returns))
                sortino_ratio = avg_return / downside_std if downside_std > 0 else 0
            else:
                sortino_ratio = 999 if avg_return > 0 else 0
            
            # Calmar Ratio
            calmar_ratio = (roi_percent / 100) / abs(max_drawdown) if max_drawdown < 0 else 999
        else:
            sharpe_ratio = sortino_ratio = calmar_ratio = 0
        
        return jsonify({
            'backtest': backtest_result,
            'price_data': price_data,
            'investment_metrics': {
                'starting_capital': starting_capital,
                'risk_per_trade': risk_per_trade,
                'total_invested': total_invested,
                'total_return': total_return,
                'final_capital': final_capital,
                'roi_percent': roi_percent,
                'equity_curve': equity_curve,
                'max_drawdown_percent': max_drawdown * 100,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest-results')
def api_backtest_results():
    try:
        with open('../cache/backtest_results.json', 'r') as f:
            results = json.load(f)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fetch-data')
def fetch_data():
    data_type = request.args.get('type', 'stocks')
    symbol = request.args.get('symbol', 'AAPL')
    
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
        
        table_name = symbol.replace('/', '_')
        
        # Fetch new data
        if data_type == 'stocks':
            df = fetcher.fetch_daily_data(symbol)
        elif data_type == 'forex':
            from_symbol, to_symbol = symbol.split('/')
            df = fetcher.fetch_forex_data(from_symbol, to_symbol)
        else:  # commodities
            df = fetcher.fetch_commodity_data(symbol)
        
        # Save to database
        fetcher.save_to_db(df, db_path, table_name)
        
        return jsonify({'success': f'Data fetched and cached for {symbol}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data')
def api_data():
    data_type = request.args.get('type', 'stocks')
    symbol = request.args.get('symbol', 'AAPL')
    time_range = request.args.get('range', '1Y')
    
    try:
        # Load from JSON cache
        with open('../cache/market_data.json', 'r') as f:
            cache_data = json.load(f)
        
        table_name = symbol.replace('/', '_')
        
        if data_type not in cache_data or table_name not in cache_data[data_type]:
            return jsonify({'error': f'No cached data for {symbol}'}), 404
        
        data = cache_data[data_type][table_name]
        
        # Filter data based on time range
        range_map = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730}
        limit = range_map.get(time_range, 365)
        
        filtered_data = {
            'dates': data['dates'][-limit:],
            'prices': {
                'open': data['prices']['open'][-limit:],
                'high': data['prices']['high'][-limit:],
                'low': data['prices']['low'][-limit:],
                'close': data['prices']['close'][-limit:],
                'volume': data['prices']['volume'][-limit:]
            }
        }
        
        return jsonify(filtered_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)