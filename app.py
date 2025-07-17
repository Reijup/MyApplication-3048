from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import json
import calendar
from datetime import datetime, timedelta
import uuid
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this-in-production'

# PythonAnywhere用のパス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
DATA_FILE = os.path.join(BASE_DIR, 'calendar_data.json')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 必要なディレクトリの作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)

# グローバル変数
records = {}
notifications = {}

def load_records():
    """記録データの読み込み"""
    global records
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except:
            records = {}
    else:
        records = {}

def save_records():
    """記録データの保存"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"データ保存エラー: {e}")

def allowed_file(filename):
    """許可されたファイル拡張子かチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_calendar_data(year, month):
    """カレンダーデータの生成（日曜日から土曜日）"""
    # 日曜日から土曜日でカレンダーを生成
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(year, month)
    calendar_data = []
    
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                has_record = date_str in records
                week_data.append({
                    'day': day,
                    'date': date_str,
                    'has_record': has_record
                })
        calendar_data.append(week_data)
    
    return calendar_data

def start_notification_system():
    """通知システム開始（PythonAnywhereでは制限があるため簡易版）"""
    # PythonAnywhereでは常時実行スレッドに制限があるため、
    # 実際の通知はリクエスト時にチェックする方式に変更
    pass

@app.route('/')
def index():
    """メインページ"""
    today = datetime.now()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    
    # 月の境界チェック
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    calendar_data = generate_calendar_data(year, month)
    
    # 前月・次月の計算
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    return render_template('index.html', 
                         calendar_data=calendar_data,
                         year=year,
                         month=month,
                         month_name=calendar.month_name[month],
                         prev_year=prev_year,
                         prev_month=prev_month,
                         next_year=next_year,
                         next_month=next_month)

@app.route('/record/<date>')
def record_detail(date):
    """記録詳細ページ"""
    record = records.get(date, {})
    return render_template('record.html', date=date, record=record)

@app.route('/save_record', methods=['POST'])
def save_record():
    """記録保存"""
    date = request.form.get('date')
    comment = request.form.get('comment', '')
    notification_enabled = request.form.get('notification') == 'on'
    notification_time = request.form.get('notification_time', '09:00')
    
    if not date:
        flash('日付が指定されていません', 'error')
        return redirect(url_for('index'))
    
    # 既存の記録を取得
    record = records.get(date, {})
    record['comment'] = comment
    record['notification'] = notification_enabled
    record['notification_time'] = notification_time
    
    # 画像アップロード処理
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '' and allowed_file(file.filename):
            # 古い画像の削除
            if 'image_path' in record and record['image_path']:
                old_path = os.path.join(BASE_DIR, 'static', record['image_path'])
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # 新しい画像の保存
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            record['image_path'] = f"uploads/{unique_filename}"
    
    # 記録を保存
    records[date] = record
    save_records()
    
    # 通知設定（PythonAnywhere用に簡易化）
    if notification_enabled:
        try:
            notification_datetime = datetime.strptime(f"{date} {notification_time}", "%Y-%m-%d %H:%M")
            notifications[date] = notification_datetime
        except ValueError:
            flash('通知時刻の形式が正しくありません', 'error')
    
    flash('記録を保存しました', 'success')
    return redirect(url_for('record_detail', date=date))

@app.route('/delete_record/<date>')
def delete_record(date):
    """記録削除"""
    if date in records:
        record = records[date]
        # 画像ファイルの削除
        if 'image_path' in record and record['image_path']:
            image_path = os.path.join(BASE_DIR, 'static', record['image_path'])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # 記録削除
        del records[date]
        save_records()
        
        # 通知削除
        if date in notifications:
            del notifications[date]
        
        flash('記録を削除しました', 'success')
    else:
        flash('削除する記録がありません', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete_image/<date>')
def delete_image(date):
    """画像削除"""
    if date in records and 'image_path' in records[date]:
        image_path = os.path.join(BASE_DIR, 'static', records[date]['image_path'])
        if os.path.exists(image_path):
            os.remove(image_path)
        
        del records[date]['image_path']
        save_records()
        flash('画像を削除しました', 'success')
    
    return redirect(url_for('record_detail', date=date))

@app.route('/api/notifications')
def get_notifications():
    """通知一覧API"""
    current_notifications = []
    current_time = datetime.now()
    
    for date_str, notification_time in notifications.items():
        if current_time >= notification_time:
            record = records.get(date_str, {})
            current_notifications.append({
                'date': date_str,
                'comment': record.get('comment', ''),
                'time': notification_time.strftime('%H:%M')
            })
    
    return jsonify(current_notifications)

def create_templates():
    """HTMLテンプレートの作成"""
    templates_dir = os.path.join(BASE_DIR, 'templates')
    
    # base.html
    base_template = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>記録カレンダーアプリ</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .calendar-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .calendar-nav button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        .calendar-nav button:hover {
            background-color: #0056b3;
        }
        .calendar-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        .calendar-table th, .calendar-table td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
            vertical-align: top;
            height: 80px;
        }
        .calendar-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .calendar-day {
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .calendar-day:hover {
            background-color: #f0f0f0;
        }
        .has-record {
            background-color: #e3f2fd;
            border: 2px solid #2196f3;
        }
        .flash-messages {
            margin-bottom: 20px;
        }
        .flash-message {
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
        }
        .flash-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .flash-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .record-form {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .form-group textarea {
            height: 100px;
            resize: vertical;
        }
        .btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-right: 10px;
        }
        .btn:hover {
            background-color: #0056b3;
        }
        .btn-danger {
            background-color: #dc3545;
        }
        .btn-danger:hover {
            background-color: #c82333;
        }
        .image-preview {
            max-width: 300px;
            max-height: 200px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>記録カレンダーアプリ</h1>
        </div>
        
        <div class="flash-messages">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        
        {% block content %}{% endblock %}
    </div>
    
    <script>
        // 通知チェック（PythonAnywhere用に簡易化）
        function checkNotifications() {
            fetch('/api/notifications')
                .then(response => response.json())
                .then(notifications => {
                    notifications.forEach(notification => {
                        console.log(`通知: ${notification.date} - ${notification.comment}`);
                    });
                })
                .catch(error => console.log('通知チェックエラー:', error));
        }
        
        // ページロード時に通知チェック
        window.onload = checkNotifications;
    </script>
</body>
</html>'''
    
    # index.html
    index_template = '''{% extends "base.html" %}

{% block content %}
<div class="calendar-nav">
    <button onclick="location.href='?year={{ prev_year }}&month={{ prev_month }}'">← 前月</button>
    <h2>{{ year }}年 {{ month_name }}</h2>
    <button onclick="location.href='?year={{ next_year }}&month={{ next_month }}'">次月 →</button>
</div>

<table class="calendar-table">
    <thead>
        <tr>
            <th>日</th>
            <th>月</th>
            <th>火</th>
            <th>水</th>
            <th>木</th>
            <th>金</th>
            <th>土</th>
        </tr>
    </thead>
    <tbody>
        {% for week in calendar_data %}
        <tr>
            {% for day in week %}
            <td class="calendar-day {% if day and day.has_record %}has-record{% endif %}"
                {% if day %}onclick="location.href='/record/{{ day.date }}'"{% endif %}>
                {% if day %}
                    {{ day.day }}
                    {% if day.has_record %}
                        <br><small>📝</small>
                    {% endif %}
                {% endif %}
            </td>
            {% endfor %}
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}'''
    
    # record.html
    record_template = '''{% extends "base.html" %}

{% block content %}
<div style="margin-bottom: 20px;">
    <button onclick="location.href='/'" class="btn">← カレンダーに戻る</button>
</div>

<h2>{{ date }} の記録</h2>

<form method="POST" action="/save_record" enctype="multipart/form-data" class="record-form">
    <input type="hidden" name="date" value="{{ date }}">
    
    <div class="form-group">
        <label for="comment">コメント:</label>
        <textarea name="comment" id="comment" placeholder="今日の出来事を記録してください...">{{ record.comment or '' }}</textarea>
    </div>
    
    <div class="form-group">
        <label for="image">画像:</label>
        <input type="file" name="image" id="image" accept="image/*">
        {% if record.image_path %}
            <div style="margin-top: 10px;">
                <img src="{{ url_for('static', filename=record.image_path) }}" alt="記録画像" class="image-preview">
                <br>
                <button type="button" onclick="if(confirm('画像を削除しますか？')) location.href='/delete_image/{{ date }}'" class="btn btn-danger">画像を削除</button>
            </div>
        {% endif %}
    </div>
    
    <div class="form-group">
        <div class="checkbox-group">
            <input type="checkbox" name="notification" id="notification" {% if record.notification %}checked{% endif %}>
            <label for="notification">通知を設定</label>
            <input type="time" name="notification_time" value="{{ record.notification_time or '09:00' }}">
        </div>
    </div>
    
    <div class="form-group">
        <button type="submit" class="btn">保存</button>
        {% if record %}
            <button type="button" onclick="if(confirm('この記録を削除しますか？')) location.href='/delete_record/{{ date }}'" class="btn btn-danger">削除</button>
        {% endif %}
    </div>
</form>
{% endblock %}'''
    
    # テンプレートファイルの作成
    with open(os.path.join(templates_dir, 'base.html'), 'w', encoding='utf-8') as f:
        f.write(base_template)
    
    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_template)
    
    with open(os.path.join(templates_dir, 'record.html'), 'w', encoding='utf-8') as f:
        f.write(record_template)

# 初期化処理
create_templates()
load_records()
start_notification_system()

# PythonAnywhere用の設定
if __name__ == '__main__':
    app.run(debug=False)
else:
    # PythonAnywhereで実行される場合
    application = app