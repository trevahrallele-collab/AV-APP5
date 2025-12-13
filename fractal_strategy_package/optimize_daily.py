# -*- coding: utf-8 -*-
"""
Daily Data Optimizer for the Fractal Trading Strategy
-----------------------------------------------------
Runs a parameter grid search tailored to DAILY OHLC data,
selects the best configuration by Sharpe, and saves reports.

Usage:
    python optimize_daily.py --data YOUR_DATA.csv --date-col Date --output-dir outputs_daily

Outputs:
    - best_params.json
    - grid_results.csv
    - performance_summary.json
    - equity_curve.csv / drawdown.csv / trades.csv
    - equity_curve.png / fractals_price.png

Disclaimer: Educational use only. Not financial advice.
"""
import os, json, argparse
import pandas as pd
from fractal_strategy import (
    FractalParams, backtest, grid_search, plot_equity, plot_fractals_on_price
)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def trades_to_df(trades):
    rows = []
    for t in trades:
        rows.append({
            'entry_ts': t.entry_idx.isoformat() if t.entry_idx is not None else None,
            'exit_ts': t.exit_idx.isoformat() if t.exit_idx is not None else None,
            'side': t.side,
            'qty': t.qty,
            'entry_price': t.entry_price,
            'stop_initial': t.stop_initial,
            'stop_exit_price': t.stop_exit_price,
            'exit_price': t.exit_price,
            'pnl': t.pnl,
            'R_multiple': t.R_multiple
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description='Optimize Fractal Strategy for Daily Data')
    parser.add_argument('--data', required=False, default='example_data.csv', help='Path to CSV with Date,Open,High,Low,Close[,Volume]')
    parser.add_argument('--date-col', default='Date', help='Name of date column')
    parser.add_argument('--output-dir', default='outputs_daily', help='Directory to save outputs')
    parser.add_argument('--use-htf', action='store_true', help='Enable weekly HTF confirmation')
    args = parser.parse_args()
    ensure_dir(args.output_dir)

    # Load data
    df = pd.read_csv(args.data)
    if args.date_col in df.columns:
        df[args.date_col] = pd.to_datetime(df[args.date_col])
        df = df.set_index(args.date_col).sort_index()
    else:
        raise ValueError(f"Date column '{args.date_col}' not found in {args.data}")

    required_cols = {'Open','High','Low','Close'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Data must contain columns: {required_cols}")

    base = FractalParams(
        left_bars=2,
        right_bars=2,
        lookback=20,
        ema_period=50,
        atr_period=14,
        atr_mult_stop=2.0,
        atr_mult_trail=3.0,
        risk_per_trade=0.01,
        slippage_bps=5.0,   # daily fills often gap; use a slightly higher slippage
        commission_bps=10.0,
        take_profit_R=None,
        use_htf=args.use_htf,
        htf_rule='W',
        use_short=True
    )

    # Daily-appropriate parameter ranges (kept modest to be fast)
    param_grid = {
        'lookback': [10, 20, 40],
        'ema_period': [34, 50, 100, 200],
        'atr_mult_stop': [1.5, 2.0, 2.5],
        'atr_mult_trail': [2.0, 3.0, 4.0],
        'left_bars': [2, 3],
        'right_bars': [2, 3],
        'use_htf': [args.use_htf]  # fixed to CLI choice
    }

    best_p, best_perf, results = grid_search(df, param_grid, base)

    # Save grid results and best params
    results.to_csv(os.path.join(args.output_dir, 'grid_results.csv'), index=False)
    with open(os.path.join(args.output_dir, 'best_params.json'), 'w') as f:
        json.dump(best_p.__dict__, f, indent=2)

    # Save performance summary & series
    with open(os.path.join(args.output_dir, 'performance_summary.json'), 'w') as f:
        json.dump(best_perf.stats, f, indent=2)
    best_perf.equity_curve.to_csv(os.path.join(args.output_dir, 'equity_curve.csv'), header=['equity'])
    best_perf.drawdown.to_csv(os.path.join(args.output_dir, 'drawdown.csv'), header=['drawdown'])
    trades_df = trades_to_df(best_perf.trades)
    trades_df.to_csv(os.path.join(args.output_dir, 'trades.csv'), index=False)

    # Save plots
    plot_equity(best_perf, title='Daily Optimized Fractal Strategy — Equity Curve',
                save_path=os.path.join(args.output_dir, 'equity_curve.png'))
    plot_fractals_on_price(df, best_p, save_path=os.path.join(args.output_dir, 'fractals_price.png'))

    print('Optimization complete.')
    print('Best params:', best_p)
    print('Outputs:', os.path.abspath(args.output_dir))

if __name__ == '__main__':
    main()
