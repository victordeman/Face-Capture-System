from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import sqlite3
import numpy as np
import face_recognition
import cv2
from cryptography.fernet import Fernet
import os
import functools

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'visage-track-2026-super-secure-key-32bytes'  # Used for session and JWT
app.config['JWT_SECRET_KEY'] = app.secret_key
jwt = JWTManager(app)

# Encryption key
key = Fernet.generate_key()
cipher = Fernet(key)

# Database init
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT, embedding BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY, user_id INTEGER, timestamp TEXT, status TEXT)''')
    # Demo users
    c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", ('Admin', 'admin@ex.com', 'pass123', 'admin'))
    c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", ('Employee', 'employee@ex.com', 'pass123', 'employee'))
    conn.commit()
    c.execute("SELECT * FROM users")
    print("Users in DB:", c.fetchall())
    conn.close()

init_db()

# Helpers
def encode_embedding(embedding):
    return cipher.encrypt(embedding.tobytes())

def decode_embedding(encrypted):
    return np.frombuffer(cipher.decrypt(encrypted), dtype=np.float64)

def is_live(frames):
    if len(frames) < 2:
        return False
    gray1 = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frames[1], cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray1, gray2)
    return np.mean(diff) > 5

# Session-based decorator for HTML routes
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

# Native API Routes (no Flask-RESTful)
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, role FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()

    if user:
        session['user_id'] = user[0]
        session['role'] = user[1]
        access_token = create_access_token(identity={'id': user[0], 'role': user[1]})
        return jsonify({'access_token': access_token, 'role': user[1]}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['GET'])
def api_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/enroll', methods=['POST'])
@jwt_required()
def api_enroll():
    current_user = get_jwt_identity()

    name = request.form.get('name')
    email = request.form.get('email')
    if not name or not email:
        return jsonify({'message': 'Name and email are required'}), 400

    images = []
    for i in range(1, 11):
        key = f'image{i}'
        if key in request.files:
            file = request.files[key]
            if file and file.filename != '':
                file_bytes = file.read()
                frame = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    images.append(frame)

    if len(images) < 2:
        return jsonify({'message': 'Need at least 2 valid images for enrollment'}), 400

    if not is_live(images[:2]):
        return jsonify({'message': 'Liveness check failed'}), 400

    embeddings = []
    for frame in images:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        if locations:
            embeddings.append(face_recognition.face_encodings(rgb, locations)[0])

    if not embeddings:
        return jsonify({'message': 'No face detected'}), 400

    avg_embedding = np.mean(embeddings, axis=0)
    encrypted = encode_embedding(avg_embedding)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)",
                  (name, email, encrypted, 'employee', 'defaultpass'))
        conn.commit()
        return jsonify({'message': 'Enrollment successful'}), 200
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Email already exists'}), 400
    finally:
        conn.close()

@app.route('/api/recognize', methods=['POST'])
@jwt_required()
def api_recognize():
    current_user = get_jwt_identity()

    if 'image' not in request.files:
        return jsonify({'message': 'No image file'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    file_bytes = image_file.read()
    frame = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({'message': 'Invalid image'}), 400

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)
    if not locations:
        return jsonify({'message': 'No face detected'}), 400

    new_embedding = face_recognition.face_encodings(rgb, locations)[0]

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, embedding FROM users")
    users = c.fetchall()

    match_found = False
    user_id = None
    for uid, encrypted in users:
        stored = decode_embedding(encrypted)
        distance = face_recognition.face_distance([stored], new_embedding)[0]
        if distance < 0.6:
            c.execute("INSERT INTO attendance (user_id, timestamp, status) VALUES (?, datetime('now'), 'present')",
                      (uid,))
            conn.commit()
            match_found = True
            user_id = uid
            break

    conn.close()

    if match_found:
        return jsonify({'message': 'Attendance recorded with your face', 'user_id': user_id}), 200
    return jsonify({'message': 'Face not recognized'}), 401

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def api_admin_users():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, name, email, role FROM users")
    users = [{'id': row[0], 'name': row[1], 'email': row[2], 'role': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify({'users': users}), 200

@app.route('/api/admin/attendance', methods=['GET'])
@jwt_required()
def api_admin_attendance():
    current_user = get_jwt_identity()
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if current_user['role'] == 'admin':
        c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC")
    else:
        c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id WHERE u.id = ? ORDER BY a.timestamp DESC",
                  (current_user['id'],))

    logs = [{'id': row[0], 'name': row[1], 'timestamp': row[2], 'status': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify({'logs': logs}), 200

# Protected pages
@app.route('/attendance')
@login_required
def serve_attendance_page():
    return send_from_directory('.', 'attendance.html')

@app.route('/enroll')
@login_required
def serve_enroll_page():
    return send_from_directory('.', 'enroll.html')

@app.route('/dashboard')
@login_required
def serve_dashboard_page():
    return send_from_directory('.', 'dashboard.html')

@app.route('/admin')
@login_required
def serve_admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('serve_dashboard_page'))
    return send_from_directory('.', 'admin.html')

# Serve index and static
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
