import yfinance as yf
import telebot
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv
import pandas as pd
import time

# إعدادات التليجرام
BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'
CHAT_ID = '679809289'
bot = telebot.TeleBot(BOT_TOKEN)

# تحميل العقل المدرب
model = PPO.load("gold_master_model")

def get_live_data():
    # سحب بيانات آخر فترة
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    df = df[['Close']].copy()
    return df

def trade():
    df = get_live_data()
    # إنشاء بيئة مؤقتة لاتخاذ القرار
    env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
    obs, _ = env.reset()
    
    # اتخاذ القرار باستخدام العقل المدرب
    action, _ = model.predict(obs)
    
    # 0 = بيع (Sell), 1 = شراء (Buy)
    if action == 1:
        bot.send_message(CHAT_ID, "🟢 إشارة: شراء الذهب (Gold Buy Signal)")
    else:
        bot.send_message(CHAT_ID, "🔴 إشارة: بيع الذهب (Gold Sell Signal)")

print("البوت يعمل الآن ويراقب السوق...")
while True:
    try:
        trade()
    except Exception as e:
        print(f"حدث خطأ: {e}")
    time.sleep(300) # يكرر العملية كل 5 دقائق
