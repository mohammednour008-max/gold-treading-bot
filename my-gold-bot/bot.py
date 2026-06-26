import time
import yfinance as yf
import telebot
from stable_baselines3 import PPO
from gym_anytrading.envs import StocksEnv

# إعدادات التليجرام الخاصه بك

BOT_TOKEN = '8713571843:AAEZXUlKQI2ahJojJIucz7yetf2_tqAPGiM'

CHAT_ID = '679809289'

bot = telebot.TeleBot(BOT_TOKEN)


# تحميل العقل المدرب
model = PPO.load("gold_master_model")

def get_live_data():
    # سحب بيانات آخر 5 أيام
    df = yf.download("GC=F", period="5d", interval="5m", auto_adjust=True)
    df = df.dropna()
    df = df[['Close']].copy()
    return df

def trade():
    df = get_live_data()
    
    # 1. تحقق من أن البيانات ليست فارغة أو غير كافية للنافذة (Window Size=20)
    if df.empty or len(df) < 30:
        print("تحذير: البيانات المستلمة غير كافية.")
        return

    try:
        # 2. إنشاء البيئة
        env = StocksEnv(df=df, window_size=20, frame_bound=(20, len(df)))
        obs, _ = env.reset()
        
        # 3. اتخاذ القرار
        action, _ = model.predict(obs)
        
        # 4. إرسال إشارة التداول
        if action == 1:
            msg = "🟢 إشارة: شراء الذهب (Gold Buy Signal)"
        else:
            msg = "🔴 إشارة: بيع الذهب (Gold Sell Signal)"
            
        bot.send_message(CHAT_ID, msg)
        print(f"تم إرسال الإشارة: {msg}")
            
    except Exception as e:
        print(f"خطأ في معالجة البيئة: {e}")

# رسالة تأكيد عند بدء البوت
print("البوت يعمل الآن ويراقب السوق...")
bot.send_message(CHAT_ID, "✅ البوت يعمل الآن وبدأ في مراقبة سوق الذهب بنجاح.")

while True:
    try:
        trade()
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
    
    # الانتظار لمدة 5 دقائق قبل المحاولة التالية
    time.sleep(300)
