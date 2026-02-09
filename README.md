# VisageTrack AI - Face Recognition Attendance System

**Record attendance with your face** — a touchless, secure, and efficient web-based attendance tracking prototype using facial recognition.

This project is a full-stack prototype that allows users to **record attendance with your face** via a laptop webcam. It includes:

- Modern, responsive frontend (inspired by VisageTrack design)
- Flask backend for face enrollment and recognition
- Real-time facial recognition using `face_recognition` and OpenCV
- Basic liveness detection (motion check between frames)
- SQLite database for storing encrypted face embeddings and attendance logs
- JWT-based authentication (basic implementation)
- Touchless clock-in experience

Perfect for educational institutions, small offices, or research projects — especially in resource-constrained environments like many parts of Nigeria.

## Features

- **Enroll Face**: Capture multiple images → generate and encrypt face embedding
- **Clock In / Record Attendance with Your Face**: Live webcam preview → capture frame → send to backend → verify identity → log attendance
- **Liveness Check**: Prevents photo/video spoofing with basic motion detection
- **Privacy**: Stores only encrypted numerical embeddings (not photos)
- **Admin-friendly**: Attendance logs stored in SQLite (easy to query/export)
- **Responsive UI**: Tailwind CSS + dark mode support
- **Local-first**: Runs entirely on your laptop (no cloud required for development)

## Tech Stack

**Frontend**
- HTML5 + Tailwind CSS (via CDN)
- JavaScript (vanilla + Feather Icons)
- WebRTC for webcam access

**Backend**
- Python 3.10+
- Flask + Flask-RESTful + Flask-JWT-Extended
- face_recognition (dlib-based embeddings)
- OpenCV (image processing)
- SQLite (database)
- cryptography (Fernet encryption for embeddings)

## Prerequisites

- Python 3.10 or higher
- Git
- Webcam-enabled laptop/computer
- (Windows users may need Visual Studio Build Tools for dlib compilation)

## Installation & Local Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/victordeman/Face-Capture-System.git
cd Face-Capture-System

## Step-by-Step Integration Process

### 1. Clone the Repository Locally (If Not Already Done):

```Open a terminal.
Navigate to your project folder: cd path/to/Face-Capture-System.
If not cloned: git clone https://github.com/victordeman/Face-Capture-System.git.
