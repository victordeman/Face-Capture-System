from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_jwt
import sqlite3
import numpy as np
import face_recognition
import cv2
from cryptography.fernet import Fernet
import os
import functools

app = Flask(__name__, static_folder=None)
app.secret_key = 'visage-track-2026-super-secure-key-32bytes'
app.config['JWT_SECRET_KEY'] = app.secret_key
app.config['JWT_ERROR_MESSAGE_KEY'] = 'message'
jwt = JWTManager(app)

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'message': 'Invalid token', 'error': str(error)}), 422

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'message': 'Missing token', 'error': str(error)}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'message': 'Token has expired'}), 401

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Encryption - Persistent key
key_file = os.path.join(BASE_DIR, 'encryption.key')
if os.path.exists(key_file):
    with open(key_file, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(key_file, 'wb') as f:
        f.write(key)
cipher = Fernet(key)

# Database
def init_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT, embedding BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY, user_id INTEGER, timestamp TEXT, status TEXT)''')
    c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", ('Admin', 'admin@ex.com', 'pass123', 'admin'))
    c.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", ('Employee', 'employee@ex.com', 'pass123', 'employee'))
    conn.commit()
    print("Users in DB:", c.execute("SELECT * FROM users").fetchall())
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
    return np.mean(cv2.absdiff(gray1, gray2)) > 5

# Session decorator for HTML pages
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index_page'))
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

    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
    c = conn.cursor()
    c.execute("SELECT id, role FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()

    if user:
        session['user_id'] = user[0]
        session['role'] = user[1]
        # Use string identity for 'sub' claim and additional_claims for role to stay stateless
        token = create_access_token(identity=str(user[0]), additional_claims={"role": user[1]})
        return jsonify({'access_token': token, 'role': user[1]}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/enroll', methods=['POST'])
@jwt_required(optional=True)
def api_enroll():
    print("=== ENROLL REQUEST RECEIVED ===")
    print("Form data:", dict(request.form))
    print("Files received:", list(request.files.keys()))

    name = request.form.get('name')
    email = request.form.get('email')
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
                print(f"Error reading image {i}: {e}")

    print(f"Valid images captured: {len(images)}")

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

    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
    c = conn.cursor()
    try:
        # Check if user already exists
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = c.fetchone()

        current_identity = get_jwt_identity()

        if user:
            # If user exists, require authentication as that user to update
            if not current_identity:
                return jsonify({'message': 'User already exists. Please login to update your face enrollment.'}), 400

            if str(user[0]) != str(current_identity):
                return jsonify({'message': 'Unauthorized: You can only update your own enrollment.'}), 403

            # Update existing user's name and embedding
            c.execute("UPDATE users SET name = ?, embedding = ? WHERE id = ?",
                      (name, encrypted, user[0]))
            message = 'Face enrollment updated successfully'
        else:
            # Create new user
            c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)",
                      (name, email, encrypted, 'employee', 'defaultpass'))
            message = 'Enrollment successful'

        conn.commit()
        return jsonify({'message': message}), 200
    except Exception as e:
        print(f"Database error during enrollment: {e}")
        return jsonify({'message': 'Error saving enrollment data'}), 500
    finally:
        conn.close()

@app.route('/api/recognize', methods=['POST'])
@jwt_required(optional=True)
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

    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
    c = conn.cursor()
    c.execute("SELECT id, embedding FROM users")
    users = c.fetchall()

    for uid, encrypted in users:
        stored = decode_embedding(encrypted)
        distance = face_recognition.face_distance([stored], new_embedding)[0]
        if distance < 0.6:
            c.execute("INSERT INTO attendance (user_id, timestamp, status) VALUES (?, datetime('now'), 'present')", (uid,))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Attendance recorded with your face', 'user_id': uid}), 200

    conn.close()
    return jsonify({'message': 'Face not recognized'}), 401

# Admin APIs
@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def api_admin_users():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
    c = conn.cursor()
    c.execute("SELECT id, name, email, role FROM users")
    users = [{'id': row[0], 'name': row[1], 'email': row[2], 'role': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify({'users': users}), 200

def get_attendance_logs(identity, role):
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))
    c = conn.cursor()
    if role == 'admin':
        c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC")
    else:
        # If no identity, return empty list (for optional JWT)
        if not identity:
            return []
        c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id WHERE u.id = ? ORDER BY a.timestamp DESC", (int(identity),))
    logs = [{'id': row[0], 'name': row[1], 'timestamp': row[2], 'status': row[3]} for row in c.fetchall()]
    conn.close()
    return logs

@app.route('/api/admin/attendance', methods=['GET'])
@jwt_required()
def api_admin_attendance():
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    logs = get_attendance_logs(identity, role)
    return jsonify({'logs': logs}), 200

@app.route('/api/logs', methods=['GET'])
@jwt_required(optional=True)
def api_logs():
    identity = get_jwt_identity()
    role = get_jwt().get('role') if identity else None

    # Fallback to session if JWT is missing
    if not identity and 'user_id' in session:
        identity = session['user_id']
        role = session.get('role')

    logs = get_attendance_logs(identity, role)
    return jsonify({'logs': logs}), 200

# Protected HTML pages
@app.route('/attendance')
@login_required
def serve_attendance_page():
    return send_from_directory(BASE_DIR, 'attendance.html')

@app.route('/enroll')
@login_required
def serve_enroll_page():
    return send_from_directory(BASE_DIR, 'enroll.html')

@app.route('/dashboard')
@login_required
def serve_dashboard_page():
    return send_from_directory(BASE_DIR, 'dashboard.html')

@app.route('/admin')
@login_required
def serve_admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('serve_dashboard_page'))
    return send_from_directory(BASE_DIR, 'admin.html')

# Static serving
@app.route('/')
def index_page():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    # Block sensitive files from being served as static content
    sensitive_extensions = ('.py', '.db', '.sqlite', '.log', '.key', '.sh')
    if path.endswith(sensitive_extensions) or path.startswith('.'):
        return redirect(url_for('index_page'))

    full_path = os.path.join(BASE_DIR, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return send_from_directory(BASE_DIR, path)

    # Fallback to index.html for unknown routes to support client-side routing
    return send_from_directory(BASE_DIR, 'index.html')

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'message': 'Resource not found', 'error': str(error)}), 404
    return redirect(url_for('index_page'))

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error', 'error': str(error)}), 500

if __name__ == '__main__':
    app.run(debug=True)
