from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
from flask_restful import Api, Resource, reqparse
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
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, help='Email is required')
        parser.add_argument('password', type=str, required=True, help='Password is required')
        parser.add_argument('role', type=str, required=False)  # optional

        args = parser.parse_args()
        email = args['email']
        password = args['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, role FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['role'] = user[1]
            access_token = create_access_token(identity={'id': user[0], 'role': user[1]})
            return {'access_token': access_token, 'role': user[1]}
        return {'message': 'Invalid credentials'}, 401

class Logout(Resource):
    def get(self):
        session.clear()
        return redirect(url_for('index'))

# Updated Enroll
class Enroll(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()

        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, location='form', help='Name is required')
        parser.add_argument('email', type=str, required=True, location='form', help='Email is required')

        args = parser.parse_args()
        name = args['name']
        email = args['email']

        images = []
        for i in range(1, 11):
            key = f'image{i}'
            if key in request.files:
                file = request.files[key]
                if file.filename != '':
                    try:
                        file_bytes = file.read()
                        frame = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            images.append(frame)
                    except Exception as e:
                        print(f"Error decoding image {i}: {e}")

        if len(images) < 2:
            return {'message': 'Need at least 2 valid images for enrollment'}, 400

        if not is_live(images[:2]):
            return {'message': 'Liveness check failed (no motion detected)'}, 400

        embeddings = []
        for frame in images:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            if locations:
                embeddings.append(face_recognition.face_encodings(rgb, locations)[0])

        if not embeddings:
            return {'message': 'No valid face detected in uploaded images'}, 400

        avg_embedding = np.mean(embeddings, axis=0)
        encrypted = encode_embedding(avg_embedding)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, embedding, role, password) VALUES (?, ?, ?, ?, ?)",
                      (name, email, encrypted, 'employee', 'defaultpass'))
            conn.commit()
            return {'message': 'Enrollment successful'}, 200
        except sqlite3.IntegrityError:
            conn.rollback()
            return {'message': 'Email already enrolled'}, 409
        finally:
            conn.close()

# Updated Recognize
class Recognize(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()

        parser = reqparse.RequestParser()
        parser.add_argument('image', type=reqparse.FileStorage, location='files', required=True,
                            help='Single image file is required')

        args = parser.parse_args()
        image_file = args['image']

        if not image_file or not image_file.filename:
            return {'message': 'No valid image file received'}, 400

        try:
            file_bytes = image_file.read()
            frame = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                return {'message': 'Invalid or corrupted image file'}, 400
        except Exception as e:
            return {'message': f'Image processing failed: {str(e)}'}, 400

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        if not locations:
            return {'message': 'No face detected in the image'}, 400

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
            return {'message': 'Attendance recorded with your face', 'user_id': user_id}, 200
        return {'message': 'Face not recognized'}, 401

# AdminUsers
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

# AdminAttendance
class AdminAttendance(Resource):
    @jwt_required()
    def get(self):
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
        return {'logs': logs}

api.add_resource(Login, '/api/login')
api.add_resource(Logout, '/api/logout')
api.add_resource(Enroll, '/api/enroll')
api.add_resource(Recognize, '/api/recognize')
api.add_resource(AdminUsers, '/api/admin/users')
api.add_resource(AdminAttendance, '/api/admin/attendance')

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
