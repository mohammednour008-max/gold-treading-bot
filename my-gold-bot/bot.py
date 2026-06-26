import time
import yfinance as yf
import telebot
import traceback
import pandas as pd
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv

# إعدادات التليجرام الخاص.. 
BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'
CHAT_ID = '679809289'
bot = telebot.TeleBot(BOT_TOKEN)

# تحميل النموذج
try:
    model = PPO.load("gold_master_model")
except Exception as e:
    print(f"خطأ في تحميل النموذج: {e}")

def get_live_data():
    # جلب البيانات
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    
    # --- التنظيف الصارم للبيانات (حل مشكلة الـ Concatenation) ---
    if df.empty:
        return None
    
    # حذف الصفوف الفارغة
    df = df.dropna()
    
    # التأكد من أن العمود هو 'Close' فقط وتنسيق البيانات
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs('Close', axis=1, level=0)
    elif 'Close' in df.columns:
        df = df[['Close']]
        
    df = df.sort_index()
    df = df.astype(float)
    
    return df

def trade():
    df = get_live_data()
    
    # تحقق أمني: التأكد من وجود بيانات كافية (window_size=20 + هامش)
    if df is None or len(df) < 25:
        print("تحذير: بيانات السوق غير كافية، سيتم الانتظار...")
        return

    try:
        # إنشاء البيئة
        env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
        obs, _ = env.reset()
        
        # اتخاذ القرار
        action, _ = model.predict(obs)
        
        # إرسال التنبيه
        msg = "🟢 إشارة: شراء الذهب (Gold Buy Signal)" if action == 1 else "🔴 إشارة: بيع الذهب (Gold Sell Signal)"
            
        bot.send_message(CHAT_ID, msg)
        print(f"تم تنفيذ العملية بنجاح: {msg}")
            
    except Exception as e:
        print(f"خطأ أثناء معالجة النموذج: {e}")
        traceback.print_exc()

# --- بدء التشغيل ---
print("البوت يعمل الآن ويراقب السوق...")
try:
    bot.send_message(CHAT_ID, "✅ تم تشغيل البوت بنجاح! البوت الآن يراقب سوق الذهب.")
except Exception as e:
    print(f"خطأ في إرسال رسالة التأكيد: {e}")

while True:
    try:
        trade()
    except Exception as e:
        print(f"خطأ عام: {e}")
    
    time.sleep(300) # انتظار 5 دقائق
