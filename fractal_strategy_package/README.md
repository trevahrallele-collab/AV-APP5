# Fractal Trading Strategy (Python)

**Disclaimer:** For educational use only — not financial advice. Trading involves risk.

This package provides a robust, non-repainting **Bill Williams fractal** strategy with:
- Fractal detection (configurable 5-bar default)
- Multi-timeframe confirmation (optional)
- EMA trend filter
- ATR-based initial and trailing stops (Chandelier)
- Position sizing by risk per trade
- Slippage & commission modeling
- Clean backtesting loop and performance metrics

## Quick Start

1. **Install requirements** (Python 3.10+ recommended):
```bash
pip install -r requirements.txt
```

2. **Run the demo** using the included synthetic dataset:
```bash
python run_backtest.py --data example_data.csv --date-col Date --output-dir outputs --use-htf --htf-rule W
```

3. **Run on your own CSV** (`Date,Open,High,Low,Close[,Volume]`):
```bash
python run_backtest.py --data YOUR_DATA.csv --date-col Date --output-dir outputs --ema 50 --lookback 20 --atr 14 --use-htf --htf-rule W
```

Outputs will be saved to the `outputs/` folder:
- `performance_summary.json` — key stats (CAGR, Sharpe, MaxDD, Win rate)
- `equity_curve.csv`, `drawdown.csv` — time series
- `trades.csv` — each trade’s details
- `equity_curve.png`, `fractals_price.png` — charts

## Files

- `fractal_strategy.py` — core library (indicators, fractals, backtest, plotting, optimizer)
- `run_backtest.py` — CLI runner that saves reports and charts
- `example_data.csv` — synthetic OHLC demo data
- `requirements.txt` — Python dependencies

## Notes
- Fractals are **confirmed** by shifting the pivot by `right_bars` bars to avoid look-ahead.
- For intraday data and weekly confirmation, ensure your index is a `DatetimeIndex`.
- Adjust `risk_per_trade`, `slippage_bps`, and `commission_bps` to reflect your market.

## Contact
Generated on 2025-12-12T22:51:08 UTC by M365 Copilot.


## Daily Data Optimization

Run a parameter sweep tuned for daily OHLC: 

```bash
python optimize_daily.py --data example_data.csv --date-col Date --output-dir outputs_daily --use-htf
```

Adjust ranges inside `optimize_daily.py` for faster or deeper search.

Sample outputs from the included demo are saved in `outputs_daily_example/`.
