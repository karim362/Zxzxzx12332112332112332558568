from flask import Flask, render_template, jsonify
import json
import os
import logging # استيراد مكتبة التسجيل
# نستورد فقط الدوال التي نحتاجها للوحة التحكم
from referral_bot import load_stats # استيراد load_stats من ملف البوت

# إعداد التسجيل (Logging) للوحة التحكم
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# لم نعد نحتاج bot_running أو logic لبدء thread هنا

@app.route('/')
def index():
    """صفحة لوحة التحكم الرئيسية."""
    stats = load_stats() # استخدام الدالة المستوردة لتحميل الإحصائيات
    # لا نرسل bot_status من هنا بعد الآن، لأن لوحة التحكم لا تشغل البوت
    # يمكن تعديل الـ HTML لإزالة حالة "قيد التشغيل/متوقف" المرتبطة بزر التشغيل
    return render_template('dashboard.html', stats=stats)

# تم حذف نقطة النهاية '/start-bot' بالكامل

# نقطة نهاية اختيارية لجلب الإحصائيات كتنسيق JSON (مفيد للتحديثات المستقبلية)
@app.route('/stats')
def get_stats():
    """نقطة نهاية لجلب الإحصائيات بصيغة JSON."""
    stats = load_stats()
    return jsonify(stats)


if __name__ == "__main__":
    # Render يحدد المنفذ عبر متغير البيئة PORT
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Starting dashboard on port: {port}")
    # استخدم waitress أو gunicorn في بيئة الإنتاج
    # app.run(host='0.0.0.0', port=port) # استخدام الخادم المدمج (للتجربة المحلية أو البسيطة جدا)
    # مثال لـ Gunicorn (تحتاج لإضافة gunicorn في requirements.txt وتغيير startCommand في render.yaml)
    # from gunicorn.app.base import BaseApplication
    # class FlaskApp(BaseApplication):
    #     def __init__(self, app, options=None):
    #         self.options = options or {}
    #         self.application = app
    #         super().__init__()
    #     def load_config(self):
    #         config = {key: value for key, value in self.options.items()
    #                   if key in self.cfg.settings and value is not None}
    #         for key, value in config.items():
    #             self.cfg.set(key.lower(), value)
    #     def load_wsgi(self):
    #         return self.application
    # if __name__ == '__main__':
    #     options = {
    #         'bind': f'0.0.0.0:{port}',
    #         'workers': 1, # عدد العمال
    #     }
    #     FlaskApp(app, options).run()

    # للاحتفاظ بالبساطة كما في الكود الأصلي:
    app.run(host='0.0.0.0', port=port)

