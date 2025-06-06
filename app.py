from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os
import base64
import time
import re
from flask import render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime
import glob
import requests
import json
from urllib.parse import unquote

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Create instance folder if it doesn't exist
if not os.path.exists('instance'):
    os.makedirs('instance')

# Global variable to store admin password for each IP
ip_admin_passwords = {}

def count_db_files():
    """Count and list all database files in instance folder"""
    db_files = glob.glob(os.path.join('instance', 'users_*.db'))
    print(f"\nTotal .db files in instance folder: {len(db_files)}")
    for db_file in db_files:
        print(f"Found database: {db_file}")
    return len(db_files)

def get_real_ip():
    """Get the real client IP address using only ipify"""
    # If we already detected the real IP in this session, use it
    if 'real_ip' in session:
        return session['real_ip']
    
    # Get IP from ipify
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=3)
        if response.status_code == 200:
            ip = response.json()['ip']
            session['real_ip'] = ip
            print(f"Got real IP {ip} from ipify")
            return ip
    except Exception as e:
        print(f"Failed to get IP from ipify: {str(e)}")
    
    # If ipify fails, use remote_addr as fallback
    ip = request.remote_addr
    session['real_ip'] = ip
    print(f"Using fallback IP: {ip}")
    return ip

def get_user_db_path(ip=None):
    """Get database path specific to user's IP address"""
    if ip is None:
        if request:
            ip = get_real_ip()
        else:
            ip = 'default'
    
    safe_ip = ip.replace('.', '_').replace(':', '_')  # Sanitize IP for filename
    db_path = os.path.join('instance', f'users_{safe_ip}.db')
    print(f"\nAccessing database for IP: {ip}")
    print(f"Database path: {db_path}")
    return db_path

def init_user_db(db_path, ip=None):
    """Initialize a new database for a specific path"""
    if ip is None and request:
        ip = get_real_ip()
    
    print(f"\nInitializing new database for IP: {ip}")
    print(f"Creating database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  is_admin INTEGER DEFAULT 0,
                  preferences TEXT DEFAULT '{}')''')

    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  title TEXT NOT NULL,
                  content TEXT NOT NULL,
                  is_deletable INTEGER DEFAULT 1)''')

    c.execute('''CREATE TABLE IF NOT EXISTS solved_challenges
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  challenge_name TEXT NOT NULL,
                  solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Generate random passwords for admin and cabinet
    admin_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    cabinet_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # Store admin password for this IP
    if ip:
        ip_admin_passwords[ip] = admin_password


    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
             ('admin', admin_password, 1))
    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
             ('user', 'password123', 0))
    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
             ('Unknown', 'Th3w3eknd15th3be35T', 0))
    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
             ('cabinet', cabinet_password, 0))
    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
             ('cyscom', '15012022', 0))

    # Add the non-deletable notes
    image_note = '<div style="text-align: center;"><h3>My Darkest Hours</h3><img src="/userdata/88382n2nbd92.png" alt="Different girls on the floor, distractin my thoughts of you" style="max-width: 100%; height: auto;"><p>Girl, I felt so alone inside of this crowded room</p></div>'
    c.execute("INSERT OR IGNORE INTO notes (username, title, content, is_deletable) VALUES (?, ?, ?, ?)",
             ('Unknown', 'Important Notice', image_note, 0))

    audio_note = '''<div style="text-align: center;">
        <h3>Internal Meeting Recording - Confidential</h3>
        <audio controls style="width: 100%; max-width: 500px;">
            <source src="/userdata/internalmeet28-03-2025.wav" type="audio/wav">
            Your browser does not support the audio element.
        </audio>
        <p style="color: black; margin-top: 10px;">No. The file is not corrupted.</p>
        <p><a href="/userdata/internalmeet28-03-2025.wav" download class="btn btn-primary" style="display: inline-block; padding: 8px 16px; background: #4f46e5; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px;">Download Recording</a></p>
    </div>'''
    c.execute("INSERT OR IGNORE INTO notes (username, title, content, is_deletable) VALUES (?, ?, ?, ?)",
             ('user', 'Internal Meeting Recording', audio_note, 0))
    c.execute("INSERT OR IGNORE INTO notes (username, title, content, is_deletable) VALUES (?, ?, ?, ?)",
             ('cabinet', 'Remember The Date, When it wsas created', '<a href="https://cyscomvit.com/">Click Me!</a>', 0))
    c.execute("INSERT OR IGNORE INTO notes (username, title, content, is_deletable) VALUES (?, ?, ?, ?)",
             ('cabinet', 'Attention!','Our main account will be deleted soon since the password was too easy to guess. I mean who uses a date as password? Please inform all members to create new accounts with stronger passwords', 0))

    conn.commit()
    conn.close()

    print(f"Database initialized successfully")
    print(f"Admin password for IP {ip}: {admin_password}")
    print(f"Cyscom password for IP {ip}: {cabinet_password}")
    
    # Print current database count
    count_db_files()

def get_db():
    """Connect to the IP-specific database"""
    db_path = get_user_db_path()
    
    # Initialize the database if it doesn't exist
    if not os.path.exists(db_path):
        init_user_db(db_path, get_real_ip())
    
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

@app.before_request
def before_request():
    """Ensure user's IP-specific database exists before each request"""
    if request.endpoint != 'static':  # Skip for static files
        real_ip = get_real_ip()
        db_path = get_user_db_path(real_ip)
        if not os.path.exists(db_path):
            init_user_db(db_path, real_ip)
        elif 'username' in session and session.get('is_admin') and real_ip in ip_admin_passwords:
            # Update admin password in session if it exists for this IP
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username='admin'")
            stored_password = c.fetchone()[0]
            ip_admin_passwords[real_ip] = stored_password
            conn.close()

# Remove default database initialization
if os.path.exists(os.path.join('instance', 'users_default.db')):
    os.remove(os.path.join('instance', 'users_default.db'))

# Print initial database count
print("\nInitial database count:")
count_db_files()

# Flag definitions with challenge display names
CHALLENGE_NAMES = {
    'sql_injection': 'SQL Injection',
    'privilege_escalation': 'Privilege Escalation as Real Admin',
    'stored_xss': 'Stored XSS',
    'event_xss': 'Event-Based XSS',
    'admin_panel': 'Admin Panel',
    'hidden_info': 'Hidden Info',
    'idor': 'IDOR',
    'ssti': 'SSTI',
    'osint': 'Lost User',
    'broken_access': 'Broken Access Control',
    'broken_auth': 'Broken Authentication',
    'type_juggling': 'Type Juggling',
    'proto_pollution': 'Prototype Pollution',
    'ssti_advanced': 'Advanced SSTI',
    'xss_encoded': 'Encoded XSS'
}

FLAGS = {
    'sql_injection': 'CYSM{sql_iNj3ct-10n}',
    'privilege_escalation': 'CYSM{pr1v1l3g3@escal}',
    'stored_xss': 'CYSM{S70*Xs5}',
    'event_xss': 'CYSM{3v3nt_b4s3d_Xs5}',
    'admin_panel': 'CYSM{4DMINc0n-s0-1}',
    'hidden_info': 'CYSM{cr4ckedbyWH0?}',
    'idor': 'CYSM{n0t3-Sn1ff3r}',
    'ssti': 'CYSM{T3mPl4t3^1nj3cT10n}',
    'osint': 'CYSM{Th15-4cc0unt-d035nt-3X1St}',
    'broken_access': 'CYSM{Br0k3_my_4cc355_C0ntr0l}',
    'broken_auth': 'CYSM{Br0k3N=P45S_R353t}',
    'type_juggling': 'CYSM{Pyth0n_typ3_juggl1ng_1s_fun}',
    'proto_pollution': 'CYSM{pr0t0_p0llut10n_1n_th3_w1ld}',
    'ssti_advanced': 'CYSM{s5t1_4dv4nc3d_1s_fun}',
    'xss_encoded': 'CYSM{xss_3nc0d3d_1s_fun}'
}

def generate_session_token(username):
    timestamp = str(int(time.time()))
    token = base64.b64encode(f"{username}:{timestamp}".encode()).decode()
    return token

def mark_challenge_solved(username, challenge_name):
    try:
        # Don't store flags for 'om' user
        if username == 'cyscom':
            return True

        conn = get_db()
        c = conn.cursor()
        # Check if already solved for this IP (any user)
        result = c.execute(
            "SELECT id FROM solved_challenges WHERE challenge_name=?",
            (challenge_name,)
        ).fetchone()
        
        if not result:
            c.execute(
                "INSERT INTO solved_challenges (username, challenge_name) VALUES (?, ?)",
                (username, challenge_name)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Error marking challenge as solved: {e}")
    finally:
        conn.close()
    return False

def get_solved_challenges(username):
    """Get all solved challenges for the current IP (shared across users except 'om')"""
    try:
        # Special handling for 'om' user - only show osint flag
        if username == 'cyscom':
            return ['osint']

        conn = get_db()
        c = conn.cursor()
        # Get all solved challenges for this IP regardless of user
        solved = c.execute(
            "SELECT DISTINCT challenge_name FROM solved_challenges"
        ).fetchall()
        return [row[0] for row in solved]
    except Exception as e:
        print(f"Error getting solved challenges: {e}")
        return []
    finally:
        conn.close()

@app.route('/')
def index():
    # TEMPORARY CODE FOR IP CHANGE DETECTION - REMOVE AFTER TESTING
    try:
        current_ip = requests.get('https://api.ipify.org?format=json', timeout=3).json()['ip']
        if 'real_ip' in session and session['real_ip'] != current_ip:
            print(f"\n[IP CHANGE DETECTED] Old IP: {session['real_ip']}, New IP: {current_ip}")
            session.clear()  # Clear session if IP changed
            print("Session cleared due to IP change")
    except Exception as e:
        print(f"\n[IP CHECK ERROR] {str(e)}")
    # END OF TEMPORARY CODE
    
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db()
            if not conn:
                return render_template('login.html', error='Database connection error')
            
            c = conn.cursor()
            
            # Block OR-based SQL injections
            or_patterns = [
                r"(?i)'\s*or\s*'?[0-9a-z]+\s*=\s*'?[0-9a-z]+",  # matches ' OR '1'='1', 'or'a'='a', etc
                r"(?i)'\s*or\s*'.*?'.*?'",      # matches ' OR 'anything'='anything'
                r"(?i)'\s*or\s*true",           # matches ' OR TRUE and variations
                r"(?i)'\s*or\s*1",              # matches ' OR 1 and variations
                r"(?i)'\s*or\s*[0-9]+",         # matches ' OR 2=2 and variations
                r"(?i).*?\bor\b.*?=",           # matches any OR with equals
                r"(?i)'\s*or\s*'",              # matches ' OR ' pattern
            ]
            
            if any(re.search(pattern, username) or re.search(pattern, password) for pattern in or_patterns):
                return render_template('login.html', error='Nice try! OR-based injections are blocked. Try another technique!')
            
            # Intentionally vulnerable to SQL injection (but not OR-based ones)
            query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
            result = c.execute(query).fetchone()
            conn.close()

            if result:
                session['logged_in'] = True
                session['username'] = username
                session['token'] = generate_session_token(username)
                session['is_admin'] = bool(result[3])
                
                # Award privilege escalation flag for legitimate admin login
                real_ip = get_real_ip()
                if username == 'admin' and password == ip_admin_passwords.get(real_ip):
                    print(f"Debug: Admin login detected - IP: {real_ip}, Password: {password}, Stored Password: {ip_admin_passwords.get(real_ip)}")
                    if mark_challenge_solved(username, 'privilege_escalation'):
                        flash(f"Congratulations! You gained admin access with legitimate credentials! Flag: {FLAGS['privilege_escalation']}")
                
                # If someone logs in as cyscom, grant the osint flag to other accounts
                if username == 'cyscom':
                    try:
                        conn = get_db()
                        c = conn.cursor()
                        # Insert the osint flag for a generic username to make it available for all
                        c.execute(
                            "INSERT OR IGNORE INTO solved_challenges (username, challenge_name) VALUES (?, ?)",
                            ('user', 'osint')
                        )
                        conn.commit()
                        conn.close()
                        flash("Lost user flag has been granted to all accounts.")
                    except Exception as e:
                        print(f"Error granting osint flag: {e}")
                
                # Check for SQL injection - award for any successful injection
                sql_patterns = [
                    r"(?i)--",                   # SQL comment
                    r"(?i)#",                    # SQL comment
                    r"(?i)/\*",                  # SQL comment block
                    r"(?i)union",                # UNION attack
                    r"(?i)'\s*;",                # SQL query stacking
                    r"(?i)'\s*$"                 # Single quote at end
                ]
                
                # Check if this is a SQL injection attempt
                is_injection = any(re.search(pattern, username) or re.search(pattern, password) for pattern in sql_patterns)
                
                if is_injection:
                    # Verify it's not a normal login
                    check_conn = get_db()
                    check_c = check_conn.cursor()
                    normal_query = "SELECT * FROM users WHERE username=? AND password=?"
                    normal_result = check_c.execute(normal_query, (username, password)).fetchone()
                    check_conn.close()
                    
                    if not normal_result and mark_challenge_solved(username, 'sql_injection'):
                        flash(f"Congratulations! You solved the SQL Injection challenge! Flag: {FLAGS['sql_injection']}")
                
                return redirect(url_for('dashboard'))
            
            return render_template('login.html', error='Invalid credentials')
            
        except Exception as e:
            # For SQL injection debugging - intentionally reveal error
            return render_template('login.html', error=f'Error: {str(e)}')
    
    return render_template('login.html')

@app.route('/flags')
def flags():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if session['username'] == 'cyscom':
        return render_template_string('''
            <div style="max-width: 800px; margin: 2rem auto; padding: 2rem; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #4f46e5; margin-bottom: 1rem;">🏆 Solved Challenges</h2>
                <div style="background: #f3f4f6; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1.5rem;">
                    <div style="border: 1px solid #d1d5db; border-radius: 0.375rem; padding: 1rem; margin-bottom: 1rem;">
                        <h3 style="color: #374151; font-size: 1.1rem; margin-bottom: 0.5rem;">Lost User</h3>
                        <p style="color: #6b7280; font-family: monospace; background: #e5e7eb; padding: 0.5rem; border-radius: 0.25rem;">
                            {{ flag }}
                        </p>
                    </div>
                </div>
                <div style="display: flex; gap: 1rem;">
                    <a href="/dashboard" style="text-decoration: none; padding: 0.5rem 1rem; background: #4f46e5; color: white; border-radius: 0.375rem;">Back to Dashboard</a>
                    <a href="/logout" style="text-decoration: none; padding: 0.5rem 1rem; background: #ef4444; color: white; border-radius: 0.375rem;">Logout</a>
                </div>
            </div>
        ''', flag=FLAGS['osint'])
    
    # Get solved challenges for other accounts
    solved_challenges = get_solved_challenges(session['username'])
    return render_template('flags.html', 
                         username=session['username'],
                         solved_challenges=solved_challenges,
                         flags=FLAGS,
                         challenge_names=CHALLENGE_NAMES)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Special handling for 'om' account
    if session['username'] == 'cyscom':
        return render_template_string('''
            <div style="max-width: 800px; margin: 2rem auto; padding: 2rem; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #4f46e5; margin-bottom: 1rem;">Account Status: Scheduled for Deletion</h2>
                <div style="background: #f3f4f6; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1.5rem;">
                    <p style="color: #374151; margin-bottom: 1rem;">
                        This account was marked for deletion by user request on 28-03-2024.
                        All notes and files have been removed as per deletion protocol. You can still view the flags this account has solved.
                    </p>
                    <p style="color: #6b7280;">
                        Account will be permanently removed from our systems within 30 days.
                    </p>
                </div>
                <div style="display: flex; gap: 1rem;">
                    <a href="/flags" style="text-decoration: none; padding: 0.5rem 1rem; background: #4f46e5; color: white; border-radius: 0.375rem;">View Flags</a>
                    <a href="/logout" style="text-decoration: none; padding: 0.5rem 1rem; background: #ef4444; color: white; border-radius: 0.375rem;">Logout</a>
                </div>
            </div>
        ''')
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, title, content FROM notes WHERE username=?", (session['username'],))
    notes = [{'id': row[0], 'title': row[1], 'content': row[2]} for row in c.fetchall()]
    db.close()
    
    is_admin = session.get('is_admin', False)
    return render_template('dashboard.html', username=session['username'], notes=notes, is_admin=is_admin)

@app.route('/add_note', methods=['POST'])
def add_note():
    """Add a new note with XSS and encoded XSS vulnerabilities"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    title = request.form.get('title', 'Untitled')
    # Check both 'content' and 'note' parameters
    content = request.form.get('content', '') or request.form.get('note', '')
    
    print(f"Debug: Received note - Title: {title}, Content: {content}")
    
    # VULNERABILITY 1: Basic XSS Check
    xss_patterns = ['<script', 'onerror=', 'onload=']
    if any(pattern in content.lower() for pattern in xss_patterns):
        if mark_challenge_solved(session['username'], 'stored_xss'):
            flash(f"Congratulations! You solved the Stored XSS challenge! Flag: {FLAGS['stored_xss']}")
    
    # VULNERABILITY 2: HTML Entity XSS Bypass
    # First URL decode the content to handle fully encoded payloads
    try:
        decoded_content = unquote(content)
        print(f"Debug: Decoded content: {decoded_content}")
    except:
        decoded_content = content
    
    # Check for encoded XSS in both original and decoded content
    xss_encoded_patterns = [
        '&#x3c;script', '&#60;script',     # HTML entity encoded
        '&lt;script',                      # Named entity
        '%3Cscript',                       # URL encoded
        '\\x3Cscript',                     # JS hex
        '\\u003Cscript',                   # JS unicode
        '%3Cimg%20src%3Dx%20onerror%3D',
        '&#x3c;img src=x onerror=',
        '&lt;img src=x onerror='
    ]
    
    content_lower = decoded_content.lower()
    original_lower = content.lower()
    
    if any(pattern.lower() in content_lower for pattern in xss_encoded_patterns) or \
       any(pattern.lower() in original_lower for pattern in xss_encoded_patterns):
        print("Debug: Encoded XSS pattern detected")
        print(f"Debug: Original content: {content}")
        print(f"Debug: Decoded content: {decoded_content}")
        if mark_challenge_solved(session.get('username'), 'xss_encoded'):
            flash(f"Congratulations! You found the encoded XSS vulnerability! Flag: {FLAGS['xss_encoded']}")
    
    # VULNERABILITY 3: Template Injection in title
    if '{{' in title and '}}' in title:
        try:
            # If they try to evaluate something sensitive
            if 'config' in title.lower() or 'class' in title.lower():
                if mark_challenge_solved(session.get('username'), 'ssti_advanced'):
                    flash(f"Congratulations! You found the advanced SSTI vulnerability! Flag: {FLAGS['ssti_advanced']}")
        except:
            pass
    
    try:
        # Store the note
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO notes (username, title, content, is_deletable) VALUES (?, ?, ?, ?)",
                 (session['username'], title, content, 1))
        conn.commit()
        conn.close()
        print(f"Debug: Note saved successfully")
    except Exception as e:
        print(f"Debug: Error saving note: {str(e)}")
        flash("Error saving note: " + str(e))
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_panel():
    # Check if user is logged in first
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Check if user is actually admin
    if not session.get('is_admin'):
        return "Unauthorized - Admin access required", 403
    
    conn = get_db()
    c = conn.cursor()
    users = c.execute("SELECT username, password, is_admin FROM users").fetchall()
    conn.close()
    
    # Mark admin panel challenge as solved only when accessing admin panel
    if mark_challenge_solved(session['username'], 'admin_panel'):
        flash(f"Congratulations! You accessed the admin panel! Flag: {FLAGS['admin_panel']}")
    
    return render_template('admin.html', users=users)

@app.route('/docs')
def docs():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return "Unauthorized - Admin access required", 403
    return render_template('docs.html')

@app.route('/api/v1/users')
def api_users():
    return jsonify({'error': 'Endpoint deprecated for security reasons'}), 403

@app.route('/api/v1/backup')
def api_backup():
    token = request.args.get('token', '')
    
    # Check if token is base64 encoded
    try:
        decoded_token = base64.b64decode(token).decode('utf-8')
        username, timestamp = decoded_token.split(':')
        
        if username == 'admin':
            # Mark the hidden info challenge as solved if user is logged in
            if session.get('logged_in'):
                if mark_challenge_solved(session['username'], 'hidden_info'):
                    flash(f"Congratulations! You found the hidden backup endpoint! Flag: {FLAGS['hidden_info']}")
            
            return render_template('backup_response.html', 
                                success=True,
                                flag=FLAGS['hidden_info'])
    except:
        pass
    
    return render_template('backup_response.html',
                         success=False,
                         error_message="Invalid backup token.")

@app.route('/api/v1/debug')
def api_debug():
    return jsonify({'error': 'Debug mode disabled in production'}), 503

@app.route('/api/v1/internal/users', methods=['GET'])
def internal_users_api():

    try:
        conn = get_db()
        c = conn.cursor()
        users = c.execute("SELECT username, is_admin FROM users").fetchall()
        conn.close()
        
        # If accessed, award the broken access control flag
        if session.get('logged_in'):
            if mark_challenge_solved(session['username'], 'broken_access'):
                flash(f"Congratulations! You found the unprotected internal API! Flag: {FLAGS['broken_access']}")
        
        return jsonify({
            'status': 'success',
            'message': 'Internal API - Restricted Access Only',
            'users': [{'username': user[0], 'is_admin': bool(user[1])} for user in users]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Replace the vulnerable serve_userdata route with a secure version
@app.route('/userdata/<path:filename>')
def serve_userdata(filename):
    """Serve files from userdata directory with proper path sanitization"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Sanitize the filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    
    try:
        return send_file(os.path.join('userdata', safe_filename))
    except Exception as e:
        return "File not found", 404

@app.route('/discussions')
def discussions():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('discussions.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Get query from either POST or GET
    query = request.form.get('query', '') or request.args.get('q', '')
    print(f"Debug: Search query received: {query}")
    
    # URL decode the query to handle encoded payloads
    try:
        decoded_query = unquote(query)
    except:
        decoded_query = query
    
    print(f"Debug: Decoded search query: {decoded_query}")
    
    # Check for event-based XSS patterns
    event_patterns = [
        'onmouseover=', 'onmouseout=', 'onclick=', 'onload=', 'onerror=',
        'onmouseenter=', 'onmouseleave=', 'onfocus=', 'onblur=', 'onchange=',
        'onkeyup=', 'onkeydown=', 'onkeypress=', 'ondblclick=', 'oncontextmenu=',
        'onmouseup=', 'onmousedown=', 'onsubmit=', 'onreset=', 'onselect=',
        'onabort=', 'ondrag=', 'ondrop=', 'onpaste=', 'oncopy='
    ]
    
    # Check for both regular and encoded event handlers
    encoded_events = [event.replace('on', '%6f%6e') for event in event_patterns]  # URL encoded
    encoded_events.extend([event.replace('on', '&#x6f;&#x6e;') for event in event_patterns])  # HTML hex encoded
    encoded_events.extend([event.replace('on', '&#111;&#110;') for event in event_patterns])  # HTML decimal encoded
    
    all_patterns = event_patterns + encoded_events
    
    # Check both original and decoded query
    if any(pattern.lower() in query.lower() for pattern in all_patterns) or \
       any(pattern.lower() in decoded_query.lower() for pattern in all_patterns):
        print("Debug: Event-based XSS pattern detected")
        if mark_challenge_solved(session['username'], 'event_xss'):
            flash(f"Congratulations! You found the event-based XSS vulnerability! Flag: {FLAGS['event_xss']}")
    
    # Check for template injection attempts (keep existing SSTI check)
    ssti_patterns = ['{{', '{%', 'config', '__class__', '__globals__']
    if any(pattern in decoded_query for pattern in ssti_patterns):
        if mark_challenge_solved(session['username'], 'ssti'):
            flash(f"Congratulations! You found the Template Injection vulnerability! Flag: {FLAGS['ssti']}")
    
    # Intentionally vulnerable to both XSS and template injection
    template = f'''
        <div class="search-results">
            <h3>Search Results for: {decoded_query}</h3>
            <p>No results found.</p>
        </div>
    '''
    return render_template_string(template)

# Add a GET route for search to handle URL parameters
@app.route('/search.html')
def search_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('search'))

@app.route('/note/<int:note_id>')
def view_note(note_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db()  # This will get the IP-specific database
    c = conn.cursor()
    note = c.execute("SELECT username, title, content FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    
    if note:
        # Special handling for Unknown user's note
        if note[0] == 'Unknown':
            return render_template_string('''
                <div style="padding: 20px;">
                    <h3>Note Details</h3>
                    <p><strong>Author:</strong> {{ note[0] }}</p>
                    <div style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem;">
                        <p style="color: #6b7280; text-align: center;">
                            🔒 This note has been encrypted by user request.
                        </p>
                    </div>
                    <br>
                    <a href="/dashboard" class="btn">Back to Dashboard</a>
                </div>
            ''', note=note)
        
        # IDOR vulnerability - intentionally not checking if the note belongs to current user
        if note[0] != session['username']:
            if mark_challenge_solved(session['username'], 'idor'):
                flash(f"Congratulations! You found the IDOR vulnerability! Flag: {FLAGS['idor']}")
        
        return render_template_string('''
            <div style="padding: 20px;">
                <h3>Note Details</h3>
                <p><strong>Author:</strong> {{ note[0] }}</p>
                <p><strong>Title:</strong> {{ note[1] }}</p>
                <div>{{ note[2] | safe }}</div>
                <br>
                <a href="/dashboard" class="btn">Back to Dashboard</a>
            </div>
        ''', note=note)
    
    return "Note not found", 404

@app.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        new_password = data.get('new_password')
        reset_token = data.get('token')
        
        # Only allow password resets for 'user' and 'cabinet' accounts
        if username not in ['user', 'cabinet']:
            return jsonify({'status': 'error', 'message': 'Password reset not available for this account'})
        
        # Rest of the function remains the same
        current_date = time.strftime('%d')
        expected_token = base64.b64encode(f"{username}:{current_date}".encode()).decode()
        
        if reset_token == expected_token:
            try:
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET password = ? WHERE username = ?", 
                         (new_password, username))
                conn.commit()
                
                c.execute("INSERT INTO solved_challenges (username, challenge_name) VALUES (?, ?)",
                         (username, 'broken_auth'))
                conn.commit()
                conn.close()
                
                return jsonify({
                    'status': 'success', 
                    'message': f'Password updated successfully! You found the authentication vulnerability! Flag: {FLAGS["broken_auth"]}'
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
        
        return jsonify({'status': 'error', 'message': 'Invalid reset token'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/clear_notes')
def clear_notes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE username=? AND is_deletable=1", (session['username'],))
    conn.commit()
    conn.close()
    
    flash("All deletable notes have been cleared!")
    return redirect(url_for('dashboard'))

@app.route('/about')
def about():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template('about.html')

@app.route('/api/v1/verify_backup', methods=['POST'])
def verify_backup():
    """Endpoint vulnerable to type juggling"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({'status': 'error', 'message': 'No data provided'})
            
        backup_hash = data.get('hash', '')
        backup_id = data.get('id')
        
        print(f"Debug: Received data = {data}")
        print(f"Debug: backup_id = {backup_id} ({type(backup_id)})")
        print(f"Debug: backup_hash = {backup_hash} ({type(backup_hash)})")
        
        # Simple type juggling check
        if backup_id == 123 and isinstance(backup_hash, str) and backup_hash.startswith('0e'):
            print("Debug: Basic checks passed")
            try:
                # This is the vulnerable part - converting string to float
                float_hash = float(backup_hash)
                print(f"Debug: float_hash = {float_hash}")
                if float_hash == 0.0:
                    print("Debug: Hash comparison passed")
                    if mark_challenge_solved(session.get('username'), 'type_juggling'):
                        return jsonify({
                            'status': 'success',
                            'message': f'Congratulations! You found the type juggling vulnerability! Flag: {FLAGS["type_juggling"]}'
                        })
            except ValueError as ve:
                print(f"Debug: Float conversion failed: {ve}")
                
    except Exception as e:
        print(f"Debug: Error in verify_backup: {str(e)}")
    
    return jsonify({'status': 'error', 'message': 'Invalid backup verification'})

@app.route('/api/v1/user/preferences', methods=['POST'])
def update_preferences():
    """Endpoint vulnerable to prototype pollution"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        # Get new preferences from request
        new_prefs = request.get_json()
        if not new_prefs:
            return jsonify({'status': 'error', 'message': 'No preferences provided'})
            
        print(f"Debug: Received preferences = {new_prefs}")
        
        # Get the current preferences
        conn = get_db()
        c = conn.cursor()
        
        # Get and parse current preferences
        c.execute("SELECT preferences FROM users WHERE username = ?", (session['username'],))
        result = c.fetchone()
        current_prefs = json.loads(result[0]) if result and result[0] else {}
        
        print(f"Debug: Current preferences = {current_prefs}")
        
        # Check for prototype pollution attempt first
        if '__proto__' in str(new_prefs) or 'constructor' in str(new_prefs):
            print("Debug: Prototype pollution detected")
            if mark_challenge_solved(session['username'], 'proto_pollution'):
                return jsonify({
                    'status': 'success',
                    'message': f'Congratulations! You found the prototype pollution vulnerability! Flag: {FLAGS["proto_pollution"]}'
                })
        
        # Store the new preferences
        c.execute("UPDATE users SET preferences = ? WHERE username = ?", 
                 (json.dumps(new_prefs), session['username']))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Preferences updated successfully'})
        
    except Exception as e:
        print(f"Debug: Error in update_preferences: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)  # Debug mode enabled intentionally 