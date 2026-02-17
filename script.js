// Initialize Feather icons
if (typeof feather !== 'undefined') {
    feather.replace();
}

/**
 * Shared Helpers
 */

// Theme Management
const initTheme = () => {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = document.body.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
    }
    if (localStorage.getItem('theme') === 'dark' ||
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.body.classList.add('dark');
    }
};

// UI Feedback
const showStatus = (elementId, message, type = 'info') => {
    const el = document.getElementById(elementId);
    if (!el) return;

    // Handle nested status-text if present
    const target = el.querySelector('#status-text') || el;

    target.classList.remove('hidden', 'text-emerald-500', 'text-red-500', 'text-blue-500', 'text-emerald-600', 'text-red-600');
    let colorClass = 'text-blue-500';
    if (type === 'success') colorClass = 'text-emerald-600';
    else if (type === 'error') colorClass = 'text-red-600';

    target.classList.add(colorClass);
    target.textContent = message;
};

// JWT Management
const getAuthHeader = () => {
    const token = localStorage.getItem('jwt_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Camera Management
const startCamera = async (videoElementId, statusElementId) => {
    const video = document.getElementById(videoElementId);
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720, facingMode: 'user' }
        });
        if (video) video.srcObject = stream;
        showStatus(statusElementId, "Camera ready", "success");
        return stream;
    } catch (err) {
        console.error("Camera error:", err);
        showStatus(statusElementId, "Camera access denied or not found.", "error");
        return null;
    }
};

/**
 * Page Specific Logic
 */

// Login (index.html)
const initLogin = () => {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const role = document.querySelector('input[name="role"]:checked')?.value || 'employee';
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const errorEl = 'login-error';

        showStatus(errorEl, "Signing in...", "info");

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, role })
            });
            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('jwt_token', data.access_token);
                localStorage.setItem('user_role', role);
                window.location.href = role === 'admin' ? '/admin' : '/dashboard';
            } else {
                showStatus(errorEl, data.message || "Login failed", "error");
            }
        } catch (err) {
            showStatus(errorEl, "Connection error", "error");
        }
    });
};

// Attendance (attendance.html)
const initAttendance = async () => {
    const clockInBtn = document.getElementById('clock-in-btn');
    if (!clockInBtn) return;

    const video = document.getElementById('video');
    const statusId = 'status';

    await startCamera('video', statusId);

    clockInBtn.addEventListener('click', async () => {
        clockInBtn.disabled = true;
        showStatus(statusId, "Analyzing face...", "info");

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.95));
        const formData = new FormData();
        formData.append('image', blob, 'capture.jpg');

        try {
            const response = await fetch('/api/recognize', {
                method: 'POST',
                headers: getAuthHeader(),
                body: formData
            });
            const data = await response.json();

            if (response.ok) {
                showStatus(statusId, data.message || "Attendance recorded!", "success");
                clockInBtn.innerHTML = '<i data-feather="check"></i> Success';
                if (typeof feather !== 'undefined') feather.replace();
            } else {
                showStatus(statusId, data.message || "Recognition failed", "error");
                clockInBtn.disabled = false;
            }
        } catch (err) {
            showStatus(statusId, "Server error", "error");
            clockInBtn.disabled = false;
        }
    });
};

// Dashboard (dashboard.html)
const initDashboard = async () => {
    const logsContainer = document.getElementById('logs');
    if (!logsContainer) return;

    const refreshBtn = document.getElementById('refresh-logs');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => fetchAndDisplayLogs());
    }

    window.fetchAndDisplayLogs = async () => {
        try {
            const response = await fetch('/api/logs', {
                headers: getAuthHeader()
            });
            const logs = await response.json();

            if (response.ok) {
                logsContainer.innerHTML = logs.length ? '' : '<p class="text-slate-500">No logs found.</p>';
                logs.forEach(log => {
                    const div = document.createElement('div');
                    div.className = "flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-700";
                    div.innerHTML = `
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center">
                                <i data-feather="check-circle" class="w-5 h-5"></i>
                            </div>
                            <div>
                                <p class="log-timestamp font-semibold"></p>
                                <p class="text-xs text-slate-500">Verified via FaceID</p>
                            </div>
                        </div>
                        <span class="px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">Present</span>
                    `;
                    div.querySelector('.log-timestamp').textContent = log.timestamp;
                    logsContainer.appendChild(div);
                });
                if (typeof feather !== 'undefined') feather.replace();
            } else if (response.status === 401) {
                window.location.href = '/';
            }
        } catch (err) {
            logsContainer.innerHTML = '<p class="text-red-500">Failed to load logs.</p>';
        }
    };

    fetchAndDisplayLogs();
};

// Admin (admin.html)
const initAdmin = async () => {
    const statsUsers = document.getElementById('stat-total-users');
    if (!statsUsers) return;

    const refreshBtn = document.getElementById('refresh-admin');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadData());
    }

    window.loadData = async () => {
        const token = localStorage.getItem('jwt_token');
        if (!token) { window.location.href = '/'; return; }

        try {
            // Stats
            const statsRes = await fetch('/api/admin/stats', { headers: getAuthHeader() });
            if (statsRes.ok) {
                const stats = await statsRes.json();
                document.getElementById('stat-total-users').textContent = stats.total_users;
                document.getElementById('stat-today-attendance').textContent = stats.today_attendance || stats.total_logs;
            }

            // Users
            const usersRes = await fetch('/api/admin/users', { headers: getAuthHeader() });
            if (usersRes.ok) {
                const data = await usersRes.json();
                const users = Array.isArray(data) ? data : data.users;
                const list = document.getElementById('users-list');
                list.innerHTML = '';
                users.forEach(user => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="px-6 py-4">
                            <div class="user-name font-medium text-slate-900 dark:text-white"></div>
                            <div class="user-email text-sm text-slate-500"></div>
                        </td>
                        <td class="px-6 py-4 text-right">
                            <button class="delete-user-btn text-red-500 hover:text-red-700 transition-colors p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20">
                                <i data-feather="trash-2" class="w-5 h-5"></i>
                            </button>
                        </td>
                    `;
                    tr.querySelector('.user-name').textContent = user.name;
                    tr.querySelector('.user-email').textContent = user.email;
                    tr.querySelector('.delete-user-btn').addEventListener('click', () => deleteUser(user.id));
                    list.appendChild(tr);
                });
            }

            // Logs
            const logsRes = await fetch('/api/admin/attendance', { headers: getAuthHeader() });
            if (logsRes.ok) {
                const data = await logsRes.json();
                const logs = Array.isArray(data) ? data : data.logs;
                const list = document.getElementById('logs-list');
                list.innerHTML = '';
                logs.forEach(log => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="log-name px-6 py-4 font-medium text-slate-900 dark:text-white"></td>
                        <td class="log-timestamp px-6 py-4 text-slate-500 text-sm"></td>
                        <td class="px-6 py-4 text-right">
                            <span class="log-status px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"></span>
                        </td>
                    `;
                    tr.querySelector('.log-name').textContent = log.name;
                    tr.querySelector('.log-timestamp').textContent = log.timestamp;
                    tr.querySelector('.log-status').textContent = (log.status || 'Present').toUpperCase();
                    list.appendChild(tr);
                });
            }

            const lastUpdated = document.getElementById('last-updated');
            if (lastUpdated) lastUpdated.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
            if (typeof feather !== 'undefined') feather.replace();

        } catch (err) { console.error('Error loading admin data:', err); }
    };

    window.deleteUser = async (userId) => {
        if (!confirm('Are you sure you want to delete this user? All their attendance records will also be removed.')) return;
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'DELETE',
                headers: getAuthHeader()
            });
            if (response.ok) loadData();
            else {
                const data = await response.json();
                alert(data.message || 'Error deleting user');
            }
        } catch (err) { alert('Connection error'); }
    };

    loadData();
};

// Enrollment (enroll.html)
const initEnroll = async () => {
    const enrollBtn = document.getElementById('enroll-btn');
    if (!enrollBtn) return;

    const video = document.getElementById('video');
    const statusId = 'status';
    const captureOverlay = document.getElementById('capture-overlay');

    await startCamera('video', statusId);

    enrollBtn.addEventListener('click', async () => {
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;

        if (!name || !email) {
            alert('Please fill in your name and email first.');
            return;
        }

        enrollBtn.disabled = true;
        if (captureOverlay) captureOverlay.classList.remove('opacity-0');
        if (captureOverlay) captureOverlay.classList.add('opacity-100');

        const images = [];
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');

        for (let i = 1; i <= 10; i++) {
            showStatus(statusId, `Capturing face: ${i}/10`, "info");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
            images.push(blob);
            await new Promise(r => setTimeout(r, 300));
        }

        if (captureOverlay) captureOverlay.classList.remove('opacity-100');
        if (captureOverlay) captureOverlay.classList.add('opacity-0');
        showStatus(statusId, "Processing and enrolling...", "info");

        const formData = new FormData();
        formData.append('name', name);
        formData.append('email', email);
        images.forEach((blob, i) => formData.append(`image${i+1}`, blob, `face_${i+1}.jpg`));

        try {
            const response = await fetch('/api/enroll', {
                method: 'POST',
                headers: getAuthHeader(),
                body: formData
            });
            const data = await response.json();
            if (response.ok) {
                showStatus(statusId, "Enrollment successful! Redirecting...", "success");
                setTimeout(() => window.location.href = '/dashboard', 2000);
            } else {
                showStatus(statusId, data.message || "Enrollment failed", "error");
                enrollBtn.disabled = false;
            }
        } catch (err) {
            showStatus(statusId, "Connection error", "error");
            enrollBtn.disabled = false;
        }
    });
};

// Global Initialization
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initLogin();
    initAttendance();
    initDashboard();
    initAdmin();
    initEnroll();
});
