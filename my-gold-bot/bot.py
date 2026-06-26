import time, datetime, csv, os, telebot, yfinance as yf, pandas as pd
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv

# إعدادات 
BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'
CHAT_ID = '679809289'
bot = telebot.TeleBot(BOT_TOKEN)

# تحميل النموذج
model = PPO.load("gold_master_model")
active_trades = []

def log_trade(trade_type, result, profit):
    with open(LOG_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([datetime.datetime.now(), trade_type, result, profit])

def get_report(period='day'):
    if not os.path.exists(LOG_FILE): return "لا توجد صفقات مسجلة."
    df = pd.read_csv(LOG_FILE, names=['date', 'type', 'result', 'profit'], parse_dates=['date'])
    now = datetime.datetime.now()
    if period == 'day': df = df[df['date'].dt.date == now.date()]
    elif period == 'week': df = df[df['date'] >= (now - datetime.timedelta(days=7))]
    elif period == 'month': df = df[df['date'] >= (now - datetime.timedelta(days=30))]
    
    wins = len(df[df['result'] == 'win'])
    losses = len(df[df['result'] == 'loss'])
    return f"📊 تقرير الأداء ({period}):\n✅ فوز: {wins} | ❌ خسارة: {losses}\n💰 الربح الإجمالي: {df['profit'].sum():.2f}"

def get_live_data():
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if 'Close' not in df.columns: df.rename(columns={df.columns[0]: 'Close'}, inplace=True)
    return df[['Close']].copy().dropna().sort_index().astype(float)

@bot.message_handler(commands=['report'])
def send_report(message):
    bot.reply_to(message, get_report('day') + "\n\n" + get_report('week') + "\n\n" + get_report('month'))

def trade():
    df = get_live_data()
    if df is None or len(df) < 25: return
    current_price = float(df['Close'].iloc[-1])
    
    # متابعة الصفقات المفتوحة
    for t in active_trades[:]:
        if (t['type'] == 'buy' and current_price >= t['tp']) or (t['type'] == 'sell' and current_price <= t['tp']):
            log_trade(t['type'], 'win', abs(t['tp'] - t['entry'])); bot.send_message(CHAT_ID, "✅ صفقة ناجحة!"); active_trades.remove(t)
        elif (t['type'] == 'buy' and current_price <= t['sl']) or (t['type'] == 'sell' and current_price >= t['sl']):
            log_trade(t['type'], 'loss', -abs(t['sl'] - t['entry'])); bot.send_message(CHAT_ID, "❌ صفقة خاسرة!"); active_trades.remove(t)

    # اتخاذ قرار وتدريب لحظي
    try:
        env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
        model.learn(total_timesteps=50) # تدريب لحظي
        action, _ = model.predict(env.reset()[0])
        
        if action in [0, 1] and len(active_trades) < 2:
            sl, tp = (current_price*0.995, current_price*1.015) if action == 1 else (current_price*1.005, current_price*0.985)
            active_trades.append({'type': 'buy' if action == 1 else 'sell', 'tp': tp, 'sl': sl, 'entry': current_price})
            bot.send_message(CHAT_ID, f"{'🟢' if action==1 else '🔴'} دخول {'شراء' if action==1 else 'بيع'} | فريم 5m\n🎯 الهدف: {tp:.2f}\n🛑 الوقف: {sl:.2f}")
    except Exception as e: print(e)

# --- التشغيل ---
import threading
def run_bot():
    while True:
        trade()
        time.sleep(300)

threading.Thread(target=run_bot).start()
bot.infinity_polling()
