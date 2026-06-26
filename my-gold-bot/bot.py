import time, datetime, csv, os, telebot, yfinance as yf, pandas as pd, pandas_ta as ta, threading
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv

# إعدادات 
BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'
CHAT_ID = '679809289'
LOG_FILE = "trades_log.csv"
bot = telebot.TeleBot(BOT_TOKEN)

# تحميل النموذج الذكي
model = PPO.load("gold_master_model")
active_trades = []

def log_trade(trade_type, result, profit):
    with open(LOG_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([datetime.datetime.now(), trade_type, result, profit])

def get_live_data():
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    if df.empty: return None
    
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if 'Close' not in df.columns: df.rename(columns={df.columns[0]: 'Close'}, inplace=True)
    
    # إضافة المؤشرات الفنية
    df.ta.rsi(length=14, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.macd(append=True)
    
    return df.dropna().astype(float)

def trade():
    df = get_live_data()
    if df is None or len(df) < 25: return
    
    current_price = float(df['Close'].iloc[-1])
    
    # إدارة الصفقات المفتوحة
    for t in active_trades[:]:
        if (t['type'] == 'buy' and current_price >= t['tp']) or (t['type'] == 'sell' and current_price <= t['tp']):
            log_trade(t['type'], 'win', abs(t['tp'] - t['entry']))
            bot.send_message(CHAT_ID, "✅ Trade Closed: Profit/Win")
            active_trades.remove(t)
        elif (t['type'] == 'buy' and current_price <= t['sl']) or (t['type'] == 'sell' and current_price >= t['sl']):
            log_trade(t['type'], 'loss', -abs(t['sl'] - t['entry']))
            bot.send_message(CHAT_ID, "❌ Trade Closed: Loss/Stop Hit")
            active_trades.remove(t)

    # اتخاذ القرار
    try:
        env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
        obs, _ = env.reset()
        action, _ = model.predict(obs)
        
        if action in [0, 1] and len(active_trades) < 2:
            sl, tp = (current_price*0.995, current_price*1.015) if action == 1 else (current_price*1.005, current_price*0.985)
            trade_type = "BUY" if action == 1 else "SELL"
            icon = "🟢" if action == 1 else "🔴"
            
            # الرسالة بتنسيق إنجليزي احترافي
            message = (
                f"{icon} {trade_type} Signal | Gold (GC=F)\n"
                f"Entry: {current_price:.2f}\n"
                f"Stop Loss: {sl:.2f}\n"
                f"Take Profit: {tp:.2f}"
            )
            
            bot.send_message(CHAT_ID, message)
            active_trades.append({'type': 'buy' if action == 1 else 'sell', 'tp': tp, 'sl': sl, 'entry': current_price})
    except Exception as e: 
        print(f"Decision Error: {e}")

# --- تشغيل البوت ---
def run_bot():
    while True:
        trade()
        time.sleep(300) 

threading.Thread(target=run_bot, daemon=True).start()
bot.infinity_polling()
