from flask_restful import reqparse
from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
from flask_restful import Api, Resource
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import sqlite3
import numpy as np
import face_recognition
import cv2
from cryptography.fernet import Fernet
import os
import functools

app = Flask(__name__, static_folder='.', static_url_path='')
api = Api(app)
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

class Login(Resource):
    def post(self):
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, role FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            # Set session for HTML protection
            session['user_id'] = user[0]
            session['role'] = user[1]
            # Also return JWT for APIs
            access_token = create_access_token(identity={'id': user[0], 'role': user[1]})
            return {'access_token': access_token, 'role': user[1]}
        return {'message': 'Invalid credentials'}, 401

class Logout(Resource):
    def get(self):
        session.clear()
        return {'message': 'Logged out'}, 200

class Enroll(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name is required')
        parser.add_argument('email', type=str, required=True, help='Email is required')
        
        args = parser.parse_args()
        name = args['name']
        email = args['email']
        
        # Get images from multipart form
        images = []
        for i in range(1, 11):
            file_key = f'image{i}'
            if file_key in request.files:
                images.append(request.files[file_key])
        
        if len(images) < 2:
            return {'message': 'At least 2 images required for liveness check'}, 400
        
        frames = []
        for img in images:
            img_bytes = img.read()
            frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                frames.append(frame)
        
        if not is_live(frames[:2]):
            return {'message': 'Liveness check failed'}, 400
        
        embeddings = []
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb)
            if face_locations:
                embeddings.append(face_recognition.face_encodings(rgb, face_locations)[0])
        
        if not embeddings:
            return {'message': 'No face detected in any image'}, 400
        
        avg_embedding = np.mean(embeddings, axis=0)
        encrypted = encode_embedding(avg_embedding)
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)",
                  (name, email, encrypted, 'employee', 'defaultpass'))
        conn.commit()
        conn.close()
        
        return {'message': 'Enrollment successful'}, 200


class Recognize(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        
        parser = reqparse.RequestParser()
        parser.add_argument('image', type=reqparse.FileStorage, location='files', required=True)
        args = parser.parse_args()
        image_file = args['image']
        
        if not image_file:
            return {'message': 'No image provided'}, 400
        
        img_bytes = image_file.read()
        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return {'message': 'Invalid image file'}, 400
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb)
        if not face_locations:
            return {'message': 'No face detected'}, 400
        
        new_embedding = face_recognition.face_encodings(rgb, face_locations)[0]
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, embedding FROM users")
        users = c.fetchall()
        
        for user_id, encrypted in users:
            stored_embedding = decode_embedding(encrypted)
            distance = face_recognition.face_distance([stored_embedding], new_embedding)[0]
            if distance < 0.6:
                c.execute("INSERT INTO attendance (user_id, timestamp, status) VALUES (?, datetime('now'), 'present')", (user_id,))
                conn.commit()
                conn.close()
                return {'message': 'Attendance recorded with your face', 'user_id': user_id}, 200
        
        conn.close()
        return {'message': 'Face not recognized'}, 401


class AdminUsers(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        if current_user['role'] != 'admin':
            return {'message': 'Admin access required'}, 403
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, name, email, role FROM users")
        users = [{'id': row[0], 'name': row[1], 'email': row[2], 'role': row[3]} for row in c.fetchall()]
        conn.close()
        return {'users': users}

class AdminAttendance(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        if current_user['role'] == 'admin':
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC")
        else:
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id WHERE u.id = ? ORDER BY a.timestamp DESC", (current_user['id'],))
        logs = [{'id': row[0], 'name': row[1], 'timestamp': row[2], 'status': row[3]} for row in c.fetchall()]
        conn.close()
        return {'logs': logs}

api.add_resource(Login, '/api/login')
api.add_resource(Logout, '/api/logout')
api.add_resource(Enroll, '/api/enroll')
api.add_resource(Recognize, '/api/recognize')
api.add_resource(AdminUsers, '/api/admin/users')
api.add_resource(AdminAttendance, '/api/admin/attendance')

# Protected pages (now with login_required using session)
@app.route('/attendance')
@login_required
def serve_attendance_page():
    return send_from_directory('.', 'attendance.html')

@app.route('/enroll')
@login_required
def serve_enroll_page():
    return send_from_directory('.', 'enroll.html')

@app.route('/admin')
@login_required
def serve_admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('serve_dashboard_page'))  # Now points to real dashboard
    return send_from_directory('.', 'admin.html')

@app.route('/dashboard')
@login_required
def serve_dashboard_page():
    return send_from_directory('.', 'dashboard.html')

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
