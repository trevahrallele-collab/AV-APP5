#!/usr/bin/env python3
"""
Strategy Installation Script
Installs trading strategies for backtesting
"""
import os
import shutil
import json

def install_strategy(strategy_name):
    """Install a strategy by copying files to main directory"""
    strategy_files = {
        'ob_refined_strategy': ['ob_refined_strategy.py'],
        'fractal_refined_strategy': ['fractal_refined_strategy.py'],
        'fractal_ob_strategy': ['fractal_ob_strategy.py'],
        'fractal_package': [
            'fractal_strategy_package/fractal_strategy.py',
            'fractal_strategy_package/optimize_daily.py', 
            'fractal_strategy_package/run_backtest.py'
        ],
        'fractal_ob_package': [
            'fractal_strategy_package_ob/order_blocks.py',
            'fractal_strategy_package_ob/run_ob_backtest.py'
        ]
    }
    
    if strategy_name not in strategy_files:
        print(f"❌ Unknown strategy: {strategy_name}")
        return False
    
    print(f"📦 Installing {strategy_name}...")
    
    for file_path in strategy_files[strategy_name]:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            shutil.copy2(file_path, filename)
            print(f"  ✅ Installed {filename}")
        else:
            print(f"  ❌ Missing {file_path}")
            return False
    
    print(f"🎉 {strategy_name} installed successfully!")
    return True

def list_available_strategies():
    """List all available strategies"""
    strategies = {
        'ob_refined_strategy': 'Order Block Strategy - SMC-based order block detection',
        'fractal_refined_strategy': 'Fractal Strategy - Bill Williams fractal breakouts',
        'fractal_ob_strategy': 'Fractal + OB Strategy - Combined fractal and order block signals',
        'fractal_package': 'Full Fractal Package - Complete fractal trading system',
        'fractal_ob_package': 'Fractal OB Package - Advanced order block tools'
    }
    
    print("📋 Available Strategies:")
    for name, desc in strategies.items():
        print(f"  • {name}: {desc}")

def install_all_strategies():
    """Install all available strategies"""
    strategies = ['ob_refined_strategy', 'fractal_refined_strategy', 'fractal_ob_strategy']
    
    print("🚀 Installing all core strategies...")
    success_count = 0
    
    for strategy in strategies:
        if install_strategy(strategy):
            success_count += 1
    
    print(f"\n✅ Installed {success_count}/{len(strategies)} strategies successfully!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python install_strategies.py [strategy_name|list|all]")
        print("\nExamples:")
        print("  python install_strategies.py list")
        print("  python install_strategies.py all") 
        print("  python install_strategies.py fractal_refined_strategy")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_available_strategies()
    elif command == "all":
        install_all_strategies()
    else:
        install_strategy(command)