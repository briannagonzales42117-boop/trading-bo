import yfinance as yf
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import os

# =========================
# TELEGRAM CONFIG (ENV)
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def generate_signal(symbol, name):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)

    if df.empty or len(df) < 150:
        print(f"{name}: Not enough data")
        return

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()

    rsi = RSIIndicator(close, 14).rsi()
    macd = MACD(close)
    macd_line = macd.macd()
    macd_signal = macd.macd_signal()
    ema200 = EMAIndicator(close, 200).ema_indicator()
    atr = AverageTrueRange(high, low, close).average_true_range()
    adx = ADXIndicator(high, low, close, 14).adx()

    df = pd.DataFrame({
        "close": close,
        "rsi": rsi,
        "macd": macd_line,
        "macd_signal": macd_signal,
        "ema200": ema200,
        "atr": atr,
        "adx": adx
    }).dropna()

    last = df.iloc[-1]
    price = float(last["close"])

    strong_trend = last["adx"] > 22
    enough_volatility = last["atr"] > df["atr"].mean()

    buy = price > last["ema200"] and last["rsi"] < 35 and last["macd"] > last["macd_signal"] and strong_trend and enough_volatility
    sell = price < last["ema200"] and last["rsi"] > 65 and last["macd"] < last["macd_signal"] and strong_trend and enough_volatility

    if not buy and not sell:
        print(f"{name}: No signal")
        return

    direction = "BUY 🟢" if buy else "SELL 🔴"
    sl = price - last["atr"] * 1.6 if buy else price + last["atr"] * 1.6
    tp = price + last["atr"] * 3.0 if buy else price - last["atr"] * 3.0

    message = f"""
📊 {name} HIGH-ACCURACY SIGNAL
🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC

📈 Direction: {direction}
🎯 Entry: {price:.2f}
🛑 Stop Loss: {sl:.2f}
🏁 Take Profit: {tp:.2f}
⏱ Timeframe: 15m
"""

    send_telegram(message)
    print(f"{name}: Signal sent")

while True:
    try:
        generate_signal("GC=F", "GOLD (GC=F)")
        generate_signal("BTC-USD", "BITCOIN (BTC)")
    except Exception as e:
        print("Error:", e)

    time.sleep(3600)
