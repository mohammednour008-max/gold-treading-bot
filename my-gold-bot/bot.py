import time
import yfinance as yf
import telebot
import traceback
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv

# إعدادات التليجرام هنا
BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'
CHAT_ID = '679809289'
bot = telebot.TeleBot(BOT_TOKEN)

# تحميل النموذج (تأكد أن الملف gold_master_model.zip موجود في نفس المسار)
try:
    model = PPO.load("gold_master_model")
except Exception as e:
    print(f"خطأ في تحميل النموذج: {e}")

def get_live_data():
    # جلب بيانات 5 أيام لضمان وجود نقاط كافية للنافذة (window_size=20)
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    if df.empty:
        return None
    # تنظيف البيانات من القيم الفارغة
    df = df.dropna()
    df = df[['Close']].copy()
    return df

def trade():
    df = get_live_data()
    
    # تحقق أمني: التأكد من وجود بيانات كافية للنموذج (أكثر من 25 صفاً)
    if df is None or len(df) < 25:
        print("تحذير: بيانات السوق غير كافية حالياً، انتظار الدورة القادمة...")
        return

    try:
        # إنشاء البيئة
        env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
        obs, _ = env.reset()
        
        # اتخاذ القرار
        action, _ = model.predict(obs)
        
        # إرسال التنبيه
        if action == 1:
            msg = "🟢 إشارة: شراء الذهب (Gold Buy Signal)"
        else:
            msg = "🔴 إشارة: بيع الذهب (Gold Sell Signal)"
            
        bot.send_message(CHAT_ID, msg)
        print(f"تم تنفيذ العملية بنجاح: {msg}")
            
    except Exception as e:
        print(f"خطأ أثناء معالجة النموذج: {e}")
        # طباعة تفاصيل الخطأ للـ Logs
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
        print(f"خطأ عام في حلقة العمل: {e}")
    
    # انتظار 5 دقائق (300 ثانية)
    time.sleep(300)
