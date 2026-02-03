// Initialize Feather icons (already in HTML: feather.replace())

// Theme toggle
const themeToggle = document.getElementById('theme-toggle');
themeToggle.addEventListener('click', () => {
  document.body.classList.toggle('dark');
  localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
});

// Load saved theme
if (localStorage.getItem('theme') === 'dark') {
  document.body.classList.add('dark');
}

// Login form submission (demo: log to console)
const loginForm = document.getElementById('login-form');
loginForm.addEventListener('submit', (e) => {
  e.preventDefault();
  console.log('Login submitted - Role:', document.querySelector('input[name="role"]:checked').value);
  alert('Logged in successfully! Redirecting to dashboard...');
  // In production, redirect or fetch data
});

// Face-api.js demo init (for recording attendance with your face)
Promise.all([
  faceapi.nets.tinyFaceDetector.loadFromUri('https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/models'),
  faceapi.nets.faceLandmark68Net.loadFromUri('https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/models'),
  faceapi.nets.faceRecognitionNet.loadFromUri('https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/models')
]).then(() => {
  console.log('Face-api models loaded. Ready to record attendance with your face.');
  // Add webcam logic here if needed, e.g., startVideo()
});

function startVideo() {
  navigator.mediaDevices.getUserMedia({ video: {} })
    .then(stream => {
      const video = document.createElement('video');
      video.srcObject = stream;
      video.play();
      // Use faceapi.detectAllFaces(video) to detect and record attendance with your face
    })
    .catch(err => console.error('Webcam error:', err));
}

// Call startVideo() on button click if needed
