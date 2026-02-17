// components/navbar.js
class CustomNavbar extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <nav class="custom-navbar bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 transition-colors duration-300">
        <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <a href="/" class="text-2xl font-bold text-primary-600 hover:text-primary-700 transition">
            VisageTrack AI
          </a>

          <!-- Desktop Menu -->
          <ul class="hidden md:flex items-center space-x-8">
            <li><a href="/" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Home</a></li>
            <li><a href="/attendance" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Attendance</a></li>
            <li><a href="/enroll" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Enroll</a></li>
            <li><a href="/dashboard" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Dashboard</a></li>
            <li><a href="/admin" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Admin</a></li>
            <li>
              <button id="logout-btn" class="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition flex items-center gap-2">
                <i data-feather="log-out" class="w-4 h-4"></i>
                Logout
              </button>
            </li>
          </ul>

          <!-- Mobile Menu Button -->
          <button id="mobile-menu-btn" class="md:hidden p-2 text-slate-600 dark:text-slate-300">
            <i data-feather="menu"></i>
          </button>
        </div>

        <!-- Mobile Menu -->
        <div id="mobile-menu" class="hidden md:hidden border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
          <ul class="px-6 py-4 space-y-4">
            <li><a href="/" class="block text-slate-700 dark:text-slate-300">Home</a></li>
            <li><a href="/attendance" class="block text-slate-700 dark:text-slate-300">Attendance</a></li>
            <li><a href="/enroll" class="block text-slate-700 dark:text-slate-300">Enroll</a></li>
            <li><a href="/dashboard" class="block text-slate-700 dark:text-slate-300">Dashboard</a></li>
            <li><a href="/admin" class="block text-slate-700 dark:text-slate-300">Admin</a></li>
            <li>
              <button id="mobile-logout-btn" class="w-full text-left text-red-600 flex items-center gap-2">
                <i data-feather="log-out" class="w-4 h-4"></i>
                Logout
              </button>
            </li>
          </ul>
        </div>
      </nav>
    `;

    // Handle logout
    const handleLogout = async () => {
      try {
        await fetch('/api/logout', { method: 'POST' });
        localStorage.removeItem('jwt_token');
        window.location.href = '/';
      } catch (err) {
        console.error("Logout failed:", err);
        localStorage.removeItem('jwt_token');
        window.location.href = '/';
      }
    };

    this.querySelector('#logout-btn')?.addEventListener('click', handleLogout);
    this.querySelector('#mobile-logout-btn')?.addEventListener('click', handleLogout);

    // Toggle mobile menu
    const menuBtn = this.querySelector('#mobile-menu-btn');
    const menu = this.querySelector('#mobile-menu');
    menuBtn?.addEventListener('click', () => {
      menu?.classList.toggle('hidden');
    });

    feather.replace();
  }
}

customElements.define('custom-navbar', CustomNavbar);
