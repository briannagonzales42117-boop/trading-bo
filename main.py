import os
import time
import requests
import yfinance as yf
import pandas as pd
import logging
import signal
import sys
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ===== TELEGRAM (RAILWAY ENV VARIABLES) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logging.error("Missing BOT_TOKEN or CHAT_ID environment variables. Set them in Railway variables.")
    sys.exit(1)

# ===== SETTINGS =====
INTERVAL = "15m"
PERIOD = "5d"

def interval_to_seconds(interval_str):
    # basic mapping for common intervals
    if interval_str.endswith("m"):
        return int(interval_str[:-1]) * 60
    if interval_str.endswith("h"):
        return int(interval_str[:-1]) * 3600
    if interval_str.endswith("d"):
        return int(interval_str[:-1]) * 86400
    return 900

SLEEP_TIME = interval_to_seconds(INTERVAL)

# ===== TELEGRAM SEND =====
def send_telegram(msg, max_retries=3):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(url, data=payload, timeout=10)
            if r.status_code == 200:
                logging.info("Telegram message sent.")
                return True
            else:
                logging.warning("Telegram response %s: %s", r.status_code, r.text)
        except Exception as e:
            logging.warning("Telegram send attempt %d failed: %s", attempt, e)
        time.sleep(attempt * 1.5)
    logging.error("Failed to send Telegram message after %d attempts.", max_retries)
    return False

# ===== DATA FETCH =====
def fetch_data(symbol):
    try:
        df = yf.download(symbol, period=PERIOD, interval=INTERVAL, progress=False)
        if df.empty:
            logging.warning("No data returned for %s", symbol)
            return None
        df = df.reset_index()
        return df
    except Exception as e:
        logging.error("Error fetching data for %s: %s", symbol, e)
        return None

# ===== SIGNAL LOGIC =====
def generate_signal(df, name):
    # ensure enough rows for indicators (EMA200 needs >=200)
    if df.shape[0] < 50:
        return None

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

    # Use last closed candle (previous row), not the in-progress candle
    last = df.iloc[-2]
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

    return {
        "text": f"📊 {name} SIGNAL\n🕒 {pd.Timestamp.utcnow()} UTC\n\n📈 Direction: {direction}\n🎯 Entry: {price:.2f}\n🛑 Stop Loss: {sl:.2f}\n🏁 Take Profit: {tp:.2f}\n⏱ Timeframe: {INTERVAL}",
        "direction": direction
    }

# ===== MAIN LOOP =====
running = True

def handle_exit(sig, frame):
    global running
    logging.info("Received exit signal, shutting down...")
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def run_bot():
    last_sent = {}  # keep last direction sent per symbol name
    symbols = [("GC=F", "GOLD (GC=F)"), ("BTC-USD", "BITCOIN (BTC)")]
    while running:
        try:
            for sym, name in symbols:
                df = fetch_data(sym)
                if df is None:
                    continue
                result = generate_signal(df, name)
                if result:
                    direction = result["direction"]
                    prev = last_sent.get(name)
                    if prev != direction:
                        sent = send_telegram(result["text"])
                        if sent:
                            last_sent[name] = direction
                    else:
                        logging.info("Signal for %s is same as last sent, skipping.", name)
                else:
                    # reset last_sent if no signal (optional behavior)
                    last_sent.pop(name, None)
        except Exception as e:
            logging.exception("Error in main loop: %s", e)

        sleep_left = SLEEP_TIME
        while running and sleep_left > 0:
            time.sleep(min(5, sleep_left))
            sleep_left -= 5

if __name__ == "__main__":
    run_bot()
