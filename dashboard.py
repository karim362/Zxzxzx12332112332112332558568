from flask import Flask, jsonify, render_template
import json

app = Flask(__name__)

@app.route('/')
def dashboard():
    try:
        with open('stats.json') as f:
            stats = json.load(f)
    except:
        stats = {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}
    return render_template('dashboard.html', stats=stats)

app.run(host='0.0.0.0', port=10000)
