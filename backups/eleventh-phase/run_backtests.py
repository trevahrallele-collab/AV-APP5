import json
import os
import pandas as pd

def convert_json_to_dataframe(data):
    """Convert JSON data to DataFrame format expected by strategies"""
    return pd.DataFrame({
        'open': data['prices']['open'],
        'high': data['prices']['high'],
        'low': data['prices']['low'],
        'close': data['prices']['close']
    }, index=pd.to_datetime(data['dates']))

def format_strategy_results(symbol_name, summary, trades, strategy_name):
    """Format strategy results for JSON serialization"""
    trades_dict = []
    if not trades.empty:
        for _, trade in trades.iterrows():
            trade_dict = trade.to_dict()
            for key, value in trade_dict.items():
                if pd.isna(value):
                    trade_dict[key] = None
                elif hasattr(value, 'isoformat'):
                    trade_dict[key] = value.isoformat()
            trades_dict.append(trade_dict)
    
    return {
        'symbol': symbol_name,
        'strategy': strategy_name,
        'summary': summary,
        'trades': trades_dict,
        'equity_curve': trades['outcome_R'].cumsum().tolist() if not trades.empty else []
    }

def handle_strategy_error(symbol_name, strategy_name, error):
    """Handle strategy execution errors"""
    return {
        'symbol': symbol_name,
        'strategy': strategy_name,
        'error': str(error),
        'summary': {
            'num_trades': 0,
            'avg_outcome_R': 0.0,
            'win_rate_pos_R': 0.0,
            'bullish_trades': 0,
            'bearish_trades': 0
        }
    }

def run_strategy_backtest(data, symbol_name, strategy_name="ob_refined_strategy"):
    """Run any strategy on symbol data"""
    try:
        # Import strategy module
        if strategy_name == "ob_refined_strategy":
            from ob_refined_strategy import (
                compute_indicators, detect_order_blocks, refined_backtest, 
                summarize_trades
            )
            # Original OB strategy logic
            df = convert_json_to_dataframe(data)
            df = compute_indicators(df, ema_span=50, atr_span=14)
            ob = detect_order_blocks(df, lookback=10)
            trades = refined_backtest(df=df, ob=ob, entry_wait_bars=60, 
                                   atr_threshold=0.0060, stop_on_tie=True)
            summary = summarize_trades(trades)
            
        elif strategy_name == "fractal_refined_strategy":
            import fractal_refined_strategy as strategy_module
            df = convert_json_to_dataframe(data)
            signals = strategy_module.detect_signals(df)
            trades = strategy_module.execute_backtest(df, signals)
            summary = strategy_module.summarize_results(trades)
            
        elif strategy_name == "fractal_ob_strategy":
            import fractal_ob_strategy as strategy_module
            df = convert_json_to_dataframe(data)
            signals = strategy_module.detect_signals(df)
            trades = strategy_module.execute_backtest(df, signals)
            summary = strategy_module.summarize_results(trades)
            
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        return format_strategy_results(symbol_name, summary, trades, strategy_name)
        
    except Exception as e:
        return handle_strategy_error(symbol_name, strategy_name, e)

def run_backtest_on_symbol(data, symbol_name, strategy_name="ob_refined_strategy"):
    """Run backtest on a single symbol's data"""
    return run_strategy_backtest(data, symbol_name, strategy_name)

def run_all_backtests(strategy_name="ob_refined_strategy"):
    """Run backtests on all cached data"""
    print(f"=== RUNNING {strategy_name.upper()} BACKTESTS ON ALL DATA ===\\n")
    
    # Load cached data
    with open('cache/market_data.json', 'r') as f:
        cache_data = json.load(f)
    
    results = {}
    
    # Run backtests for each data type and symbol
    for data_type, symbols in cache_data.items():
        print(f"Processing {data_type.upper()}...")
        results[data_type] = {}
        
        for symbol, data in symbols.items():
            if symbol == 'daily_prices':  # Skip generic table
                continue
                
            print(f"  Running {strategy_name} backtest on {symbol}...")
            result = run_backtest_on_symbol(data, symbol, strategy_name)
            results[data_type][symbol] = result
            
            if 'error' not in result:
                summary = result['summary']
                print(f"    ✅ {summary['num_trades']} trades, {summary['avg_outcome_R']:.2f}R avg, {summary['win_rate_pos_R']:.1%} win rate")
            else:
                print(f"    ❌ Error: {result['error']}")
    
    # Save results
    os.makedirs('cache', exist_ok=True)
    cache_file = f'cache/{strategy_name}_results.json'
    with open(cache_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\\n✅ {strategy_name} results saved to {cache_file}")
    return results

if __name__ == "__main__":
    # Run all strategies
    run_all_backtests("ob_refined_strategy")
    run_all_backtests("fractal_refined_strategy")
    run_all_backtests("fractal_ob_strategy")