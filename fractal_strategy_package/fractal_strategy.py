# -*- coding: utf-8 -*-
"""
Fractal Trading Strategy (Bill Williams style) — Non-repainting, Backtest-ready

Disclaimer: For educational use only. Trading involves risk. Not financial advice.

Author: M365 Copilot
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Tuple, List

# -----------------------
# Utilities & Indicators
# -----------------------

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range using classic Wilder smoothing.
    Requires columns: High, Low, Close.
    """
    high, low, close = df['High'], df['Low'], df['Close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr_series = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr_series

def detect_fractals(df: pd.DataFrame, left_bars: int = 2, right_bars: int = 2) -> pd.DataFrame:
    """
    Bill Williams fractals.
    Returns confirmed pivots shifted by `right_bars` to avoid look-ahead.
    """
    if not {'High', 'Low'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'High' and 'Low'.")

    H, L = df['High'].values, df['Low'].values
    n = len(df)
    bearish = np.zeros(n, dtype=bool)
    bullish = np.zeros(n, dtype=bool)

    lb, rb = left_bars, right_bars
    for i in range(lb, n - rb):
        # top fractal
        window_highs = H[i - lb: i + rb + 1]
        if H[i] == window_highs.max() and H[i] > H[i - lb:i].max() and H[i] > H[i + 1:i + rb + 1].max():
            bearish[i] = True
        # bottom fractal
        window_lows = L[i - lb: i + rb + 1]
        if L[i] == window_lows.min() and L[i] < L[i - lb:i].min() and L[i] < L[i + 1:i + rb + 1].min():
            bullish[i] = True

    out = pd.DataFrame(index=df.index)
    out['bearish_fractal_raw'] = bearish
    out['bullish_fractal_raw'] = bullish
    out['bearish_fractal'] = out['bearish_fractal_raw'].shift(right_bars).fillna(False).astype(bool)
    out['bullish_fractal'] = out['bullish_fractal_raw'].shift(right_bars).fillna(False).astype(bool)
    out['fractal_high'] = np.where(out['bearish_fractal'], df['High'], np.nan)
    out['fractal_low']  = np.where(out['bullish_fractal'], df['Low'],  np.nan)
    return out


def most_recent(series: pd.Series) -> pd.Series:
    """Forward-fill the last known non-NaN value."""
    return series.ffill()


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    Resample OHLCV to higher timeframe (e.g., 'W', 'M', '4H').
    If Volume is missing, it's handled gracefully.
    """
    agg = {
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last'
    }
    if 'Volume' in df.columns:
        agg['Volume'] = 'sum'
    htf = df.resample(rule).apply(agg).dropna()
    return htf


def forward_map_htf_levels(ltf_index: pd.DatetimeIndex,
                           htf_fr: pd.DataFrame,
                           level_col: str) -> pd.Series:
    """
    Map HTF fractal levels forward to LTF timeline.
    We take the last known HTF level at or before each LTF timestamp.
    """
    ts = htf_fr[level_col].copy()
    ts = ts.where(~ts.isna())
    mapped = ts.reindex(ltf_index, method='ffill')
    return mapped

# -----------------------
# Strategy Configuration
# -----------------------

@dataclass
class FractalParams:
    left_bars: int = 2
    right_bars: int = 2
    lookback: int = 20                # window for selecting breakout levels
    ema_period: int = 50              # trend filter
    atr_period: int = 14
    atr_mult_stop: float = 2.0        # initial stop
    atr_mult_trail: float = 3.0       # chandelier trailing
    risk_per_trade: float = 0.01      # 1% of equity
    slippage_bps: float = 2.0         # 2 bps
    commission_bps: float = 10.0      # 10 bps per side
    take_profit_R: Optional[float] = None  # e.g., 3.0 for 3R TP
    use_htf: bool = True
    htf_rule: str = 'W'               # 'W', 'M', '4H', etc.
    use_short: bool = True
    allow_multiple_positions: bool = False  # engine uses 1 position at a time

# -----------------------
# Signal Construction
# -----------------------

def build_signals(df: pd.DataFrame, p: FractalParams) -> Dict[str, pd.Series]:
    """
    Build indicators and breakout levels.
    Returns a dict of series aligned to df.index
    """
    series = {}
    series['ema'] = ema(df['Close'], p.ema_period)
    series['atr'] = atr(df, p.atr_period)

    fr_ltf = detect_fractals(df, p.left_bars, p.right_bars)

    # Rolling breakout levels
    series['ltf_long_level'] = fr_ltf['fractal_high'].rolling(p.lookback, min_periods=1).max()
    series['ltf_short_level'] = fr_ltf['fractal_low'].rolling(p.lookback, min_periods=1).min()

    if p.use_htf:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("HTF confirmation requires a DatetimeIndex on df.")
        htf = resample_ohlc(df, p.htf_rule)
        fr_htf = detect_fractals(htf, p.left_bars, p.right_bars)
        htf_bear_high = fr_htf['fractal_high']
        htf_bull_low  = fr_htf['fractal_low']
        mapped_bear_high = forward_map_htf_levels(df.index, htf_bear_high.to_frame('fractal_high'), 'fractal_high')
        mapped_bull_low  = forward_map_htf_levels(df.index, htf_bull_low.to_frame('fractal_low'), 'fractal_low')
        series['htf_bearish_high'] = mapped_bear_high
        series['htf_bullish_low']  = mapped_bull_low
    else:
        series['htf_bearish_high'] = pd.Series(index=df.index, dtype=float)
        series['htf_bullish_low']  = pd.Series(index=df.index, dtype=float)

    return series

# -----------------------
# Backtest Engine
# -----------------------

@dataclass
class Trade:
    entry_idx: pd.Timestamp
    exit_idx: Optional[pd.Timestamp]
    side: int                 # +1 long, -1 short
    qty: float
    entry_price: float
    stop_initial: float
    stop_exit_price: Optional[float]
    exit_price: Optional[float]
    pnl: Optional[float]
    mae: float                # max adverse excursion in R
    mfe: float                # max favorable excursion in R
    R_multiple: Optional[float]

@dataclass
class Performance:
    equity_curve: pd.Series
    drawdown: pd.Series
    stats: Dict[str, float]
    trades: List[Trade]


def _apply_cost(price: float, side: int, slippage_bps: float, commission_bps: float) -> float:
    """
    Adjust fill price for slippage and commissions.
    We fold commissions into effective price via half-spread approach.
    """
    slip = price * (slippage_bps / 1e4)
    comm = price * (commission_bps / 1e4)
    if side == +1:
        return price + slip + comm
    else:
        return price - slip - comm


def backtest(df: pd.DataFrame, p: FractalParams) -> Performance:
    """
    Event-driven loop, one position at a time.
    Orders are filled at NEXT bar's open with slippage + commission.
    Stops/TP are checked intrabar using High/Low.
    """
    s = build_signals(df, p)
    close, open_, high, low = df['Close'], df['Open'], df['High'], df['Low']
    ema_s, atr_s = s['ema'], s['atr']
    ltf_long_level, ltf_short_level = s['ltf_long_level'], s['ltf_short_level']
    htf_bear_high, htf_bull_low = s['htf_bearish_high'], s['htf_bullish_low']

    equity = 100_000.0
    equity_curve = []
    drawdown = []
    high_water = equity

    position = 0      # +1 long, -1 short, 0 flat
    qty = 0.0
    entry_price = np.nan
    stop_price = np.nan
    trail_price = np.nan
    risk_per_share = np.nan
    entry_equity = np.nan
    entry_idx = None
    peak_since_entry = -np.inf
    trough_since_entry = np.inf
    trades: List[Trade] = []

    def long_breakout_level(i):
        l1 = ltf_long_level.iat[i]
        l2 = htf_bear_high.iat[i] if not np.isnan(htf_bear_high.iat[i]) else -np.inf
        return max(l1, l2) if p.use_htf else l1

    def short_breakout_level(i):
        s1 = ltf_short_level.iat[i]
        s2 = htf_bull_low.iat[i] if not np.isnan(htf_bull_low.iat[i]) else np.inf
        return min(s1, s2) if p.use_htf else s1

    idx_list = df.index.to_list()
    n = len(df)

    for i in range(1, n):  # start at 1 for next-open fills
        ts_prev, ts = idx_list[i-1], idx_list[i]

        equity_curve.append((ts_prev, equity))
        high_water = max(high_water, equity)
        dd = (equity - high_water) / high_water if high_water > 0 else 0.0
        drawdown.append((ts_prev, dd))

        c, o, h, l = close.iat[i], open_.iat[i], high.iat[i], low.iat[i]
        ema_now = ema_s.iat[i]
        atr_now = atr_s.iat[i]

        # Position management intrabar
        if position != 0:
            if position == +1:
                peak_since_entry = max(peak_since_entry, c)
                chand = peak_since_entry - p.atr_mult_trail * atr_now
                if not np.isnan(chand):
                    trail_price = max(trail_price, chand) if not np.isnan(trail_price) else chand
                exit_px = None
                effective_stop = max(stop_price, trail_price) if not np.isnan(trail_price) else stop_price
                if l <= effective_stop <= h:
                    exit_px = effective_stop
                elif p.take_profit_R is not None and not np.isnan(risk_per_share):
                    tp_price = entry_price + p.take_profit_R * risk_per_share
                    if l <= tp_price <= h:
                        exit_px = tp_price
                if exit_px is None and l < (effective_stop or -np.inf):
                    exit_px = l
                if exit_px is None and p.take_profit_R is not None and h > (entry_price + p.take_profit_R * risk_per_share):
                    exit_px = entry_price + p.take_profit_R * risk_per_share
                if exit_px is not None:
                    exit_fill = _apply_cost(exit_px, -position, p.slippage_bps, p.commission_bps)
                    pnl = (exit_fill - entry_price) * qty
                    trade_R = (exit_fill - entry_price) / risk_per_share if risk_per_share != 0 else np.nan
                    trades.append(Trade(entry_idx=entry_idx, exit_idx=ts, side=position, qty=qty,
                                        entry_price=entry_price, stop_initial=stop_price,
                                        stop_exit_price=effective_stop, exit_price=exit_fill, pnl=pnl,
                                        mae=np.nan, mfe=np.nan, R_multiple=trade_R))
                    equity += pnl
                    position = 0
                    qty = 0
                    entry_price = np.nan
                    stop_price = np.nan
                    trail_price = np.nan
                    risk_per_share = np.nan
                    entry_equity = np.nan
                    entry_idx = None
                    peak_since_entry = -np.inf
                    trough_since_entry = np.inf

            elif position == -1:
                trough_since_entry = min(trough_since_entry, c)
                chand = trough_since_entry + p.atr_mult_trail * atr_now
                if not np.isnan(chand):
                    trail_price = min(trail_price, chand) if not np.isnan(trail_price) else chand
                exit_px = None
                effective_stop = min(stop_price, trail_price) if not np.isnan(trail_price) else stop_price
                if l <= effective_stop <= h:
                    exit_px = effective_stop
                elif p.take_profit_R is not None and not np.isnan(risk_per_share):
                    tp_price = entry_price - p.take_profit_R * risk_per_share
                    if l <= tp_price <= h:
                        exit_px = tp_price
                if exit_px is None and h > (effective_stop or np.inf):
                    exit_px = h
                if exit_px is None and p.take_profit_R is not None and l < (entry_price - p.take_profit_R * risk_per_share):
                    exit_px = entry_price - p.take_profit_R * risk_per_share
                if exit_px is not None:
                    exit_fill = _apply_cost(exit_px, -position, p.slippage_bps, p.commission_bps)
                    pnl = (entry_price - exit_fill) * qty
                    trade_R = (entry_price - exit_fill) / risk_per_share if risk_per_share != 0 else np.nan
                    trades.append(Trade(entry_idx=entry_idx, exit_idx=ts, side=position, qty=qty,
                                        entry_price=entry_price, stop_initial=stop_price,
                                        stop_exit_price=effective_stop, exit_price=exit_fill, pnl=pnl,
                                        mae=np.nan, mfe=np.nan, R_multiple=trade_R))
                    equity += pnl
                    position = 0
                    qty = 0
                    entry_price = np.nan
                    stop_price = np.nan
                    trail_price = np.nan
                    risk_per_share = np.nan
                    entry_equity = np.nan
                    entry_idx = None
                    peak_since_entry = -np.inf
                    trough_since_entry = np.inf

        # Entries using prev close vs breakout level; fill next open
        if position == 0:
            L_level = long_breakout_level(i-1)
            S_level = short_breakout_level(i-1)
            prev_close = close.iat[i-1]
            trend_up = prev_close > ema_s.iat[i-1]
            trend_dn = prev_close < ema_s.iat[i-1]
            long_setup = trend_up and prev_close > L_level
            short_setup = p.use_short and trend_dn and prev_close < S_level
            atr_prev = atr_s.iat[i-1]
            opp_long_stop = (min(s['ltf_short_level'].iat[i-1], prev_close - p.atr_mult_stop * atr_prev)
                             if not np.isnan(s['ltf_short_level'].iat[i-1]) else prev_close - p.atr_mult_stop * atr_prev)
            opp_short_stop = (max(s['ltf_long_level'].iat[i-1], prev_close + p.atr_mult_stop * atr_prev)
                              if not np.isnan(s['ltf_long_level'].iat[i-1]) else prev_close + p.atr_mult_stop * atr_prev)

            if long_setup:
                entry_px_raw = open_.iat[i]
                entry_px = _apply_cost(entry_px_raw, +1, p.slippage_bps, p.commission_bps)
                stop_px = opp_long_stop
                risk_ps = max(entry_px - stop_px, 1e-8)
                capital_risk = equity * p.risk_per_trade
                qty = np.floor(capital_risk / risk_ps)
                if qty >= 1:
                    position = +1
                    entry_price = entry_px
                    stop_price = stop_px
                    trail_price = np.nan
                    risk_per_share = risk_ps
                    entry_equity = equity
                    entry_idx = ts
                    peak_since_entry = entry_px
                    trough_since_entry = entry_px

            elif short_setup:
                entry_px_raw = open_.iat[i]
                entry_px = _apply_cost(entry_px_raw, -1, p.slippage_bps, p.commission_bps)
                stop_px = opp_short_stop
                risk_ps = max(stop_px - entry_px, 1e-8)
                capital_risk = equity * p.risk_per_trade
                qty = np.floor(capital_risk / risk_ps)
                if qty >= 1:
                    position = -1
                    entry_price = entry_px
                    stop_price = stop_px
                    trail_price = np.nan
                    risk_per_share = risk_ps
                    entry_equity = equity
                    entry_idx = ts
                    peak_since_entry = entry_px
                    trough_since_entry = entry_px

    equity_curve.append((df.index[-1], equity))
    high_water = max(high_water, equity)
    dd = (equity - high_water) / high_water if high_water > 0 else 0.0
    drawdown.append((df.index[-1], dd))

    ec = pd.Series({t: v for t, v in equity_curve}).sort_index()
    dd_s = pd.Series({t: v for t, v in drawdown}).sort_index()

    returns = ec.pct_change().fillna(0.0)
    days = (ec.index[-1] - ec.index[0]).days or 1
    years = days / 365.25
    cagr = (ec.iloc[-1] / ec.iloc[0]) ** (1 / max(years, 1e-6)) - 1
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0
    max_dd = dd_s.min()

    wins = [t for t in trades if t.pnl is not None and t.pnl > 0]
    losses = [t for t in trades if t.pnl is not None and t.pnl <= 0]
    win_rate = len(wins) / len(trades) if trades else np.nan
    profit_factor = (sum([t.pnl for t in wins]) / abs(sum([t.pnl for t in losses]))) if losses else np.nan
    avg_R = np.nanmean([t.R_multiple for t in trades if t.R_multiple is not None]) if trades else np.nan

    stats = {
        'Start Equity': float(ec.iloc[0]),
        'End Equity': float(ec.iloc[-1]),
        'CAGR': float(cagr),
        'Sharpe (daily≈252)': float(sharpe),
        'Max Drawdown': float(max_dd),
        '# Trades': int(len(trades)),
        'Win Rate': float(win_rate) if win_rate == win_rate else None,
        'Profit Factor': float(profit_factor) if profit_factor == profit_factor else None,
        'Avg R': float(avg_R) if avg_R == avg_R else None
    }

    return Performance(ec, dd_s, stats, trades)

# -----------------------
# Plotting
# -----------------------

def plot_equity(perf: Performance, title: str = "Equity Curve", save_path: Optional[str] = None):
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax[0].plot(perf.equity_curve.index, perf.equity_curve.values, color='black')
    ax[0].set_title(title)
    ax[0].grid(True, alpha=0.3)
    ax[1].fill_between(perf.drawdown.index, perf.drawdown.values, 0, color='red', alpha=0.3)
    ax[1].set_title("Drawdown")
    ax[1].grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


def plot_fractals_on_price(df: pd.DataFrame, p: FractalParams, save_path: Optional[str] = None):
    fr = detect_fractals(df, p.left_bars, p.right_bars)
    fig = plt.figure(figsize=(12,6))
    plt.plot(df.index, df['Close'], color='black', lw=1.2, label='Close')
    plt.scatter(fr.index[fr['bearish_fractal']], df['High'][fr['bearish_fractal']],
                marker='^', color='red', s=50, label='Bearish fractal (top)')
    plt.scatter(fr.index[fr['bullish_fractal']], df['Low'][fr['bullish_fractal']],
                marker='v', color='green', s=50, label='Bullish fractal (bottom)')
    plt.legend()
    plt.title("Confirmed Fractals (shifted, non-repainting)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()

# -----------------------
# Optimizer (Optional)
# -----------------------

def grid_search(df: pd.DataFrame,
                param_grid: Dict[str, List],
                base: FractalParams,
                score_key: str = 'Sharpe (daily≈252)') -> Tuple[FractalParams, Performance, pd.DataFrame]:
    """
    Simple brute-force grid search.
    Returns best params, best performance, and a DataFrame of all runs.
    """
    from itertools import product
    keys = list(param_grid.keys())
    combos = list(product(*[param_grid[k] for k in keys]))
    rows = []
    best_perf = None
    best_params = None
    best_score = -np.inf

    for combo in combos:
        params_dict = asdict(base).copy()
        for k, v in zip(keys, combo):
            params_dict[k] = v
        p = FractalParams(**params_dict)
        try:
            perf = backtest(df, p)
            score = perf.stats.get(score_key, -np.inf)
            row = {**params_dict, **perf.stats}
            rows.append(row)
            if score is not None and score > best_score:
                best_score = score
                best_perf = perf
                best_params = p
        except Exception as e:
            rows.append({**params_dict, 'error': str(e)})

    results = pd.DataFrame(rows)
    return best_params, best_perf, results
