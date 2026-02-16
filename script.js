// script.js - Unified frontend logic for VisageTrack AI

// 1. Theme Management
const applyTheme = (theme) => {
    if (theme === 'dark') {
        document.documentElement.classList.add('dark');
        document.body.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
        document.body.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
};

// Initialize theme
const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
applyTheme(savedTheme);

// Theme Toggle Listener
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = document.documentElement.classList.contains('dark');
            applyTheme(isDark ? 'light' : 'dark');
            feather.replace();
        });
    }
    feather.replace();
});

// 2. Login Logic
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const role = document.querySelector('input[name="role"]:checked').value;
        const errorEl = document.getElementById('login-error');
        const submitBtn = document.getElementById('login-btn');

        // Reset UI
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span> Signing In...';

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
                window.location.href = data.role === 'admin' ? '/admin' : '/dashboard';
            } else {
                errorEl.textContent = data.message || 'Login failed. Please check your credentials.';
                errorEl.classList.remove('hidden');
            }
        } catch (err) {
            console.error('Login error:', err);
            errorEl.textContent = 'Connection error. Please try again later.';
            errorEl.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Sign In to Dashboard</span>';
            feather.replace();
        }
    });
}

// 3. Camera & Recognition Logic
let activeStream = null;

async function startWebcam(videoId) {
    const video = document.getElementById(videoId);
    if (!video) return;

    try {
        activeStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720, facingMode: 'user' }
        });
        video.srcObject = activeStream;
        const status = document.getElementById('status');
        if (status) status.textContent = 'Camera active';
    } catch (err) {
        console.error('Error accessing webcam:', err);
        const status = document.getElementById('status');
        if (status) status.innerHTML = '<span class="text-red-500">Error: Could not access webcam.</span>';
    }
}

async function recordAttendance() {
    const video = document.getElementById('video');
    const status = document.getElementById('status');
    const clockInBtn = document.getElementById('clock-in-btn');

    if (!video || !clockInBtn) return;

    clockInBtn.disabled = true;
    const originalBtnText = clockInBtn.innerHTML;
    clockInBtn.innerHTML = '<span class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span> Verifying...';
    status.textContent = 'Capturing and verifying...';

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    try {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
        const formData = new FormData();
        formData.append('image', blob, 'capture.jpg');

        const token = localStorage.getItem('jwt_token');
        const response = await fetch('/api/recognize', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            status.innerHTML = `<span class="text-emerald-500 font-bold">${data.message}</span>`;
            clockInBtn.innerHTML = '<i data-feather="check-circle" class="mr-2"></i> Attendance Recorded!';
            clockInBtn.classList.remove('bg-primary-600', 'hover:bg-primary-700');
            clockInBtn.classList.add('bg-emerald-600');
            feather.replace();
        } else {
            status.innerHTML = `<span class="text-red-500">${data.message}</span>`;
            clockInBtn.disabled = false;
            clockInBtn.innerHTML = originalBtnText;
        }
    } catch (err) {
        console.error('Recognition error:', err);
        status.innerHTML = '<span class="text-red-500">Connection error. Try again.</span>';
        clockInBtn.disabled = false;
        clockInBtn.innerHTML = originalBtnText;
    }
}

async function enrollFace() {
    const video = document.getElementById('video');
    const status = document.getElementById('status');
    const enrollBtn = document.getElementById('enroll-btn');
    const name = document.getElementById('name')?.value;
    const email = document.getElementById('email')?.value;

    if (!video || !enrollBtn || !name || !email) {
        alert('Please fill in all details first.');
        return;
    }

    enrollBtn.disabled = true;
    const originalBtnText = enrollBtn.innerHTML;
    status.textContent = 'Starting enrollment...';

    const images = [];
    const captureCount = 10;

    try {
        for (let i = 1; i <= captureCount; i++) {
            status.textContent = `Capturing frame ${i}/${captureCount}...`;
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);

            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
            images.push(blob);

            // Wait a bit between captures
            await new Promise(r => setTimeout(r, 300));
        }

        status.textContent = 'Processing and uploading...';
        const formData = new FormData();
        formData.append('name', name);
        formData.append('email', email);
        images.forEach((blob, idx) => {
            formData.append(`image${idx + 1}`, blob, `frame${idx + 1}.jpg`);
        });

        const token = localStorage.getItem('jwt_token');
        const response = await fetch('/api/enroll', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            status.innerHTML = `<span class="text-emerald-500 font-bold">${data.message}</span>`;
            enrollBtn.innerHTML = '<i data-feather="check-circle" class="mr-2"></i> Enrolled Successfully!';
            enrollBtn.classList.add('bg-emerald-600');
            feather.replace();
        } else {
            status.innerHTML = `<span class="text-red-500">${data.message}</span>`;
            enrollBtn.disabled = false;
            enrollBtn.innerHTML = originalBtnText;
        }
    } catch (err) {
        console.error('Enrollment error:', err);
        status.innerHTML = '<span class="text-red-500">Enrollment failed. Try again.</span>';
        enrollBtn.disabled = false;
        enrollBtn.innerHTML = originalBtnText;
    }
}

// Attach listeners for camera pages
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('video')) {
        startWebcam('video');
    }

    const clockInBtn = document.getElementById('clock-in-btn');
    if (clockInBtn) {
        clockInBtn.addEventListener('click', recordAttendance);
    }

    const enrollBtn = document.getElementById('enroll-btn');
    if (enrollBtn) {
        enrollBtn.addEventListener('click', enrollFace);
    }
});

// 4. Logs Logic
async function fetchAndDisplayLogs() {
    const logsContainer = document.getElementById('logs');
    if (!logsContainer) return;

    try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch('/api/admin/attendance', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        if (response.ok) {
            if (data.logs && data.logs.length > 0) {
                logsContainer.innerHTML = data.logs.map(log => `
                    <div class="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                        <div class="flex items-center space-x-4">
                            <div class="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600">
                                <i data-feather="user"></i>
                            </div>
                            <div>
                                <p class="font-semibold text-slate-900 dark:text-white">${log.name}</p>
                                <p class="text-sm text-slate-500">${new Date(log.timestamp).toLocaleString()}</p>
                            </div>
                        </div>
                        <div class="px-3 py-1 rounded-full text-xs font-medium ${
                            log.status === 'present' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                        }">
                            ${log.status.toUpperCase()}
                        </div>
                    </div>
                `).join('');
                feather.replace();
            } else {
                logsContainer.innerHTML = '<p class="text-center text-slate-500 py-8">No attendance logs found.</p>';
            }
        } else {
            logsContainer.innerHTML = `<p class="text-center text-red-500 py-8">${data.message || 'Error fetching logs'}</p>`;
        }
    } catch (err) {
        console.error('Error fetching logs:', err);
        logsContainer.innerHTML = '<p class="text-center text-red-500 py-8">Connection error. Could not load logs.</p>';
    }
}

// Attach log fetcher
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('logs')) {
        fetchAndDisplayLogs();
    }
});
