from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import sqlite3
import numpy as np
import face_recognition
import cv2
from cryptography.fernet import Fernet
import os
import functools
import logging
import uuid
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')

# Configuration
app.config['SECRET_KEY'] = 'visage-track-2026-super-secure-key-32bytes'
app.config['JWT_SECRET_KEY'] = 'visage-track-2026-super-secure-key-32bytes'
app.config['JWT_TOKEN_LOCATION'] = ['headers']

jwt = JWTManager(app)

# Ensure uploads directory exists
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT,
            embedding BLOB,
            image_path TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            status TEXT
        )''')

        # Check if image_path column exists (simple migration)
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        if 'image_path' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN image_path TEXT")

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
        logger.info("Database initialized.")

init_db()

# Helpers
def encode_embedding(embedding):
    return cipher.encrypt(embedding.tobytes())

def decode_embedding(encrypted):
    return np.frombuffer(cipher.decrypt(encrypted), dtype=np.float64)

# Session decorator for HTML pages
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

# JWT Error Handlers
@jwt.unauthorized_loader
def unauthorized_response(callback):
    return jsonify({'message': 'Missing Authorization Header'}), 401

@jwt.invalid_token_loader
def invalid_token_response(callback):
    return jsonify({'message': 'Invalid Token', 'details': str(callback)}), 422

@app.before_request
def log_request_info():
    if request.path.startswith('/api/'):
        logger.info(f"API Request: {request.method} {request.path}")

@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Error: {str(e)}", exc_info=True)
    return jsonify({'message': 'An internal error occurred', 'error': str(e)}), 500

# ====================== API ROUTES ======================

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

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
        token = create_access_token(identity=str(user['id']))
        return jsonify({
            'message': 'Login successful',
            'access_token': token,
            'role': user['role']
        }), 200

    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/enroll', methods=['POST'])
@jwt_required()
def api_enroll():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password', 'defaultpass')

    if not name or not email:
        return jsonify({'message': 'Name and email are required'}), 400

    # Handle file storage
    image_file = request.files.get('image1') # Just take the first one for simplicity
    if not image_file:
        return jsonify({'message': 'No image captured'}), 400

    filename = f"{uuid.uuid4()}_{image_file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Save file to disk
    image_file.save(filepath)
    logger.info(f"Saved enrollment image to {filepath}")

    # Process for recognition (generate embedding)
    try:
        frame = cv2.imread(filepath)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        if not locations:
            return jsonify({'message': 'No face detected in the image'}), 400

        embedding = face_recognition.face_encodings(rgb, locations)[0]
        encrypted_embedding = encode_embedding(embedding)
    except Exception as e:
        logger.error(f"Error processing face: {e}")
        return jsonify({'message': 'Error processing face image'}), 500

    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, embedding, image_path, role, password) VALUES (?, ?, ?, ?, ?, ?)",
                      (name, email, encrypted_embedding, filename, 'employee', generate_password_hash(password)))
            conn.commit()
            return jsonify({'message': 'Enrollment successful', 'image': filename}), 200
        except sqlite3.IntegrityError:
            return jsonify({'message': 'Email already enrolled'}), 400

@app.route('/api/recognize', methods=['POST'])
@jwt_required()
def api_recognize():
    if 'image' not in request.files:
        return jsonify({'message': 'No image file'}), 400

    image_file = request.files['image']
    file_bytes = image_file.read()
    nparr = np.frombuffer(file_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

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
            try:
                stored = decode_embedding(user['embedding'])
                distance = face_recognition.face_distance([stored], new_embedding)[0]
                if distance < 0.6:
                    c.execute("INSERT INTO attendance (user_id, timestamp, status) VALUES (?, datetime('now'), 'present')", (user['id'],))
                    conn.commit()
                    return jsonify({'message': 'Attendance recorded', 'user_id': user['id']}), 200
            except Exception as e:
                logger.error(f"Error matching face: {e}")

    return jsonify({'message': 'Face not recognized'}), 401

@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def api_admin_stats():
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user or user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403

        c.execute("SELECT COUNT(*) as count FROM users")
        user_count = c.fetchone()['count']
        c.execute("SELECT COUNT(*) as count FROM attendance")
        log_count = c.fetchone()['count']

        return jsonify({
            'message': 'Stats retrieved successfully',
            'user_count': user_count,
            'log_count': log_count
        }), 200

@app.route('/api/logs', methods=['GET'])
@app.route('/api/admin/attendance', methods=['GET'])
@jwt_required()
def api_admin_attendance():
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()

        if user['role'] == 'admin':
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC")
        else:
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id WHERE u.id = ? ORDER BY a.timestamp DESC", (user_id,))
        logs = [dict(row) for row in c.fetchall()]
    return jsonify({'message': 'Logs retrieved successfully', 'logs': logs}), 200

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def api_admin_users():
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user or user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403

        c.execute("SELECT id, name, email, role, image_path FROM users")
        users = [dict(row) for row in c.fetchall()]
    return jsonify({'message': 'Users retrieved successfully', 'users': users}), 200

@app.route('/api/admin/users/<int:target_user_id>', methods=['DELETE'])
@jwt_required()
def api_admin_delete_user(target_user_id):
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user or user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403

        # Delete user and their attendance
        c.execute("DELETE FROM attendance WHERE user_id = ?", (target_user_id,))
        c.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
        conn.commit()
    return jsonify({'message': f'User {target_user_id} and their records deleted'}), 200

@app.route('/api/admin/attendance/<int:log_id>', methods=['DELETE'])
@jwt_required()
def api_admin_delete_log(log_id):
    user_id = get_jwt_identity()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user or user['role'] != 'admin':
            return jsonify({'message': 'Admin access required'}), 403

        c.execute("DELETE FROM attendance WHERE id = ?", (log_id,))
        conn.commit()
    return jsonify({'message': f'Attendance log {log_id} deleted'}), 200

# ====================== PAGE ROUTES ======================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

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

@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
