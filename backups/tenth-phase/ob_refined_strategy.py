#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refined Order Block (OB) Strategy – Daily time-frame backtest

Implements:
- OB detection using symmetric 3-bar fractals and BOS (break of structure).
- Refined entry with mitigation to OB mid-body + candle confirmation.
- EMA(50) bias filter and ATR(14) volatility filter.
- Risk management: partial at 1R, move stop to BE, 2R target for remaining half.
- Robust, reproducible outputs: trade log, summary, equity curve, year-by-year breakdown.

Usage (CLI):
    python ob_refined_strategy.py \
        --csv GBP_USD_daily.csv \
        --outdir ./outputs \
        --ema 50 \
        --atr-threshold 0.0060 \
        --entry-wait 60 \
        --lookback 10

Notes:
- ATR threshold is in *price units*. For GBP/USD, 60 pips ≈ 0.0060.
- "Stop-first" rule is applied when both stop and target are tagged in the same bar.
- This script assumes the input CSV has columns: Date, Open, High, Low, Close (case-insensitive).

Author: M365 Copilot
"""

import argparse
import os
import json
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ------------------------------
# Utilities
# ------------------------------
def load_price_csv(path: str) -> pd.DataFrame:
    """Load OHLC CSV and standardize column names."""
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [c.strip().lower() for c in df.columns]
    required = {'open', 'high', 'low', 'close'}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"CSV must contain columns: {required}. Found: {df.columns.tolist()}")
    # Coerce numeric
    for c in ['open', 'high', 'low', 'close']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna()
    return df


def compute_indicators(df: pd.DataFrame, ema_span: int = 50, atr_span: int = 14) -> pd.DataFrame:
    """Add EMA(50) and ATR(14) to the DataFrame."""
    df = df.copy()
    df['ema'] = df['close'].ewm(span=ema_span, adjust=False).mean()
    # True range components
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    df['tr'] = np.maximum(tr1, np.maximum(tr2, tr3))
    df['atr'] = df['tr'].ewm(span=atr_span, adjust=False).mean()
    return df


# ------------------------------
# OB Detection via 3-bar fractals
# ------------------------------
def _fractal_pivots(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Return boolean arrays marking 3-bar swing highs and swing lows."""
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)
    pivot_high = np.zeros(n, dtype=bool)
    pivot_low = np.zeros(n, dtype=bool)
    for i in range(1, n - 1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            pivot_high[i] = True
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            pivot_low[i] = True
    return pivot_high, pivot_low


def _last_pivot(idx_list: List[int], i: int) -> int:
    """Index of last pivot <= i; returns None if none."""
    import bisect
    pos = bisect.bisect_left(idx_list, i)
    return idx_list[pos - 1] if pos > 0 else None


def detect_order_blocks(
    df: pd.DataFrame,
    lookback: int = 10
) -> pd.DataFrame:
    """
    Detect OBs based on BOS relative to the last 3-bar swing high/low.

    OB rules:
      - Bullish BOS: today's high > last swing high ⇒ OB is last bearish candle body within lookback.
      - Bearish BOS: today's low < last swing low ⇒ OB is last bullish candle body within lookback.

    Returns: DataFrame with columns:
      ['type','ob_date','bos_date','ob_open','ob_close','ob_high','ob_low']
    """
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    closes = df['close'].values
    n = len(df)

    ph, pl = _fractal_pivots(df)
    ph_idx = np.where(ph)[0].tolist()
    pl_idx = np.where(pl)[0].tolist()

    records = []
    for i in range(2, n):
        # Bullish BOS
        lph = _last_pivot(ph_idx, i)
        if lph is not None and highs[i] > highs[lph]:
            start = max(0, i - lookback)
            j_candidates = [j for j in range(start, i) if closes[j] < opens[j]]
            if j_candidates:
                j = j_candidates[-1]
                records.append(dict(
                    type='Bullish',
                    ob_date=df.index[j],
                    bos_date=df.index[i],
                    ob_open=float(opens[j]),
                    ob_close=float(closes[j]),
                    ob_high=float(highs[j]),
                    ob_low=float(lows[j]),
                ))
        # Bearish BOS
        lpl = _last_pivot(pl_idx, i)
        if lpl is not None and lows[i] < lows[lpl]:
            start = max(0, i - lookback)
            j_candidates = [j for j in range(start, i) if closes[j] > opens[j]]
            if j_candidates:
                j = j_candidates[-1]
                records.append(dict(
                    type='Bearish',
                    ob_date=df.index[j],
                    bos_date=df.index[i],
                    ob_open=float(opens[j]),
                    ob_close=float(closes[j]),
                    ob_high=float(highs[j]),
                    ob_low=float(lows[j]),
                ))
    ob = pd.DataFrame(records).sort_values('bos_date').reset_index(drop=True)
    return ob


# ------------------------------
# Refined Backtest (partial 1R, BE, 2R)
# ------------------------------
def refined_backtest(
    df: pd.DataFrame,
    ob: pd.DataFrame,
    entry_wait_bars: int = 60,
    atr_threshold: float = 0.0060,
    stop_on_tie: bool = True
) -> pd.DataFrame:
    """
    Execute refined backtest:
      - Entry at OB mid-body on mitigation with candle confirmation.
      - EMA(50) trend bias & ATR(14) volatility filter on the entry bar.
      - 50% partial at 1R, move stop to BE, and aim for 2R on remaining half.
      - Conservative 'stop-first' rule when both levels are touched in same bar.

    Returns: trades DataFrame with columns:
      ['type','ob_date','bos_date','entry_date','entry','stop','R','outcome_R']
    """
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    closes = df['close'].values
    n = len(df)

    trades = []

    # Helper: index of date
    def idx_of(ts) -> int:
        try:
            return df.index.get_loc(ts)
        except KeyError:
            return df.index.searchsorted(ts)

    for _, row in ob.iterrows():
        typ = row['type']
        bos_i = idx_of(row['bos_date'])
        if bos_i is None or bos_i >= n - 1:
            continue

        ob_open = row['ob_open']
        ob_close = row['ob_close']
        ob_low = row['ob_low']
        ob_high = row['ob_high']
        mid = (ob_open + ob_close) / 2.0

        # Search for mitigation + confirmation within window
        start = bos_i + 1
        end = min(bos_i + 1 + entry_wait_bars, n)
        entry_i = None
        entry_px = None

        if typ == 'Bullish':
            for i in range(start, end):
                # mitigation touch
                if lows[i] <= mid:
                    # confirmation in zone: candle closes bullish and above mid
                    if closes[i] > opens[i] and closes[i] > mid:
                        # Filters: EMA bias & ATR threshold
                        if df['close'].iloc[i] > df['ema'].iloc[i] and df['atr'].iloc[i] >= atr_threshold:
                            entry_i = i
                            entry_px = mid
                            break
            if entry_i is None:
                continue
            stop = ob_low
            if entry_px <= stop:
                continue
            R = entry_px - stop
            r1 = entry_px + 1.0 * R
            r2 = entry_px + 2.0 * R

            partial_taken = False
            total_R = None
            exit_i = None

            for t in range(entry_i + 1, n):
                lo = lows[t]
                hi = highs[t]
                if not partial_taken:
                    stop_hit = lo <= stop
                    r1_hit = hi >= r1

                    if stop_on_tie:
                        if stop_hit and r1_hit:
                            total_R = -1.0
                            exit_i = t
                            break

                    if stop_hit:
                        total_R = -1.0
                        exit_i = t
                        break
                    if r1_hit:
                        partial_taken = True
                        # +0.5R realized; move SL to BE
                        stop_be = entry_px
                        # Same-bar check for r2 vs BE (conservative stop-first)
                        r2_hit_same = hi >= r2
                        be_hit_same = lo <= stop_be
                        if stop_on_tie and be_hit_same and r2_hit_same:
                            total_R = 0.5 * 1.0 + 0.0
                            exit_i = t
                            break
                        if r2_hit_same:
                            total_R = 0.5 * 1.0 + 0.5 * 2.0
                            exit_i = t
                            break
                        if be_hit_same:
                            total_R = 0.5 * 1.0 + 0.0
                            exit_i = t
                            break
                        trailing = {'stop_be': stop_be, 'r2': r2}
                        continue
                else:
                    stop_hit = lows[t] <= trailing['stop_be']
                    r2_hit = highs[t] >= trailing['r2']
                    if stop_on_tie and stop_hit and r2_hit:
                        total_R = 0.5 * 1.0 + 0.0
                        exit_i = t
                        break
                    if stop_hit:
                        total_R = 0.5 * 1.0 + 0.0
                        exit_i = t
                        break
                    if r2_hit:
                        total_R = 0.5 * 1.0 + 0.5 * 2.0
                        exit_i = t
                        break

            if exit_i is None:
                # End-of-series close handling
                if partial_taken:
                    rem_R = (closes[n - 1] - entry_px) / R
                    total_R = 0.5 * 1.0 + 0.5 * rem_R
                else:
                    total_R = (closes[n - 1] - entry_px) / R
                exit_i = n - 1

            trades.append(dict(
                type=typ,
                ob_date=row['ob_date'],
                bos_date=row['bos_date'],
                entry_date=df.index[entry_i],
                entry=float(entry_px),
                stop=float(stop),
                R=float(R),
                outcome_R=float(total_R),
            ))

        else:  # Bearish
            for i in range(start, end):
                if highs[i] >= mid:
                    if closes[i] < opens[i] and closes[i] < mid:
                        if df['close'].iloc[i] < df['ema'].iloc[i] and df['atr'].iloc[i] >= atr_threshold:
                            entry_i = i
                            entry_px = mid
                            break
            if entry_i is None:
                continue
            stop = ob_high
            if entry_px >= stop:
                continue
            R = stop - entry_px
            r1 = entry_px - 1.0 * R
            r2 = entry_px - 2.0 * R

            partial_taken = False
            total_R = None
            exit_i = None

            for t in range(entry_i + 1, n):
                lo = lows[t]
                hi = highs[t]
                if not partial_taken:
                    stop_hit = hi >= stop
                    r1_hit = lo <= r1

                    if stop_on_tie:
                        if stop_hit and r1_hit:
                            total_R = -1.0
                            exit_i = t
                            break

                    if stop_hit:
                        total_R = -1.0
                        exit_i = t
                        break
                    if r1_hit:
                        partial_taken = True
                        stop_be = entry_px
                        r2_hit_same = lo <= r2
                        be_hit_same = hi >= stop_be
                        if stop_on_tie and be_hit_same and r2_hit_same:
                            total_R = 0.5 * 1.0 + 0.0
                            exit_i = t
                            break
                        if r2_hit_same:
                            total_R = 0.5 * 1.0 + 0.5 * 2.0
                            exit_i = t
                            break
                        if be_hit_same:
                            total_R = 0.5 * 1.0 + 0.0
                            exit_i = t
                            break
                        trailing = {'stop_be': stop_be, 'r2': r2}
                        continue
                else:
                    stop_hit = highs[t] >= trailing['stop_be']
                    r2_hit = lows[t] <= trailing['r2']
                    if stop_on_tie and stop_hit and r2_hit:
                        total_R = 0.5 * 1.0 + 0.0
                        exit_i = t
                        break
                    if stop_hit:
                        total_R = 0.5 * 1.0 + 0.0
                        exit_i = t
                        break
                    if r2_hit:
                        total_R = 0.5 * 1.0 + 0.5 * 2.0
                        exit_i = t
                        break

            if exit_i is None:
                if partial_taken:
                    rem_R = (entry_px - closes[n - 1]) / R
                    total_R = 0.5 * 1.0 + 0.5 * rem_R
                else:
                    total_R = (entry_px - closes[n - 1]) / R
                exit_i = n - 1

            trades.append(dict(
                type=typ,
                ob_date=row['ob_date'],
                bos_date=row['bos_date'],
                entry_date=df.index[entry_i],
                entry=float(entry_px),
                stop=float(stop),
                R=float(R),
                outcome_R=float(total_R),
            ))

    return pd.DataFrame(trades)


# ------------------------------
# Reporting & Charts
# ------------------------------
def summarize_trades(trades: pd.DataFrame) -> Dict:
    """Compute global metrics."""
    if trades.empty:
        return {
            'num_trades': 0,
            'bullish_trades': 0,
            'bearish_trades': 0,
            'avg_outcome_R': 0.0,
            'win_rate_pos_R': 0.0,
        }
    out = {
        'num_trades': int(len(trades)),
        'bullish_trades': int((trades['type'] == 'Bullish').sum()),
        'bearish_trades': int((trades['type'] == 'Bearish').sum()),
        'avg_outcome_R': float(trades['outcome_R'].mean()),
        'win_rate_pos_R': float((trades['outcome_R'] > 0).mean()),
    }
    return out


def year_by_year(trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trades by calendar year."""
    trades = trades.copy()
    trades['year'] = trades['entry_date'].dt.year
    by_year = trades.groupby('year').agg(
        trades=('outcome_R', 'count'),
        avg_R=('outcome_R', 'mean'),
        win_rate=('outcome_R', lambda s: (s > 0).mean()),
        cum_R=('outcome_R', 'sum'),
        bulls=('type', lambda s: (s == 'Bullish').sum()),
        bears=('type', lambda s: (s == 'Bearish').sum()),
    ).reset_index()
    return by_year


def plot_equity_curve(trades: pd.DataFrame, outpath: str):
    """Plot cumulative R equity curve (chronological by entry date)."""
    if trades.empty:
        return
    srt = trades.sort_values('entry_date')
    eq = srt['outcome_R'].cumsum().values
    x = np.arange(len(eq))
    plt.figure(figsize=(12, 4))
    plt.plot(x, eq, color='darkgreen', lw=1.4)
    plt.title('Refined OB Setup – Equity Curve (Partial at 1R, BE, 2R)')
    plt.xlabel('Trade # (chronological)')
    plt.ylabel('Cumulative R')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_yearly_cumR(by_year: pd.DataFrame, outpath: str):
    """Bar chart of cumulative R per year."""
    if by_year.empty:
        return
    plt.figure(figsize=(12, 5))
    colors = ['#2e7d32' if x >= 0 else '#c62828' for x in by_year['cum_R']]
    plt.bar(by_year['year'], by_year['cum_R'], color=colors)
    plt.title('Refined OB Setup – Year-by-Year Cumulative R')
    plt.xlabel('Year')
    plt.ylabel('Cumulative R')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


# ------------------------------
# Main (CLI)
# ------------------------------
def main():
    parser = argparse.ArgumentParser(description="Refined OB Strategy Backtest (Daily)")
    parser.add_argument("--csv", required=True, help="Input OHLC CSV (Date index; columns: Open, High, Low, Close)")
    parser.add_argument("--outdir", default="./outputs", help="Directory to save outputs")
    parser.add_argument("--ema", type=int, default=50, help="EMA span for trend bias (default=50)")
    parser.add_argument("--atr-span", type=int, default=14, help="ATR span (default=14)")
    parser.add_argument("--atr-threshold", type=float, default=0.0060, help="ATR threshold in price units (e.g., 0.0060 ≈ 60 pips)")
    parser.add_argument("--entry-wait", type=int, default=60, help="Max bars to wait for mitigation entry after BOS")
    parser.add_argument("--lookback", type=int, default=10, help="Lookback bars to find last opposing candle as OB")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # 1) Load data & indicators
    df = load_price_csv(args.csv)
    df = compute_indicators(df, ema_span=args.ema, atr_span=args.atr_span)

    # 2) Detect OBs (3-bar fractal BOS)
    ob = detect_order_blocks(df, lookback=args.lookback)
    ob_path = os.path.join(args.outdir, "order_blocks_3bar_refined_input.csv")
    ob.to_csv(ob_path, index=False)

    # 3) Backtest refined rules
    trades = refined_backtest(
        df=df,
        ob=ob,
        entry_wait_bars=args.entry_wait,
        atr_threshold=args.atr_threshold,
        stop_on_tie=True,
    )

    # 4) Summaries & charts
    summary = summarize_trades(trades)
    by_year = year_by_year(trades)

    # Save outputs
    trades_path = os.path.join(args.outdir, "ob_backtest_trades_refined.csv")
    summary_path = os.path.join(args.outdir, "ob_backtest_summary_refined.json")
    byyear_path = os.path.join(args.outdir, "refined_yearly_breakdown.csv")
    eq_path = os.path.join(args.outdir, "equity_curve_refined_R.png")
    yearly_chart_path = os.path.join(args.outdir, "refined_yearly_cumR.png")

    trades.to_csv(trades_path, index=False)
    pd.Series(summary).to_json(summary_path)
    by_year.to_csv(byyear_path, index=False)
    plot_equity_curve(trades, eq_path)
    plot_yearly_cumR(by_year, yearly_chart_path)

    # Console output
    start = df.index.min().date().isoformat()
    end = df.index.max().date().isoformat()
    print("\nBacktest window:", start, "→", end)
    print("Summary:", json.dumps(summary, indent=2))
    print("\nFiles written:")
    print("  • OBs:", ob_path)
    print("  • Trades:", trades_path)
    print("  • Summary:", summary_path)
    print("  • Yearly Breakdown:", byyear_path)
    print("  • Equity Curve:", eq_path)
    print("  • Yearly CumR Chart:", yearly_chart_path)


if __name__ == "__main__":
    main()
