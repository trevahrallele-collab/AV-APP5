# AV-APP

A clean financial data visualization application using Alpha Vantage API.

## Structure
```
/
├── src/                 # Source code
│   ├── av_data_fetcher.py  # Data fetching from Alpha Vantage
│   ├── web_app.py          # Flask web application
│   ├── dash_app.py         # Dash dashboard
│   └── plotter.py          # Plotting utilities
├── templates/           # HTML templates
├── static/             # Static files (CSS, JS, images)
├── cache/              # JSON data cache
├── database/           # SQLite databases
├── data-storage/       # CSV data storage
├── backups/            # Phase backups
├── requirements.txt    # Python dependencies
├── smoke_test.py      # Smoke tests
└── run_tests.sh       # Test runner
```

## Quick Start
1. Install dependencies: `pip install -r requirements.txt`
2. Run tests: `bash run_tests.sh`
3. Start web app: `python src/web_app.py`

## Testing
Run smoke tests after any changes:
```bash
bash run_tests.sh
```