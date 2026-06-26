import time, datetime, csv, os, telebot, yfinance as yf, pandas as pd, pandas_ta as ta, threading
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv

# إعدادات 
BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'
CHAT_ID = '679809289'
LOG_FILE = "trades_log.csv"
bot = telebot.TeleBot(BOT_TOKEN)

# تحميل النموذج
model = PPO.load("gold_master_model")
active_trades = []

# --- وظائف مساعدة ---
def log_trade(trade_type, result, profit):
    with open(LOG_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([datetime.datetime.now(), trade_type, result, profit])

def get_report():
    if not os.path.exists(LOG_FILE): return "No trades recorded yet."
    df = pd.read_csv(LOG_FILE, names=['date', 'type', 'result', 'profit'], parse_dates=['date'])
    wins = len(df[df['result'] == 'win'])
    losses = len(df[df['result'] == 'loss'])
    total_profit = df['profit'].sum()
    return f"📊 Performance Report:\n✅ Wins: {wins} | ❌ Losses: {losses}\n💰 Total Profit: {total_profit:.2f}"

# --- الأوامر ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bot is active and running!")

@bot.message_handler(commands=['report'])
def send_report(message):
    bot.reply_to(message, get_report())

# --- دالة التداول ---
def get_live_data():
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if 'Close' not in df.columns: df.rename(columns={df.columns[0]: 'Close'}, inplace=True)
    df.ta.atr(length=14, append=True)
    return df.dropna().astype(float)

def trade():
    df = get_live_data()
    if df is None or len(df) < 25: return
    
    current_price = float(df['Close'].iloc[-1])
    atr = float(df['ATRr_14'].iloc[-1])
    
    for t in active_trades[:]:
        if (t['type'] == 'buy' and current_price >= t['tp']) or (t['type'] == 'sell' and current_price <= t['tp']):
            log_trade(t['type'], 'win', abs(t['tp'] - t['entry']))
            bot.send_message(CHAT_ID, "✅ Trade Closed: Profit/Win")
            active_trades.remove(t)
        elif (t['type'] == 'buy' and current_price <= t['sl']) or (t['type'] == 'sell' and current_price >= t['sl']):
            log_trade(t['type'], 'loss', -abs(t['sl'] - t['entry']))
            bot.send_message(CHAT_ID, "❌ Trade Closed: Loss/Stop Hit")
            active_trades.remove(t)

    try:
        env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
        obs, _ = env.reset()
        action, _ = model.predict(obs)
        
        if action in [0, 1] and len(active_trades) < 2:
            if action == 1: # BUY
                sl, tp = current_price - (atr * 1.0), current_price + (atr * 2.0)
            else: # SELL
                sl, tp = current_price + (atr * 1.0), current_price - (atr * 2.0)
            
            trade_type = "BUY" if action == 1 else "SELL"
            icon = "🟢" if action == 1 else "🔴"
            
            message = (
                f"{icon} {trade_type} Signal | Gold (GC=F)\n"
                f"Entry: {current_price:.2f}\n"
                f"Stop Loss: {sl:.2f}\n"
                f"Take Profit: {tp:.2f}"
            )
            bot.send_message(CHAT_ID, message)
            active_trades.append({'type': 'buy' if action == 1 else 'sell', 'tp': tp, 'sl': sl, 'entry': current_price})
    except Exception as e: print(f"Decision Error: {e}")

# --- التشغيل ---
def run_bot():
    while True:
        trade()
        time.sleep(300)

threading.Thread(target=run_bot, daemon=True).start()
bot.infinity_polling()
