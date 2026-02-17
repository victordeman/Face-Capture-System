// Initialize Feather icons
feather.replace();

// Theme toggle logic (integrated into body)
if (localStorage.getItem('theme') === 'dark') {
  document.body.classList.add('dark');
}

// Global functions for actions
async function deleteUser(id) {
  if (!confirm("Are you sure you want to delete this user and all their logs?")) return;
  try {
    const token = localStorage.getItem('jwt_token');
    const response = await fetch(`/api/admin/users/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    alert(data.message);
    if (response.ok) loadAdminDashboard();
  } catch (err) {
    console.error("Delete failed:", err);
  }
}

async function deleteLog(id) {
  if (!confirm("Delete this log?")) return;
  try {
    const token = localStorage.getItem('jwt_token');
    const response = await fetch(`/api/admin/attendance/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    if (response.ok) loadAdminDashboard();
  } catch (err) {
    console.error("Delete failed:", err);
  }
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
        localStorage.setItem('user_role', data.role);
        console.log('Login successful:', data.message);
        window.location.href = data.role === 'admin' ? '/admin' : '/dashboard';
      } else {
        alert(data.message || 'Login failed');
      }
    } catch (err) {
      alert('Error connecting to server');
      console.error(err);
    }
  });
}

// Camera helper
async function startCamera(videoElement) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoElement.srcObject = stream;
    console.log("Camera started successfully.");
  } catch (err) {
    console.error("Error accessing camera:", err);
    alert("Could not access camera. Ensure you are on HTTPS and have given permissions.");
  }
}

// Record Attendance (on attendance.html)
async function recordAttendance(video, status, clockInBtn) {
  clockInBtn.disabled = true;
  status.textContent = 'Capturing and verifying...';

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
    status.innerHTML = response.ok
      ? `<span class="text-emerald-600 font-bold">${data.message}</span>`
      : `<span class="text-red-600">${data.message}</span>`;

    if (response.ok) {
      clockInBtn.innerHTML = '<i data-feather="check-circle"></i> Success!';
      clockInBtn.classList.add('bg-emerald-600');
      feather.replace();
    } else {
      clockInBtn.disabled = false;
      if (response.status === 401) {
        alert("Session expired. Please login again.");
        window.location.href = '/';
      }
    }
  } catch (err) {
    status.textContent = 'Error connecting to server.';
    clockInBtn.disabled = false;
    console.error(err);
  }
}

const clockInBtn = document.getElementById('clock-in-btn');
if (clockInBtn) {
  const video = document.getElementById('video');
  const status = document.getElementById('status');
  startCamera(video);
  clockInBtn.addEventListener('click', () => recordAttendance(video, status, clockInBtn));
}

// Enroll Face Logic
const enrollBtn = document.getElementById('enroll-btn');
if (enrollBtn) {
  const video = document.getElementById('video');
  const status = document.getElementById('status');
  startCamera(video);

  enrollBtn.addEventListener('click', async () => {
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    if (!name || !email) return alert("Fill name and email");

    enrollBtn.disabled = true;
    status.textContent = 'Capturing...';

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));

    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);
    formData.append('image1', blob, 'enroll.jpg');

    try {
      const token = localStorage.getItem('jwt_token');
      const response = await fetch('/api/enroll', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await response.json();
      if (response.ok) {
        status.innerHTML = `<span class="text-emerald-600 font-bold">Enrollment Successful!</span>`;
        enrollBtn.innerHTML = 'Enrolled';
      } else {
        status.innerHTML = `<span class="text-red-600">${data.message}</span>`;
        enrollBtn.disabled = false;
      }
    } catch (err) {
      status.textContent = 'Error.';
      enrollBtn.disabled = false;
    }
  });
}

// Fetch and display logs
async function loadLogs() {
  const container = document.getElementById('logs');
  if (!container) return;

  try {
    const token = localStorage.getItem('jwt_token');
    if (!token) return;

    const response = await fetch('/api/logs', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    console.log("Attendance logs received:", data.logs?.length || 0);

    if (response.ok && data.logs && data.logs.length > 0) {
      const isAdmin = localStorage.getItem('user_role') === 'admin';
      container.innerHTML = data.logs.map(log => `
        <div class="p-4 bg-white dark:bg-slate-800 rounded-xl flex justify-between items-center border border-slate-100 dark:border-slate-700 shadow-sm">
          <div>
            <p class="font-bold text-slate-900 dark:text-white">${log.name}</p>
            <p class="text-sm text-slate-500">${new Date(log.timestamp).toLocaleString()}</p>
          </div>
          <div class="flex items-center gap-3">
            <span class="px-3 py-1 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 rounded-full text-xs font-bold uppercase tracking-wider">Present</span>
            ${isAdmin ? `<button onclick="deleteLog(${log.id})" class="p-2 text-slate-400 hover:text-red-600 transition"><i data-feather="trash-2" class="w-4 h-4"></i></button>` : ''}
          </div>
        </div>
      `).join('');
      feather.replace();
    } else {
      container.innerHTML = `
        <div class="text-center py-10">
          <div class="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
            <i data-feather="calendar"></i>
          </div>
          <p class="text-slate-500 font-medium">No attendance records found.</p>
          <p class="text-sm text-slate-400 mt-1">Clock in to see your logs here.</p>
        </div>
      `;
      feather.replace();
    }
  } catch (err) {
    console.error("Error loading logs:", err);
    container.innerHTML = `<p class="text-center text-red-500 py-4">Error loading data.</p>`;
  }
}

// Admin Dashboard Loader
async function loadAdminDashboard() {
  const userTable = document.getElementById('user-table-body');
  if (!userTable) return; // Only run on admin page

  const token = localStorage.getItem('jwt_token');
  if (!token) return window.location.href = '/';

  try {
    // Load Stats
    const statsRes = await fetch('/api/admin/stats', { headers: { 'Authorization': `Bearer ${token}` } });
    const statsData = await statsRes.json();
    if (statsRes.ok) {
      document.getElementById('stat-users').textContent = statsData.user_count;
      document.getElementById('stat-logs').textContent = statsData.log_count;
    }

    // Load Users
    const usersRes = await fetch('/api/admin/users', { headers: { 'Authorization': `Bearer ${token}` } });
    const usersData = await usersRes.json();
    if (usersRes.ok) {
      userTable.innerHTML = usersData.users.map(u => `
        <tr>
          <td class="py-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 font-bold">
                ${u.name[0]}
              </div>
              <div>
                <p class="font-medium">${u.name}</p>
                <p class="text-xs text-slate-500">${u.email}</p>
              </div>
            </div>
          </td>
          <td class="py-4">
            <span class="px-2 py-1 ${u.role === 'admin' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'} rounded text-[10px] font-bold uppercase tracking-tighter">
              ${u.role}
            </span>
          </td>
          <td class="py-4">
            <button onclick="deleteUser(${u.id})" class="p-2 text-slate-400 hover:text-red-600 transition">
              <i data-feather="user-x" class="w-4 h-4"></i>
            </button>
          </td>
        </tr>
      `).join('') || '<tr><td colspan="3" class="text-center py-4">No users.</td></tr>';
      feather.replace();
    }

    // Load Logs
    loadLogs();
  } catch (err) {
    console.error("Admin dashboard load failed:", err);
  }
}

// Global init
loadLogs();

console.log('VisageTrack AI Logic Ready.');
