from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import sqlite3
import numpy as np
import face_recognition
import cv2
from cryptography.fernet import Fernet
import base64
import os
import functools

app = Flask(__name__, static_folder='.', static_url_path='')
api = Api(app)
app.config['JWT_SECRET_KEY'] = 'visage-track-2026-super-secure-key-32bytes'  # Fixed length warning
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
    conn.close()

init_db()

# Helpers (unchanged)
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

# Token decorator (unchanged)
def token_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        try:
            verify_jwt_in_request()
            return view(**kwargs)
        except:
            return redirect(url_for('index'))
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
            access_token = create_access_token(identity={'id': user[0], 'role': user[1]})
            return {'access_token': access_token, 'role': user[1]}
        return {'message': 'Invalid credentials'}, 401

class Enroll(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        data = request.form
        name = data['name']
        email = data['email']
        images = [request.files[f'image{i}'] for i in range(1, 11) if f'image{i}' in request.files]
        frames = [cv2.imdecode(np.frombuffer(img.read(), np.uint8), cv2.IMREAD_COLOR) for img in images]
        
        if not is_live(frames[:2]):
            return {'message': 'Liveness check failed'}, 400
        
        embeddings = []
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb)
            if face_locations:
                embeddings.append(face_recognition.face_encodings(rgb, face_locations)[0])
        
        if not embeddings:
            return {'message': 'No face detected'}, 400
        
        avg_embedding = np.mean(embeddings, axis=0)
        encrypted = encode_embedding(avg_embedding)
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)", (name, email, encrypted, 'employee', 'defaultpass'))
        conn.commit()
        conn.close()
        
        return {'message': 'Enrollment successful'}, 200

class Recognize(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        image = request.files['image']
        frame = cv2.imdecode(np.frombuffer(image.read(), np.uint8), cv2.IMREAD_COLOR)
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

# Admin Resources (unchanged)
class AdminUsers(Resource):
    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        if current_user.get('role') != 'admin':
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
        if current_user.get('role') == 'admin':
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC")
        else:
            c.execute("SELECT a.id, u.name, a.timestamp, a.status FROM attendance a JOIN users u ON a.user_id = u.id WHERE u.id = ? ORDER BY a.timestamp DESC", (current_user['id'],))
        logs = [{'id': row[0], 'name': row[1], 'timestamp': row[2], 'status': row[3]} for row in c.fetchall()]
        conn.close()
        return {'logs': logs}

api.add_resource(Login, '/api/login')
api.add_resource(Enroll, '/api/enroll')
api.add_resource(Recognize, '/api/recognize')
api.add_resource(AdminUsers, '/api/admin/users')
api.add_resource(AdminAttendance, '/api/admin/attendance')

# Protected pages
@app.route('/attendance')
@token_required
def serve_attendance_page():
    return send_from_directory('.', 'attendance.html')

@app.route('/enroll')
@token_required
def serve_enroll_page():
    return send_from_directory('.', 'enroll.html')

@app.route('/dashboard')
@token_required
def serve_dashboard_page():
    return send_from_directory('.', 'dashboard.html')

@app.route('/admin')
@token_required
def serve_admin_dashboard():
    if get_jwt_identity().get('role') != 'admin':
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
