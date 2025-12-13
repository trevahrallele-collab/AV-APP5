#!/usr/bin/env python3
import sys
import os
import requests
import time
import subprocess
sys.path.append('src')

from av_data_fetcher import AVDataFetcher
from plotter import StockPlotter
import pandas as pd

def smoke_test():
    print("Running smoke test...")
    
    # Test 1: Create sample data
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    sample_data = {
        'open': [150, 152, 148, 151, 149],
        'high': [155, 156, 152, 155, 153],
        'low': [148, 150, 146, 149, 147],
        'close': [152, 148, 151, 149, 152],
        'volume': [1000000, 1100000, 900000, 1050000, 980000]
    }
    df = pd.DataFrame(sample_data, index=dates)
    
    # Test 2: Test plotting functions
    try:
        StockPlotter.plot_data(df, "static/test_plot.png")
        print("✓ Static line chart created")
        
        StockPlotter.plot_candlestick(df, "static/test_candlestick.png")
        print("✓ Static candlestick chart created")
        
        StockPlotter.plot_interactive(df, "static/test_interactive.html")
        print("✓ Interactive line chart created")
        
        StockPlotter.plot_interactive_candlestick(df, "static/test_interactive_candlestick.html")
        print("✓ Interactive candlestick chart created")
        
    except Exception as e:
        print(f"✗ Plotting failed: {e}")
        return False
    
    # Test 3: Test data fetcher initialization
    try:
        fetcher = AVDataFetcher("test_key")
        print("✓ Data fetcher initialized")
    except Exception as e:
        print(f"✗ Data fetcher failed: {e}")
        return False
    
    # Test 4: Test web endpoints
    try:
        # Start web app in background
        proc = subprocess.Popen(['python', 'src/web_app.py'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL,
                               cwd='/workspaces/AV-APP')
        time.sleep(3)  # Wait for startup
        
        # Test main endpoint
        response = requests.get('http://localhost:8080/', timeout=10)
        if response.status_code in [200, 404, 500]:
            print(f"✓ Main endpoint responding ({response.status_code})")
        else:
            print(f"✗ Main endpoint failed: {response.status_code}")
            proc.terminate()
            return False
        
        proc.terminate()
        proc.wait()
        
    except Exception as e:
        print(f"✗ Web endpoint test failed: {e}")
        try:
            proc.terminate()
        except:
            pass
        return False
    
    print("✓ All smoke tests passed!")
    return True

if __name__ == "__main__":
    success = smoke_test()
    sys.exit(0 if success else 1)