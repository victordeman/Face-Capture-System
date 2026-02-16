// Initialize Feather icons
feather.replace();

// Theme toggle
const themeToggle = document.getElementById('theme-toggle');
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
  });
}

// Load saved theme
if (localStorage.getItem('theme') === 'dark') {
  document.body.classList.add('dark');
}

// Login form (on index.html)
const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const role = document.querySelector('input[name="role"]:checked').value;
    const email = loginForm.querySelector('input[type="text"]').value;
    const password = loginForm.querySelector('input[type="password"]').value;

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role })
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('jwt_token', data.access_token);
        alert('Logged in! Redirecting...');
        window.location.href = role === 'admin' ? '/admin' : '/dashboard';
      } else {
        alert(data.message || 'Login failed');
      }
    } catch (err) {
      alert('Error logging in');
      console.error(err);
    }
  });
}

// Camera Management
async function startCamera(videoElement) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
    videoElement.srcObject = stream;
    const status = document.getElementById('status');
    if (status) {
      status.textContent = 'Camera active. Position your face and click record.';
      status.className = 'text-center p-4 rounded-xl mb-6 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium transition-all duration-300';
    }
  } catch (err) {
    console.error("Camera access error:", err);
    const status = document.getElementById('status');
    if (status) {
      status.textContent = 'Camera access denied. Please enable your camera to continue.';
      status.className = 'text-center p-4 rounded-xl mb-6 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium transition-all duration-300';
    }
  }
}

// Record Attendance (on attendance.html)
async function recordAttendance(video, status, clockInBtn) {
  clockInBtn.disabled = true;
  const originalBtnContent = clockInBtn.innerHTML;
  clockInBtn.innerHTML = '<i data-feather="loader" class="animate-spin"></i> <span>Verifying...</span>';
  feather.replace();

  status.textContent = 'Capturing and verifying your face...';
  status.className = 'text-center p-4 rounded-xl mb-6 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 font-medium transition-all duration-300';

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);

  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  const formData = new FormData();
  formData.append('image', blob, 'capture.jpg');

  try {
    const token = localStorage.getItem('jwt_token');
    const response = await fetch('/api/recognize', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    const data = await response.json();
    const message = data.message || (response.ok ? 'Success!' : 'Unknown error');

    if (response.ok) {
      status.innerHTML = `<i data-feather="check-circle" class="inline-block mr-2"></i> ${message}`;
      status.className = 'text-center p-4 rounded-xl mb-6 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 font-bold transition-all duration-300';
      clockInBtn.innerHTML = '<i data-feather="check-circle"></i> <span>Attendance Recorded!</span>';
      clockInBtn.className = 'w-full py-4 rounded-xl bg-emerald-600 text-white font-semibold shadow-lg transition-all flex items-center justify-center gap-3';
      feather.replace();
    } else {
      status.innerHTML = `<i data-feather="alert-circle" class="inline-block mr-2"></i> ${message}`;
      status.className = 'text-center p-4 rounded-xl mb-6 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-bold transition-all duration-300';
      clockInBtn.disabled = false;
      clockInBtn.innerHTML = originalBtnContent;
      feather.replace();
    }
  } catch (err) {
    console.error("Fetch error:", err);
    status.innerHTML = '<i data-feather="wifi-off" class="inline-block mr-2"></i> Connection error. Try again.';
    status.className = 'text-center p-4 rounded-xl mb-6 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-bold transition-all duration-300';
    clockInBtn.disabled = false;
    clockInBtn.innerHTML = originalBtnContent;
    feather.replace();
  }
}

// Page-specific initialization
document.addEventListener('DOMContentLoaded', () => {
  const clockInBtn = document.getElementById('clock-in-btn');
  const video = document.getElementById('video');
  const status = document.getElementById('status');

  if (clockInBtn && video) {
    startCamera(video);
    clockInBtn.addEventListener('click', () => recordAttendance(video, status, clockInBtn));
  }
});

// Enroll Face (on enroll.html) - Moved to inline script in enroll.html for page-specific logic

// Remove face-api promise to avoid load error (optional library not used in core logic)
console.log('Ready to record attendance with your face. Face-api not loaded due to CDN issues.');
