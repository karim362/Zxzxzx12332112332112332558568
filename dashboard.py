from flask import Flask, render_template, jsonify, request
import asyncio
import threading
import json
import os
import logging # استيراد مكتبة التسجيل
# لا نستورد main_loop مباشرة إذا كنا لا نريد تشغيلها من هنا
# ولكن في هذا السيناريو سنبقيها للاستدعاء عند الضغط على الزر
from referral_bot import main_loop, load_stats # استيراد load_stats أيضاً

# إعداد التسجيل (Logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# علامة لتتبع حالة تشغيل البوت
bot_running = False
bot_thread = None

# استخدم load_stats من referral_bot.py لتجنب تكرار الكود
# def load_stats():
#     stats_path = 'stats.json'
#     if os.path.exists(stats_path):
#         try:
#             with open(stats_path, "r") as f:
#                 return json.load(f)
#         except:
#             pass
#     return {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}

@app.route('/')
def index():
    """صفحة لوحة التحكم الرئيسية."""
    stats = load_stats() # استخدم الدالة المستوردة
    # تمرير حالة البوت أيضاً لواجهة المستخدم (اختياري)
    return render_template('dashboard.html', stats=stats, bot_status="قيد التشغيل" if bot_running else "متوقف")

# دالة مساعدة لتشغيل حلقة asyncio في مؤشر ترابط منفصل
def run_bot_loop(loop):
    """تشغيل حلقة asyncio في مؤشر ترابط مخصص."""
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_loop())
    except Exception as e:
        logging.error(f"خطأ في حلقة البوت: {e}")
    finally:
        # يتم الوصول إلى هنا إذا انتهت الحلقة (نظرياً لا يحدث في حلقة while True)
        # أو إذا حدث خطأ فادح أوقف الحلقة
        global bot_running
        bot_running = False
        logging.info("تم إنهاء حلقة البوت.")


@app.route('/start-bot', methods=['POST'])
def start_bot():
    """نقطة نهاية لبدء تشغيل البوت."""
    global bot_running, bot_thread
    if bot_running:
        logging.warning("محاولة بدء البوت وهو قيد التشغيل بالفعل.")
        return jsonify({"status": "البوت قيد التشغيل بالفعل."}), 409 # 409 Conflict

    try:
        logging.info("تلقي طلب بدء تشغيل البوت.")
        bot_running = True
        # إنشاء حلقة أحداث جديدة للمؤشر المنفصل وتشغيل main_loop فيها
        loop = asyncio.new_event_loop()
        bot_thread = threading.Thread(target=run_bot_loop, args=(loop,))
        bot_thread.start()
        logging.info("تم بدء مؤشر ترابط البوت بنجاح.")
        return jsonify({"status": "بدأ البوت بنجاح."})

    except Exception as e:
        bot_running = False # إعادة تعيين العلامة في حالة الفشل
        logging.error(f"فشل بدء تشغيل البوت: {e}")
        return jsonify({"status": f"فشل التشغيل: {str(e)}"}), 500 # 500 Internal Server Error

# نقطة نهاية اختيارية للتحقق من حالة البوت
@app.route('/status')
def get_status():
    """نقطة نهاية لجلب حالة البوت."""
    return jsonify({"running": bot_running, "thread_alive": bot_thread is not None and bot_thread.is_alive()})


if __name__ == "__main__":
    # Render يحدد المنفذ عبر متغير البيئة PORT
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"بدء تشغيل لوحة التحكم على المنفذ: {port}")
    # في بيئة الإنتاج مثل Render، استخدم waitress أو gunicorn
    # على سبيل المثال: gunicorn --bind 0.0.0.0:$PORT dashboard:app
    # لكن لغرض الاختبار أو في حالات بسيطة، يمكنك استخدام خادم Flask المدمج
    app.run(host='0.0.0.0', port=port)

