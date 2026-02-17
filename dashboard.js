/**
 * DashboardJS Component
 * Supports Synchronous and Asynchronous data loading.
 * Handles automatic polling for database updates.
 */
class DashboardJS {
    constructor(options = {}) {
        this.mode = options.mode || 'async'; // 'sync' or 'async'
        this.data = options.data || null;
        this.pollInterval = options.pollInterval || 5000;
        this.containers = {
            logs: document.getElementById('logs'),
            present: document.getElementById('stat-present'),
            absent: document.getElementById('stat-absent'),
            userName: document.getElementById('user-name'),
            userRole: document.getElementById('user-role')
        };
        this.timer = null;
    }

    async init() {
        console.log(`Initializing DashboardJS in ${this.mode} mode...`);
        if (this.mode === 'sync' && this.data) {
            this.render(this.data);
        } else {
            await this.refresh();
            this.startPolling();
        }
    }

    async refresh() {
        try {
            const [profile, stats, logs] = await Promise.all([
                this.fetchData('/api/user/profile'),
                this.fetchData('/api/user/stats'),
                this.fetchData('/api/logs')
            ]);

            this.render({ profile, stats, logs });
        } catch (err) {
            console.error("Dashboard refresh failed:", err);
        }
    }

    async fetchData(url) {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }

    render(data) {
        const { profile, stats, logs } = data;

        if (profile && this.containers.userName) {
            this.containers.userName.textContent = `Welcome, ${profile.name}`;
            this.containers.userRole.textContent = `${profile.role.charAt(0).toUpperCase() + profile.role.slice(1)} Dashboard`;
        }

        if (stats) {
            if (this.containers.present) this.containers.present.textContent = stats.present;
            if (this.containers.absent) this.containers.absent.textContent = stats.absent;
        }

        if (logs && this.containers.logs) {
            this.renderLogs(logs);
        }
    }

    renderLogs(logs) {
        this.containers.logs.innerHTML = logs.length ? '' : '<p class="text-slate-500">No logs found.</p>';
        logs.forEach(log => {
            const div = document.createElement('div');
            div.className = "flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-700";
            div.innerHTML = `
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center">
                        <i data-feather="check-circle" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <p class="font-semibold">${log.timestamp}</p>
                        <p class="text-xs text-slate-500">Verified via FaceID</p>
                    </div>
                </div>
                <span class="px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">${log.status.toUpperCase()}</span>
            `;
            this.containers.logs.appendChild(div);
        });
        if (typeof feather !== 'undefined') feather.replace();
    }

    startPolling() {
        if (this.timer) clearInterval(this.timer);
        this.timer = setInterval(() => {
            console.log("Polling for new entries...");
            this.refresh();
        }, this.pollInterval);
    }

    stopPolling() {
        if (this.timer) clearInterval(this.timer);
    }
}

// Export for use in HTML
window.DashboardJS = DashboardJS;
