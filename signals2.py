import requests
import pandas as pd
import numpy as np
from datetime import datetime
import csv
import os
import time


def get_xrp_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price',
                                params={
                                    'ids': 'ripple',
                                    'vs_currencies': 'usd',
                                    'precision': 4
                                },
                                headers={
                                    'Accept': 'application/json',
                                    'User-Agent': 'Mozilla/5.0'
                                })

        data = response.json()
        if 'ripple' in data and 'usd' in data['ripple']:
            return float(data['ripple']['usd'])
        else:
            raise ValueError(f"Unexpected API response format: {data}")

    except Exception as e:
        print(f"Error fetching price: {e}")
        return None


def calculate_available_indicators(prices):
    """Calculate whatever indicators are possible with available data"""
    df = pd.DataFrame(prices, columns=['price'])
    indicators = {
        'SMA20': None,
        'SMA50': None,
        'RSI': None,
        'momentum': None
    }

    # Calculate moving averages if enough data
    if len(prices) >= 20:
        indicators['SMA20'] = df['price'].rolling(window=20).mean().iloc[-1]
    if len(prices) >= 50:
        indicators['SMA50'] = df['price'].rolling(window=50).mean().iloc[-1]

    # Calculate RSI if enough data (needs 14 periods)
    if len(prices) >= 14:
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        indicators['RSI'] = (100 - (100 / (1 + rs))).iloc[-1]

    # Calculate momentum if enough data (needs 10 periods)
    if len(prices) >= 10:
        indicators['momentum'] = (df['price'].pct_change(periods=10) * 100).iloc[-1]

    return indicators


def generate_basic_signal(current_price, prev_price, indicators):
    """Generate basic trading signals with available data"""
    signal = "HOLD"
    reasons = []

    # Basic price movement signal
    if prev_price is not None:
        price_change_pct = ((current_price - prev_price) / prev_price) * 100
        if price_change_pct >= 2:  # 2% or more increase
            signal = "BUY"
            reasons.append(f"Price up {price_change_pct:.2f}%")
        elif price_change_pct <= -2:  # 2% or more decrease
            signal = "SELL"
            reasons.append(f"Price down {price_change_pct:.2f}%")

    # Add RSI signals if available
    if indicators['RSI'] is not None:
        if indicators['RSI'] > 70:
            signal = "SELL"
            reasons.append(f"RSI overbought: {indicators['RSI']:.2f}")
        elif indicators['RSI'] < 30:
            signal = "BUY"
            reasons.append(f"RSI oversold: {indicators['RSI']:.2f}")

    # Add momentum signals if available
    if indicators['momentum'] is not None:
        if indicators['momentum'] > 5:
            signal = "BUY"
            reasons.append(f"Strong positive momentum: {indicators['momentum']:.2f}%")
        elif indicators['momentum'] < -5:
            signal = "SELL"
            reasons.append(f"Strong negative momentum: {indicators['momentum']:.2f}%")

    # Add MA crossover signals if both MAs are available
    if indicators['SMA20'] is not None and indicators['SMA50'] is not None:
        if indicators['SMA20'] > indicators['SMA50']:
            signal = "BUY"
            reasons.append("SMA20 above SMA50")
        elif indicators['SMA20'] < indicators['SMA50']:
            signal = "SELL"
            reasons.append("SMA20 below SMA50")

    return signal, " & ".join(reasons) if reasons else "Initial price logging"


def log_trading_signal(signal_data):
    """Log trading signals to CSV file"""
    filename = 'trading_signals.csv'
    file_exists = os.path.isfile(filename)

    with open(filename, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'price', 'signal', 'reason',
            'rsi', 'sma20', 'sma50', 'momentum'
        ])

        if not file_exists:
            writer.writeheader()

        writer.writerow(signal_data)


def monitor_xrp_trading(interval=300):  # 5 minutes interval
    """Main function to monitor XRP price and generate trading signals"""
    prices = []
    prev_price = None
    print("Starting XRP trading monitor...")

    while True:
        try:
            current_price = get_xrp_price()

            if current_price:
                prices.append(current_price)

                # Keep only last 100 prices for analysis
                if len(prices) > 100:
                    prices.pop(0)

                # Calculate available indicators
                indicators = calculate_available_indicators(prices)

                # Generate trading signal
                signal, reason = generate_basic_signal(current_price, prev_price, indicators)

                # Prepare signal data for logging
                signal_data = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'price': current_price,
                    'signal': signal,
                    'reason': reason,
                    'rsi': indicators['RSI'],
                    'sma20': indicators['SMA20'],
                    'sma50': indicators['SMA50'],
                    'momentum': indicators['momentum']
                }

                # Log the signal
                log_trading_signal(signal_data)

                # Print current status
                print(f"\nTime: {signal_data['timestamp']}")
                print(f"Price: ${current_price:.4f}")
                print(f"Signal: {signal}")
                print(f"Reason: {reason}")

                # Print available indicators
                if indicators['RSI'] is not None:
                    print(f"RSI: {indicators['RSI']:.2f}")
                if indicators['momentum'] is not None:
                    print(f"Momentum: {indicators['momentum']:.2f}%")
                if indicators['SMA20'] is not None:
                    print(f"SMA20: ${indicators['SMA20']:.4f}")
                if indicators['SMA50'] is not None:
                    print(f"SMA50: ${indicators['SMA50']:.4f}")

                # Update previous price
                prev_price = current_price

                # Show data collection progress if not all indicators are available
                if None in indicators.values():
                    available = sum(1 for x in indicators.values() if x is not None)
                    total = len(indicators)
                    print(f"\nCollecting data... ({available}/{total} indicators available)")

            time.sleep(interval)

        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    print("Starting XRP Trading Signal Monitor...")
    try:
        monitor_xrp_trading()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")