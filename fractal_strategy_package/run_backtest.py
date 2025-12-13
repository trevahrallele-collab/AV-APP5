# -*- coding: utf-8 -*-
"""
CLI runner for the Fractal Trading Strategy.

Usage:
    python run_backtest.py --data data.csv --date-col Date --output-dir outputs \
        --ema 50 --lookback 20 --atr 14 --htf-rule W --use-htf --use-short

Outputs:
    - performance_summary.json
    - equity_curve.csv
    - drawdown.csv
    - trades.csv
    - equity_curve.png
    - fractals_price.png
"""
import os, json, argparse
import pandas as pd
from fractal_strategy import (
    FractalParams, backtest, plot_equity, plot_fractals_on_price
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
    parser = argparse.ArgumentParser(description='Run Fractal Strategy backtest')
    parser.add_argument('--data', required=False, default='example_data.csv', help='Path to CSV with Date,Open,High,Low,Close[,Volume]')
    parser.add_argument('--date-col', default='Date', help='Name of date column')
    parser.add_argument('--output-dir', default='outputs', help='Directory to save outputs')
    parser.add_argument('--ema', type=int, default=50, help='EMA period for trend filter')
    parser.add_argument('--lookback', type=int, default=20, help='Lookback bars for breakout levels')
    parser.add_argument('--atr', type=int, default=14, help='ATR period')
    parser.add_argument('--atr-stop', type=float, default=2.0, help='ATR multiple for initial stop')
    parser.add_argument('--atr-trail', type=float, default=3.0, help='ATR multiple for trailing stop')
    parser.add_argument('--risk', type=float, default=0.01, help='Risk per trade fraction of equity')
    parser.add_argument('--slip-bps', type=float, default=2.0, help='Slippage in basis points')
    parser.add_argument('--comm-bps', type=float, default=10.0, help='Commission per side in basis points')
    parser.add_argument('--tpR', type=float, default=None, help='Fixed take-profit in R (e.g., 3.0)')
    parser.add_argument('--use-htf', action='store_true', help='Enable HTF confirmation')
    parser.add_argument('--htf-rule', default='W', help='Resample rule for HTF (e.g., W, M, 4H)')
    parser.add_argument('--no-short', action='store_true', help='Disable short selling')

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

    params = FractalParams(
        left_bars=2,
        right_bars=2,
        lookback=args.lookback,
        ema_period=args.ema,
        atr_period=args.atr,
        atr_mult_stop=args.atr_stop,
        atr_mult_trail=args.atr_trail,
        risk_per_trade=args.risk,
        slippage_bps=args.slip_bps,
        commission_bps=args.comm_bps,
        take_profit_R=args.tpR,
        use_htf=args.use_htf,
        htf_rule=args.htf_rule,
        use_short=(not args.no_short)
    )

    perf = backtest(df, params)

    # Save performance summary
    with open(os.path.join(args.output_dir, 'performance_summary.json'), 'w') as f:
        json.dump(perf.stats, f, indent=2)

    # Save curves
    perf.equity_curve.to_csv(os.path.join(args.output_dir, 'equity_curve.csv'), header=['equity'])
    perf.drawdown.to_csv(os.path.join(args.output_dir, 'drawdown.csv'), header=['drawdown'])

    # Save trades
    trades_df = trades_to_df(perf.trades)
    trades_df.to_csv(os.path.join(args.output_dir, 'trades.csv'), index=False)

    # Save plots
    plot_equity(perf, title='Fractal Strategy Equity Curve', save_path=os.path.join(args.output_dir, 'equity_curve.png'))
    plot_fractals_on_price(df, params, save_path=os.path.join(args.output_dir, 'fractals_price.png'))

    print("Backtest complete. Outputs saved to:", os.path.abspath(args.output_dir))

if __name__ == '__main__':
    main()
