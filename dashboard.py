from flask import Flask, render_template, jsonify, request
import asyncio
import threading
import json
import os
from referral_bot import main_loop  # تأكد أن هذا الملف موجود في نفس المجلد

app = Flask(__name__)

# تحميل الإحصائيات من الملف
def load_stats():
    if os.path.exists("stats.json"):
        try:
            with open("stats.json", "r") as f:
                return json.load(f)
        except:
            pass
    return {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}

@app.route('/')
def index():
    stats = load_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/start-bot', methods=['POST'])
def start_bot():
    try:
        threading.Thread(target=lambda: asyncio.run(main_loop())).start()
        return jsonify({"status": "بدأ البوت بنجاح"})
    except Exception as e:
        return jsonify({"status": f"فشل التشغيل: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
