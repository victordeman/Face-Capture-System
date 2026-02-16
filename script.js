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

    el.classList.remove('hidden', 'text-emerald-500', 'text-red-500', 'text-blue-500');
    const colorClass = type === 'success' ? 'text-emerald-500' : type === 'error' ? 'text-red-500' : 'text-blue-500';
    el.classList.add(colorClass);
    el.textContent = message;
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
            video: { width: 640, height: 480, facingMode: 'user' }
        });
        if (video) video.srcObject = stream;
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

// Admin (admin.html)
const initAdmin = async () => {
    const statsUsers = document.getElementById('stats-users');
    if (!statsUsers) return;

    const loadStats = async () => {
        try {
            const response = await fetch('/api/admin/stats', { headers: getAuthHeader() });
            const data = await response.json();
            if (response.ok) {
                document.getElementById('stats-users').textContent = data.total_users;
                document.getElementById('stats-attendance').textContent = data.total_logs;
            }
        } catch (err) { console.error("Stats error", err); }
    };

    const loadUsers = async () => {
        const tableBody = document.getElementById('users-table-body');
        try {
            const response = await fetch('/api/admin/users', { headers: getAuthHeader() });
            const users = await response.json();
            if (response.ok) {
                tableBody.innerHTML = '';
                users.forEach(user => {
                    const tr = document.createElement('tr');
                    tr.className = "border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors";
                    tr.innerHTML = `
                        <td class="py-4 px-4">
                            <div class="flex items-center gap-3">
                                <div class="user-avatar w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center font-bold text-xs"></div>
                                <span class="user-name font-medium"></span>
                            </div>
                        </td>
                        <td class="user-email py-4 px-4 text-slate-500"></td>
                        <td class="py-4 px-4">
                            <span class="user-role px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-700 text-xs"></span>
                        </td>
                        <td class="py-4 px-4 text-right">
                            <button class="delete-user-btn text-red-500 hover:text-red-700 p-2">
                                <i data-feather="trash-2" class="w-4 h-4"></i>
                            </button>
                        </td>
                    `;
                    tr.querySelector('.user-avatar').textContent = user.name ? user.name.charAt(0) : '?';
                    tr.querySelector('.user-name').textContent = user.name || 'Unknown';
                    tr.querySelector('.user-email').textContent = user.email || '';
                    tr.querySelector('.user-role').textContent = user.role || '';
                    tr.querySelector('.delete-user-btn').addEventListener('click', () => window.deleteUser(user.id));
                    tableBody.appendChild(tr);
                });
                if (typeof feather !== 'undefined') feather.replace();
            }
        } catch (err) { console.error("Users error", err); }
    };

    window.deleteUser = async (id) => {
        if (!confirm('Are you sure you want to delete this user?')) return;
        try {
            const response = await fetch(`/api/admin/users/${id}`, {
                method: 'DELETE',
                headers: getAuthHeader()
            });
            if (response.ok) {
                loadUsers();
                loadStats();
            }
        } catch (err) { alert("Delete failed"); }
    };

    loadStats();
    loadUsers();
};

// Enrollment (enroll.html)
const initEnroll = async () => {
    const enrollForm = document.getElementById('enroll-form');
    if (!enrollForm) return;

    const video = document.getElementById('video');
    const statusId = 'status';
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    await startCamera('video', statusId);

    enrollForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const role = document.getElementById('role').value;

        enrollForm.querySelector('button[type="submit"]').disabled = true;
        progressContainer.classList.remove('hidden');

        const images = [];
        for (let i = 1; i <= 10; i++) {
            showStatus(statusId, `Capturing image ${i}/10...`, "info");
            const percent = i * 10;
            progressBar.style.width = `${percent}%`;
            progressText.textContent = `${percent}%`;

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.95));
            images.push(blob);
            await new Promise(r => setTimeout(r, 300)); // Small delay between captures
        }

        showStatus(statusId, "Uploading and processing...", "info");
        const formData = new FormData();
        formData.append('name', name);
        formData.append('email', email);
        formData.append('password', password);
        formData.append('role', role);
        images.forEach((blob, i) => formData.append(`image${i+1}`, blob, `img${i+1}.jpg`));

        try {
            const response = await fetch('/api/enroll', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (response.ok) {
                showStatus(statusId, "Enrollment successful!", "success");
                setTimeout(() => window.location.href = '/', 2000);
            } else {
                showStatus(statusId, data.message || "Enrollment failed", "error");
                enrollForm.querySelector('button[type="submit"]').disabled = false;
            }
        } catch (err) {
            showStatus(statusId, "Connection error", "error");
            enrollForm.querySelector('button[type="submit"]').disabled = false;
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
