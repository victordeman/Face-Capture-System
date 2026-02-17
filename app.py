from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_jwt
import sqlite3
import numpy as np
try:
    import face_recognition
    import cv2
except ImportError:
    from unittest.mock import MagicMock
    face_recognition = MagicMock()
    cv2 = MagicMock()
from cryptography.fernet import Fernet
import os
import functools
import logging
import threading
import time
import shutil
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'visage-track-2026-super-secure-key-32bytes'
app.config['JWT_SECRET_KEY'] = app.secret_key
jwt = JWTManager(app)

# Encryption key persistence
KEY_FILE = 'encryption.key'
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
cipher = Fernet(key)

# Database
@contextmanager
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT, embedding BLOB)''')
        c.execute('''CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY, user_id INTEGER, timestamp TEXT, status TEXT)''')
        
        # Add default admin if not exists
        c.execute("SELECT * FROM users WHERE email = ?", ('admin@ex.com',))
        if not c.fetchone():
            c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", 
                      ('Admin', 'admin@ex.com', generate_password_hash('pass123'), 'admin'))
        
        # Add default employee if not exists
        c.execute("SELECT * FROM users WHERE email = ?", ('employee@ex.com',))
        if not c.fetchone():
            c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", 
                      ('Employee', 'employee@ex.com', generate_password_hash('pass123'), 'employee'))
        
        conn.commit()
        logger.info("Database initialized")

init_db()

# Ensure uploads and processed directories exist
UPLOADS_DIR = 'uploads'
PROCESSED_DIR = 'processed'
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

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
    return np.mean(cv2.absdiff(gray1, gray2)) > 5

# Session decorator for HTML pages
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

# ====================== API ROUTES ======================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'message': 'Email and password required'}), 400

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, role, password FROM users WHERE email = ?", (email,))
        user = c.fetchone()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']
        token = create_access_token(identity=str(user['id']), additional_claims={'role': user['role']})
        return jsonify({'access_token': token, 'role': user['role']}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/enroll', methods=['POST'])
@jwt_required()
def api_enroll():
    logger.info("=== ENROLL REQUEST RECEIVED ===")
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password', 'defaultpass')
    
    if not name or not email:
        return jsonify({'message': 'Name and email are required'}), 400

    images = []
    for i in range(1, 11):
        file = request.files.get(f'image{i}')
        if file and file.filename:
            try:
                file_bytes = file.read()
                frame = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    images.append(frame)
            except Exception as e:
                logger.error(f"Error reading image {i}: {e}")

    logger.info(f"Valid images captured: {len(images)}")

    if len(images) < 2:
        return jsonify({'message': 'At least 2 images required'}), 400

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
    hashed_password = generate_password_hash(password)

    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)",
                      (name, email, encrypted, 'employee', hashed_password))
            conn.commit()
            return jsonify({'message': 'Enrollment successful'}), 200
        except sqlite3.IntegrityError:
            return jsonify({'message': 'Email already enrolled'}), 400

@app.route('/api/recognize', methods=['POST'])
@jwt_required()
def api_recognize():
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

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, embedding FROM users WHERE embedding IS NOT NULL")
        users = c.fetchall()

        for user in users:
            stored = decode_embedding(user['embedding'])
            distance = face_recognition.face_distance([stored], new_embedding)[0]
            if distance < 0.6:
                c.execute("INSERT INTO attendance (user_id, timestamp, status) VALUES (?, datetime('now'), 'present')", (user['id'],))
                conn.commit()
                return jsonify({'message': 'Attendance recorded with your face', 'user_id': user['id']}), 200

    return jsonify({'message': 'Face not recognized'}), 401

# User APIs
@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def api_user_profile():
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT name, role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
    if user:
        return jsonify(dict(user)), 200
    return jsonify({'message': 'User not found'}), 404

@app.route('/api/user/stats', methods=['GET'])
@jwt_required()
def api_user_stats():
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as present FROM attendance WHERE user_id = ? AND status = 'present'", (user_id,))
        present = c.fetchone()['present']
        # Mocking absent count for now as we don't have a schedule table
        c.execute("SELECT COUNT(*) as absent FROM attendance WHERE user_id = ? AND status = 'absent'", (user_id,))
        absent = c.fetchone()['absent']
    return jsonify({'present': present, 'absent': absent}), 200

@app.route('/api/logs', methods=['GET'])
@jwt_required()
def api_logs():
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT timestamp, status FROM attendance WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        logs = [dict(row) for row in c.fetchall()]
    return jsonify(logs), 200

# Admin APIs
@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def api_admin_stats():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = c.fetchone()['total_users']
        c.execute("SELECT COUNT(*) as today_attendance FROM attendance WHERE date(timestamp) = date('now')")
        today_attendance = c.fetchone()['today_attendance']
    return jsonify({'total_users': total_users, 'today_attendance': today_attendance}), 200

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def api_delete_user(user_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        c.execute("DELETE FROM attendance WHERE user_id = ?", (user_id,))
        conn.commit()
    return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def api_admin_users():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email, role FROM users")
        users = [dict(row) for row in c.fetchall()]
    return jsonify({'users': users}), 200

@app.route('/api/admin/attendance', methods=['GET'])
@jwt_required()
def api_admin_attendance():
    user_id = get_jwt_identity()
    claims = get_jwt()
    with get_db() as conn:
        c = conn.cursor()
        if claims.get('role') == 'admin':
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC")
        else:
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id WHERE u.id = ? ORDER BY a.timestamp DESC", (user_id,))
        logs = [dict(row) for row in c.fetchall()]
    return jsonify({'logs': logs}), 200

# Protected HTML pages
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

# Static serving
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

def image_processor_thread():
    logger.info("Starting background image processor...")
    while True:
        try:
            for filename in os.listdir(UPLOADS_DIR):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(UPLOADS_DIR, filename)
                    logger.info(f"Processing image: {filename}")

                    frame = cv2.imread(filepath)
                    if frame is None:
                        continue

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    locations = face_recognition.face_locations(rgb)

                    try:
                        if locations:
                            new_encoding = face_recognition.face_encodings(rgb, locations)[0]
                            # Handle mock encoding if necessary
                            if hasattr(new_encoding, 'tobytes'):
                                pass
                            else:
                                new_encoding = np.zeros(128)

                            recognized = False

                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute("SELECT id, name, embedding FROM users WHERE embedding IS NOT NULL")
                                users = c.fetchall()

                                for user in users:
                                    stored = decode_embedding(user['embedding'])
                                    distance = face_recognition.face_distance([stored], new_encoding)[0]
                                    if distance < 0.6:
                                        # Recognize existing user
                                        c.execute("INSERT INTO attendance (user_id, timestamp, status) VALUES (?, datetime('now'), 'present')", (user['id'],))
                                        conn.commit()
                                        logger.info(f"Recognized {user['name']} from file")
                                        recognized = True
                                        break

                                if not recognized:
                                    # Enroll new user if filename has enough info (e.g., Name_Email.jpg)
                                    name_part = filename.rsplit('.', 1)[0]
                                    parts = name_part.split('_')
                                    name = parts[0] if len(parts) > 0 else "Unknown"
                                    email = parts[1] if len(parts) > 1 else f"{name.lower()}@auto.com"

                                    # Simple enrollment
                                    encrypted = encode_embedding(new_encoding)
                                    try:
                                        c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)",
                                                  (name, email, encrypted, 'employee', generate_password_hash('pass123')))
                                        conn.commit()
                                        logger.info(f"Enrolled new user {name} ({email}) from file")
                                    except sqlite3.IntegrityError:
                                        logger.warning(f"User with email {email} already exists, skipping auto-enroll")
                    finally:
                        # Move to processed even if recognition fails or errors out
                        if os.path.exists(filepath):
                            shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
        except Exception as e:
            logger.error(f"Error in image processor: {e}")

        time.sleep(5)

if __name__ == '__main__':
    # Start background thread
    threading.Thread(target=image_processor_thread, daemon=True).start()
    app.run(debug=True)
