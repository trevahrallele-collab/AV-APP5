import numpy as np
import pandas as pd

def detect_signals(df, left_bars=2, right_bars=2, lookback=20, ema_period=50, atr_period=14):
    """
    Detect fractal trading signals from price data
    Returns: DataFrame with columns ['type', 'signal_date', 'entry_price', ...]
    """
    # Calculate indicators
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    df['atr'] = calculate_atr(df, atr_period)
    
    # Detect fractals
    fractals = detect_fractals(df, left_bars, right_bars)
    
    # Calculate breakout levels
    fractal_highs = fractals['fractal_high'].rolling(lookback, min_periods=1).max()
    fractal_lows = fractals['fractal_low'].rolling(lookback, min_periods=1).min()
    
    signals = []
    
    for i in range(1, len(df)):
        prev_close = df['close'].iloc[i-1]
        current_open = df['open'].iloc[i]
        ema_val = df['ema'].iloc[i-1]
        
        # Long signal: price above EMA and breaks fractal high
        if (prev_close > ema_val and 
            prev_close > fractal_highs.iloc[i-1] and 
            not pd.isna(fractal_highs.iloc[i-1])):
            
            signals.append({
                'type': 'Bullish',
                'signal_date': df.index[i],
                'entry_price': current_open,
                'fractal_level': fractal_highs.iloc[i-1],
                'ema_level': ema_val,
                'atr': df['atr'].iloc[i-1]
            })
        
        # Short signal: price below EMA and breaks fractal low
        elif (prev_close < ema_val and 
              prev_close < fractal_lows.iloc[i-1] and 
              not pd.isna(fractal_lows.iloc[i-1])):
            
            signals.append({
                'type': 'Bearish',
                'signal_date': df.index[i],
                'entry_price': current_open,
                'fractal_level': fractal_lows.iloc[i-1],
                'ema_level': ema_val,
                'atr': df['atr'].iloc[i-1]
            })
    
    return pd.DataFrame(signals)

def execute_backtest(df, signals, atr_mult_stop=2.0, risk_per_trade=0.01):
    """
    Execute backtest with risk management
    Returns: DataFrame with columns ['type', 'entry_date', 'entry', 'stop', 'R', 'outcome_R']
    """
    trades = []
    
    for _, signal in signals.iterrows():
        entry_date = signal['signal_date']
        entry_price = signal['entry_price']
        signal_type = signal['type']
        atr_val = signal['atr']
        
        # Calculate stop loss
        if signal_type == 'Bullish':
            stop_price = entry_price - (atr_mult_stop * atr_val)
        else:  # Bearish
            stop_price = entry_price + (atr_mult_stop * atr_val)
        
        # Calculate R (risk per share)
        R = abs(entry_price - stop_price)
        
        # Find exit
        outcome_R = find_exit(df, entry_date, entry_price, stop_price, signal_type)
        
        trades.append({
            'type': signal_type,
            'entry_date': entry_date,
            'entry': entry_price,
            'stop': stop_price,
            'R': R,
            'outcome_R': outcome_R
        })
    
    return pd.DataFrame(trades)

def summarize_results(trades):
    """
    Calculate summary metrics
    Returns: Dict with keys ['num_trades', 'avg_outcome_R', 'win_rate_pos_R', 'bullish_trades', 'bearish_trades']
    """
    if trades.empty:
        return {
            'num_trades': 0,
            'avg_outcome_R': 0.0,
            'win_rate_pos_R': 0.0,
            'bullish_trades': 0,
            'bearish_trades': 0
        }
    
    num_trades = len(trades)
    avg_outcome_R = trades['outcome_R'].mean()
    win_rate_pos_R = (trades['outcome_R'] > 0).mean()
    bullish_trades = len(trades[trades['type'] == 'Bullish'])
    bearish_trades = len(trades[trades['type'] == 'Bearish'])
    
    return {
        'num_trades': num_trades,
        'avg_outcome_R': round(avg_outcome_R, 3),
        'win_rate_pos_R': round(win_rate_pos_R, 3),
        'bullish_trades': bullish_trades,
        'bearish_trades': bearish_trades
    }

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    return tr.ewm(alpha=1/period, adjust=False).mean()

def detect_fractals(df, left_bars=2, right_bars=2):
    """Detect Bill Williams fractals"""
    high = df['high'].values
    low = df['low'].values
    n = len(df)
    
    bearish = np.zeros(n, dtype=bool)
    bullish = np.zeros(n, dtype=bool)
    
    for i in range(left_bars, n - right_bars):
        # Top fractal (bearish)
        if (high[i] == max(high[i-left_bars:i+right_bars+1]) and
            high[i] > max(high[i-left_bars:i]) and
            high[i] > max(high[i+1:i+right_bars+1])):
            bearish[i] = True
        
        # Bottom fractal (bullish)
        if (low[i] == min(low[i-left_bars:i+right_bars+1]) and
            low[i] < min(low[i-left_bars:i]) and
            low[i] < min(low[i+1:i+right_bars+1])):
            bullish[i] = True
    
    result = pd.DataFrame(index=df.index)
    result['bearish_fractal'] = bearish
    result['bullish_fractal'] = bullish
    result['fractal_high'] = np.where(bearish, df['high'], np.nan)
    result['fractal_low'] = np.where(bullish, df['low'], np.nan)
    
    # Shift to avoid look-ahead bias
    result['fractal_high'] = result['fractal_high'].shift(right_bars)
    result['fractal_low'] = result['fractal_low'].shift(right_bars)
    
    return result

def find_exit(df, entry_date, entry_price, stop_price, signal_type):
    """Find trade exit and calculate outcome in R"""
    try:
        entry_idx = df.index.get_loc(entry_date)
        R = abs(entry_price - stop_price)
        
        # Look for exit in subsequent bars
        for i in range(entry_idx + 1, len(df)):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            if signal_type == 'Bullish':
                # Check stop loss
                if low <= stop_price:
                    return -1.0  # -1R loss
                # Check for profit (simple 2R target)
                target_price = entry_price + (2 * R)
                if high >= target_price:
                    return 2.0  # 2R profit
            else:  # Bearish
                # Check stop loss
                if high >= stop_price:
                    return -1.0  # -1R loss
                # Check for profit (simple 2R target)
                target_price = entry_price - (2 * R)
                if low <= target_price:
                    return 2.0  # 2R profit
        
        # No exit found, assume breakeven
        return 0.0
        
    except Exception:
        return 0.0