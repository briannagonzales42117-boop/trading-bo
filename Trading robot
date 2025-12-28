import time
import requests
import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator

# ===== TELEGRAM (SET IN RAILWAY ENV VARIABLES) =====
BOT_TOKEN = None
CHAT_ID = None

# ===== SETTINGS =====
INTERVAL = "15m"
PERIOD = "5d"
SLEEP_TIME = 3600  # 1 hour

# ===== TELEGRAM SEND =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=payload)

# ===== DATA FETCH =====
def fetch_data(symbol):
    df = yf.download(symbol, period=PERIOD, interval=INTERVAL, progress=False)
    if df.empty:
        return None
    df = df.reset_index()
    return df

# ===== SIGNAL LOGIC =====
def generate_signal(df, name):
    close = df["Close"]

    rsi = RSIIndicator(close).rsi()
    macd = MACD(close)
    ema200 = EMAIndicator(close, 200).ema_indicator()
    adx = ADXIndicator(df["High"], df["Low"], close).adx()

    df["RSI"] = rsi
    df["MACD"] = macd.macd()
    df["MACD_SIGNAL"] = macd.macd_signal()
    df["EMA200"] = ema200
    df["ADX"] = adx
    df.dropna(inplace=True)

    if len(df) < 5:
        return None

    last = df.iloc[-1]
    price = float(last["Close"])

    if last["ADX"] > 20 and price > last["EMA200"] and last["RSI"] < 35 and last["MACD"] > last["MACD_SIGNAL"]:
        sl = price - price * 0.003
        tp = price + price * 0.006
        direction = "BUY 🟢"
    elif last["ADX"] > 20 and price < last["EMA200"] and last["RSI"] > 65 and last["MACD"] < last["MACD_SIGNAL"]:
        sl = price + price * 0.003
        tp = price - price * 0.006
        direction = "SELL 🔴"
    else:
        return None

    return f"""
📊 {name} SIGNAL
🕒 {pd.Timestamp.utcnow()} UTC

📈 Direction: {direction}
🎯 Entry: {price:.2f}
🛑 Stop Loss: {sl:.2f}
🏁 Take Profit: {tp:.2f}
⏱ Timeframe: 15m
"""

# ===== MAIN LOOP =====
def run_bot():
    while True:
        try:
            gold = fetch_data("GC=F")
            btc = fetch_data("BTC-USD")

            if gold is not None:
                sig = generate_signal(gold, "GOLD (GC=F)")
                if sig:
                    send_telegram(sig)

            if btc is not None:
                sig = generate_signal(btc, "BITCOIN (BTC)")
                if sig:
                    send_telegram(sig)

        except Exception as e:
            print("Error:", e)

        time.sleep(SLEEP_TIME)

# ===== START =====
if __name__ == "__main__":
    run_bot()
