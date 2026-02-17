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

// Helper to get auth headers
function getAuthHeaders(headers = {}) {
  const token = localStorage.getItem('jwt_token');
  if (token && token !== 'null' && token !== 'undefined') {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// Record Attendance (on attendance.html)
async function recordAttendance(video, status, clockInBtn) {
  clockInBtn.disabled = true;
  status.textContent = 'Capturing and verifying your face...';

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);

  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  const formData = new FormData();
  formData.append('image', blob, 'capture.jpg');

  try {
    const response = await fetch('/api/recognize', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData
    });
    const data = await response.json();
    const message = data.message || (response.ok ? 'Success!' : 'Unknown error');
    status.innerHTML = response.ok ? `<span class="text-emerald-600 font-bold">${message}</span>` : `<span class="text-red-600">${message}</span>`;
    if (response.ok) {
      clockInBtn.innerHTML = '<i data-feather="check-circle"></i> Attendance Recorded!';
      clockInBtn.classList.add('bg-emerald-600');
    } else {
      clockInBtn.disabled = false;
    }
  } catch (err) {
    status.textContent = 'Error connecting to server. Try again.';
    clockInBtn.disabled = false;
    console.error(err);
  }
}

// If on attendance page, attach listener
const clockInBtn = document.getElementById('clock-in-btn');
if (clockInBtn) {
  const video = document.getElementById('video');
  const status = document.getElementById('status');
  const statusText = document.getElementById('status-text');

  // Initialize camera for attendance
  async function initAttendanceCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      if (statusText) statusText.textContent = 'Camera ready';
    } catch (err) {
      console.error('Camera error:', err);
      if (statusText) statusText.textContent = 'Camera error or permission denied';
    }
  }
  initAttendanceCamera();

  clockInBtn.addEventListener('click', () => recordAttendance(video, status, clockInBtn));
}

// Fetch and display logs (on admin or dashboard pages)
const logsContainer = document.getElementById('logs');
if (logsContainer) {
  async function fetchLogs() {
    try {
      const response = await fetch('/api/logs', {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (response.ok) {
        logsContainer.innerHTML = data.logs.map(log => `
          <div class="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 flex justify-between items-center">
            <div>
              <p class="font-bold">${log.name}</p>
              <p class="text-sm text-slate-500">${log.timestamp}</p>
            </div>
            <span class="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold uppercase">${log.status}</span>
          </div>
        `).join('') || '<p class="text-center text-slate-500 py-8">No attendance logs found yet.</p>';
      } else if (response.status === 401 || response.status === 422) {
        localStorage.removeItem('jwt_token');
        if (window.location.pathname !== '/') window.location.href = '/';
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
    }
  }
  fetchLogs();
}

// Enroll Face (on enroll.html) - Moved to inline script in enroll.html for page-specific logic

// Remove face-api promise to avoid load error (optional library not used in core logic)
console.log('Ready to record attendance with your face. Face-api not loaded due to CDN issues.');
